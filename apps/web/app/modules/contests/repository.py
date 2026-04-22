"""Repositories cho Contest / ContestProblem / ContestRegistration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contests.models import (
    Contest,
    ContestProblem,
    ContestRegistration,
)


class ContestRepository(Protocol):
    async def get(self, id: UUID) -> Contest | None: ...
    async def get_by_slug(self, slug: str) -> Contest | None: ...
    async def list_all(self) -> Sequence[Contest]: ...
    async def add(self, entity: Contest) -> Contest: ...
    async def update(self, entity: Contest, data: dict) -> Contest: ...
    async def delete(self, id: UUID) -> None: ...


class SqlAlchemyContestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: UUID) -> Contest | None:
        return await self._session.get(Contest, id)

    async def get_by_slug(self, slug: str) -> Contest | None:
        stmt = select(Contest).where(Contest.slug == slug)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_all(self) -> Sequence[Contest]:
        stmt = select(Contest).order_by(Contest.start_at.desc())
        return (await self._session.execute(stmt)).scalars().all()

    async def add(self, entity: Contest) -> Contest:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity: Contest, data: dict) -> Contest:
        for k, v in data.items():
            setattr(entity, k, v)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> None:
        entity = await self._session.get(Contest, id)
        if entity is not None:
            await self._session.delete(entity)
            await self._session.flush()


class ContestProblemRepository(Protocol):
    async def list_by_contest(self, contest_id: UUID) -> Sequence[ContestProblem]: ...
    async def get(self, id: UUID) -> ContestProblem | None: ...
    async def add(self, entity: ContestProblem) -> ContestProblem: ...
    async def delete(self, id: UUID) -> None: ...


class SqlAlchemyContestProblemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_contest(self, contest_id: UUID) -> Sequence[ContestProblem]:
        stmt = (
            select(ContestProblem)
            .where(ContestProblem.contest_id == contest_id)
            .order_by(ContestProblem.order_index.asc(), ContestProblem.letter.asc())
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def get(self, id: UUID) -> ContestProblem | None:
        return await self._session.get(ContestProblem, id)

    async def add(self, entity: ContestProblem) -> ContestProblem:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> None:
        entity = await self._session.get(ContestProblem, id)
        if entity is not None:
            await self._session.delete(entity)
            await self._session.flush()


class ContestRegistrationRepository(Protocol):
    async def list_by_contest(self, contest_id: UUID) -> Sequence[ContestRegistration]: ...
    async def get(
        self, contest_id: UUID, user_id: UUID
    ) -> ContestRegistration | None: ...
    async def add(self, entity: ContestRegistration) -> ContestRegistration: ...


class SqlAlchemyContestRegistrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_contest(self, contest_id: UUID) -> Sequence[ContestRegistration]:
        stmt = (
            select(ContestRegistration)
            .where(ContestRegistration.contest_id == contest_id)
            .order_by(ContestRegistration.registered_at.asc())
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def get(
        self, contest_id: UUID, user_id: UUID
    ) -> ContestRegistration | None:
        stmt = select(ContestRegistration).where(
            and_(
                ContestRegistration.contest_id == contest_id,
                ContestRegistration.user_id == user_id,
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, entity: ContestRegistration) -> ContestRegistration:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
