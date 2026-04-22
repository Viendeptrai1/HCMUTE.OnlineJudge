"""Seed dữ liệu mẫu cho môi trường local.

Tạo:
  - 1 educator (edu / edu@hcmute.local / password123)
  - 2 student (alice / bob — password123)
  - 3 bài tập, author = educator

Idempotent: truncate bảng trước khi insert.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "web"))

from app.core.config import get_settings  # noqa: E402
from app.modules.problems.models import Difficulty, Problem  # noqa: E402
from app.modules.users.models import User, UserRole  # noqa: E402
from app.modules.users.security import hash_password  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

PROBLEMS = [
    (
        "A + B",
        """\
# A + B

Cho hai số nguyên `a` và `b`, in ra `a + b`.

## Input
Một dòng chứa hai số nguyên `a, b` (`-10^9 ≤ a, b ≤ 10^9`).

## Output
Một số nguyên duy nhất là `a + b`.

## Ví dụ
```
2 3     →    5
```

Công thức: \\( a + b = c \\)
""",
        1000,
        65536,
        Difficulty.EASY,
    ),
    (
        "Sắp xếp mảng",
        """\
# Sắp xếp mảng

Cho mảng `n` phần tử, in ra mảng đã sắp xếp tăng dần.

## Input
- Dòng 1: `n` (`1 ≤ n ≤ 10^5`)
- Dòng 2: `n` số nguyên

## Output
Mảng đã sắp xếp, cách nhau bởi dấu cách.

Gợi ý: dùng `std::sort` trong C++ hoặc `sorted()` trong Python.
""",
        2000,
        131072,
        Difficulty.MEDIUM,
    ),
    (
        "Đường đi ngắn nhất",
        """\
# Đường đi ngắn nhất (Dijkstra)

Cho đồ thị vô hướng có trọng số không âm gồm `n` đỉnh, `m` cạnh. Tìm độ
dài đường đi ngắn nhất từ đỉnh `s` tới đỉnh `t`.

## Ràng buộc
- \\( 1 \\le n \\le 10^5 \\)
- \\( 0 \\le m \\le 2 \\cdot 10^5 \\)
- Trọng số không âm \\( w \\le 10^9 \\)

## Thuật toán
Dijkstra với heap: độ phức tạp \\( O((n + m) \\log n) \\).
""",
        3000,
        262144,
        Difficulty.HARD,
    ),
]


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        await session.execute(text("TRUNCATE TABLE submissions, problems, users CASCADE"))

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

        for title, statement, tl, ml, diff in PROBLEMS:
            session.add(
                Problem(
                    title=title,
                    statement_md=statement,
                    time_limit_ms=tl,
                    memory_limit_kb=ml,
                    difficulty=diff,
                    author_id=edu.id,
                )
            )

        await session.commit()

    await engine.dispose()
    print(
        "✓ Seed xong. Tài khoản demo:\n"
        "  - edu   / password123 (educator)\n"
        "  - alice / password123 (student)\n"
        "  - bob   / password123 (student)"
    )


if __name__ == "__main__":
    asyncio.run(main())
