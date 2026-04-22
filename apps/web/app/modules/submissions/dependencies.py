"""Dependency injection cho module Submissions."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.modules.submissions.queue import (
    InMemorySubmissionPublisher,
    SqsSubmissionPublisher,
    SubmissionPublisher,
)
from app.modules.submissions.repository import (
    SqlAlchemySubmissionRepository,
    SubmissionRepository,
)
from app.modules.submissions.service import SubmissionService


def get_submission_repository(
    session: AsyncSession = Depends(get_session),
) -> SubmissionRepository:
    return SqlAlchemySubmissionRepository(session)


@lru_cache(maxsize=1)
def _build_publisher(queue_url: str, region: str, endpoint_url: str | None) -> SubmissionPublisher:
    if not queue_url:
        return InMemorySubmissionPublisher()
    return SqsSubmissionPublisher(queue_url=queue_url, region=region, endpoint_url=endpoint_url)


def get_submission_publisher(
    settings: Settings = Depends(get_settings),
) -> SubmissionPublisher:
    return _build_publisher(
        queue_url=settings.sqs_judge_queue_url,
        region=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
    )


def get_submission_service(
    repo: SubmissionRepository = Depends(get_submission_repository),
    publisher: SubmissionPublisher = Depends(get_submission_publisher),
) -> SubmissionService:
    return SubmissionService(repo, publisher)
