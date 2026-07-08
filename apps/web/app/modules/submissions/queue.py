"""Publisher đẩy submission lên queue (SQS / in-memory cho test)."""

from __future__ import annotations

import json
from typing import Protocol
from uuid import UUID

import boto3


class SubmissionPublisher(Protocol):
    """Contract gửi submission_id lên queue cho judge worker tiêu thụ."""

    async def publish(self, submission_id: UUID) -> None: ...


class SqsSubmissionPublisher:
    """Impl SQS dùng boto3 (sync) gói trong asyncio.to_thread.

    Endpoint URL = LocalStack ở local, AWS thật ở prod.
    """

    def __init__(self, queue_url: str, region: str, endpoint_url: str | None = None, aws_access_key_id: str | None = None, aws_secret_access_key: str | None = None) -> None:
        self._queue_url = queue_url
        self._client = boto3.client(
            "sqs",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    async def publish(self, submission_id: UUID) -> None:
        import asyncio

        if not self._queue_url:
            raise RuntimeError("SQS_JUDGE_QUEUE_URL is empty")

        body = json.dumps({"submission_id": str(submission_id)})
        await asyncio.to_thread(
            self._client.send_message,
            QueueUrl=self._queue_url,
            MessageBody=body,
        )


class InMemorySubmissionPublisher:
    """Publisher in-memory dùng cho test — chỉ lưu các submission_id đã publish."""

    def __init__(self) -> None:
        self.published: list[UUID] = []

    async def publish(self, submission_id: UUID) -> None:
        self.published.append(submission_id)
