"""Cấu hình worker."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    aws_endpoint_url: str | None = None
    aws_region: str = "us-east-1"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    sqs_judge_queue_url: str = ""
    s3_bucket: str = "oj-local"
    poll_wait_seconds: int = 10
    poll_max_messages: int = 1
    sync_database_url: str = "postgresql://oj:oj_password@localhost:5432/oj"


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    return WorkerSettings()
