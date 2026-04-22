"""DI cho Contests."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.contests.leaderboard import LeaderboardService
from app.modules.contests.repository import (
    ContestProblemRepository,
    ContestRegistrationRepository,
    ContestRepository,
    SqlAlchemyContestProblemRepository,
    SqlAlchemyContestRegistrationRepository,
    SqlAlchemyContestRepository,
)
from app.modules.contests.service import ContestService


def get_contest_repo(session: AsyncSession = Depends(get_session)) -> ContestRepository:
    return SqlAlchemyContestRepository(session)


def get_contest_problem_repo(
    session: AsyncSession = Depends(get_session),
) -> ContestProblemRepository:
    return SqlAlchemyContestProblemRepository(session)


def get_contest_reg_repo(
    session: AsyncSession = Depends(get_session),
) -> ContestRegistrationRepository:
    return SqlAlchemyContestRegistrationRepository(session)


def get_contest_service(
    repo: ContestRepository = Depends(get_contest_repo),
    cp_repo: ContestProblemRepository = Depends(get_contest_problem_repo),
    reg_repo: ContestRegistrationRepository = Depends(get_contest_reg_repo),
) -> ContestService:
    return ContestService(repo, cp_repo, reg_repo)


def get_leaderboard_service(
    session: AsyncSession = Depends(get_session),
) -> LeaderboardService:
    return LeaderboardService(session)
