"""Public user profile: /users/{username}.

Tách thành router riêng (prefix `/users`) để không bị bọc dưới `/auth`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.modules.submissions.dependencies import get_submission_service
from app.modules.submissions.service import SubmissionService
from app.modules.users.dependencies import get_user_repository
from app.modules.users.repository import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{username}")
async def profile(
    username: str,
    user_repo: UserRepository = Depends(get_user_repository),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> dict:
    user = await user_repo.get_by_username(username)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User không tồn tại")

    recent = await submission_service.list_by_user(user.id, limit=20)
    accepted = await submission_service.count_accepted_problems(user.id)

    return {
        "profile_user": {
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "student_code": user.student_code,
            "class_name": user.class_name,
            "role": user.role.value,
        },
        "recent_submissions": recent,
        "accepted_count": accepted,
    }
