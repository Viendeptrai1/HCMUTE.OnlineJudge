"""ORM cho Tag + association table problem_tags.

Giữ module độc lập: không thêm relationship ngược vào `Problem` — query tags
thông qua association table ở repository layer. Trade-off: không eager-load
được `problem.tags` qua ORM, nhưng bù lại Problem model không phụ thuộc module tags.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, TimestampMixin, UUIDMixin

problem_tags = Table(
    "problem_tags",
    Base.metadata,
    Column(
        "problem_id",
        PG_UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("slug", name="uq_tag_slug"),)

    slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
