"""ORM model cho Submission."""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.problems.models import Problem
from app.modules.users.models import User
from app.shared.base_model import Base, TimestampMixin, UUIDMixin


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    JUDGING = "judging"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT = "time_limit"
    MEMORY_LIMIT = "memory_limit"
    RUNTIME_ERROR = "runtime_error"
    COMPILE_ERROR = "compile_error"
    INTERNAL_ERROR = "internal_error"


class Language(StrEnum):
    C = "c"
    CPP = "cpp"
    JAVA = "java"
    PYTHON = "python"


class Submission(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "submissions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contest_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    language: Mapped[Language] = mapped_column(
        Enum(Language, name="submission_language"), nullable=False
    )
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    source_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """S3 object key — nếu null thì `source_code` là source of truth (legacy)."""

    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status"),
        nullable=False,
        default=SubmissionStatus.PENDING,
        index=True,
    )
    time_used_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_used_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verdict_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(User, lazy="joined")
    problem: Mapped[Problem] = relationship(Problem, lazy="joined")
