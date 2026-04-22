"""Integration test cho auth router + guard trên Problems."""

from __future__ import annotations

from httpx import AsyncClient


async def test_register_then_login_flow(client: AsyncClient) -> None:
    res = await client.post(
        "/auth/register",
        data={
            "email": "bob@test.com",
            "username": "bob",
            "password": "abc123",
            "full_name": "Bob",
            "role": "student",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/problems"

    res2 = await client.get("/auth/me")
    assert res2.status_code == 200
    assert "bob" in res2.text


async def test_login_bad_credentials(client: AsyncClient) -> None:
    res = await client.post(
        "/auth/login",
        data={"identifier": "nobody", "password": "x"},
    )
    assert res.status_code == 400


async def test_problems_create_requires_educator_role(client: AsyncClient) -> None:
    # student → forbidden
    await client.post(
        "/auth/register",
        data={
            "email": "s@t.com",
            "username": "student1",
            "password": "abc123",
            "role": "student",
        },
    )
    res = await client.get("/problems/new")
    assert res.status_code == 403


async def test_problems_create_ok_with_educator(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        data={
            "email": "e@t.com",
            "username": "edu1",
            "password": "abc123",
            "role": "educator",
        },
    )
    res = await client.get("/problems/new")
    assert res.status_code == 200

    res2 = await client.post(
        "/problems",
        data={
            "title": "Sample",
            "statement_md": "hello",
            "time_limit_ms": 1000,
            "memory_limit_kb": 262144,
            "difficulty": "easy",
        },
        follow_redirects=False,
    )
    assert res2.status_code == 303
    assert res2.headers["location"].startswith("/problems/")


async def test_problems_create_anonymous_redirects_to_login(client: AsyncClient) -> None:
    res = await client.get("/problems/new", follow_redirects=False)
    assert res.status_code == 401
