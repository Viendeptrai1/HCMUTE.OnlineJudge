"""Repository cho Problem: Protocol + impl SQLAlchemy."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, or_, select

from app.modules.problems.models import Difficulty, Problem
from app.shared.repository import SqlAlchemyRepository


class ProblemRepository(Protocol):
    """Contract cho Problem persistence — service chỉ biết tới interface này."""

    async def get(self, id: UUID) -> Problem | None: ...

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[Problem]: ...

    async def search(
        self,
        *,
        q: str | None = None,
        difficulty: Difficulty | None = None,
        problem_ids: Sequence[UUID] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Problem], int]: ...

    async def add(self, entity: Problem) -> Problem: ...

    async def update(self, entity: Problem, data: dict[str, object]) -> Problem: ...

    async def delete(self, id: UUID) -> None: ...


class SqlAlchemyProblemRepository(SqlAlchemyRepository[Problem]):
    model = Problem

    async def search(
        self,
        *,
        q: str | None = None,
        difficulty: Difficulty | None = None,
        problem_ids: Sequence[UUID] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Problem], int]:
        filters = []
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    Problem.title.ilike(pattern),
                    Problem.statement_md.ilike(pattern),
                )
            )
        if difficulty is not None:
            filters.append(Problem.difficulty == difficulty)
        if problem_ids is not None:
            # Nếu filter theo tag mà list rỗng → guarantee zero results.
            if not problem_ids:
                return [], 0
            filters.append(Problem.id.in_(problem_ids))

        count_stmt = select(func.count(Problem.id))
        list_stmt = select(Problem).order_by(Problem.created_at.desc())

        for f in filters:
            count_stmt = count_stmt.where(f)
            list_stmt = list_stmt.where(f)

        list_stmt = list_stmt.limit(limit).offset(offset)

        total = int((await self.session.execute(count_stmt)).scalar_one() or 0)
        items = (await self.session.execute(list_stmt)).scalars().all()
        return items, total
