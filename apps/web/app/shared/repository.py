"""Generic Repository abstraction (Dependency Inversion).

Service layer phụ thuộc vào Protocol `Repository[T]`, không phụ thuộc trực tiếp
vào SQLAlchemy. Điều này cho phép:

- Thay thế persistence layer (ví dụ in-memory cho test) mà không đụng service.
- Test service với fake repo đơn giản hơn.
- Tuân thủ OCP + DIP trong SOLID.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, Protocol, TypeVar
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.base_model import Base

T = TypeVar("T", bound=Base)


class Repository(Protocol[T]):
    """Contract tối thiểu một repository phải cung cấp."""

    async def get(self, id: UUID) -> T | None: ...

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[T]: ...

    async def add(self, entity: T) -> T: ...

    async def delete(self, id: UUID) -> None: ...


class SqlAlchemyRepository(Generic[T]):
    """Base SQLAlchemy repository — cung cấp CRUD chuẩn cho 1 model.

    Subclass chỉ cần khai báo class attribute `model` và có thể bổ sung
    các query đặc thù của domain (ví dụ `find_by_difficulty`).
    """

    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: UUID) -> T | None:
        return await self.session.get(self.model, id)

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[T]:
        stmt = select(self.model).order_by(self.model.id).limit(limit).offset(offset)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: T, data: dict[str, Any]) -> T:
        for key, value in data.items():
            setattr(entity, key, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> None:
        await self.session.execute(delete(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        await self.session.flush()
