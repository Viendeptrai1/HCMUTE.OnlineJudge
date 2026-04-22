"""Unit test ProblemService dùng FakeRepository (in-memory).

Minh hoạ lợi ích Dependency Inversion: service không cần DB thật để test.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from app.modules.problems.models import Difficulty, Problem
from app.modules.problems.schemas import ProblemCreate, ProblemUpdate
from app.modules.problems.service import ProblemService
from app.shared.exceptions import EntityNotFoundError


class FakeProblemRepository:
    """In-memory repo, tuân thủ `ProblemRepository` Protocol."""

    def __init__(self) -> None:
        self._store: dict[UUID, Problem] = {}

    async def get(self, id: UUID) -> Problem | None:
        return self._store.get(id)

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[Problem]:
        return list(self._store.values())[offset : offset + limit]

    async def add(self, entity: Problem) -> Problem:
        if entity.id is None:
            entity.id = uuid4()
        self._store[entity.id] = entity
        return entity

    async def update(self, entity: Problem, data: dict[str, object]) -> Problem:
        for key, value in data.items():
            setattr(entity, key, value)
        return entity

    async def delete(self, id: UUID) -> None:
        self._store.pop(id, None)


pytestmark = pytest.mark.asyncio


async def test_create_then_get() -> None:
    service = ProblemService(FakeProblemRepository())
    created = await service.create_problem(ProblemCreate(title="A+B"))
    fetched = await service.get_problem(created.id)
    assert fetched.title == "A+B"


async def test_get_missing_raises() -> None:
    service = ProblemService(FakeProblemRepository())
    with pytest.raises(EntityNotFoundError):
        await service.get_problem(uuid4())


async def test_update() -> None:
    service = ProblemService(FakeProblemRepository())
    created = await service.create_problem(ProblemCreate(title="A", difficulty=Difficulty.EASY))
    updated = await service.update_problem(
        created.id,
        ProblemUpdate(title="A (rev)", difficulty=Difficulty.HARD),
    )
    assert updated.title == "A (rev)"
    assert updated.difficulty == Difficulty.HARD


async def test_delete_then_get_raises() -> None:
    service = ProblemService(FakeProblemRepository())
    created = await service.create_problem(ProblemCreate(title="X"))
    await service.delete_problem(created.id)
    with pytest.raises(EntityNotFoundError):
        await service.get_problem(created.id)
