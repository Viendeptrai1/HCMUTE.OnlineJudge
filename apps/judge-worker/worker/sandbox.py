"""Sandbox — compile + run source code thật trên máy local.

Phase 1 chưa có cách ly cgroup/isolate. `LocalSandbox` chạy trực tiếp bằng
`subprocess` với `timeout` (giới hạn thời gian) và `resource` (giới hạn bộ nhớ
trên POSIX — chỉ dùng khi khả dụng). Khi chuyển sang production, `LocalSandbox`
sẽ được thay bởi `IsolateSandbox` cách ly thật trong container.

Contract giữa JudgeWorker và Sandbox:
- `compile(source, language, workdir) -> CompileResult`: biên dịch source, trả
  về binary path (có thể là file .py) + stderr (nếu CE).
- `run(binary_path, stdin, time_limit_ms, memory_limit_kb) -> RunResult`: chạy
  binary với stdin đã cho, trả stdout/stderr/time/mem/exit_code.
"""

from __future__ import annotations

import asyncio
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from worker.languages import LANGUAGES


@dataclass(slots=True)
class CompileResult:
    ok: bool
    binary_path: str  # File để `run` thực thi (có thể là .py với Python)
    stderr: str
    workdir: str  # Thư mục tạm để cleanup sau khi chấm xong


@dataclass(slots=True)
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    time_used_ms: int
    memory_used_kb: int
    timed_out: bool = False


class Sandbox(Protocol):
    async def compile(self, source: str, language: str) -> CompileResult: ...

    async def run(
        self,
        compiled: CompileResult,
        stdin_data: str,
        time_limit_ms: int,
        memory_limit_kb: int,
    ) -> RunResult: ...

    def cleanup(self, compiled: CompileResult) -> None: ...


class LocalSandbox:
    """Chạy subprocess trực tiếp. Không cách ly network/FS thật nhưng có:

    * `RLIMIT_CPU` — kernel kill khi CPU quá giới hạn (hardcap).
    * `RLIMIT_AS`  — giới hạn virtual memory.
    * `RLIMIT_FSIZE` — giới hạn dung lượng file ghi (tránh fill disk).
    * `RLIMIT_NPROC` — giới hạn số process (chống fork bomb).
    * Output cap = 2 MB — truncate stdout/stderr để tránh OOM khi load vào DB.
    * Sanitized env — chỉ giữ PATH + LANG để đảm bảo determinism.
    * `setsid()` → chạy trong process group mới, timeout kill toàn nhóm.
    """

    COMPILE_TIMEOUT_SEC = 15
    OUTPUT_CAP_BYTES = 2 * 1024 * 1024  # 2 MB
    NPROC_LIMIT = 64
    FSIZE_LIMIT_BYTES = 16 * 1024 * 1024  # 16 MB

    async def compile(self, source: str, language: str) -> CompileResult:
        spec = LANGUAGES.get(language)
        if spec is None:
            return CompileResult(ok=False, binary_path="", stderr=f"unsupported language: {language}", workdir="")

        workdir = tempfile.mkdtemp(prefix="oj_sub_")
        src_path = str(Path(workdir) / f"source{spec.source_ext}")
        Path(src_path).write_text(source, encoding="utf-8")

        bin_path = str(Path(workdir) / "program")

        if spec.compile_cmd is None:
            # Ngôn ngữ thông dịch — chạy thẳng source, "binary" = source path.
            return CompileResult(ok=True, binary_path=src_path, stderr="", workdir=workdir)

        cmd = [part.replace("{src}", src_path).replace("{bin}", bin_path) for part in spec.compile_cmd]
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=self.COMPILE_TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired:
            return CompileResult(
                ok=False,
                binary_path="",
                stderr=f"compile timed out after {self.COMPILE_TIMEOUT_SEC}s",
                workdir=workdir,
            )
        except FileNotFoundError as e:
            return CompileResult(ok=False, binary_path="", stderr=f"compiler not found: {e}", workdir=workdir)

        if proc.returncode != 0:
            raw = proc.stderr or proc.stdout
            # Che workdir tạm (VD `/var/folders/.../oj_sub_xxx/source.cpp`)
            # để không lộ đường dẫn hệ thống xuống client.
            cleaned = raw.replace(workdir + "/", "").replace(src_path, "source" + spec.source_ext)
            return CompileResult(ok=False, binary_path="", stderr=cleaned, workdir=workdir)
        return CompileResult(ok=True, binary_path=bin_path, stderr="", workdir=workdir)

    async def run(
        self,
        compiled: CompileResult,
        stdin_data: str,
        time_limit_ms: int,
        memory_limit_kb: int,
    ) -> RunResult:
        spec_lang = _infer_language_from_path(compiled.binary_path)
        spec = LANGUAGES[spec_lang] if spec_lang else None

        if spec is None or spec.compile_cmd is None:
            # Python: python3 source.py
            cmd = (
                [part.replace("{src}", compiled.binary_path).replace("{bin}", compiled.binary_path)
                 for part in (spec.run_cmd if spec else ["python3", compiled.binary_path])]
            )
        else:
            cmd = [part.replace("{bin}", compiled.binary_path).replace("{src}", compiled.binary_path)
                   for part in spec.run_cmd]

        # Cộng thêm 500ms buffer cho subprocess setup + GC.
        timeout_sec = (time_limit_ms / 1000.0) + 0.5

        cpu_limit_sec = max(1, int((time_limit_ms + 999) / 1000) + 1)
        env = _sanitized_env()

        def _target() -> tuple[str, str, int, int, int, bool]:
            """Chạy subprocess với rlimit + process-group → kill clean khi TLE."""
            start = time.monotonic()
            preexec = (
                _rlimit_preexec(
                    memory_limit_kb=memory_limit_kb,
                    cpu_sec=cpu_limit_sec,
                    nproc=self.NPROC_LIMIT,
                    fsize=self.FSIZE_LIMIT_BYTES,
                )
                if sys.platform != "win32"
                else None
            )
            try:
                proc = subprocess.run(
                    cmd,
                    input=stdin_data,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    preexec_fn=preexec,  # type: ignore[arg-type]
                    env=env,
                    start_new_session=sys.platform != "win32",
                )
            except subprocess.TimeoutExpired as e:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                stdout = _truncate(e.stdout or "", self.OUTPUT_CAP_BYTES)
                return (stdout, "timed out", 124, elapsed_ms, 0, True)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            stdout = _truncate(proc.stdout, self.OUTPUT_CAP_BYTES)
            stderr = _truncate(proc.stderr, self.OUTPUT_CAP_BYTES)
            # Lưu ý: không đo mem chính xác được trên macOS mà không phải root;
            # trả 0, Phase sau dùng cgroup v2 để đo thật.
            return (stdout, stderr, proc.returncode, elapsed_ms, 0, False)

        stdout, stderr, rc, elapsed_ms, mem_kb, timed_out = await asyncio.to_thread(_target)

        if not timed_out and elapsed_ms > time_limit_ms:
            # Completed nhưng vượt time limit mềm ⇒ TLE.
            return RunResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=rc,
                time_used_ms=elapsed_ms,
                memory_used_kb=mem_kb,
                timed_out=True,
            )

        return RunResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=rc,
            time_used_ms=elapsed_ms,
            memory_used_kb=mem_kb,
            timed_out=timed_out,
        )

    def cleanup(self, compiled: CompileResult) -> None:
        if compiled.workdir and os.path.isdir(compiled.workdir):
            shutil.rmtree(compiled.workdir, ignore_errors=True)


