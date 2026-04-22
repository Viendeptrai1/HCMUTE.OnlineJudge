"""HTTP routes cho module Courses.

Routes:
- GET    /courses                              — danh sách lớp của viewer
- GET    /courses/new                          — form tạo lớp (educator+)
- POST   /courses                              — tạo lớp
- GET    /courses/{id}                         — chi tiết lớp + assignments + progress
- GET    /courses/{id}/edit                    — form sửa (owner)
- POST   /courses/{id}                         — cập nhật
- POST   /courses/{id}/delete                  — xoá
- POST   /courses/{id}/members                 — invite user vào lớp
- POST   /courses/{id}/members/{enrollment_id}/delete — kick user
- POST   /courses/{id}/assignments             — gán problem vào lớp
- POST   /courses/{id}/assignments/{aid}/delete — bỏ gán
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.templating import templates
from app.modules.courses.dependencies import (
    get_assignment_service,
    get_course_service,
    get_enrollment_service,
    get_progress_service,
)
from app.modules.courses.models import CourseRole
from app.modules.courses.progress import ProgressService
from app.modules.courses.schemas import (
    CourseCreate,
    CourseProblemCreate,
    CourseUpdate,
)
from app.modules.courses.service import (
    AlreadyEnrolledError,
    AssignmentService,
    CourseCodeTakenError,
    CourseService,
    EnrollmentService,
    ProblemAlreadyAssignedError,
)
from app.modules.problems.dependencies import get_problem_service
from app.modules.problems.service import ProblemService
from app.modules.users.dependencies import require_role, require_user
from app.modules.users.models import User, UserRole
from app.shared.exceptions import DomainError, EntityNotFoundError

router = APIRouter(prefix="/courses", tags=["courses"])

_MANAGE_ROLES = (UserRole.EDUCATOR, UserRole.ADMIN)


@router.get("", response_class=HTMLResponse)
async def list_courses(
    request: Request,
    user: User = Depends(require_user),
    service: CourseService = Depends(get_course_service),
) -> Response:
    courses = await service.list_for_viewer(user)
    return templates.TemplateResponse(
        request,
        "courses/list.html",
        {"courses": courses, "manage_roles": _MANAGE_ROLES},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_course_form(
    request: Request,
    _user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> Response:
    return templates.TemplateResponse(
        request,
        "courses/form.html",
        {"course": None, "error": None},
    )


@router.post("", response_class=HTMLResponse)
async def create_course(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    semester: str = Form(""),
    description: str = Form(""),
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: CourseService = Depends(get_course_service),
) -> Response:
    try:
        course = await service.create(
            educator_id=user.id,
            data=CourseCreate(
                code=code, name=name, semester=semester, description=description
            ),
        )
    except CourseCodeTakenError as e:
        return templates.TemplateResponse(
            request,
            "courses/form.html",
            {
                "course": None,
                "error": str(e),
                "form": {
                    "code": code,
                    "name": name,
                    "semester": semester,
                    "description": description,
                },
            },
            status_code=400,
        )
    return RedirectResponse(
        url=f"/courses/{course.id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/{course_id}", response_class=HTMLResponse)
async def course_detail(
    course_id: UUID,
    request: Request,
    user: User = Depends(require_user),
    course_service: CourseService = Depends(get_course_service),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
    assignment_service: AssignmentService = Depends(get_assignment_service),
    progress_service: ProgressService = Depends(get_progress_service),
) -> Response:
    try:
        course = await course_service.get(course_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    is_member = await course_service.is_member(course, user)
    if not is_member:
        raise HTTPException(
            status_code=403,
            detail="Bạn chưa được thêm vào lớp này",
        )

    can_manage = await course_service.can_manage(course, user)
    members = await enrollment_service.list_members(course_id)
    assignments = await assignment_service.list_for_course(course_id)
    user_progress = await progress_service.problem_progress_for_user(course_id, user.id)
    member_progress = (
        await progress_service.member_progress(course_id) if can_manage else []
    )

    return templates.TemplateResponse(
        request,
        "courses/detail.html",
        {
            "course": course,
            "members": members,
            "assignments": assignments,
            "can_manage": can_manage,
            "user_progress": user_progress,
            "member_progress": member_progress,
            "now": datetime.utcnow(),
        },
    )


@router.get("/{course_id}/edit", response_class=HTMLResponse)
async def edit_course_form(
    course_id: UUID,
    request: Request,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: CourseService = Depends(get_course_service),
) -> Response:
    try:
        course = await service.get(course_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if not await service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    return templates.TemplateResponse(
        request, "courses/form.html", {"course": course, "error": None}
    )


@router.post("/{course_id}", response_class=HTMLResponse)
async def update_course(
    course_id: UUID,
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    semester: str = Form(""),
    description: str = Form(""),
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: CourseService = Depends(get_course_service),
) -> Response:
    course = await service.get(course_id)
    if not await service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    try:
        await service.update(
            course_id,
            CourseUpdate(code=code, name=name, semester=semester, description=description),
        )
    except CourseCodeTakenError as e:
        return templates.TemplateResponse(
            request,
            "courses/form.html",
            {"course": course, "error": str(e)},
            status_code=400,
        )
    return RedirectResponse(
        url=f"/courses/{course_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{course_id}/delete", response_class=HTMLResponse)
async def delete_course(
    course_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: CourseService = Depends(get_course_service),
) -> Response:
    course = await service.get(course_id)
    if not await service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    await service.delete(course_id)
    return RedirectResponse(url="/courses", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{course_id}/members", response_class=HTMLResponse)
async def invite_member(
    course_id: UUID,
    username_or_email: str = Form(...),
    role_in_course: CourseRole = Form(CourseRole.STUDENT),
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> Response:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    try:
        await enrollment_service.enroll_by_identifier(
            course_id, username_or_email, role_in_course
        )
    except (DomainError, AlreadyEnrolledError):
        # Fail silently → redirect về trang lớp để UI hiển thị danh sách hiện tại.
        # (Có thể cải thiện flash message sau.)
        pass
    return RedirectResponse(
        url=f"/courses/{course_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{course_id}/members/{enrollment_id}/delete", response_class=HTMLResponse)
async def remove_member(
    course_id: UUID,
    enrollment_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> Response:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    await enrollment_service.remove(enrollment_id)
    return RedirectResponse(
        url=f"/courses/{course_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{course_id}/assignments", response_class=HTMLResponse)
async def assign_problem(
    course_id: UUID,
    problem_id: UUID = Form(...),
    deadline: str = Form(""),
    weight: int = Form(10),
    order_index: int = Form(0),
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    assignment_service: AssignmentService = Depends(get_assignment_service),
    problem_service: ProblemService = Depends(get_problem_service),
) -> Response:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    # Verify problem tồn tại
    try:
        await problem_service.get_problem(problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    parsed_deadline: datetime | None = None
    if deadline.strip():
        # input type="datetime-local" trả "YYYY-MM-DDTHH:MM"
        try:
            parsed_deadline = datetime.fromisoformat(deadline)
        except ValueError:
            parsed_deadline = None

    try:
        await assignment_service.assign(
            course_id,
            CourseProblemCreate(
                problem_id=problem_id,
                deadline=parsed_deadline,
                weight=weight,
                order_index=order_index,
            ),
        )
    except ProblemAlreadyAssignedError:
        pass
    return RedirectResponse(
        url=f"/courses/{course_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post(
    "/{course_id}/assignments/{assignment_id}/delete", response_class=HTMLResponse
)
async def unassign_problem(
    course_id: UUID,
    assignment_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    assignment_service: AssignmentService = Depends(get_assignment_service),
) -> Response:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    await assignment_service.unassign(assignment_id)
    return RedirectResponse(
        url=f"/courses/{course_id}", status_code=status.HTTP_303_SEE_OTHER
    )
