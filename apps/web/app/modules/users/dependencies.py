"""Dependency injection cho module Users + auth guard chung cho toàn app."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.users.models import User, UserRole
from app.modules.users.repository import SqlAlchemyUserRepository, UserRepository
from app.modules.users.service import UserService
from app.shared.exceptions import EntityNotFoundError


def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(repo)


async def get_current_user_optional(
    request: Request,
    service: UserService = Depends(get_user_service),
) -> User | None:
    """Trả về User nếu session cookie có `user_id` hợp lệ, ngược lại None."""

    user_id_str: str | None = request.session.get("user_id")
    if not user_id_str:
        return None
    try:
        user_id = UUID(user_id_str)
        return await service.get_by_id(user_id)
    except (ValueError, EntityNotFoundError):
        request.session.pop("user_id", None)
        return None


async def require_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn cần đăng nhập để thực hiện hành động này.",
            headers={"Location": "/auth/login"},
        )
    return user


def require_role(
    *allowed: UserRole,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    async def _check(user: User = Depends(require_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện hành động này.",
            )
        return user

    return _check
