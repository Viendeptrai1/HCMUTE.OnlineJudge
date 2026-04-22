"""Pydantic DTO cho Testcase."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class TestcaseCreate(BaseModel):
    input_text: str = Field(default="")
    expected_output: str = Field(default="")
    is_sample: bool = False
    score: int = 10
    order_index: int = 0


class TestcaseUpdate(BaseModel):
    input_text: str | None = None
    expected_output: str | None = None
    is_sample: bool | None = None
    score: int | None = None
    order_index: int | None = None


class TestcaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    problem_id: uuid.UUID
    order_index: int
    input_text: str
    expected_output: str
    is_sample: bool
    score: int
