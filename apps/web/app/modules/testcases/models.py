"""ORM model cho Testcase."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.problems.models import Problem
from app.shared.base_model import Base, TimestampMixin, UUIDMixin


class Testcase(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "testcases"

    problem_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # order_index dùng để sắp xếp hiển thị + xác định thứ tự chấm (TC1, TC2, ...).
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # is_sample=True ⇒ hiển thị công khai trong phần "Ví dụ" trên trang bài.
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Điểm của testcase — tổng điểm thường = 100 chia đều, nhưng cho phép custom.
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    problem: Mapped[Problem] = relationship(Problem, lazy="joined")
