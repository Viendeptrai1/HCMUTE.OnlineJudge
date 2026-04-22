"""restrict submission languages to cpp+python.

Revision ID: d664a1aee91e
Revises: 0b7fc1b93571
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "d664a1aee91e"
down_revision: str | Sequence[str] | None = "3aa37b6ac265"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PG không hỗ trợ xoá value khỏi enum; phải recreate type.
    op.execute("ALTER TABLE submissions ALTER COLUMN language TYPE VARCHAR(32) USING language::text")
    op.execute("DROP TYPE submission_language")
    op.execute("CREATE TYPE submission_language AS ENUM ('CPP', 'PYTHON')")
    op.execute(
        "ALTER TABLE submissions "
        "ALTER COLUMN language TYPE submission_language USING language::submission_language"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE submissions ALTER COLUMN language TYPE VARCHAR(32) USING language::text")
    op.execute("DROP TYPE submission_language")
    op.execute("CREATE TYPE submission_language AS ENUM ('CPP', 'C', 'PYTHON', 'JAVA')")
    op.execute(
        "ALTER TABLE submissions "
        "ALTER COLUMN language TYPE submission_language USING language::submission_language"
    )
