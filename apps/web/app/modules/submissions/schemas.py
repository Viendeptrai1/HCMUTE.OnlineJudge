"""Pydantic schemas cho Submission."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.submissions.models import Language, SubmissionStatus


class SubmissionCreate(BaseModel):
    problem_id: UUID
    contest_id: UUID | None = None
    language: Language
    source_code: str = Field(min_length=1, max_length=200_000)


class SubmissionVerdict(BaseModel):
    status: SubmissionStatus
    time_used_ms: int | None = None
    memory_used_kb: int | None = None
    verdict_message: str | None = None


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    problem_id: UUID
    language: Language
    status: SubmissionStatus
    time_used_ms: int | None
    memory_used_kb: int | None
    verdict_message: str | None
    created_at: datetime
    updated_at: datetime
