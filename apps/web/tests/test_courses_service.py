"""Unit tests cho CourseService/EnrollmentService/AssignmentService + ProgressService
với fake in-memory repositories (Dependency Inversion).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.modules.courses.models import (
    Course,
    CourseProblem,
    CourseRole,
    Enrollment,
)
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
from app.modules.users.models import User, UserRole


def _make_user(username: str, role: UserRole = UserRole.STUDENT) -> User:
    u = User(
        email=f"{username}@test.local",
        username=username,
        password_hash="x",
        full_name=username.title(),
        role=role,
        is_active=True,
    )
    u.id = uuid4()
    return u


class FakeCourseRepo:
    def __init__(self) -> None:
        self._store: dict[UUID, Course] = {}

    async def get(self, id: UUID) -> Course | None:
        return self._store.get(id)

    async def get_by_code(self, code: str) -> Course | None:
        for c in self._store.values():
            if c.code == code:
                return c
        return None

    async def list_all(self) -> Sequence[Course]:
        return list(self._store.values())

    async def list_by_educator(self, educator_id: UUID) -> Sequence[Course]:
        return [c for c in self._store.values() if c.educator_id == educator_id]

    async def list_for_user(self, user_id: UUID) -> Sequence[Course]:
        # Fake: không tự tính, trả rỗng — gọi flow này cần enrollment repo.
        return []

    async def add(self, entity: Course) -> Course:
        if entity.id is None:
            entity.id = uuid4()
        self._store[entity.id] = entity
        return entity

    async def update(self, entity: Course, data: dict) -> Course:
        for k, v in data.items():
            setattr(entity, k, v)
        return entity

    async def delete(self, id: UUID) -> None:
        self._store.pop(id, None)


class FakeEnrollmentRepo:
    def __init__(self) -> None:
        self._store: dict[UUID, Enrollment] = {}

    async def list_by_course(self, course_id: UUID) -> Sequence[Enrollment]:
        return [e for e in self._store.values() if e.course_id == course_id]

    async def get(self, course_id: UUID, user_id: UUID) -> Enrollment | None:
        for e in self._store.values():
            if e.course_id == course_id and e.user_id == user_id:
                return e
        return None

    async def add(self, entity: Enrollment) -> Enrollment:
        if entity.id is None:
            entity.id = uuid4()
        self._store[entity.id] = entity
        return entity

    async def delete(self, id: UUID) -> None:
        self._store.pop(id, None)


class FakeUserRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, User] = {}

    def add_user(self, user: User) -> None:
        self._by_id[user.id] = user

    async def add(self, user: User) -> User:
        self._by_id[user.id] = user
        return user

    async def get(self, id: UUID) -> User | None:
        return self._by_id.get(id)

    async def get_by_identifier(self, identifier: str) -> User | None:
        for u in self._by_id.values():
            if u.email == identifier or u.username == identifier:
                return u
        return None

    async def get_by_email(self, email: str) -> User | None:
        for u in self._by_id.values():
            if u.email == email:
                return u
        return None

    async def get_by_username(self, username: str) -> User | None:
        for u in self._by_id.values():
            if u.username == username:
                return u
        return None


class FakeAssignmentRepo:
    def __init__(self) -> None:
        self._store: dict[UUID, CourseProblem] = {}

    async def list_by_course(self, course_id: UUID) -> Sequence[CourseProblem]:
        items = [c for c in self._store.values() if c.course_id == course_id]
        items.sort(key=lambda c: c.order_index)
        return items

    async def get(self, id: UUID) -> CourseProblem | None:
        return self._store.get(id)

    async def add(self, entity: CourseProblem) -> CourseProblem:
        if entity.id is None:
            entity.id = uuid4()
        self._store[entity.id] = entity
        return entity

    async def update(self, entity: CourseProblem, data: dict) -> CourseProblem:
        for k, v in data.items():
            setattr(entity, k, v)
        return entity

    async def delete(self, id: UUID) -> None:
        self._store.pop(id, None)


# ---------- CourseService tests ----------


async def test_create_course_assigns_educator() -> None:
    course_repo = FakeCourseRepo()
    service = CourseService(course_repo, FakeEnrollmentRepo())
    edu = _make_user("edu", UserRole.EDUCATOR)

    course = await service.create(
        edu.id, CourseCreate(code="CTT-001", name="CTDL", semester="HK1")
    )

    assert course.educator_id == edu.id
    assert course.code == "CTT-001"


async def test_create_duplicate_code_raises() -> None:
    repo = FakeCourseRepo()
    service = CourseService(repo, FakeEnrollmentRepo())
    edu = _make_user("edu", UserRole.EDUCATOR)

    await service.create(edu.id, CourseCreate(code="X", name="A"))
    with pytest.raises(CourseCodeTakenError):
        await service.create(edu.id, CourseCreate(code="X", name="B"))


async def test_update_code_collision_raises() -> None:
    repo = FakeCourseRepo()
    service = CourseService(repo, FakeEnrollmentRepo())
    edu = _make_user("edu", UserRole.EDUCATOR)

    a = await service.create(edu.id, CourseCreate(code="A", name="A"))
    await service.create(edu.id, CourseCreate(code="B", name="B"))

    with pytest.raises(CourseCodeTakenError):
        await service.update(a.id, CourseUpdate(code="B"))


async def test_can_manage_owner_vs_stranger() -> None:
    service = CourseService(FakeCourseRepo(), FakeEnrollmentRepo())
    edu = _make_user("edu", UserRole.EDUCATOR)
    edu2 = _make_user("edu2", UserRole.EDUCATOR)
    admin = _make_user("root", UserRole.ADMIN)
    course = await service.create(edu.id, CourseCreate(code="A", name="N"))

    assert await service.can_manage(course, edu)
    assert await service.can_manage(course, admin)
    assert not await service.can_manage(course, edu2)


async def test_is_member_includes_enrolled_students() -> None:
    course_repo = FakeCourseRepo()
    enroll_repo = FakeEnrollmentRepo()
    service = CourseService(course_repo, enroll_repo)
    edu = _make_user("edu", UserRole.EDUCATOR)
    alice = _make_user("alice")
    bob = _make_user("bob")
    course = await service.create(edu.id, CourseCreate(code="A", name="N"))
    await enroll_repo.add(
        Enrollment(course_id=course.id, user_id=alice.id, role_in_course=CourseRole.STUDENT)
    )

    assert await service.is_member(course, alice)
    assert not await service.is_member(course, bob)


# ---------- EnrollmentService tests ----------


async def test_enroll_by_username() -> None:
    course_repo = FakeCourseRepo()
    enroll_repo = FakeEnrollmentRepo()
    user_repo = FakeUserRepo()
    edu = _make_user("edu", UserRole.EDUCATOR)
    alice = _make_user("alice")
    user_repo.add_user(alice)

    course = await course_repo.add(
        Course(code="A", name="N", semester="", description="", educator_id=edu.id)
    )

    svc = EnrollmentService(course_repo, enroll_repo, user_repo)
    enrollment = await svc.enroll_by_identifier(course.id, "alice")
    assert enrollment.user_id == alice.id
    assert enrollment.role_in_course == CourseRole.STUDENT


async def test_enroll_twice_raises() -> None:
    course_repo = FakeCourseRepo()
    enroll_repo = FakeEnrollmentRepo()
    user_repo = FakeUserRepo()
    edu = _make_user("edu", UserRole.EDUCATOR)
    alice = _make_user("alice")
    user_repo.add_user(alice)
    course = await course_repo.add(
        Course(code="A", name="N", semester="", description="", educator_id=edu.id)
    )
    svc = EnrollmentService(course_repo, enroll_repo, user_repo)

    await svc.enroll_by_identifier(course.id, "alice")
    with pytest.raises(AlreadyEnrolledError):
        await svc.enroll_by_identifier(course.id, "alice")


# ---------- AssignmentService tests ----------


async def test_assign_problem_twice_raises() -> None:
    repo = FakeAssignmentRepo()
    svc = AssignmentService(repo)
    course_id = uuid4()
    problem_id = uuid4()

    await svc.assign(
        course_id,
        CourseProblemCreate(problem_id=problem_id, deadline=None, weight=10, order_index=1),
    )
    with pytest.raises(ProblemAlreadyAssignedError):
        await svc.assign(
            course_id,
            CourseProblemCreate(problem_id=problem_id, deadline=None, weight=5, order_index=2),
        )


async def test_assignments_are_ordered() -> None:
    repo = FakeAssignmentRepo()
    svc = AssignmentService(repo)
    course_id = uuid4()
    deadline = datetime.now(UTC) + timedelta(days=7)

    await svc.assign(
        course_id, CourseProblemCreate(problem_id=uuid4(), deadline=deadline, order_index=2)
    )
    await svc.assign(
        course_id, CourseProblemCreate(problem_id=uuid4(), deadline=None, order_index=1)
    )

    items = await svc.list_for_course(course_id)
    assert [i.order_index for i in items] == [1, 2]
