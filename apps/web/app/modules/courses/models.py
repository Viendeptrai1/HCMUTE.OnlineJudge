"""ORM cho Course + Enrollment + CourseProblem (assignment)."""

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


class CourseRole(StrEnum):
    """Vai trò của user trong 1 course (không phải role hệ thống)."""

    STUDENT = "student"
    TA = "ta"


class Course(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    semester: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    educator_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    educator: Mapped[User] = relationship(User, lazy="joined")


class Enrollment(Base, UUIDMixin):
    """User đăng ký vào 1 course (role trong lớp riêng biệt với role hệ thống)."""

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_enrollment_course_user"),)

    course_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_in_course: Mapped[CourseRole] = mapped_column(
        Enum(CourseRole, name="course_role"),
        nullable=False,
        default=CourseRole.STUDENT,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    course: Mapped[Course] = relationship(Course, lazy="joined")
    user: Mapped[User] = relationship(User, lazy="joined")


class CourseProblem(Base, UUIDMixin, TimestampMixin):
    """Bài tập được gán vào course (assignment). Deadline tuỳ chọn."""

    __tablename__ = "course_problems"
    __table_args__ = (
        UniqueConstraint("course_id", "problem_id", name="uq_course_problem"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    course: Mapped[Course] = relationship(Course, lazy="joined")
    problem: Mapped[Problem] = relationship(Problem, lazy="joined")
