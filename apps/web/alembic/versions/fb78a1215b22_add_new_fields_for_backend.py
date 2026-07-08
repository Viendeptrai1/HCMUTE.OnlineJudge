"""add new fields for backend

Revision ID: fb78a1215b22
Revises: ea435f6ff13c
Create Date: 2026-06-13 14:30:00.000000+00:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'fb78a1215b22'
down_revision: str | Sequence[str] | None = 'ea435f6ff13c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users: student_code
    op.add_column('users', sa.Column('student_code', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_users_student_code'), 'users', ['student_code'], unique=True)
    
    # 2. courses: invite_code
    op.add_column('courses', sa.Column('invite_code', sa.String(length=32), nullable=True))
    op.create_index(op.f('ix_courses_invite_code'), 'courses', ['invite_code'], unique=True)

    # 3. submissions: contest_id
    op.add_column('submissions', sa.Column('contest_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_submissions_contest_id', 'submissions', 'contests', ['contest_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_submissions_contest_id'), 'submissions', ['contest_id'], unique=False)

    # 4. submissions: language enum
    op.execute("ALTER TYPE submission_language ADD VALUE IF NOT EXISTS 'c'")
    op.execute("ALTER TYPE submission_language ADD VALUE IF NOT EXISTS 'java'")

    # 5. contests: password_hash
    op.add_column('contests', sa.Column('password_hash', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('contests', 'password_hash')
    
    # We cannot easily drop enum values in Postgres, so we skip downgrading enum values.
    
    op.drop_index(op.f('ix_submissions_contest_id'), table_name='submissions')
    op.drop_constraint('fk_submissions_contest_id', 'submissions', type_='foreignkey')
    op.drop_column('submissions', 'contest_id')

    op.drop_index(op.f('ix_courses_invite_code'), table_name='courses')
    op.drop_column('courses', 'invite_code')

    op.drop_index(op.f('ix_users_student_code'), table_name='users')
    op.drop_column('users', 'student_code')
