"""DI cho module Testcases."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.testcases.repository import (
    SqlAlchemyTestcaseRepository,
    TestcaseRepository,
)
from app.modules.testcases.service import TestcaseService


def get_testcase_repository(
    session: AsyncSession = Depends(get_session),
) -> TestcaseRepository:
    return SqlAlchemyTestcaseRepository(session)


def get_testcase_service(
    repo: TestcaseRepository = Depends(get_testcase_repository),
) -> TestcaseService:
    return TestcaseService(repo)
