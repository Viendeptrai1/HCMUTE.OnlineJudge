"""Business logic cho Submission."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.submissions.models import Submission, SubmissionStatus
from app.modules.submissions.queue import SubmissionPublisher
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import SubmissionCreate
from app.shared.exceptions import EntityNotFoundError


class SubmissionService:
    """Use case nộp bài + đọc verdict.

    Dependency Inversion: nhận `SubmissionRepository` + `SubmissionPublisher`
    qua constructor — test có thể truyền fake repo + InMemoryPublisher.
    """

    def __init__(self, repo: SubmissionRepository, publisher: SubmissionPublisher) -> None:
        self._repo = repo
        self._publisher = publisher

    async def submit(self, data: SubmissionCreate, user_id: UUID) -> Submission:
        entity = Submission(
            user_id=user_id,
            problem_id=data.problem_id,
            language=data.language,
            source_code=data.source_code,
            status=SubmissionStatus.PENDING,
        )
        saved = await self._repo.add(entity)
        await self._publisher.publish(saved.id)
        return saved

    async def get(self, id: UUID) -> Submission:
        sub = await self._repo.get(id)
        if sub is None:
            raise EntityNotFoundError("Submission", id)
        return sub

    async def list_recent(self, limit: int = 50) -> Sequence[Submission]:
        return await self._repo.list_recent(limit=limit)

    async def list_by_user(self, user_id: UUID, limit: int = 50) -> Sequence[Submission]:
        return await self._repo.list_by_user(user_id=user_id, limit=limit)
