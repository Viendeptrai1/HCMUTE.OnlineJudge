"""HTTP routes cho module Problems (HTML + HTMX partial)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

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

router = APIRouter(prefix="/problems", tags=["problems"])

_AUTHOR_ROLES = (UserRole.EDUCATOR, UserRole.ADMIN)
_PAGE_SIZE = 20


@router.get("")
async def list_problems(
    request: Request,
    q: str = Query("", description="Từ khoá tìm kiếm trong tiêu đề/đề bài"),
    difficulty: str = Query("", description="Lọc độ khó: easy|medium|hard"),
    tag: str = Query("", description="Slug tag để lọc"),
    page: int = Query(1, ge=1),
    service: ProblemService = Depends(get_problem_service),
    tag_service: TagService = Depends(get_tag_service),
) -> dict:
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
    
    return ctx


@router.post("")
async def create_problem(
    data: ProblemCreate,
    tags_csv: str = Query(""), # Tag có thể để dạng Query string hoặc gắn vào DTO sau
    service: ProblemService = Depends(get_problem_service),
    tag_service: TagService = Depends(get_tag_service),
    user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> dict:
    
    problem = await service.create_problem(data, author_id=user.id)
    
    slugs = [s for s in tags_csv.split(",") if s.strip()]
    if slugs:
        await tag_service.set_for_problem(problem.id, slugs)
        
    return {"message": "Tạo bài tập thành công", "problem_id": str(problem.id)}


@router.get("/{problem_id}")
async def problem_detail(
    problem_id: UUID,
    contest_id: UUID | None = Query(None),
    service: ProblemService = Depends(get_problem_service),
    tc_service: TestcaseService = Depends(get_testcase_service),
    tag_service: TagService = Depends(get_tag_service),
    submission_service: SubmissionService = Depends(get_submission_service),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
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

    return {
        "problem": problem,
        "samples": samples,
        "testcase_count": len(all_tcs),
        "problem_tags": problem_tags,
        "my_subs": my_subs,
        "has_solved": has_solved,
        "can_see_editorial": can_see_editorial,
        "contest_id": contest_id,
    }


# 1. Đổi @router.post thành @router.put (chuẩn REST API cho Update)
@router.put("/{problem_id}")
async def update_problem(
    problem_id: UUID,
    data: ProblemUpdate, # 2. Nhận nguyên một Object JSON từ Frontend
    tags_csv: str = Query(""), # Lấy tag từ URL query string
    service: ProblemService = Depends(get_problem_service),
    tag_service: TagService = Depends(get_tag_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)), # Chặn quyền: Chỉ Giáo viên/Admin mới được sửa
) -> dict: # 3. Trả về kiểu dict (JSON)
    
    try:
        # Gọi xuống service để update dữ liệu vào Database
        await service.update_problem(problem_id, data)
    except EntityNotFoundError as e:
        # Nếu không tìm thấy bài tập -> Ném lỗi 404
        raise HTTPException(status_code=404, detail=str(e)) from e
        
    # Cập nhật lại Tags (nếu có truyền lên)
    slugs = [s for s in tags_csv.split(",") if s.strip()]
    if slugs:
        await tag_service.set_for_problem(problem_id, slugs)
        
    # 4. Trả về JSON báo thành công thay vì Redirect HTML
    return {
        "message": "Cập nhật bài tập thành công", 
        "problem_id": str(problem_id)
    }


@router.delete("/{problem_id}")
async def delete_problem(
    problem_id: UUID,
    service: ProblemService = Depends(get_problem_service),
    _user: User = Depends(require_role(*_AUTHOR_ROLES)),
) -> dict:
    try:
        await service.delete_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"message": "Đã xóa bài tập"}
