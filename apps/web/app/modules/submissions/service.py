"""Business logic cho Submission."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from app.modules.submissions.models import Submission, SubmissionStatus
from app.modules.submissions.queue import SubmissionPublisher
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import SubmissionCreate
from app.shared.exceptions import EntityNotFoundError
from app.shared.storage import SourceStorage

_log = logging.getLogger(__name__)


class SubmissionService:
    """Use case nộp bài + đọc verdict.

    Dependency Inversion: nhận `SubmissionRepository` + `SubmissionPublisher`
    qua constructor — test có thể truyền fake repo + InMemoryPublisher.
    """

    def __init__(
        self,
        repo: SubmissionRepository,
        publisher: SubmissionPublisher,
        storage: SourceStorage | None = None,
    ) -> None:
        self._repo = repo
        self._publisher = publisher
        self._storage = storage

    async def submit(self, data: SubmissionCreate, user_id: UUID) -> Submission:
        entity = Submission(
            user_id=user_id,
            problem_id=data.problem_id,
            contest_id=data.contest_id,
            language=data.language,
            source_code=data.source_code,
            status=SubmissionStatus.PENDING,
        )
        saved = await self._repo.add(entity)

        # Best-effort upload source code sang S3 (không fail submit nếu S3 lỗi).
        if self._storage is not None:
            key = SourceStorage.key_for_submission(saved.id, data.language.value)
            try:
                await self._storage.put(key, data.source_code)
                saved.source_key = key
                await self._repo.update_source_key(saved.id, key)
            except Exception as e:
                _log.warning("S3 put failed cho submission %s: %s", saved.id, e)

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

    async def list_by_user_and_problem(
        self, user_id: UUID, problem_id: UUID, limit: int = 20
    ) -> Sequence[Submission]:
        return await self._repo.list_by_user_and_problem(user_id, problem_id, limit=limit)

    async def count_accepted_problems(self, user_id: UUID) -> int:
        return await self._repo.count_accepted_problems(user_id)

    async def user_has_solved(self, user_id: UUID, problem_id: UUID) -> bool:
        subs = await self._repo.list_by_user_and_problem(user_id, problem_id, limit=100)
        return any(s.status == SubmissionStatus.ACCEPTED for s in subs)
