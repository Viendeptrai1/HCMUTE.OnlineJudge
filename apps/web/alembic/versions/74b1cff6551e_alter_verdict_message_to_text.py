"""alter verdict_message to text

Revision ID: 74b1cff6551e
Revises: 8db1d5056d99
Create Date: 2026-04-22 09:45:34.511696+00:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '74b1cff6551e'
down_revision: str | Sequence[str] | None = '8db1d5056d99'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "submissions",
        "verdict_message",
        existing_type=sa.String(length=1024),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "submissions",
        "verdict_message",
        existing_type=sa.Text(),
        type_=sa.String(length=1024),
        existing_nullable=True,
    )
