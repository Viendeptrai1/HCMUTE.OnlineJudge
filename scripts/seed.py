"""Seed dữ liệu mẫu cho môi trường local.

Tạo:
  - 1 educator (edu / password123)
  - 2 student  (alice, bob / password123)
  - 3 bài dễ + mỗi bài 4 testcases (1 sample public, 3 hidden)

Idempotent: truncate bảng trước khi insert.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "web"))

from app.core.config import get_settings  # noqa: E402
from app.modules.courses.models import (  # noqa: E402
    Course,
    CourseProblem,
    CourseRole,
    Enrollment,
)
from app.modules.problems.models import Difficulty, Problem  # noqa: E402
from app.modules.tags.models import Tag, problem_tags  # noqa: E402
from app.modules.testcases.models import Testcase  # noqa: E402
from app.modules.users.models import User, UserRole  # noqa: E402
from app.modules.users.security import hash_password  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402


@dataclass
class ProblemSeed:
    title: str
    statement: str
    time_limit_ms: int
    memory_limit_kb: int
    difficulty: Difficulty
    testcases: list[tuple[str, str, bool, int]]  # (input, expected, is_sample, score)
    tags: list[str]  # list slug
    editorial: str = ""


PROBLEMS: list[ProblemSeed] = [
    ProblemSeed(
        title="A + B",
        statement="""\
# A + B

Cho hai số nguyên $a$ và $b$, in ra $a + b$.

## Input
Một dòng chứa hai số nguyên $a, b$ $(-10^9 \\le a, b \\le 10^9)$.

## Output
Một số nguyên duy nhất là $a + b$.

## Ghi chú
Công thức: $a + b = c$.

Gợi ý code C++:
```cpp
#include <iostream>
int main(){
    long long a, b; std::cin >> a >> b;
    std::cout << a + b;
}
```

Gợi ý code Python:
```python
a, b = map(int, input().split())
print(a + b)
```
""",
        time_limit_ms=1000,
        memory_limit_kb=65536,
        difficulty=Difficulty.EASY,
        testcases=[
            ("2 3\n", "5\n", True, 25),
            ("0 0\n", "0\n", False, 25),
            ("-1000000000 1000000000\n", "0\n", False, 25),
            ("-7 15\n", "8\n", False, 25),
        ],
        tags=["math", "implementation"],
        editorial=(
            "## Hướng dẫn\n\n"
            "Chỉ cần đọc 2 số và in tổng. Trong C++ dùng `long long` để tránh tràn.\n"
        ),
    ),
    ProblemSeed(
        title="Tổng mảng",
        statement="""\
# Tổng mảng

Cho mảng gồm $n$ số nguyên, tính tổng của các phần tử.

## Input
- Dòng 1: số nguyên $n$ $(1 \\le n \\le 10^5)$.
- Dòng 2: $n$ số nguyên cách nhau bởi dấu cách $(-10^4 \\le a_i \\le 10^4)$.

## Output
Một số nguyên là $\\sum_{i=1}^{n} a_i$.
""",
        time_limit_ms=1000,
        memory_limit_kb=65536,
        difficulty=Difficulty.EASY,
        testcases=[
            ("5\n1 2 3 4 5\n", "15\n", True, 25),
            ("1\n42\n", "42\n", False, 25),
            ("4\n-1 -2 -3 -4\n", "-10\n", False, 25),
            ("6\n10 20 30 -5 -5 0\n", "50\n", False, 25),
        ],
        tags=["array", "implementation"],
        editorial=(
            "## Hướng dẫn\n\n"
            "Duyệt qua mảng và cộng dồn. Độ phức tạp $O(n)$.\n"
        ),
    ),
    ProblemSeed(
        title="Tìm max",
        statement="""\
# Tìm max

Cho mảng gồm $n$ số nguyên, in ra giá trị **lớn nhất**.

## Input
- Dòng 1: $n$ $(1 \\le n \\le 10^5)$.
- Dòng 2: $n$ số nguyên $(-10^9 \\le a_i \\le 10^9)$.

