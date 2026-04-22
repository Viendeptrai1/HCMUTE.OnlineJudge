"""Smoke test LocalSandbox stub."""

from __future__ import annotations

import random

import pytest
from worker.sandbox import LocalSandbox

pytestmark = pytest.mark.asyncio


async def test_local_sandbox_compile_ok_with_main() -> None:
    sb = LocalSandbox()
    result = await sb.compile("int main() { return 0; }", "cpp")
    assert result.exit_code == 0


async def test_local_sandbox_compile_error_when_no_entry() -> None:
    sb = LocalSandbox()
    result = await sb.compile("", "cpp")
    assert result.exit_code != 0


async def test_local_sandbox_run_deterministic_ac(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force roll < 0.7 → kết quả AC."""

    monkeypatch.setattr(random, "random", lambda: 0.1)
    monkeypatch.setattr(random, "randint", lambda a, b: (a + b) // 2)

    sb = LocalSandbox()
    result = await sb.run("/tmp/bin", "/dev/null", 1000, 65536)
    assert result.exit_code == 0
    assert not result.timed_out
    assert result.stdout == "accepted"


async def test_local_sandbox_run_deterministic_tle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(random, "random", lambda: 0.9)
    monkeypatch.setattr(random, "randint", lambda a, b: (a + b) // 2)

    sb = LocalSandbox()
    result = await sb.run("/tmp/bin", "/dev/null", 500, 65536)
    assert result.timed_out
    assert result.time_used_ms == 500
