"""HTTP routes cho Testcase — lồng dưới /problems/{problem_id}/testcases."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

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


@router.get("")
async def list_testcases(
    problem_id: UUID,
    problem_service: ProblemService = Depends(get_problem_service),
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> dict:
    try:
        await problem_service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    testcases = await tc_service.list_for_problem(problem_id)
    return {"testcases": testcases}


@router.post("")
async def create_testcase(
    problem_id: UUID,
    data: TestcaseCreate,
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> dict:
    await tc_service.create(problem_id, data)
    return {"message": "Tạo testcase thành công"}


@router.post("/upload-zip")
async def upload_testcases_zip(
    problem_id: UUID,
    file: UploadFile = File(...),
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> dict:
    content = await file.read()
    result = await tc_service.create_from_zip(problem_id, content)
    return {"result": result}


@router.put("/{tc_id}")
async def update_testcase(
    problem_id: UUID,
    tc_id: UUID,
    data: TestcaseUpdate,
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> dict:
    await tc_service.update(tc_id, data)
    return {"message": "Cập nhật testcase thành công"}


@router.delete("/{tc_id}")
async def delete_testcase(
    problem_id: UUID,
    tc_id: UUID,
    tc_service: TestcaseService = Depends(get_testcase_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> dict:
    await tc_service.delete(tc_id)
    return {"message": "Đã xóa testcase"}
