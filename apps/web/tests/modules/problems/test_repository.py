"""Integration test: SqlAlchemyProblemRepository CRUD."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.modules.problems.models import Difficulty, Problem
from app.modules.problems.repository import SqlAlchemyProblemRepository

pytestmark = pytest.mark.asyncio


async def test_add_and_get(db_session) -> None:
    repo = SqlAlchemyProblemRepository(db_session)
    saved = await repo.add(
        Problem(
            title="Hello",
            statement_md="# hi",
            time_limit_ms=1000,
            memory_limit_kb=65536,
            difficulty=Difficulty.EASY,
        )
    )
    fetched = await repo.get(saved.id)
    assert fetched is not None
    assert fetched.title == "Hello"


async def test_list_empty(db_session) -> None:
    repo = SqlAlchemyProblemRepository(db_session)
    assert await repo.list() == []


async def test_get_missing_returns_none(db_session) -> None:
    repo = SqlAlchemyProblemRepository(db_session)
    assert await repo.get(uuid4()) is None
