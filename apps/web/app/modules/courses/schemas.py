"""Pydantic DTO cho Courses / Enrollments / CourseProblems."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.courses.models import CourseRole


class CourseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    semester: str = Field(default="", max_length=32)
    description: str = ""


class CourseUpdate(BaseModel):
    code: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, max_length=255)
    semester: str | None = None
    description: str | None = None


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    semester: str
    description: str
    educator_id: uuid.UUID


class EnrollmentCreate(BaseModel):
    username_or_email: str = Field(min_length=1)
    role_in_course: CourseRole = CourseRole.STUDENT


class CourseProblemCreate(BaseModel):
    problem_id: uuid.UUID
    deadline: datetime | None = None
    weight: int = 10
    order_index: int = 0


class CourseProblemUpdate(BaseModel):
    deadline: datetime | None = None
    weight: int | None = None
    order_index: int | None = None
