"""Public user profile: /users/{username}.

Tách thành router riêng (prefix `/users`) để không bị bọc dưới `/auth`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from app.core.templating import templates
from app.modules.submissions.dependencies import get_submission_service
from app.modules.submissions.service import SubmissionService
from app.modules.users.dependencies import get_user_repository
from app.modules.users.repository import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{username}", response_class=HTMLResponse)
async def profile(
    username: str,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> Response:
    user = await user_repo.get_by_username(username)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User không tồn tại")

    recent = await submission_service.list_by_user(user.id, limit=20)
    accepted = await submission_service.count_accepted_problems(user.id)

    return templates.TemplateResponse(
        request,
        "users/profile.html",
        {
            "profile_user": user,
            "recent": recent,
            "accepted_count": accepted,
        },
    )
