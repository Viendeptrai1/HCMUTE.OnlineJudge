"""Service cho Tag."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.tags.models import Tag
from app.modules.tags.repository import TagRepository
from app.modules.tags.schemas import TagCreate
from app.shared.exceptions import DomainError


class TagSlugTakenError(DomainError):
    pass


class TagService:
    def __init__(self, repo: TagRepository) -> None:
        self._repo = repo

    async def list_all(self) -> Sequence[Tag]:
        return await self._repo.list_all()

    async def create(self, data: TagCreate) -> Tag:
        existing = await self._repo.get_by_slug(data.slug)
        if existing is not None:
            raise TagSlugTakenError(f"Tag '{data.slug}' đã tồn tại")
        return await self._repo.add(Tag(slug=data.slug, name=data.name))

    async def get_or_create(self, slug: str, name: str | None = None) -> Tag:
        existing = await self._repo.get_by_slug(slug)
        if existing is not None:
            return existing
        return await self._repo.add(Tag(slug=slug, name=name or slug))

    async def list_for_problem(self, problem_id: UUID) -> Sequence[Tag]:
        return await self._repo.list_for_problem(problem_id)

    async def set_for_problem(self, problem_id: UUID, slugs: Sequence[str]) -> None:
        """Nhận list slugs (chuỗi CSV từ form), tự tạo tag chưa có, set lại m2m."""
        clean = [s.strip().lower() for s in slugs if s.strip()]
        tag_ids: list[UUID] = []
        for slug in clean:
            tag = await self.get_or_create(slug)
            tag_ids.append(tag.id)
        await self._repo.set_for_problem(problem_id, tag_ids)

    async def list_problem_ids_for_slug(self, slug: str) -> Sequence[UUID]:
        return await self._repo.list_problem_ids_for_slug(slug)

    async def list_tags_for_problems(
        self, problem_ids: Sequence[UUID]
    ) -> dict[UUID, list[Tag]]:
        return await self._repo.list_tags_for_problems(problem_ids)
