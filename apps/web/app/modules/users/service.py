"""Business logic cho Users: đăng ký + xác thực đăng nhập."""

from __future__ import annotations

from uuid import UUID

from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate
from app.modules.users.security import hash_password, verify_password
from app.shared.exceptions import DomainError, EntityNotFoundError


class UserAlreadyExistsError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class UserService:
    """Use case liên quan tới User.

    Dependency Inversion: phụ thuộc `UserRepository` (Protocol).
    """

    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def register(self, data: UserCreate) -> User:
        if await self._repo.get_by_email(data.email):
            raise UserAlreadyExistsError(f"Email already in use: {data.email}")
        if await self._repo.get_by_username(data.username):
            raise UserAlreadyExistsError(f"Username already taken: {data.username}")
        user = User(
            email=data.email,
            username=data.username,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            is_active=True,
        )
        return await self._repo.add(user)

    async def authenticate(self, identifier: str, password: str) -> User:
        user = await self._repo.get_by_identifier(identifier)
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Invalid credentials")
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")
        return user

    async def get_by_id(self, user_id: UUID) -> User:
        user: User | None = await self._repo.get(user_id)  # type: ignore[attr-defined]
        if user is None:
            raise EntityNotFoundError("User", user_id)
        return user
