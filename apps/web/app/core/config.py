"""Cấu hình ứng dụng (đọc từ biến môi trường / file .env)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Toàn bộ cấu hình runtime của app.

    Tuân thủ SRP: class này chỉ giữ config, không làm gì khác.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["local", "dev", "staging", "prod"] = "local"
    secret_key: str = "dev-secret-change-me"

    database_url: str = Field(
        default="postgresql+asyncpg://oj:oj_password@localhost:5432/oj",
        description="URL SQLAlchemy async (asyncpg) cho runtime.",
    )
    sync_database_url: str = Field(
        default="postgresql+psycopg://oj:oj_password@localhost:5432/oj",
        description="URL SQLAlchemy sync (psycopg) cho Alembic migration.",
    )

    redis_url: str = "redis://localhost:6379/0"

    aws_endpoint_url: str | None = None
    aws_region: str = "us-east-1"
    s3_bucket: str = "oj-local"
    sqs_judge_queue_url: str = ""

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton cached settings — dùng với FastAPI Depends."""

    return Settings()
