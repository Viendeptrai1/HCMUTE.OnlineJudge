"""Repository cho Submission."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import desc, select

from app.modules.submissions.models import Submission, SubmissionStatus
from app.shared.repository import SqlAlchemyRepository


class SubmissionRepository(Protocol):
    async def get(self, id: UUID) -> Submission | None: ...

    async def add(self, entity: Submission) -> Submission: ...

    async def list_recent(self, limit: int = 50) -> Sequence[Submission]: ...

    async def list_by_user(self, user_id: UUID, limit: int = 50) -> Sequence[Submission]: ...

    async def update_verdict(
        self,
        id: UUID,
        status: SubmissionStatus,
        time_used_ms: int | None,
        memory_used_kb: int | None,
        verdict_message: str | None,
    ) -> Submission | None: ...


class SqlAlchemySubmissionRepository(SqlAlchemyRepository[Submission]):
    model = Submission

    async def list_recent(self, limit: int = 50) -> Sequence[Submission]:
        stmt = select(Submission).order_by(desc(Submission.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(self, user_id: UUID, limit: int = 50) -> Sequence[Submission]:
        stmt = (
            select(Submission)
            .where(Submission.user_id == user_id)
            .order_by(desc(Submission.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_verdict(
        self,
        id: UUID,
        status: SubmissionStatus,
        time_used_ms: int | None,
        memory_used_kb: int | None,
        verdict_message: str | None,
    ) -> Submission | None:
        sub = await self.get(id)
        if sub is None:
            return None
        sub.status = status
        sub.time_used_ms = time_used_ms
        sub.memory_used_kb = memory_used_kb
        sub.verdict_message = verdict_message
        await self.session.flush()
        await self.session.refresh(sub)
        return sub
