"""ORM model cho Problem."""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.users.models import User
from app.shared.base_model import Base, TimestampMixin, UUIDMixin


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Problem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "problems"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    statement_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    editorial_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    time_limit_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    memory_limit_kb: Mapped[int] = mapped_column(Integer, nullable=False, default=262144)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="problem_difficulty"),
        nullable=False,
        default=Difficulty.EASY,
    )

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    author: Mapped[User | None] = relationship(User, lazy="joined")
