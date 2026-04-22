"""Smoke test LocalSandbox (compile + run thật bằng subprocess)."""

from __future__ import annotations

import pytest
from worker.sandbox import LocalSandbox

pytestmark = pytest.mark.asyncio


async def test_python_run_ok() -> None:
    """Python: không compile, run trực tiếp, in echo stdin."""
    sb = LocalSandbox()
    compiled = await sb.compile("import sys\nprint(sys.stdin.read().strip())\n", "python")
    try:
        assert compiled.ok, compiled.stderr
        result = await sb.run(compiled, "hello", time_limit_ms=2000, memory_limit_kb=262144)
        assert result.exit_code == 0
        assert result.stdout.strip() == "hello"
    finally:
        sb.cleanup(compiled)


async def test_cpp_compile_error() -> None:
    sb = LocalSandbox()
    compiled = await sb.compile("int main(() { return 0; }", "cpp")
    try:
        assert not compiled.ok
        assert compiled.stderr
    finally:
        sb.cleanup(compiled)


async def test_cpp_run_ok() -> None:
    sb = LocalSandbox()
    src = """
    #include <iostream>
    int main(){ int a,b; std::cin>>a>>b; std::cout<<a+b; return 0; }
    """
    compiled = await sb.compile(src, "cpp")
    try:
        assert compiled.ok, compiled.stderr
        result = await sb.run(compiled, "2 3\n", time_limit_ms=2000, memory_limit_kb=262144)
        assert result.exit_code == 0
        assert result.stdout.strip() == "5"
    finally:
        sb.cleanup(compiled)


async def test_run_timeout() -> None:
    sb = LocalSandbox()
    compiled = await sb.compile("import time\nwhile True: time.sleep(0.1)\n", "python")
    try:
        result = await sb.run(compiled, "", time_limit_ms=200, memory_limit_kb=262144)
        assert result.timed_out
    finally:
        sb.cleanup(compiled)
