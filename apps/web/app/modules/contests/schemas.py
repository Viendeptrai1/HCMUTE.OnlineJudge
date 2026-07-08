"""DTO cho Contest / ContestProblem."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.contests.models import ContestVisibility, ScoringMode


class ContestCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9\-]*$")
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    start_at: datetime
    end_at: datetime
    scoring_mode: ScoringMode = ScoringMode.ICPC
    visibility: ContestVisibility = ContestVisibility.PUBLIC
    penalty_minutes: int = 20
    password: str | None = None


class ContestUpdate(BaseModel):
    slug: str | None = Field(default=None, max_length=64)
    title: str | None = None
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    scoring_mode: ScoringMode | None = None
    visibility: ContestVisibility | None = None
    penalty_minutes: int | None = None
    password: str | None = None


class ContestProblemCreate(BaseModel):
    problem_id: uuid.UUID
    letter: str = Field(min_length=1, max_length=4)
    order_index: int = 0
    points: int = 100