def _infer_language_from_path(path: str) -> str | None:
    ext = Path(path).suffix
    for lang_key, spec in LANGUAGES.items():
        if spec.source_ext == ext:
            return lang_key
    # Không có ext khớp ⇒ coi là binary C++.
    return "cpp"


def _rlimit_preexec(
    memory_limit_kb: int,
    cpu_sec: int,
    nproc: int,
    fsize: int,
):  # type: ignore[no-untyped-def]
    """Trả về preexec_fn set các RLIMIT_* trước khi exec.

    Không raise nếu một limit nào đó không set được (khác biệt giữa Linux/macOS).
    """
    mem_bytes = memory_limit_kb * 1024

    def _apply() -> None:
        _safe_set(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        _safe_set(resource.RLIMIT_CPU, (cpu_sec, cpu_sec))
        _safe_set(resource.RLIMIT_FSIZE, (fsize, fsize))
        if hasattr(resource, "RLIMIT_NPROC"):
            _safe_set(resource.RLIMIT_NPROC, (nproc, nproc))
        # Không cho core dump — tránh fill disk khi crash.
        _safe_set(resource.RLIMIT_CORE, (0, 0))

    return _apply


def _safe_set(key: int, limits: tuple[int, int]) -> None:
    try:
        resource.setrlimit(key, limits)
    except (ValueError, OSError):
        pass


def _sanitized_env() -> dict[str, str]:
    """Env sạch cho subprocess — chỉ giữ biến tối thiểu để đảm bảo determinism."""
    keep = ("PATH", "LANG", "LC_ALL", "HOME", "PYTHONUNBUFFERED")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("LANG", "C.UTF-8")
    return env


def _truncate(s: str, cap_bytes: int) -> str:
    """Cắt chuỗi tại `cap_bytes` bytes (đếm UTF-8), kèm ký hiệu `[…truncated]`."""
    b = s.encode("utf-8")
    if len(b) <= cap_bytes:
        return s
    cut = b[:cap_bytes].decode("utf-8", errors="ignore")
    return cut + "\n[...output truncated...]"
