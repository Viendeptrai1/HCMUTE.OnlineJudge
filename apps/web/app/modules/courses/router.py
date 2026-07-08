"""HTTP routes cho module Courses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel

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
    EnrollmentCreate,
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

class JoinCourseRequest(BaseModel):
    invite_code: str


@router.get("")
async def list_courses(
    user: User = Depends(require_user),
    service: CourseService = Depends(get_course_service),
) -> dict:
    courses = await service.list_for_viewer(user)
    return {"courses": courses}


@router.post("")
async def create_course(
    data: CourseCreate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: CourseService = Depends(get_course_service),
) -> dict:
    try:
        course = await service.create(
            educator_id=user.id,
            data=data,
        )
        return {"message": "Tạo lớp học thành công", "course_id": str(course.id)}
    except CourseCodeTakenError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/join")
async def join_course_by_invite(
    data: JoinCourseRequest,
    user: User = Depends(require_user),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> dict:
    try:
        enrollment = await enrollment_service.enroll_by_invite_code(
            data.invite_code.strip(), user.id
        )
        return {"message": "Đã tham gia lớp học", "course_id": str(enrollment.course_id)}
    except (EntityNotFoundError, AlreadyEnrolledError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{course_id}")
async def course_detail(
    course_id: UUID,
    user: User = Depends(require_user),
    course_service: CourseService = Depends(get_course_service),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
    assignment_service: AssignmentService = Depends(get_assignment_service),
    progress_service: ProgressService = Depends(get_progress_service),
) -> dict:
    try:
        course = await course_service.get(course_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

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

    return {
        "course": course,
        "members": members,
        "assignments": assignments,
        "can_manage": can_manage,
        "user_progress": user_progress,
        "member_progress": member_progress,
        "now": datetime.utcnow(),
    }


@router.put("/{course_id}")
async def update_course(
    course_id: UUID,
    data: CourseUpdate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: CourseService = Depends(get_course_service),
) -> dict:
    course = await service.get(course_id)
    if not await service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    try:
        await service.update(course_id, data)
        return {"message": "Cập nhật thành công", "course_id": str(course_id)}
    except CourseCodeTakenError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{course_id}")
async def delete_course(
    course_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    service: CourseService = Depends(get_course_service),
) -> dict:
    course = await service.get(course_id)
    if not await service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    await service.delete(course_id)
    return {"message": "Đã xóa lớp học"}


@router.post("/{course_id}/members")
async def invite_member(
    course_id: UUID,
    data: EnrollmentCreate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> dict:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    try:
        await enrollment_service.enroll_by_identifier(
            course_id, data.username_or_email, data.role_in_course
        )
        return {"message": "Đã thêm thành viên"}
    except (DomainError, AlreadyEnrolledError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{course_id}/members/{enrollment_id}")
async def remove_member(
    course_id: UUID,
    enrollment_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> dict:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    await enrollment_service.remove(enrollment_id)
    return {"message": "Đã xóa thành viên"}


@router.post("/{course_id}/import-students")
async def import_students(
    course_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> dict:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    
    content = await file.read()
    text_content = content.decode("utf-8-sig", errors="ignore")
    result = await enrollment_service.import_from_csv_content(course_id, text_content)
    
    return {"result": result}


@router.get("/{course_id}/export")
async def export_course_scores(
    course_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    progress_service: ProgressService = Depends(get_progress_service),
) -> dict:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
        
    member_progress = await progress_service.member_progress(course_id)
    
    data = []
    for p in member_progress:
        data.append({
            "MSSV": p.user.student_code or "",
            "Ho Ten": p.user.full_name or p.user.username,
            "Email": p.user.email,
            "Diem": p.total_score,
            "Hoan Thanh": p.completed_count
        })
        
    return {"export_data": data}


@router.post("/{course_id}/assignments")
async def assign_problem(
    course_id: UUID,
    data: CourseProblemCreate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    assignment_service: AssignmentService = Depends(get_assignment_service),
    problem_service: ProblemService = Depends(get_problem_service),
) -> dict:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    try:
        await problem_service.get_problem(data.problem_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        await assignment_service.assign(course_id, data)
        return {"message": "Đã giao bài tập"}
    except ProblemAlreadyAssignedError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{course_id}/assignments/{assignment_id}")
async def unassign_problem(
    course_id: UUID,
    assignment_id: UUID,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    course_service: CourseService = Depends(get_course_service),
    assignment_service: AssignmentService = Depends(get_assignment_service),
) -> dict:
    course = await course_service.get(course_id)
    if not await course_service.can_manage(course, user):
        raise HTTPException(status_code=403, detail="Không phải lớp của bạn")
    await assignment_service.unassign(assignment_id)
    return {"message": "Đã hủy giao bài tập"}
