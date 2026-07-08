"""Registry các ngôn ngữ được hỗ trợ (compile & run command).

Phase 1: chỉ hỗ trợ C++17 + Python 3. Thêm ngôn ngữ mới ⇒ thêm `LanguageSpec`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LanguageSpec:
    name: str
    source_ext: str
    compile_cmd: list[str] | None  # None = không cần compile
    run_cmd: list[str]


LANGUAGES: dict[str, LanguageSpec] = {
    "cpp": LanguageSpec(
        name="C++17",
        source_ext=".cpp",
        compile_cmd=["g++", "-O2", "-std=c++17", "{src}", "-o", "{bin}"],
        run_cmd=["{bin}"],
    ),
    "python": LanguageSpec(
        name="Python 3",
        source_ext=".py",
        compile_cmd=None,
        run_cmd=["python3", "{src}"],
    ),
    "c": LanguageSpec(
        name="C",
        source_ext=".c",
        compile_cmd=["gcc", "-O2", "{src}", "-o", "{bin}", "-lm"],
        run_cmd=["{bin}"],
    ),
    "java": LanguageSpec(
        name="Java",
        source_ext=".java",
        compile_cmd=["javac", "{src}"],
        run_cmd=["java", "-cp", "{workdir}", "Main"],
    ),
}
