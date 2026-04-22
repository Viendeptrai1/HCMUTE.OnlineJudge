"""Judge orchestrator — compile submission, chấm từng testcase, tính verdict cuối.

Quy tắc verdict (first-fail):
1. Compile fail ⇒ COMPILE_ERROR (không chấm testcase nào).
2. Lặp testcase theo `order_index`:
   - timed_out                 ⇒ TIME_LIMIT_EXCEEDED, dừng.
   - exit_code != 0            ⇒ RUNTIME_ERROR, dừng.
   - stdout != expected (strip)⇒ WRONG_ANSWER, dừng.
3. Hết testcase ⇒ ACCEPTED.

Time/mem báo cáo = max qua các testcase đã chạy tới khi fail (hoặc toàn bộ nếu AC).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from worker.db import TestcaseRow
from worker.sandbox import CompileResult, Sandbox


@dataclass(slots=True)
class JudgeOutcome:
    # Phải khớp với enum `submission_status` trong DB.
    # Values: ACCEPTED, WRONG_ANSWER, TIME_LIMIT, MEMORY_LIMIT, RUNTIME_ERROR,
    # COMPILE_ERROR, INTERNAL_ERROR.
    status: str
    time_used_ms: int
    memory_used_kb: int
    message: str


class Judge:
    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    async def judge(
        self,
        source: str,
        language: str,
        testcases: Sequence[TestcaseRow],
        time_limit_ms: int,
        memory_limit_kb: int,
    ) -> JudgeOutcome:
        compiled = await self._sandbox.compile(source, language)
        try:
            if not compiled.ok:
                return JudgeOutcome(
                    status="COMPILE_ERROR",
                    time_used_ms=0,
                    memory_used_kb=0,
                    message=_truncate(compiled.stderr, 2000),
                )

            if not testcases:
                return JudgeOutcome(
                    status="COMPILE_ERROR",
                    time_used_ms=0,
                    memory_used_kb=0,
                    message="Bài toán chưa có testcase — liên hệ educator.",
                )

            max_time = 0
            max_mem = 0
            for idx, tc in enumerate(testcases, start=1):
                result = await self._sandbox.run(
                    compiled,
                    tc.input_text,
                    time_limit_ms,
                    memory_limit_kb,
                )
                max_time = max(max_time, result.time_used_ms)
                max_mem = max(max_mem, result.memory_used_kb)

                if result.timed_out:
                    return JudgeOutcome(
                        status="TIME_LIMIT",
                        time_used_ms=max_time,
                        memory_used_kb=max_mem,
                        message=f"Test #{idx}: vượt {time_limit_ms}ms",
                    )
                if result.exit_code != 0:
                    return JudgeOutcome(
                        status="RUNTIME_ERROR",
                        time_used_ms=max_time,
                        memory_used_kb=max_mem,
                        message=f"Test #{idx}: exit {result.exit_code}\n{_truncate(result.stderr, 1000)}",
                    )
                if not _output_equal(result.stdout, tc.expected_output):
                    return JudgeOutcome(
                        status="WRONG_ANSWER",
                        time_used_ms=max_time,
                        memory_used_kb=max_mem,
                        message=(
                            f"Test #{idx}: sai đáp án.\n"
                            f"Expected:\n{_truncate(tc.expected_output, 400)}\n"
                            f"Got:\n{_truncate(result.stdout, 400)}"
                        ),
                    )

            return JudgeOutcome(
                status="ACCEPTED",
                time_used_ms=max_time,
                memory_used_kb=max_mem,
                message=f"Đúng {len(testcases)}/{len(testcases)} testcase.",
            )
        finally:
            self._sandbox.cleanup(compiled)


def _output_equal(got: str, expected: str) -> bool:
    """So sánh dung thứ (tolerant): strip trailing whitespace mỗi dòng, bỏ dòng trống cuối."""

    def _norm(s: str) -> list[str]:
        lines = [line.rstrip() for line in s.splitlines()]
        while lines and lines[-1] == "":
            lines.pop()
        return lines

    return _norm(got) == _norm(expected)


def _truncate(text: str, max_len: int) -> str:
    text = text or ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n… (truncated)"


__all__ = ["CompileResult", "Judge", "JudgeOutcome"]
