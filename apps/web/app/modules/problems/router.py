"""HTTP routes cho module Problems (HTML + HTMX partial)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.templating import templates
from app.modules.problems.dependencies import get_problem_service
from app.modules.problems.models import Difficulty
from app.modules.problems.schemas import ProblemCreate, ProblemUpdate
from app.modules.problems.service import ProblemService
from app.modules.users.dependencies import require_role
from app.modules.users.models import User, UserRole
from app.shared.exceptions import EntityNotFoundError
from app.shared.htmx import is_htmx

router = APIRouter(prefix="/problems", tags=["problems"])

_AUTHOR_ROLES = (UserRole.EDUCATOR, UserRole.ADMIN)


@router.get("", response_class=HTMLResponse)
async def list_problems(
    request: Request,
    service: ProblemService = Depends(get_problem_service),
) -> Response:
    problems = await service.list_problems()
    template = "problems/_table.html" if is_htmx(request) else "problems/list.html"
    return templates.TemplateResponse(request, template, {"problems": problems})


@router.get("/new", response_class=HTMLResponse)
async def new_problem_form(
    request: Request,
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    return templates.TemplateResponse(
        request,
        "problems/form.html",
        {"problem": None, "difficulties": list(Difficulty)},
    )


@router.post("", response_class=HTMLResponse)
async def create_problem(
    title: str = Form(...),
    statement_md: str = Form(""),
    time_limit_ms: int = Form(1000),
    memory_limit_kb: int = Form(262144),
    difficulty: Difficulty = Form(Difficulty.EASY),
    service: ProblemService = Depends(get_problem_service),
    user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    data = ProblemCreate(
        title=title,
        statement_md=statement_md,
        time_limit_ms=time_limit_ms,
        memory_limit_kb=memory_limit_kb,
        difficulty=difficulty,
    )
    problem = await service.create_problem(data, author_id=user.id)
    return RedirectResponse(url=f"/problems/{problem.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{problem_id}", response_class=HTMLResponse)
async def problem_detail(
    problem_id: UUID,
    request: Request,
    service: ProblemService = Depends(get_problem_service),
) -> Response:
    try:
        problem = await service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return templates.TemplateResponse(
        request,
        "problems/detail.html",
        {"problem": problem, "author_roles": _AUTHOR_ROLES},
    )


@router.get("/{problem_id}/edit", response_class=HTMLResponse)
async def edit_problem_form(
    problem_id: UUID,
    request: Request,
    service: ProblemService = Depends(get_problem_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    try:
        problem = await service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return templates.TemplateResponse(
        request,
        "problems/form.html",
        {"problem": problem, "difficulties": list(Difficulty)},
    )


@router.post("/{problem_id}", response_class=HTMLResponse)
async def update_problem(
    problem_id: UUID,
    title: str = Form(...),
    statement_md: str = Form(""),
    time_limit_ms: int = Form(1000),
    memory_limit_kb: int = Form(262144),
    difficulty: Difficulty = Form(Difficulty.EASY),
    service: ProblemService = Depends(get_problem_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    data = ProblemUpdate(
        title=title,
        statement_md=statement_md,
        time_limit_ms=time_limit_ms,
        memory_limit_kb=memory_limit_kb,
        difficulty=difficulty,
    )
    try:
        await service.update_problem(problem_id, data)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return RedirectResponse(url=f"/problems/{problem_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.delete("/{problem_id}", response_class=HTMLResponse)
async def delete_problem(
    problem_id: UUID,
    request: Request,
    service: ProblemService = Depends(get_problem_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    try:
        await service.delete_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if is_htmx(request):
        return HTMLResponse(content="", status_code=200)
    return RedirectResponse(url="/problems", status_code=status.HTTP_303_SEE_OTHER)
