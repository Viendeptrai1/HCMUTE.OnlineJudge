"""Repository cho Problem: Protocol + impl SQLAlchemy."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.problems.models import Problem
from app.shared.repository import SqlAlchemyRepository


class ProblemRepository(Protocol):
    """Contract cho Problem persistence — service chỉ biết tới interface này."""

    async def get(self, id: UUID) -> Problem | None: ...

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[Problem]: ...

    async def add(self, entity: Problem) -> Problem: ...

    async def update(self, entity: Problem, data: dict[str, object]) -> Problem: ...

    async def delete(self, id: UUID) -> None: ...


class SqlAlchemyProblemRepository(SqlAlchemyRepository[Problem]):
    model = Problem
