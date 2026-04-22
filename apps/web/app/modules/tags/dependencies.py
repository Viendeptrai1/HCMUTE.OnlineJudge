"""DI cho Tag."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.tags.repository import SqlAlchemyTagRepository, TagRepository
from app.modules.tags.service import TagService


def get_tag_repository(session: AsyncSession = Depends(get_session)) -> TagRepository:
    return SqlAlchemyTagRepository(session)


def get_tag_service(repo: TagRepository = Depends(get_tag_repository)) -> TagService:
    return TagService(repo)
