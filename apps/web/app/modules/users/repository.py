"""Repository cho User."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import or_, select

from app.modules.users.models import User
from app.shared.repository import SqlAlchemyRepository


class UserRepository(Protocol):
    async def get_by_identifier(self, identifier: str) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_username(self, username: str) -> User | None: ...

    async def add(self, entity: User) -> User: ...

    async def update(self, entity: User, updates: dict) -> User: ...


class SqlAlchemyUserRepository(SqlAlchemyRepository[User]):
    model = User

    async def get_by_identifier(self, identifier: str) -> User | None:
        """Lookup user bằng email hoặc username — hữu ích cho login."""

        stmt = select(User).where(or_(User.email == identifier, User.username == identifier))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
