"""HTTP routes cho Testcase — lồng dưới /problems/{problem_id}/testcases."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.templating import templates
from app.modules.problems.dependencies import get_problem_service
from app.modules.problems.service import ProblemService
from app.modules.testcases.dependencies import get_testcase_service
from app.modules.testcases.schemas import TestcaseCreate, TestcaseUpdate
from app.modules.testcases.service import TestcaseService
from app.modules.users.dependencies import require_role
from app.modules.users.models import User, UserRole
from app.shared.exceptions import EntityNotFoundError

router = APIRouter(prefix="/problems/{problem_id}/testcases", tags=["testcases"])

_AUTHOR_ROLES = (UserRole.EDUCATOR, UserRole.ADMIN)


@router.get("", response_class=HTMLResponse)
async def list_testcases(
    problem_id: UUID,
    request: Request,
    problem_service: ProblemService = Depends(get_problem_service),
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    try:
        problem = await problem_service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    testcases = await tc_service.list_for_problem(problem_id)
    return templates.TemplateResponse(
        request,
        "testcases/list.html",
        {"problem": problem, "testcases": testcases},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_testcase_form(
    problem_id: UUID,
    request: Request,
    problem_service: ProblemService = Depends(get_problem_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    try:
        problem = await problem_service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return templates.TemplateResponse(
        request,
        "testcases/form.html",
        {"problem": problem, "testcase": None},
    )


@router.post("", response_class=HTMLResponse)
async def create_testcase(
    problem_id: UUID,
    input_text: str = Form(""),
    expected_output: str = Form(""),
    is_sample: bool = Form(False),
    score: int = Form(10),
    order_index: int = Form(0),
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    await tc_service.create(
        problem_id,
        TestcaseCreate(
            input_text=input_text,
            expected_output=expected_output,
            is_sample=is_sample,
            score=score,
            order_index=order_index,
        ),
    )
    return RedirectResponse(
        url=f"/problems/{problem_id}/testcases",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{tc_id}/edit", response_class=HTMLResponse)
async def edit_testcase_form(
    problem_id: UUID,
    tc_id: UUID,
    request: Request,
    problem_service: ProblemService = Depends(get_problem_service),
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    try:
        problem = await problem_service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    tcs = await tc_service.list_for_problem(problem_id)
    tc = next((t for t in tcs if t.id == tc_id), None)
    if tc is None:
        raise HTTPException(status_code=404, detail="Testcase not found")
    return templates.TemplateResponse(
        request,
        "testcases/form.html",
        {"problem": problem, "testcase": tc},
    )


@router.post("/{tc_id}", response_class=HTMLResponse)
async def update_testcase(
    problem_id: UUID,
    tc_id: UUID,
    input_text: str = Form(""),
    expected_output: str = Form(""),
    is_sample: bool = Form(False),
    score: int = Form(10),
    order_index: int = Form(0),
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    await tc_service.update(
        tc_id,
        TestcaseUpdate(
            input_text=input_text,
            expected_output=expected_output,
            is_sample=is_sample,
            score=score,
            order_index=order_index,
        ),
    )
    return RedirectResponse(
        url=f"/problems/{problem_id}/testcases",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{tc_id}/delete", response_class=HTMLResponse)
async def delete_testcase(
    problem_id: UUID,
    tc_id: UUID,
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> Response:
    await tc_service.delete(tc_id)
    return RedirectResponse(
        url=f"/problems/{problem_id}/testcases",
        status_code=status.HTTP_303_SEE_OTHER,
    )
