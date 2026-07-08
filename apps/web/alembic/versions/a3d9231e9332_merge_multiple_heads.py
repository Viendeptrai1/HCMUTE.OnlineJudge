"""Merge multiple heads

Revision ID: a3d9231e9332
Revises: 74b1cff6551e, fb78a1215b22
Create Date: 2026-06-14 02:46:12.061383+00:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'a3d9231e9332'
down_revision: str | Sequence[str] | None = ('74b1cff6551e', 'fb78a1215b22')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
