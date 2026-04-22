"""Dependency injection cho module Problems."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.problems.repository import (
    ProblemRepository,
    SqlAlchemyProblemRepository,
)
from app.modules.problems.service import ProblemService


def get_problem_repository(
    session: AsyncSession = Depends(get_session),
) -> ProblemRepository:
    return SqlAlchemyProblemRepository(session)


def get_problem_service(
    repo: ProblemRepository = Depends(get_problem_repository),
) -> ProblemService:
    return ProblemService(repo)
