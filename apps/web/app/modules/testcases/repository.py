"""Repository cho Testcase."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.testcases.models import Testcase


class TestcaseRepository(Protocol):
    async def list_by_problem(self, problem_id: UUID) -> Sequence[Testcase]: ...
    async def get(self, id: UUID) -> Testcase | None: ...
    async def add(self, entity: Testcase) -> Testcase: ...
    async def update(self, entity: Testcase, data: dict[str, object]) -> Testcase: ...
    async def delete(self, id: UUID) -> None: ...
    async def delete_by_problem(self, problem_id: UUID) -> None: ...


class SqlAlchemyTestcaseRepository:
    """Implementation SQLAlchemy — thuần CRUD, tách khỏi business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_problem(self, problem_id: UUID) -> Sequence[Testcase]:
        stmt = (
            select(Testcase)
            .where(Testcase.problem_id == problem_id)
            .order_by(Testcase.order_index.asc(), Testcase.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get(self, id: UUID) -> Testcase | None:
        return await self._session.get(Testcase, id)

    async def add(self, entity: Testcase) -> Testcase:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity: Testcase, data: dict[str, object]) -> Testcase:
        for key, value in data.items():
            setattr(entity, key, value)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> None:
        entity = await self._session.get(Testcase, id)
        if entity is not None:
            await self._session.delete(entity)
            await self._session.flush()

    async def delete_by_problem(self, problem_id: UUID) -> None:
        await self._session.execute(delete(Testcase).where(Testcase.problem_id == problem_id))
        await self._session.flush()
