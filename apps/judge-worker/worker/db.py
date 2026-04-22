"""Truy cập DB cho worker — dùng psycopg sync (đơn giản, không cần ORM).

Chỉ có vài câu lệnh: đọc submission, cập nhật trạng thái + verdict.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

import psycopg


@dataclass(frozen=True, slots=True)
class SubmissionRow:
    id: UUID
    user_id: UUID
    problem_id: UUID
    language: str
    source_code: str
    time_limit_ms: int
    memory_limit_kb: int
    source_key: str | None = None


@dataclass(frozen=True, slots=True)
class TestcaseRow:
    id: UUID
    order_index: int
    input_text: str
    expected_output: str
    score: int


def _normalize_dsn(url: str) -> str:
    """Strip SQLAlchemy `+psycopg` prefix nếu có."""

    return url.replace("postgresql+psycopg://", "postgresql://", 1)


class SubmissionDAO:
    def __init__(self, dsn: str) -> None:
        self._dsn = _normalize_dsn(dsn)

    @contextmanager
    def _conn(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self._dsn, autocommit=False) as conn:
            yield conn

    def fetch(self, submission_id: UUID) -> SubmissionRow | None:
        sql = """
            SELECT s.id, s.user_id, s.problem_id, s.language, s.source_code,
                   p.time_limit_ms, p.memory_limit_kb, s.source_key
              FROM submissions s
              JOIN problems p ON p.id = s.problem_id
             WHERE s.id = %s
        """
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (submission_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return SubmissionRow(*row)

    def fetch_testcases(self, problem_id: UUID) -> list[TestcaseRow]:
        sql = """
            SELECT id, order_index, input_text, expected_output, score
              FROM testcases
             WHERE problem_id = %s
             ORDER BY order_index ASC, created_at ASC
        """
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (problem_id,))
            return [TestcaseRow(*row) for row in cur.fetchall()]

    def mark_judging(self, submission_id: UUID) -> None:
        # Postgres enum dùng tên Python (UPPERCASE) do SQLAlchemy mặc định
        # `Enum(MemberEnum)` lấy `.name`. Worker cập nhật SQL thô nên phải
        # truyền đúng form tên (JUDGING, ACCEPTED, ...).
        sql = "UPDATE submissions SET status='JUDGING', updated_at=NOW() WHERE id=%s"
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (submission_id,))
            conn.commit()

    def update_verdict(
        self,
        submission_id: UUID,
        status: str,
        time_used_ms: int | None,
        memory_used_kb: int | None,
        verdict_message: str | None,
    ) -> None:
        sql = """
            UPDATE submissions
               SET status = %s,
                   time_used_ms = %s,
                   memory_used_kb = %s,
                   verdict_message = %s,
                   updated_at = NOW()
             WHERE id = %s
        """
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                sql,
                (status.upper(), time_used_ms, memory_used_kb, verdict_message, submission_id),
            )
            conn.commit()
