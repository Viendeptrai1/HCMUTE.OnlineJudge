"""Business logic cho Contest."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.contests.models import (
    Contest,
    ContestProblem,
    ContestRegistration,
    ContestVisibility,
)
from app.modules.contests.repository import (
    ContestProblemRepository,
    ContestRegistrationRepository,
    ContestRepository,
)
from app.modules.contests.schemas import (
    ContestCreate,
    ContestProblemCreate,
    ContestUpdate,
)
from app.modules.users.models import User, UserRole
from app.shared.exceptions import DomainError, EntityNotFoundError


class ContestSlugTakenError(DomainError):
    pass


class ContestWindowInvalidError(DomainError):
    pass


class ContestLetterTakenError(DomainError):
    pass


class ContestService:
    def __init__(
        self,
        repo: ContestRepository,
        cp_repo: ContestProblemRepository,
        reg_repo: ContestRegistrationRepository,
    ) -> None:
        self._repo = repo
        self._cp_repo = cp_repo
        self._reg_repo = reg_repo

    async def list_all(self) -> Sequence[Contest]:
        return await self._repo.list_all()

    async def get(self, id: UUID) -> Contest:
        c = await self._repo.get(id)
        if c is None:
            raise EntityNotFoundError("Contest", id)
        return c

    async def get_by_slug(self, slug: str) -> Contest:
        c = await self._repo.get_by_slug(slug)
        if c is None:
            raise EntityNotFoundError("Contest", slug)
        return c

    async def create(self, creator_id: UUID, data: ContestCreate) -> Contest:
        if await self._repo.get_by_slug(data.slug):
            raise ContestSlugTakenError(f"Slug '{data.slug}' đã tồn tại")
        if data.end_at <= data.start_at:
            raise ContestWindowInvalidError("end_at phải sau start_at")
        password_hash = None
        if data.password:
            from app.modules.users.security import hash_password
            password_hash = hash_password(data.password)

        c = Contest(
            slug=data.slug,
            title=data.title,
            description=data.description,
            start_at=data.start_at,
            end_at=data.end_at,
            scoring_mode=data.scoring_mode,
            visibility=data.visibility,
            penalty_minutes=data.penalty_minutes,
            password_hash=password_hash,
            created_by_id=creator_id,
        )
        return await self._repo.add(c)

    async def update(self, contest_id: UUID, data: ContestUpdate) -> Contest:
        c = await self.get(contest_id)
        updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None and k != "password"}
        
        if data.password is not None:
            if data.password == "":
                updates["password_hash"] = None
            else:
                from app.modules.users.security import hash_password
                updates["password_hash"] = hash_password(data.password)

        if "slug" in updates and updates["slug"] != c.slug:
            coll = await self._repo.get_by_slug(str(updates["slug"]))
            if coll is not None and coll.id != c.id:
                raise ContestSlugTakenError(f"Slug '{updates['slug']}' đã tồn tại")
        end_at = updates.get("end_at", c.end_at)
        start_at = updates.get("start_at", c.start_at)
        if end_at <= start_at:
            raise ContestWindowInvalidError("end_at phải sau start_at")
        return await self._repo.update(c, updates)

    async def delete(self, contest_id: UUID) -> None:
        await self._repo.delete(contest_id)

    async def list_problems(self, contest_id: UUID) -> Sequence[ContestProblem]:
        return await self._cp_repo.list_by_contest(contest_id)

    async def assign_problem(
        self, contest_id: UUID, data: ContestProblemCreate
    ) -> ContestProblem:
        existing = await self._cp_repo.list_by_contest(contest_id)
        if any(cp.letter == data.letter for cp in existing):
            raise ContestLetterTakenError(f"Chữ cái '{data.letter}' đã được dùng")
        if any(cp.problem_id == data.problem_id for cp in existing):
            raise DomainError("Bài đã có trong contest")
        cp = ContestProblem(
            contest_id=contest_id,
            problem_id=data.problem_id,
            letter=data.letter.upper(),
            order_index=data.order_index,
            points=data.points,
        )
        return await self._cp_repo.add(cp)

    async def unassign_problem(self, cp_id: UUID) -> None:
        await self._cp_repo.delete(cp_id)

    async def can_manage(self, contest: Contest, user: User) -> bool:
        return user.role == UserRole.ADMIN or contest.created_by_id == user.id

    async def can_view(self, contest: Contest, user: User | None) -> bool:
        if contest.visibility == ContestVisibility.PUBLIC:
            return True
        if user is None:
            return False
        if await self.can_manage(contest, user):
            return True
        return await self._reg_repo.get(contest.id, user.id) is not None

    async def register_user(self, contest_id: UUID, user_id: UUID, password: str = "") -> ContestRegistration:
        contest = await self.get(contest_id)
        if contest.password_hash:
            from app.modules.users.security import verify_password
            if not verify_password(password, contest.password_hash):
                raise DomainError("Sai mật khẩu contest")
                
        existing = await self._reg_repo.get(contest_id, user_id)
        if existing is not None:
            return existing
        reg = ContestRegistration(contest_id=contest_id, user_id=user_id)
        return await self._reg_repo.add(reg)

    async def list_registrations(
        self, contest_id: UUID
    ) -> Sequence[ContestRegistration]:
        return await self._reg_repo.list_by_contest(contest_id)

    async def is_registered(self, contest_id: UUID, user_id: UUID) -> bool:
        return await self._reg_repo.get(contest_id, user_id) is not None
