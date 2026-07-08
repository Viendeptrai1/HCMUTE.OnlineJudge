"""HTTP routes cho Contests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.modules.contests.dependencies import (
    get_contest_service,
    get_leaderboard_service,
)
from app.modules.contests.leaderboard import LeaderboardService, contest_phase
from app.modules.contests.models import ContestVisibility, ScoringMode
from app.modules.contests.schemas import (
    ContestCreate,
    ContestProblemCreate,
    ContestUpdate,
)
from app.modules.contests.service import (
    ContestLetterTakenError,
    ContestService,
    ContestSlugTakenError,
    ContestWindowInvalidError,
)
from app.modules.problems.dependencies import get_problem_service
from app.modules.problems.service import ProblemService
from app.modules.users.dependencies import (
    get_current_user_optional,
    require_role,
    require_user,
)
from app.modules.users.models import User, UserRole
from app.shared.exceptions import DomainError, EntityNotFoundError

router = APIRouter(prefix="/contests", tags=["contests"])
_MANAGE_ROLES = (UserRole.EDUCATOR, UserRole.ADMIN)

class RegisterContestRequest(BaseModel):
    password: str = ""

@router.get("")
async def list_contests(
    service: ContestService = Depends(get_contest_service),
) -> dict:
    contests = await service.list_all()
    enriched = [{"contest": c, "phase": contest_phase(c)} for c in contests]
    return {"items": enriched}


@router.post("")
async def create_contest(
    data: ContestCreate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
) -> dict:
    try:
        c = await service.create(
            creator_id=user.id,
            data=data,
        )
        return {"message": "Tạo contest thành công", "contest_id": str(c.id)}
    except (ContestSlugTakenError, ContestWindowInvalidError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{contest_id}")
async def contest_detail(
    contest_id: UUID,
    user: User | None = Depends(get_current_user_optional),
    service: ContestService = Depends(get_contest_service),
) -> dict:
    try:
        contest = await service.get(contest_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    phase = contest_phase(contest)
    can_view = await service.can_view(contest, user)
    can_manage = user is not None and await service.can_manage(contest, user)

    cps = await service.list_problems(contest_id) if can_view else []
    registrations = await service.list_registrations(contest_id) if can_manage else []

    is_registered = False
    if user is not None:
        is_registered = await service.is_registered(contest_id, user.id)

    return {
        "contest": contest,
        "phase": phase,
        "can_view": can_view,
        "can_manage": can_manage,
        "is_registered": is_registered,
        "contest_problems": cps,
        "registrations": registrations,
        "now": datetime.utcnow(),
    }


@router.put("/{contest_id}")
async def update_contest(
    contest_id: UUID,
    data: ContestUpdate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
) -> dict:
    contest = await service.get(contest_id)
    if not await service.can_manage(contest, user):
        raise HTTPException(status_code=403, detail="Không phải contest của bạn")
    try:
        await service.update(contest_id, data)
        return {"message": "Cập nhật thành công", "contest_id": str(contest_id)}
    except (ContestSlugTakenError, ContestWindowInvalidError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{contest_id}")
async def delete_contest(
    contest_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
) -> dict:
    contest = await service.get(contest_id)
    if not await service.can_manage(contest, user):
        raise HTTPException(status_code=403, detail="Không phải contest của bạn")
    await service.delete(contest_id)
    return {"message": "Đã xóa contest"}


@router.post("/{contest_id}/register")
async def register_contest(
    contest_id: UUID,
    data: RegisterContestRequest,
    user: User = Depends(require_user),
    service: ContestService = Depends(get_contest_service),
) -> dict:
    try:
        await service.register_user(contest_id, user.id, data.password)
        return {"message": "Đăng ký thành công"}
    except DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contest_id}/problems")
async def assign_problem(
    contest_id: UUID,
    data: ContestProblemCreate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
    problem_service: ProblemService = Depends(get_problem_service),
) -> dict:
    contest = await service.get(contest_id)
    if not await service.can_manage(contest, user):
        raise HTTPException(status_code=403, detail="Không phải contest của bạn")
    try:
        await problem_service.get_problem(data.problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        await service.assign_problem(contest_id, data)
        return {"message": "Đã thêm bài tập vào contest"}
    except (ContestLetterTakenError, DomainError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{contest_id}/problems/{cp_id}")
async def unassign_problem(
    contest_id: UUID,
    cp_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
) -> dict:
    contest = await service.get(contest_id)
    if not await service.can_manage(contest, user):
        raise HTTPException(status_code=403, detail="Không phải contest của bạn")
    await service.unassign_problem(cp_id)
    return {"message": "Đã xóa bài tập khỏi contest"}


@router.get("/{contest_id}/leaderboard")
async def leaderboard(
    contest_id: UUID,
    user: User | None = Depends(get_current_user_optional),
    service: ContestService = Depends(get_contest_service),
    lb_service: LeaderboardService = Depends(get_leaderboard_service),
) -> dict:
    contest = await service.get(contest_id)
    if not await service.can_view(contest, user):
        raise HTTPException(status_code=403, detail="Bạn chưa đăng ký contest này")
    cps = await service.list_problems(contest_id)
    rows = await lb_service.compute(contest)
    phase = contest_phase(contest)
    return {
        "contest": contest,
        "contest_problems": cps,
        "rows": rows,
        "phase": phase,
    }
