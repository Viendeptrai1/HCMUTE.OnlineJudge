"""Pydantic schemas cho module Problems.

Tách riêng theo loại use (Create/Update/Read) — tránh god-schema, đúng ISP.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.problems.models import Difficulty


class ProblemBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    statement_md: str = ""
    time_limit_ms: int = Field(default=1000, ge=100, le=60_000)
    memory_limit_kb: int = Field(default=262144, ge=1024, le=1_048_576)
    difficulty: Difficulty = Difficulty.EASY


class ProblemCreate(ProblemBase):
    pass


class ProblemUpdate(ProblemBase):
    pass


class ProblemRead(ProblemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
