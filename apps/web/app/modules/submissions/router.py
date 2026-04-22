"""HTTP routes cho Submission."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.core.templating import templates
from app.modules.problems.dependencies import get_problem_service
from app.modules.problems.service import ProblemService
from app.modules.submissions.dependencies import get_submission_service
from app.modules.submissions.models import Language, SubmissionStatus
from app.modules.submissions.schemas import SubmissionCreate
from app.modules.submissions.service import SubmissionService
from app.modules.users.dependencies import require_user
from app.modules.users.models import User
from app.shared.exceptions import EntityNotFoundError
from app.shared.htmx import is_htmx

router = APIRouter(prefix="/submissions", tags=["submissions"])

_FINAL_STATUSES = {
    SubmissionStatus.ACCEPTED,
    SubmissionStatus.WRONG_ANSWER,
    SubmissionStatus.TIME_LIMIT,
    SubmissionStatus.MEMORY_LIMIT,
    SubmissionStatus.RUNTIME_ERROR,
    SubmissionStatus.COMPILE_ERROR,
    SubmissionStatus.INTERNAL_ERROR,
}


@router.get("", response_class=HTMLResponse)
async def list_submissions(
    request: Request,
    service: SubmissionService = Depends(get_submission_service),
    user: User = Depends(require_user),
) -> Response:
    items = await service.list_recent(limit=100)
    template = "submissions/_table.html" if is_htmx(request) else "submissions/list.html"
    return templates.TemplateResponse(
        request,
        template,
        {"items": items, "final_statuses": _FINAL_STATUSES},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_submission_form(
    request: Request,
    problem_id: UUID,
    problems: ProblemService = Depends(get_problem_service),
    user: User = Depends(require_user),
) -> Response:
    try:
        problem = await problems.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return templates.TemplateResponse(
        request,
        "submissions/form.html",
        {"problem": problem, "languages": list(Language)},
    )


@router.post("", response_class=HTMLResponse)
async def submit(
    request: Request,
    problem_id: UUID = Form(...),
    language: Language = Form(...),
    source_code: str = Form(...),
    service: SubmissionService = Depends(get_submission_service),
    problems: ProblemService = Depends(get_problem_service),
    user: User = Depends(require_user),
) -> Response:
    try:
        problem = await problems.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    try:
        data = SubmissionCreate(
            problem_id=problem_id,
            language=language,
            source_code=source_code,
        )
    except ValidationError as e:
        return templates.TemplateResponse(
            request,
            "submissions/form.html",
            {
                "problem": problem,
                "languages": list(Language),
                "error": str(e),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    sub = await service.submit(data, user_id=user.id)
    return RedirectResponse(url=f"/submissions/{sub.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{submission_id}", response_class=HTMLResponse)
async def submission_detail(
    submission_id: UUID,
    request: Request,
    service: SubmissionService = Depends(get_submission_service),
    user: User = Depends(require_user),
) -> Response:
    try:
        sub = await service.get(submission_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    template = "submissions/_status.html" if is_htmx(request) else "submissions/detail.html"
    return templates.TemplateResponse(
        request,
        template,
        {"sub": sub, "is_final": sub.status in _FINAL_STATUSES},
    )
