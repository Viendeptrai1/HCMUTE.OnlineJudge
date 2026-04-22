"""ProgressService — tính tiến độ AC của user/members trong 1 course.

Không sở hữu repository riêng, reuse session để query cross-module một cách
đọc-đơn thuần (ok với CQRS lite). Các write-operation chỉ thuộc về module chủ
(submissions, courses).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.models import CourseProblem, Enrollment
from app.modules.submissions.models import Submission, SubmissionStatus
from app.modules.users.models import User


@dataclass(frozen=True)
class ProblemProgress:
    problem_id: UUID
    total_attempts: int
    accepted: bool


@dataclass(frozen=True)
class MemberProgress:
    user: User
    accepted_count: int
    total_problems: int

    @property
    def percent(self) -> int:
        if self.total_problems == 0:
            return 0
        return int(round(self.accepted_count * 100 / self.total_problems))


class ProgressService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def problem_progress_for_user(
        self, course_id: UUID, user_id: UUID
    ) -> dict[UUID, ProblemProgress]:
        """Map problem_id → ProblemProgress cho 1 user trong course."""
        cp_stmt = select(CourseProblem.problem_id).where(CourseProblem.course_id == course_id)
        problem_ids = (await self._session.execute(cp_stmt)).scalars().all()
        if not problem_ids:
            return {}

        attempts_stmt = (
            select(Submission.problem_id, func.count(Submission.id))
            .where(
                Submission.user_id == user_id,
                Submission.problem_id.in_(problem_ids),
            )
            .group_by(Submission.problem_id)
        )
        attempts: dict[UUID, int] = dict(
            (await self._session.execute(attempts_stmt)).all()  # type: ignore[arg-type]
        )

        accepted_stmt = select(Submission.problem_id).where(
            Submission.user_id == user_id,
            Submission.problem_id.in_(problem_ids),
            Submission.status == SubmissionStatus.ACCEPTED,
        )
        accepted_ids = set((await self._session.execute(accepted_stmt)).scalars().all())

        return {
            pid: ProblemProgress(
                problem_id=pid,
                total_attempts=int(attempts.get(pid, 0)),
                accepted=pid in accepted_ids,
            )
            for pid in problem_ids
        }

    async def member_progress(
        self, course_id: UUID
    ) -> list[MemberProgress]:
        """Cho leaderboard lớp: số bài AC / total per enrolled student/ta."""
        cp_stmt = select(func.count(CourseProblem.id)).where(
            CourseProblem.course_id == course_id
        )
        total_problems = int(
            (await self._session.execute(cp_stmt)).scalar_one() or 0
        )

        members_stmt = (
            select(Enrollment.user_id, User)
            .join(User, User.id == Enrollment.user_id)
            .where(Enrollment.course_id == course_id)
        )
        rows = (await self._session.execute(members_stmt)).all()

        results: list[MemberProgress] = []
        problem_ids_stmt = select(CourseProblem.problem_id).where(
            CourseProblem.course_id == course_id
        )
        problem_ids = (await self._session.execute(problem_ids_stmt)).scalars().all()

        for _user_id, user in rows:
            if not problem_ids:
                results.append(
                    MemberProgress(user=user, accepted_count=0, total_problems=0)
                )
                continue
            ac_stmt = (
                select(func.count(func.distinct(Submission.problem_id)))
                .where(
                    Submission.user_id == user.id,
                    Submission.problem_id.in_(problem_ids),
                    Submission.status == SubmissionStatus.ACCEPTED,
                )
            )
            ac_count = int((await self._session.execute(ac_stmt)).scalar_one() or 0)
            results.append(
                MemberProgress(
                    user=user, accepted_count=ac_count, total_problems=total_problems
                )
            )
        results.sort(key=lambda m: (-m.accepted_count, m.user.username))
        return results
