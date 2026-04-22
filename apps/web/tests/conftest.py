"""Pytest fixtures dùng chung cho apps/web."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://oj:oj_password@localhost:5432/oj_test",
)
os.environ.setdefault(
    "SYNC_DATABASE_URL",
    "postgresql+psycopg://oj:oj_password@localhost:5432/oj_test",
)

import pytest_asyncio
from app.core.config import get_settings
from app.core.db import get_session
from app.main import app
from app.shared.base_model import Base
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Async engine riêng cho mỗi test, dùng NullPool để tránh connection reuse."""

    settings = get_settings()
    eng = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine: AsyncEngine, monkeypatch) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def _override_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Middleware `inject_current_user` dùng `SessionLocal` trực tiếp (không qua
    # Depends), vì vậy patch module-level để trỏ về test engine.
    import app.main as main_module

    monkeypatch.setattr(main_module, "SessionLocal", factory)

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
