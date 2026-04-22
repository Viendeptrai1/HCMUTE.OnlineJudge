"""Unit test UserService với fake in-memory repo (Dependency Inversion)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserCreate
from app.modules.users.service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserService,
)


class FakeUserRepo:
    def __init__(self) -> None:
        self._by_id: dict = {}

    async def add(self, entity: User) -> User:
        if getattr(entity, "id", None) is None:
            entity.id = uuid4()
        self._by_id[entity.id] = entity
        return entity

    async def get(self, id):  # type: ignore[no-untyped-def]
        return self._by_id.get(id)

    async def get_by_identifier(self, identifier: str) -> User | None:
        for u in self._by_id.values():
            if u.email == identifier or u.username == identifier:
                return u
        return None

    async def get_by_email(self, email: str) -> User | None:
        for u in self._by_id.values():
            if u.email == email:
                return u
        return None

    async def get_by_username(self, username: str) -> User | None:
        for u in self._by_id.values():
            if u.username == username:
                return u
        return None


async def test_register_hashes_password() -> None:
    service = UserService(FakeUserRepo())
    user = await service.register(
        UserCreate(
            email="a@b.com",
            username="alice",
            password="secret12",
            full_name="Alice",
            role=UserRole.STUDENT,
        )
    )
    assert user.password_hash != "secret12"
    assert user.password_hash.startswith("$argon2")


async def test_register_rejects_duplicate_email() -> None:
    service = UserService(FakeUserRepo())
    await service.register(UserCreate(email="a@b.com", username="alice", password="secret12"))
    with pytest.raises(UserAlreadyExistsError):
        await service.register(UserCreate(email="a@b.com", username="alice2", password="secret12"))


async def test_authenticate_success() -> None:
    service = UserService(FakeUserRepo())
    await service.register(UserCreate(email="a@b.com", username="alice", password="secret12"))

    user = await service.authenticate("alice", "secret12")
    assert user.email == "a@b.com"


async def test_authenticate_wrong_password() -> None:
    service = UserService(FakeUserRepo())
    await service.register(UserCreate(email="a@b.com", username="alice", password="secret12"))

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("alice", "wrong-password")


async def test_authenticate_unknown_user() -> None:
    service = UserService(FakeUserRepo())
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("ghost", "whatever")
