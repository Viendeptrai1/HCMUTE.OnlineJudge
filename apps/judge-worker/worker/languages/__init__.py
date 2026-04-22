"""Registry các ngôn ngữ lập trình được hỗ trợ (compile & run command)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LanguageSpec:
    name: str
    source_ext: str
    compile_cmd: str | None
    run_cmd: str


LANGUAGES: dict[str, LanguageSpec] = {
    "cpp": LanguageSpec(
        name="C++17",
        source_ext=".cpp",
        compile_cmd="g++ -O2 -std=c++17 {src} -o {bin}",
        run_cmd="{bin}",
    ),
    "c": LanguageSpec(
        name="C",
        source_ext=".c",
        compile_cmd="gcc -O2 {src} -o {bin}",
        run_cmd="{bin}",
    ),
    "python": LanguageSpec(
        name="Python 3.12",
        source_ext=".py",
        compile_cmd=None,
        run_cmd="python3 {src}",
    ),
    "java": LanguageSpec(
        name="Java 17",
        source_ext=".java",
        compile_cmd="javac {src}",
        run_cmd="java -cp {dir} Main",
    ),
}
