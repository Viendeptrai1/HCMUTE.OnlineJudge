"""Repositories cho Course / Enrollment / CourseProblem."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.models import Course, CourseProblem, Enrollment


class CourseRepository(Protocol):
    async def get(self, id: UUID) -> Course | None: ...
    async def get_by_code(self, code: str) -> Course | None: ...
    async def list_by_educator(self, educator_id: UUID) -> Sequence[Course]: ...
    async def list_for_user(self, user_id: UUID) -> Sequence[Course]: ...
    async def list_all(self) -> Sequence[Course]: ...
    async def add(self, entity: Course) -> Course: ...
    async def update(self, entity: Course, data: dict[str, object]) -> Course: ...
    async def delete(self, id: UUID) -> None: ...


class SqlAlchemyCourseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: UUID) -> Course | None:
        return await self._session.get(Course, id)

    async def get_by_code(self, code: str) -> Course | None:
        stmt = select(Course).where(Course.code == code)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_all(self) -> Sequence[Course]:
        stmt = select(Course).order_by(Course.created_at.desc())
        return (await self._session.execute(stmt)).scalars().all()

    async def list_by_educator(self, educator_id: UUID) -> Sequence[Course]:
        stmt = (
            select(Course)
            .where(Course.educator_id == educator_id)
            .order_by(Course.created_at.desc())
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def list_for_user(self, user_id: UUID) -> Sequence[Course]:
        """Course mà user đã enroll (theo học)."""
        stmt = (
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.user_id == user_id)
            .order_by(Course.created_at.desc())
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def add(self, entity: Course) -> Course:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity: Course, data: dict[str, object]) -> Course:
        for k, v in data.items():
            setattr(entity, k, v)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> None:
        entity = await self._session.get(Course, id)
        if entity is not None:
            await self._session.delete(entity)
            await self._session.flush()


class EnrollmentRepository(Protocol):
    async def list_by_course(self, course_id: UUID) -> Sequence[Enrollment]: ...
    async def get(self, course_id: UUID, user_id: UUID) -> Enrollment | None: ...
    async def add(self, entity: Enrollment) -> Enrollment: ...
    async def delete(self, id: UUID) -> None: ...


class SqlAlchemyEnrollmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_course(self, course_id: UUID) -> Sequence[Enrollment]:
        stmt = (
            select(Enrollment)
            .where(Enrollment.course_id == course_id)
            .order_by(Enrollment.joined_at.asc())
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def get(self, course_id: UUID, user_id: UUID) -> Enrollment | None:
        stmt = select(Enrollment).where(
            and_(Enrollment.course_id == course_id, Enrollment.user_id == user_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, entity: Enrollment) -> Enrollment:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> None:
        entity = await self._session.get(Enrollment, id)
        if entity is not None:
            await self._session.delete(entity)
            await self._session.flush()


class CourseProblemRepository(Protocol):
    async def list_by_course(self, course_id: UUID) -> Sequence[CourseProblem]: ...
    async def get(self, id: UUID) -> CourseProblem | None: ...
    async def add(self, entity: CourseProblem) -> CourseProblem: ...
    async def update(self, entity: CourseProblem, data: dict[str, object]) -> CourseProblem: ...
    async def delete(self, id: UUID) -> None: ...


class SqlAlchemyCourseProblemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_course(self, course_id: UUID) -> Sequence[CourseProblem]:
        stmt = (
            select(CourseProblem)
            .where(CourseProblem.course_id == course_id)
            .order_by(CourseProblem.order_index.asc(), CourseProblem.created_at.asc())
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def get(self, id: UUID) -> CourseProblem | None:
        return await self._session.get(CourseProblem, id)

    async def add(self, entity: CourseProblem) -> CourseProblem:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(
        self, entity: CourseProblem, data: dict[str, object]
    ) -> CourseProblem:
        for k, v in data.items():
            setattr(entity, k, v)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> None:
        entity = await self._session.get(CourseProblem, id)
        if entity is not None:
            await self._session.delete(entity)
            await self._session.flush()
