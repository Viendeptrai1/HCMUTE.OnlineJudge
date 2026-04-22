"""Sandbox abstraction — giúp dev local chạy được mà không cần isolate.

Phase 1 `LocalSandbox` là stub có heuristic nhẹ để pipeline end-to-end trông
sống động hơn (AC/WA/TLE/CE dựa vào keyword trong source). Phase 2 sẽ thay
bằng `IsolateSandbox` chấm thật trong cgroup Linux.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    time_used_ms: int
    memory_used_kb: int
    timed_out: bool = False


class Sandbox(Protocol):
    """Interface mỗi loại sandbox phải cung cấp."""

    async def compile(self, source_path: str, language: str) -> RunResult: ...

    async def run(
        self,
        binary_path: str,
        stdin_path: str,
        time_limit_ms: int,
        memory_limit_kb: int,
    ) -> RunResult: ...


class LocalSandbox:
    """Stub sandbox cho Phase 1 — không cách ly thật, chỉ giả lập verdict.

    Heuristic dùng `source_path` như nội dung code (vì `JudgeWorker` truyền
    `row.source_code` vào). Điều này đủ để demo UI mà không cần compiler.
    """

    _COMPILE_HINTS = ("main", "def ", "class ", "public static", "void ", "int ")

    async def compile(self, source_path: str, language: str) -> RunResult:
        await asyncio.sleep(0.4)
        source = source_path or ""
        if not any(hint in source for hint in self._COMPILE_HINTS):
            return RunResult(
                stdout="",
                stderr=f"[{language}] compilation error: no entry point detected",
                exit_code=1,
                time_used_ms=0,
                memory_used_kb=0,
            )
        return RunResult(stdout="", stderr="", exit_code=0, time_used_ms=0, memory_used_kb=0)

    async def run(
        self,
        binary_path: str,
        stdin_path: str,
        time_limit_ms: int,
        memory_limit_kb: int,
    ) -> RunResult:
        await asyncio.sleep(0.8)

        # Heuristic dựa vào nội dung (JudgeWorker truyền source vào compile — ở run
        # chỉ có path stub). Chọn verdict ngẫu nhiên có trọng số để trông "thật".
        roll = random.random()
        if roll < 0.7:
            return RunResult(
                stdout="accepted",
                stderr="",
                exit_code=0,
                time_used_ms=random.randint(20, min(time_limit_ms - 1, 400)),
                memory_used_kb=random.randint(1024, min(memory_limit_kb, 8192)),
            )
        if roll < 0.85:
            return RunResult(
                stdout="",
                stderr="wrong answer on test 3",
                exit_code=0,
                time_used_ms=random.randint(20, 200),
                memory_used_kb=random.randint(1024, 4096),
            )
        if roll < 0.95:
            return RunResult(
                stdout="",
                stderr="execution timed out",
                exit_code=124,
                time_used_ms=time_limit_ms,
                memory_used_kb=2048,
                timed_out=True,
            )
        return RunResult(
            stdout="",
            stderr="runtime error (exit 139)",
            exit_code=139,
            time_used_ms=random.randint(10, 100),
            memory_used_kb=2048,
        )
