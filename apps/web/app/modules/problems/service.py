"""Business logic cho Problem — thuần Python, không biết FastAPI/SQLAlchemy."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.problems.models import Problem
from app.modules.problems.repository import ProblemRepository
from app.modules.problems.schemas import ProblemCreate, ProblemUpdate
from app.shared.exceptions import EntityNotFoundError


class ProblemService:
    """Orchestrate các use case liên quan tới Problem.

    Dependency Inversion: nhận `ProblemRepository` qua constructor — có thể
    truyền impl thật (SQLAlchemy) hay fake (test in-memory).
    """

    def __init__(self, repo: ProblemRepository) -> None:
        self._repo = repo

    async def list_problems(self, limit: int = 50, offset: int = 0) -> Sequence[Problem]:
        return await self._repo.list(limit=limit, offset=offset)

    async def get_problem(self, id: UUID) -> Problem:
        problem = await self._repo.get(id)
        if problem is None:
            raise EntityNotFoundError("Problem", id)
        return problem

    async def create_problem(self, data: ProblemCreate, author_id: UUID | None = None) -> Problem:
        entity = Problem(**data.model_dump(), author_id=author_id)
        return await self._repo.add(entity)

    async def update_problem(self, id: UUID, data: ProblemUpdate) -> Problem:
        entity = await self.get_problem(id)
        return await self._repo.update(entity, data.model_dump())

    async def delete_problem(self, id: UUID) -> None:
        await self.get_problem(id)
        await self._repo.delete(id)
