"""HTTP routes cho Submission."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.problems.dependencies import get_problem_service
from app.modules.problems.service import ProblemService
from app.modules.submissions.dependencies import get_submission_service
from app.modules.submissions.models import Language, SubmissionStatus
from app.modules.submissions.schemas import SubmissionCreate
from app.modules.submissions.service import SubmissionService
from app.modules.users.dependencies import require_user
from app.modules.users.models import User
from app.shared.exceptions import EntityNotFoundError

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


@router.get("")
async def list_submissions(
    service: SubmissionService = Depends(get_submission_service),
    user: User = Depends(require_user),
) -> dict:
    items = await service.list_recent(limit=100)
    return {"items": items, "final_statuses": list(s.value for s in _FINAL_STATUSES)}


@router.post("")
async def submit(
    data: SubmissionCreate,
    service: SubmissionService = Depends(get_submission_service),
    problems: ProblemService = Depends(get_problem_service),
    user: User = Depends(require_user),
) -> dict:
    try:
        await problems.get_problem(data.problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    sub = await service.submit(data, user_id=user.id)
    return {"message": "Nộp bài thành công", "submission_id": str(sub.id)}


@router.get("/{submission_id}")
async def submission_detail(
    submission_id: UUID,
    service: SubmissionService = Depends(get_submission_service),
    user: User = Depends(require_user),
) -> dict:
    try:
        sub = await service.get(submission_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "submission": sub,
        "is_final": sub.status in _FINAL_STATUSES
    }
