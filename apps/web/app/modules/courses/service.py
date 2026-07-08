"""Business logic cho Courses / Enrollments / Assignments.

Tách 3 service nhỏ để từng use case có dependency rõ ràng (SRP).
"""

from __future__ import annotations

from collections.abc import Sequence
import uuid
from uuid import UUID

from app.modules.courses.models import Course, CourseProblem, CourseRole, Enrollment
from app.modules.courses.repository import (
    CourseProblemRepository,
    CourseRepository,
    EnrollmentRepository,
)
from app.modules.courses.schemas import (
    CourseCreate,
    CourseProblemCreate,
    CourseProblemUpdate,
    CourseUpdate,
)
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.shared.exceptions import DomainError, EntityNotFoundError


class CourseCodeTakenError(DomainError):
    pass


class AlreadyEnrolledError(DomainError):
    pass


class ProblemAlreadyAssignedError(DomainError):
    pass


class CourseService:
    def __init__(
        self,
        course_repo: CourseRepository,
        enrollment_repo: EnrollmentRepository,
    ) -> None:
        self._courses = course_repo
        self._enrollments = enrollment_repo

    async def list_for_viewer(self, viewer: User | None) -> Sequence[Course]:
        """Admin thấy mọi course; educator thấy course mình tạo; student thấy course đã enroll.
        Viewer None → danh sách rỗng (chưa login)."""
        if viewer is None:
            return []
        from app.modules.users.models import UserRole  # tránh circular at top

        if viewer.role == UserRole.ADMIN:
            return await self._courses.list_all()
        if viewer.role == UserRole.EDUCATOR:
            return await self._courses.list_by_educator(viewer.id)
        return await self._courses.list_for_user(viewer.id)

    async def get(self, course_id: UUID) -> Course:
        course = await self._courses.get(course_id)
        if course is None:
            raise EntityNotFoundError("Course", course_id)
        return course

    async def create(self, educator_id: UUID, data: CourseCreate) -> Course:
        existing = await self._courses.get_by_code(data.code)
        if existing is not None:
            raise CourseCodeTakenError(f"Mã lớp '{data.code}' đã tồn tại")
        course = Course(
            code=data.code,
            name=data.name,
            semester=data.semester,
            description=data.description,
            invite_code=uuid.uuid4().hex[:8].upper(),
            educator_id=educator_id,
        )
        return await self._courses.add(course)

    async def update(self, course_id: UUID, data: CourseUpdate) -> Course:
        course = await self.get(course_id)
        updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        if "code" in updates and updates["code"] != course.code:
            collision = await self._courses.get_by_code(str(updates["code"]))
            if collision is not None and collision.id != course_id:
                raise CourseCodeTakenError(f"Mã lớp '{updates['code']}' đã tồn tại")
        return await self._courses.update(course, updates)

    async def delete(self, course_id: UUID) -> None:
        await self._courses.delete(course_id)

    async def can_manage(self, course: Course, user: User) -> bool:
        """Admin hoặc educator sở hữu course."""
        from app.modules.users.models import UserRole

        return user.role == UserRole.ADMIN or course.educator_id == user.id

    async def is_member(self, course: Course, user: User) -> bool:
        """Educator sở hữu, admin, hoặc student/ta đã enroll."""
        if await self.can_manage(course, user):
            return True
        return await self._enrollments.get(course.id, user.id) is not None


