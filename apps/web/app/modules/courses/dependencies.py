"""DI cho module Courses."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.courses.progress import ProgressService
from app.modules.courses.repository import (
    CourseProblemRepository,
    CourseRepository,
    EnrollmentRepository,
    SqlAlchemyCourseProblemRepository,
    SqlAlchemyCourseRepository,
    SqlAlchemyEnrollmentRepository,
)
from app.modules.courses.service import (
    AssignmentService,
    CourseService,
    EnrollmentService,
)
from app.modules.users.dependencies import get_user_repository
from app.modules.users.repository import UserRepository


def get_course_repository(session: AsyncSession = Depends(get_session)) -> CourseRepository:
    return SqlAlchemyCourseRepository(session)


def get_enrollment_repository(
    session: AsyncSession = Depends(get_session),
) -> EnrollmentRepository:
    return SqlAlchemyEnrollmentRepository(session)


def get_course_problem_repository(
    session: AsyncSession = Depends(get_session),
) -> CourseProblemRepository:
    return SqlAlchemyCourseProblemRepository(session)


def get_course_service(
    course_repo: CourseRepository = Depends(get_course_repository),
    enrollment_repo: EnrollmentRepository = Depends(get_enrollment_repository),
) -> CourseService:
    return CourseService(course_repo, enrollment_repo)


def get_enrollment_service(
    course_repo: CourseRepository = Depends(get_course_repository),
    enrollment_repo: EnrollmentRepository = Depends(get_enrollment_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> EnrollmentService:
    return EnrollmentService(course_repo, enrollment_repo, user_repo)


def get_assignment_service(
    cp_repo: CourseProblemRepository = Depends(get_course_problem_repository),
) -> AssignmentService:
    return AssignmentService(cp_repo)


def get_progress_service(
    session: AsyncSession = Depends(get_session),
) -> ProgressService:
    return ProgressService(session)
