"""Repository cho Tag + association problem_tags."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tags.models import Tag, problem_tags


class TagRepository(Protocol):
    async def list_all(self) -> Sequence[Tag]: ...
    async def get_by_slug(self, slug: str) -> Tag | None: ...
    async def add(self, entity: Tag) -> Tag: ...
    async def list_for_problem(self, problem_id: UUID) -> Sequence[Tag]: ...
    async def set_for_problem(self, problem_id: UUID, tag_ids: Sequence[UUID]) -> None: ...
    async def list_problem_ids_for_slug(self, slug: str) -> Sequence[UUID]: ...
    async def list_tags_for_problems(
        self, problem_ids: Sequence[UUID]
    ) -> dict[UUID, list[Tag]]: ...


class SqlAlchemyTagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> Sequence[Tag]:
        stmt = select(Tag).order_by(Tag.slug)
        return (await self._session.execute(stmt)).scalars().all()

    async def get_by_slug(self, slug: str) -> Tag | None:
        stmt = select(Tag).where(Tag.slug == slug)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, entity: Tag) -> Tag:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def list_for_problem(self, problem_id: UUID) -> Sequence[Tag]:
        stmt = (
            select(Tag)
            .join(problem_tags, problem_tags.c.tag_id == Tag.id)
            .where(problem_tags.c.problem_id == problem_id)
            .order_by(Tag.slug)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def set_for_problem(self, problem_id: UUID, tag_ids: Sequence[UUID]) -> None:
        """Thay thế toàn bộ tags cho 1 problem (idempotent)."""
        await self._session.execute(
            delete(problem_tags).where(problem_tags.c.problem_id == problem_id)
        )
        if tag_ids:
            await self._session.execute(
                insert(problem_tags),
                [{"problem_id": problem_id, "tag_id": tid} for tid in tag_ids],
            )
        await self._session.flush()

    async def list_problem_ids_for_slug(self, slug: str) -> Sequence[UUID]:
        stmt = (
            select(problem_tags.c.problem_id)
            .join(Tag, Tag.id == problem_tags.c.tag_id)
            .where(Tag.slug == slug)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def list_tags_for_problems(
        self, problem_ids: Sequence[UUID]
    ) -> dict[UUID, list[Tag]]:
        if not problem_ids:
            return {}
        stmt = (
            select(problem_tags.c.problem_id, Tag)
            .join(Tag, Tag.id == problem_tags.c.tag_id)
            .where(problem_tags.c.problem_id.in_(problem_ids))
            .order_by(Tag.slug)
        )
        rows = (await self._session.execute(stmt)).all()
        out: dict[UUID, list[Tag]] = {pid: [] for pid in problem_ids}
        for pid, tag in rows:
            out[pid].append(tag)
        return out
