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
from app.shared.storage import NullSourceStorage, S3SourceStorage, SourceStorage


def get_submission_repository(
    session: AsyncSession = Depends(get_session),
) -> SubmissionRepository:
    return SqlAlchemySubmissionRepository(session)


@lru_cache(maxsize=1)
def _build_publisher(queue_url: str, region: str, endpoint_url: str | None, aws_access_key_id: str | None, aws_secret_access_key: str | None) -> SubmissionPublisher:
    if not queue_url:
        return InMemorySubmissionPublisher()
    return SqsSubmissionPublisher(queue_url=queue_url, region=region, endpoint_url=endpoint_url, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)


def get_submission_publisher(
    settings: Settings = Depends(get_settings),
) -> SubmissionPublisher:
    return _build_publisher(
        queue_url=settings.sqs_judge_queue_url,
        region=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


@lru_cache(maxsize=1)
def _build_storage(bucket: str, region: str, endpoint_url: str | None, aws_access_key_id: str | None, aws_secret_access_key: str | None) -> SourceStorage:
    if not bucket:
        return NullSourceStorage()
    return S3SourceStorage(bucket=bucket, region=region, endpoint_url=endpoint_url, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)


def get_source_storage(settings: Settings = Depends(get_settings)) -> SourceStorage:
    return _build_storage(
        bucket=settings.s3_bucket,
        region=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def get_submission_service(
    repo: SubmissionRepository = Depends(get_submission_repository),
    publisher: SubmissionPublisher = Depends(get_submission_publisher),
    storage: SourceStorage = Depends(get_source_storage),
) -> SubmissionService:
    return SubmissionService(repo, publisher, storage)
