"""Unit test SubmissionService với fake repo + InMemory publisher."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.modules.submissions.models import Submission, SubmissionStatus
from app.modules.submissions.queue import InMemorySubmissionPublisher
from app.modules.submissions.schemas import SubmissionCreate
from app.modules.submissions.service import SubmissionService


class FakeSubRepo:
    def __init__(self) -> None:
        self._store: dict[UUID, Submission] = {}

    async def add(self, entity: Submission) -> Submission:
        if getattr(entity, "id", None) is None:
            entity.id = uuid4()
        self._store[entity.id] = entity
        return entity

    async def get(self, id: UUID) -> Submission | None:
        return self._store.get(id)

    async def list_recent(self, limit: int = 50):  # type: ignore[no-untyped-def]
        return list(self._store.values())[:limit]

    async def list_by_user(self, user_id: UUID, limit: int = 50):  # type: ignore[no-untyped-def]
        return [s for s in self._store.values() if s.user_id == user_id][:limit]

    async def update_verdict(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError


async def test_submit_persists_and_publishes() -> None:
    repo = FakeSubRepo()
    pub = InMemorySubmissionPublisher()
    service = SubmissionService(repo, pub)

    problem_id = uuid4()
    user_id = uuid4()
    sub = await service.submit(
        SubmissionCreate(problem_id=problem_id, language="cpp", source_code="int main(){}"),
        user_id=user_id,
    )

    assert sub.status == SubmissionStatus.PENDING
    assert sub.problem_id == problem_id
    assert pub.published == [sub.id]
