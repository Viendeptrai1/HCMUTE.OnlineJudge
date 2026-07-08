"""S3-compatible object storage cho source code submission.

Abstraction:
  * `SourceStorage` protocol: put / get_text / key_for_submission.
  * `S3SourceStorage`: boto3 (LocalStack endpoint ở local, AWS S3 ở prod).
  * `NullSourceStorage`: no-op (dùng trong test / khi S3 chưa config).
"""

from __future__ import annotations

import asyncio
from typing import Protocol
from uuid import UUID

import boto3


class SourceStorage(Protocol):
    async def put(self, key: str, source: str) -> None: ...
    async def get_text(self, key: str) -> str: ...

    @staticmethod
    def key_for_submission(submission_id: UUID, language: str) -> str:
        ext = {"cpp": "cpp", "python": "py"}.get(language.lower(), "txt")
        return f"submissions/{submission_id}.{ext}"


class S3SourceStorage:
    def __init__(
        self,
        bucket: str,
        region: str,
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    async def put(self, key: str, source: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=source.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )

    async def get_text(self, key: str) -> str:
        obj = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self._bucket,
            Key=key,
        )
        body = obj["Body"].read()
        return body.decode("utf-8")

    @staticmethod
    def key_for_submission(submission_id: UUID, language: str) -> str:
        return SourceStorage.key_for_submission(submission_id, language)


class NullSourceStorage:
    """No-op impl — dùng khi storage chưa khả dụng (test, hoặc local không chạy s3)."""

    async def put(self, key: str, source: str) -> None:
        return None

    async def get_text(self, key: str) -> str:
        raise RuntimeError("NullSourceStorage không lưu source.")

    @staticmethod
    def key_for_submission(submission_id: UUID, language: str) -> str:
        return SourceStorage.key_for_submission(submission_id, language)