## Output
Một số nguyên là $\\max(a_1, a_2, \\ldots, a_n)$.
""",
        time_limit_ms=1000,
        memory_limit_kb=65536,
        difficulty=Difficulty.EASY,
        testcases=[
            ("5\n3 1 4 1 5\n", "5\n", True, 25),
            ("1\n-7\n", "-7\n", False, 25),
            ("4\n-5 -10 -3 -8\n", "-3\n", False, 25),
            ("6\n1000000000 999999999 500 0 -1 7\n", "1000000000\n", False, 25),
        ],
        tags=["array", "greedy"],
        editorial=(
            "## Hướng dẫn\n\n"
            "Khởi tạo biến `ans` bằng $-\\infty$ (hoặc phần tử đầu) rồi duyệt.\n"
        ),
    ),
]


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE course_problems, enrollments, courses, "
                "problem_tags, tags, testcases, submissions, problems, users CASCADE"
            )
        )

        edu = User(
            email="edu@hcmute.local",
            username="edu",
            password_hash=hash_password("password123"),
            full_name="Giảng viên mẫu",
            role=UserRole.EDUCATOR,
            is_active=True,
        )
        alice = User(
            email="alice@hcmute.local",
            username="alice",
            password_hash=hash_password("password123"),
            full_name="Nguyễn Thị Alice",
            role=UserRole.STUDENT,
            is_active=True,
        )
        bob = User(
            email="bob@hcmute.local",
            username="bob",
            password_hash=hash_password("password123"),
            full_name="Trần Văn Bob",
            role=UserRole.STUDENT,
            is_active=True,
        )
        session.add_all([edu, alice, bob])
        await session.flush()

        # Gom set tag unique → tạo Tag trước.
        all_slugs = sorted({s for ps in PROBLEMS for s in ps.tags})
        tag_by_slug: dict[str, Tag] = {}
        for slug in all_slugs:
            tag = Tag(slug=slug, name=slug)
            session.add(tag)
            tag_by_slug[slug] = tag
        await session.flush()

        problems: list[Problem] = []
        for ps in PROBLEMS:
            prob = Problem(
                title=ps.title,
                statement_md=ps.statement,
                editorial_md=ps.editorial,
                time_limit_ms=ps.time_limit_ms,
                memory_limit_kb=ps.memory_limit_kb,
                difficulty=ps.difficulty,
                author_id=edu.id,
            )
            session.add(prob)
            await session.flush()
            problems.append(prob)

            for idx, (inp, out, is_sample, score) in enumerate(ps.testcases, start=1):
                session.add(
                    Testcase(
                        problem_id=prob.id,
                        order_index=idx,
                        input_text=inp,
                        expected_output=out,
                        is_sample=is_sample,
                        score=score,
                    )
                )

            # m2m tags cho problem
            for slug in ps.tags:
                await session.execute(
                    problem_tags.insert().values(
                        problem_id=prob.id, tag_id=tag_by_slug[slug].id
                    )
                )

        # Course demo: lớp CTDL do edu phụ trách, alice + bob enrolled,
        # 2 bài đầu được gán (A + B, Tổng mảng).
        course = Course(
            code="CTT-DEMO-01",
            name="Cấu trúc dữ liệu và giải thuật (DEMO)",
            semester="HK1 2025-2026",
            description=(
                "Lớp học demo cho môi trường local. "
                "Chứa 2 bài tập khởi động.\n\n"
                "- Mỗi tuần có 1 bài cần nộp trước deadline.\n"
                "- Nộp trễ vẫn chấm nhưng hiển thị **quá hạn**."
            ),
            educator_id=edu.id,
        )
        session.add(course)
        await session.flush()

        session.add_all(
            [
                Enrollment(course_id=course.id, user_id=alice.id, role_in_course=CourseRole.STUDENT),
                Enrollment(course_id=course.id, user_id=bob.id, role_in_course=CourseRole.STUDENT),
            ]
        )
        for idx, prob in enumerate(problems[:2], start=1):
            session.add(
                CourseProblem(
                    course_id=course.id,
                    problem_id=prob.id,
                    deadline=None,
                    weight=10,
                    order_index=idx,
                )
            )

        await session.commit()

    await engine.dispose()
    print(
        "✓ Seed xong. Tài khoản demo:\n"
        "  - edu   / password123 (educator)\n"
        "  - alice / password123 (student)\n"
        "  - bob   / password123 (student)\n"
        f"  Đã tạo {len(PROBLEMS)} bài + tổng "
        f"{sum(len(p.testcases) for p in PROBLEMS)} testcases.\n"
        "  Đã tạo 1 course demo (CTT-DEMO-01) với 2 assignments + alice/bob enrolled."
    )


if __name__ == "__main__":
    asyncio.run(main())
