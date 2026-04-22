"""HTTP routes cho Contests.

Mọi người xem được danh sách + PUBLIC contest; PRIVATE cần register hoặc ownership.
Leaderboard polled by HTMX mỗi 5s trong lúc contest đang RUNNING.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.templating import templates
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
from app.shared.htmx import is_htmx

router = APIRouter(prefix="/contests", tags=["contests"])
_MANAGE_ROLES = (UserRole.EDUCATOR, UserRole.ADMIN)


def _parse_dt(s: str) -> datetime:
    """Parse form datetime. Giả định input là giờ UTC (datetime-local) nếu không có tz."""
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Sai format thời gian: {s}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


@router.get("", response_class=HTMLResponse)
async def list_contests(
    request: Request,
    service: ContestService = Depends(get_contest_service),
) -> Response:
    contests = await service.list_all()
    enriched = [{"c": c, "phase": contest_phase(c)} for c in contests]
    return templates.TemplateResponse(
        request,
        "contests/list.html",
        {"items": enriched, "manage_roles": _MANAGE_ROLES},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_contest_form(
    request: Request,
    _user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> Response:
    return templates.TemplateResponse(
        request,
        "contests/form.html",
        {
            "contest": None,
            "error": None,
            "scoring_modes": list(ScoringMode),
            "visibilities": list(ContestVisibility),
        },
    )


@router.post("", response_class=HTMLResponse)
async def create_contest(
    request: Request,
    slug: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    start_at: str = Form(...),
    end_at: str = Form(...),
    scoring_mode: ScoringMode = Form(ScoringMode.ICPC),
    visibility: ContestVisibility = Form(ContestVisibility.PUBLIC),
    penalty_minutes: int = Form(20),
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
) -> Response:
    try:
        c = await service.create(
            creator_id=user.id,
            data=ContestCreate(
                slug=slug,
                title=title,
                description=description,
                start_at=_parse_dt(start_at),
                end_at=_parse_dt(end_at),
                scoring_mode=scoring_mode,
                visibility=visibility,
                penalty_minutes=penalty_minutes,
            ),
        )
    except (ContestSlugTakenError, ContestWindowInvalidError) as e:
        return templates.TemplateResponse(
            request,
            "contests/form.html",
            {
                "contest": None,
                "error": str(e),
                "scoring_modes": list(ScoringMode),
                "visibilities": list(ContestVisibility),
            },
            status_code=400,
        )
    return RedirectResponse(url=f"/contests/{c.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{contest_id}", response_class=HTMLResponse)
async def contest_detail(
    contest_id: UUID,
    request: Request,
    user: User | None = Depends(get_current_user_optional),
    service: ContestService = Depends(get_contest_service),
) -> Response:
    try:
        contest = await service.get(contest_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    phase = contest_phase(contest)
    can_view = await service.can_view(contest, user)
    can_manage = user is not None and await service.can_manage(contest, user)

    # Trong phase "upcoming" + "running", chỉ hiển thị problems nếu user can_view.
    cps = await service.list_problems(contest_id) if can_view else []
    registrations = await service.list_registrations(contest_id) if can_manage else []

    is_registered = False
    if user is not None:
        is_registered = await service.is_registered(contest_id, user.id)

    return templates.TemplateResponse(
        request,
        "contests/detail.html",
        {
            "contest": contest,
            "phase": phase,
            "can_view": can_view,
            "can_manage": can_manage,
            "is_registered": is_registered,
            "contest_problems": cps,
            "registrations": registrations,
            "now": datetime.utcnow(),
        },
    )


@router.get("/{contest_id}/edit", response_class=HTMLResponse)
async def edit_contest_form(
    contest_id: UUID,
    request: Request,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
) -> Response:
    contest = await service.get(contest_id)
    if not await service.can_manage(contest, user):
        raise HTTPException(status_code=403, detail="Không phải contest của bạn")
    return templates.TemplateResponse(
        request,
        "contests/form.html",
        {
            "contest": contest,
            "error": None,
            "scoring_modes": list(ScoringMode),
            "visibilities": list(ContestVisibility),
        },
    )


@router.post("/{contest_id}", response_class=HTMLResponse)
async def update_contest(
    contest_id: UUID,
    request: Request,
    slug: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    start_at: str = Form(...),
    end_at: str = Form(...),
    scoring_mode: ScoringMode = Form(ScoringMode.ICPC),
    visibility: ContestVisibility = Form(ContestVisibility.PUBLIC),
    penalty_minutes: int = Form(20),
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
) -> Response:
    contest = await service.get(contest_id)
    if not await service.can_manage(contest, user):
        raise HTTPException(status_code=403, detail="Không phải contest của bạn")
    try:
        await service.update(
            contest_id,
            ContestUpdate(
                slug=slug,
                title=title,
                description=description,
                start_at=_parse_dt(start_at),
                end_at=_parse_dt(end_at),
                scoring_mode=scoring_mode,
                visibility=visibility,
                penalty_minutes=penalty_minutes,
            ),
        )
    except (ContestSlugTakenError, ContestWindowInvalidError) as e:
        return templates.TemplateResponse(
            request,
            "contests/form.html",
            {
                "contest": contest,
                "error": str(e),
                "scoring_modes": list(ScoringMode),
                "visibilities": list(ContestVisibility),
            },
            status_code=400,
        )
    return RedirectResponse(url=f"/contests/{contest_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{contest_id}/delete", response_class=HTMLResponse)
async def delete_contest(
    contest_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
) -> Response:
    contest = await service.get(contest_id)
    if not await service.can_manage(contest, user):
        raise HTTPException(status_code=403, detail="Không phải contest của bạn")
    await service.delete(contest_id)
    return RedirectResponse(url="/contests", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{contest_id}/register", response_class=HTMLResponse)
async def register_contest(
    contest_id: UUID,
    user: User = Depends(require_user),
    service: ContestService = Depends(get_contest_service),
) -> Response:
    await service.get(contest_id)
    await service.register_user(contest_id, user.id)
    return RedirectResponse(url=f"/contests/{contest_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{contest_id}/problems", response_class=HTMLResponse)
async def assign_problem(
    contest_id: UUID,
    problem_id: UUID = Form(...),
    letter: str = Form(...),
    order_index: int = Form(0),
    points: int = Form(100),
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
    problem_service: ProblemService = Depends(get_problem_service),
) -> Response:
    contest = await service.get(contest_id)
    if not await service.can_manage(contest, user):
        raise HTTPException(status_code=403, detail="Không phải contest của bạn")
    try:
        await problem_service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    try:
        await service.assign_problem(
            contest_id,
            ContestProblemCreate(
                problem_id=problem_id,
                letter=letter,
                order_index=order_index,
                points=points,
            ),
        )
    except ContestLetterTakenError:
        pass
    except DomainError:
        pass
    return RedirectResponse(url=f"/contests/{contest_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{contest_id}/problems/{cp_id}/delete", response_class=HTMLResponse)
async def unassign_problem(
    contest_id: UUID,
    cp_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: ContestService = Depends(get_contest_service),
) -> Response:
    contest = await service.get(contest_id)
    if not await service.can_manage(contest, user):
        raise HTTPException(status_code=403, detail="Không phải contest của bạn")
    await service.unassign_problem(cp_id)
    return RedirectResponse(url=f"/contests/{contest_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{contest_id}/leaderboard", response_class=HTMLResponse)
async def leaderboard(
    contest_id: UUID,
    request: Request,
    user: User | None = Depends(get_current_user_optional),
    service: ContestService = Depends(get_contest_service),
    lb_service: LeaderboardService = Depends(get_leaderboard_service),
) -> Response:
    contest = await service.get(contest_id)
    if not await service.can_view(contest, user):
        raise HTTPException(status_code=403, detail="Bạn chưa đăng ký contest này")
    cps = await service.list_problems(contest_id)
    rows = await lb_service.compute(contest)
    phase = contest_phase(contest)
    ctx = {
        "contest": contest,
        "contest_problems": cps,
        "rows": rows,
        "phase": phase,
    }
    template = "contests/_leaderboard.html" if is_htmx(request) else "contests/leaderboard.html"
    return templates.TemplateResponse(request, template, ctx)
