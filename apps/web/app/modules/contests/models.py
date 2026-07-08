"""ORM cho Contest + ContestProblem + ContestRegistration."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.problems.models import Problem
from app.modules.users.models import User
from app.shared.base_model import Base, TimestampMixin, UUIDMixin


class ScoringMode(StrEnum):
    ICPC = "icpc"  # solved count, tie break = penalty (wrong * 20m + first-AC time)
    IOI = "ioi"  # tổng điểm best submission mỗi bài


class ContestVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"  # phải register mới xem được bài + nộp


class Contest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "contests"

    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    scoring_mode: Mapped[ScoringMode] = mapped_column(
        Enum(ScoringMode, name="contest_scoring_mode"),
        nullable=False,
        default=ScoringMode.ICPC,
    )
    visibility: Mapped[ContestVisibility] = mapped_column(
        Enum(ContestVisibility, name="contest_visibility"),
        nullable=False,
        default=ContestVisibility.PUBLIC,
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    penalty_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[User] = relationship(User, lazy="joined")


class ContestProblem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "contest_problems"
    __table_args__ = (
        UniqueConstraint("contest_id", "problem_id", name="uq_contest_problem"),
        UniqueConstraint("contest_id", "letter", name="uq_contest_letter"),
    )

    contest_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    letter: Mapped[str] = mapped_column(String(4), nullable=False, default="A")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    contest: Mapped[Contest] = relationship(Contest, lazy="joined")
    problem: Mapped[Problem] = relationship(Problem, lazy="joined")


class ContestRegistration(Base, UUIDMixin):
    __tablename__ = "contest_registrations"
    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_contest_user"),
    )

    contest_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(User, lazy="joined")
