"""Integration test router /problems qua httpx AsyncClient."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_list_empty_page(client) -> None:
    response = await client.get("/problems")
    assert response.status_code == 200
    assert "Ngân hàng bài tập" in response.text


async def test_create_and_detail_flow(client) -> None:
    await client.post(
        "/auth/register",
        data={
            "email": "edu@test.com",
            "username": "educator_router",
            "password": "abc123",
            "role": "educator",
        },
    )

    create_resp = await client.post(
        "/problems",
        data={
            "title": "Tổng 2 số",
            "statement_md": "Đề: tính `a + b`.",
            "time_limit_ms": 1000,
            "memory_limit_kb": 65536,
            "difficulty": "easy",
        },
        follow_redirects=False,
    )
    assert create_resp.status_code == 303
    detail_url = create_resp.headers["location"]
    assert detail_url.startswith("/problems/")

    detail_resp = await client.get(detail_url)
    assert detail_resp.status_code == 200
    assert "Tổng 2 số" in detail_resp.text


async def test_htmx_list_returns_partial(client) -> None:
    response = await client.get("/problems", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "<html" not in response.text.lower()