class EnrollmentService:
    def __init__(
        self,
        course_repo: CourseRepository,
        enrollment_repo: EnrollmentRepository,
        user_repo: UserRepository,
    ) -> None:
        self._courses = course_repo
        self._enrollments = enrollment_repo
        self._users = user_repo

    async def list_members(self, course_id: UUID) -> Sequence[Enrollment]:
        return await self._enrollments.list_by_course(course_id)

    async def enroll_by_identifier(
        self,
        course_id: UUID,
        identifier: str,
        role_in_course: CourseRole = CourseRole.STUDENT,
    ) -> Enrollment:
        course = await self._courses.get(course_id)
        if course is None:
            raise EntityNotFoundError("Course", course_id)
        # identifier = email hoặc username
        user = await self._users.get_by_identifier(identifier)
        if user is None:
            raise EntityNotFoundError("User", identifier)
        existing = await self._enrollments.get(course_id, user.id)
        if existing is not None:
            raise AlreadyEnrolledError(f"{user.username} đã trong lớp")
        enrollment = Enrollment(
            course_id=course_id,
            user_id=user.id,
            role_in_course=role_in_course,
        )
        return await self._enrollments.add(enrollment)

    async def enroll_by_invite_code(
        self, invite_code: str, user_id: UUID
    ) -> Enrollment:
        course = await self._courses.get_by_invite_code(invite_code)
        if course is None:
            raise EntityNotFoundError("Course", invite_code)
        existing = await self._enrollments.get(course.id, user_id)
        if existing is not None:
            raise AlreadyEnrolledError("Bạn đã tham gia lớp này")
        enrollment = Enrollment(
            course_id=course.id,
            user_id=user_id,
            role_in_course=CourseRole.STUDENT,
        )
        return await self._enrollments.add(enrollment)

    async def remove(self, enrollment_id: UUID) -> None:
        await self._enrollments.delete(enrollment_id)

    async def import_from_csv_content(self, course_id: UUID, content: str) -> dict[str, int]:
        import csv
        from app.modules.users.models import User, UserRole
        from app.modules.users.security import hash_password
        import time

        course = await self._courses.get(course_id)
        if course is None:
            raise EntityNotFoundError("Course", course_id)

        lines = content.strip().splitlines()
        if not lines:
            return {"success": 0, "error": 0}

        reader = csv.DictReader(lines)
        success_count = 0
        error_count = 0

        for row in reader:
            row_lower = {k.strip().lower() if k else "": v.strip() for k, v in row.items()}
            email = row_lower.get("email")
            student_code = row_lower.get("mssv") or row_lower.get("student_code")
            full_name = row_lower.get("ho ten") or row_lower.get("họ tên") or row_lower.get("full_name") or ""

            if not email:
                error_count += 1
                continue

            user = await self._users.get_by_email(email)
            if not user:
                base_username = email.split("@")[0]
                username = base_username
                while await self._users.get_by_username(username):
                    username = f"{base_username}_{int(time.time()*1000)}"
                
                user = User(
                    email=email,
                    username=username,
                    password_hash=hash_password(student_code or "123456"),
                    full_name=full_name,
                    student_code=student_code,
                    role=UserRole.STUDENT,
                )
                try:
                    user = await self._users.add(user)
                except Exception:
                    error_count += 1
                    continue
            
            existing = await self._enrollments.get(course.id, user.id)
            if existing is None:
                try:
                    enrollment = Enrollment(
                        course_id=course.id,
                        user_id=user.id,
                        role_in_course=CourseRole.STUDENT,
                    )
                    await self._enrollments.add(enrollment)
                    success_count += 1
                except Exception:
                    error_count += 1
            else:
                success_count += 1
                
        return {"success": success_count, "error": error_count}


class AssignmentService:
    def __init__(self, cp_repo: CourseProblemRepository) -> None:
        self._repo = cp_repo

    async def list_for_course(self, course_id: UUID) -> Sequence[CourseProblem]:
        return await self._repo.list_by_course(course_id)

    async def assign(self, course_id: UUID, data: CourseProblemCreate) -> CourseProblem:
        existing = await self._repo.list_by_course(course_id)
        if any(cp.problem_id == data.problem_id for cp in existing):
            raise ProblemAlreadyAssignedError("Bài này đã được gán vào lớp")
        cp = CourseProblem(
            course_id=course_id,
            problem_id=data.problem_id,
            deadline=data.deadline,
            weight=data.weight,
            order_index=data.order_index,
        )
        return await self._repo.add(cp)

    async def update(
        self, assignment_id: UUID, data: CourseProblemUpdate
    ) -> CourseProblem:
        cp = await self._repo.get(assignment_id)
        if cp is None:
            raise EntityNotFoundError("CourseProblem", assignment_id)
        updates = {
            k: v
            for k, v in data.model_dump(exclude_unset=True).items()
            # deadline có thể = None (xoá deadline), nên không filter None ở đây
        }
        return await self._repo.update(cp, updates)

    async def unassign(self, assignment_id: UUID) -> None:
        await self._repo.delete(assignment_id)
