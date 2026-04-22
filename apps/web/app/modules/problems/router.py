"""HTTP routes cho module Problems (HTML + HTMX partial)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.templating import templates
from app.modules.problems.dependencies import get_problem_service
from app.modules.problems.models import Difficulty
from app.modules.problems.schemas import ProblemCreate, ProblemUpdate
from app.modules.problems.service import ProblemService
from app.modules.submissions.dependencies import get_submission_service
from app.modules.submissions.service import SubmissionService
from app.modules.tags.dependencies import get_tag_service
from app.modules.tags.service import TagService
from app.modules.testcases.dependencies import get_testcase_service
from app.modules.testcases.service import TestcaseService
from app.modules.users.dependencies import get_current_user_optional, require_role
from app.modules.users.models import User, UserRole
from app.shared.exceptions import EntityNotFoundError
from app.shared.htmx import is_htmx

router = APIRouter(prefix="/problems", tags=["problems"])

_AUTHOR_ROLES = (UserRole.EDUCATOR, UserRole.ADMIN)
_PAGE_SIZE = 20


@router.get("", response_class=HTMLResponse)
async def list_problems(
    request: Request,
    q: str = Query("", description="Từ khoá tìm kiếm trong tiêu đề/đề bài"),
    difficulty: str = Query("", description="Lọc độ khó: easy|medium|hard"),
    tag: str = Query("", description="Slug tag để lọc"),
    page: int = Query(1, ge=1),
    service: ProblemService = Depends(get_problem_service),
    tag_service: TagService = Depends(get_tag_service),
) -> Response:
    diff_filter: Difficulty | None = None
    if difficulty and difficulty in (d.value for d in Difficulty):
        diff_filter = Difficulty(difficulty)

    problem_ids_filter = None
    if tag:
        ids = await tag_service.list_problem_ids_for_slug(tag)
        problem_ids_filter = list(ids)

    offset = (page - 1) * _PAGE_SIZE
    problems, total = await service.search(
        q=q or None,
        difficulty=diff_filter,
        problem_ids=problem_ids_filter,
        limit=_PAGE_SIZE,
        offset=offset,
    )
    tags_by_problem = await tag_service.list_tags_for_problems([p.id for p in problems])
    all_tags = await tag_service.list_all()
    total_pages = (total + _PAGE_SIZE - 1) // _PAGE_SIZE

    ctx = {
        "problems": problems,
        "tags_by_problem": tags_by_problem,
        "all_tags": all_tags,
        "q": q,
        "difficulty": difficulty,
        "tag": tag,
        "page": page,
        "total": total,
        "total_pages": max(total_pages, 1),
        "page_size": _PAGE_SIZE,
        "difficulties": list(Difficulty),
    }
    template = "problems/_table.html" if is_htmx(request) else "problems/list.html"
    return templates.TemplateResponse(request, template, ctx)


@router.get("/new", response_class=HTMLResponse)
async def new_problem_form(
    request: Request,
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    return templates.TemplateResponse(
        request,
        "problems/form.html",
        {
            "problem": None,
            "difficulties": list(Difficulty),
            "problem_tag_slugs": "",
        },
    )


@router.post("", response_class=HTMLResponse)
async def create_problem(
    title: str = Form(...),
    statement_md: str = Form(""),
    editorial_md: str = Form(""),
    time_limit_ms: int = Form(1000),
    memory_limit_kb: int = Form(262144),
    difficulty: Difficulty = Form(Difficulty.EASY),
    tags_csv: str = Form(""),
    service: ProblemService = Depends(get_problem_service),
    tag_service: TagService = Depends(get_tag_service),
    user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    data = ProblemCreate(
        title=title,
        statement_md=statement_md,
        editorial_md=editorial_md,
        time_limit_ms=time_limit_ms,
        memory_limit_kb=memory_limit_kb,
        difficulty=difficulty,
    )
    problem = await service.create_problem(data, author_id=user.id)
    slugs = [s for s in tags_csv.split(",") if s.strip()]
    if slugs:
        await tag_service.set_for_problem(problem.id, slugs)
    return RedirectResponse(url=f"/problems/{problem.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{problem_id}", response_class=HTMLResponse)
async def problem_detail(
    problem_id: UUID,
    request: Request,
    service: ProblemService = Depends(get_problem_service),
    tc_service: TestcaseService = Depends(get_testcase_service),
    tag_service: TagService = Depends(get_tag_service),
    submission_service: SubmissionService = Depends(get_submission_service),
    current_user: User | None = Depends(get_current_user_optional),
) -> Response:
    try:
        problem = await service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    all_tcs = await tc_service.list_for_problem(problem_id)
    samples = [tc for tc in all_tcs if tc.is_sample]
    problem_tags = await tag_service.list_for_problem(problem_id)

    # Lịch sử nộp + editorial visibility.
    my_subs: list = []
    has_solved = False
    if current_user is not None:
        my_subs = list(
            await submission_service.list_by_user_and_problem(
                current_user.id, problem_id, limit=10
            )
        )
        has_solved = any(s.status.value == "accepted" for s in my_subs)

    can_see_editorial = (
        current_user is not None
        and (
            has_solved
            or current_user.role in _AUTHOR_ROLES
        )
    )

    return templates.TemplateResponse(
        request,
        "problems/detail.html",
        {
            "problem": problem,
            "author_roles": _AUTHOR_ROLES,
            "samples": samples,
            "testcase_count": len(all_tcs),
            "problem_tags": problem_tags,
            "my_subs": my_subs,
            "has_solved": has_solved,
            "can_see_editorial": can_see_editorial,
        },
    )


@router.get("/{problem_id}/edit", response_class=HTMLResponse)
async def edit_problem_form(
    problem_id: UUID,
    request: Request,
    service: ProblemService = Depends(get_problem_service),
    tag_service: TagService = Depends(get_tag_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    try:
        problem = await service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    current_tags = await tag_service.list_for_problem(problem_id)
    return templates.TemplateResponse(
        request,
        "problems/form.html",
        {
            "problem": problem,
            "difficulties": list(Difficulty),
            "problem_tag_slugs": ",".join(t.slug for t in current_tags),
        },
    )


@router.post("/{problem_id}", response_class=HTMLResponse)
async def update_problem(
    problem_id: UUID,
    title: str = Form(...),
    statement_md: str = Form(""),
    editorial_md: str = Form(""),
    time_limit_ms: int = Form(1000),
    memory_limit_kb: int = Form(262144),
    difficulty: Difficulty = Form(Difficulty.EASY),
    tags_csv: str = Form(""),
    service: ProblemService = Depends(get_problem_service),
    tag_service: TagService = Depends(get_tag_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    data = ProblemUpdate(
        title=title,
        statement_md=statement_md,
        editorial_md=editorial_md,
        time_limit_ms=time_limit_ms,
        memory_limit_kb=memory_limit_kb,
        difficulty=difficulty,
    )
    try:
        await service.update_problem(problem_id, data)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    slugs = [s for s in tags_csv.split(",") if s.strip()]
    await tag_service.set_for_problem(problem_id, slugs)
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
