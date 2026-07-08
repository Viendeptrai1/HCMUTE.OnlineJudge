"""Leaderboard service cho Contest.

Hai mode:
  * ICPC: chấm theo (số bài AC, tổng penalty). Wrong attempt = +penalty_minutes.
          Thời gian tính từ `contest.start_at` tới thời điểm first-AC.
  * IOI:  tổng điểm best submission per problem. Best score = accepted → points,
          otherwise → 0 (không có partial trong phiên bản này).

Chỉ tính submissions thuộc window của contest: `start_at ≤ created_at ≤ end_at`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contests.models import Contest, ContestProblem, ScoringMode
from app.modules.submissions.models import Submission, SubmissionStatus
from app.modules.users.models import User


@dataclass
class ProblemCell:
    letter: str
    status: str = "none"  # "none" | "wrong" | "accepted" | "first_ac"
    attempts: int = 0
    time_from_start_min: int | None = None  # ICPC
    score: int = 0  # IOI


@dataclass
class LeaderboardRow:
    rank: int
    user: User
    cells: list[ProblemCell] = field(default_factory=list)
    solved_count: int = 0
    total_penalty_min: int = 0  # ICPC
    total_score: int = 0  # IOI


class LeaderboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compute(self, contest: Contest) -> list[LeaderboardRow]:
        # 1. Lấy danh sách problems của contest
        cp_stmt = (
            select(ContestProblem)
            .where(ContestProblem.contest_id == contest.id)
            .order_by(ContestProblem.order_index.asc(), ContestProblem.letter.asc())
        )
        cps = (await self._session.execute(cp_stmt)).scalars().all()
        if not cps:
            return []

        problem_ids = [cp.problem_id for cp in cps]
        points = {cp.problem_id: cp.points for cp in cps}

        # 2. Lấy mọi submission IN-WINDOW thuộc về contest này
        sub_stmt = (
            select(Submission)
            .where(
                and_(
                    Submission.contest_id == contest.id,
                    Submission.problem_id.in_(problem_ids),
                    Submission.created_at >= contest.start_at,
                    Submission.created_at <= contest.end_at,
                )
            )
            .order_by(Submission.created_at.asc())
        )
        subs = (await self._session.execute(sub_stmt)).scalars().all()
        if not subs:
            return []

        # 3. Aggregate per (user, problem). Dựa trên status.ACCEPTED để xác định first-AC.
        #    Còn các WA/RE/TLE/CE trước AC tính penalty.
        users_by_id: dict[UUID, User] = {}
        # (user_id, problem_id) → (attempts_before_ac, first_ac_time or None)
        # Để track IOI: best_score
        per_user_problem: dict[tuple[UUID, UUID], dict] = {}

        for s in subs:
            users_by_id[s.user_id] = s.user
            key = (s.user_id, s.problem_id)
            cell = per_user_problem.setdefault(
                key,
                {"attempts_before_ac": 0, "first_ac_at": None, "best_score": 0},
            )
            # Bỏ qua nếu đã có first_ac (ICPC: đủ solved rồi, không cộng penalty nữa;
            # IOI: best_score = max(...) vẫn giữ từ AC trước đó).
            if cell["first_ac_at"] is not None:
                # IOI: AC sau AC không cải thiện; WA sau AC cũng bỏ qua (tiêu chuẩn ICPC).
                continue

            if s.status == SubmissionStatus.ACCEPTED:
                cell["first_ac_at"] = s.created_at
                cell["best_score"] = points.get(s.problem_id, 0)
            elif s.status in (
                SubmissionStatus.WRONG_ANSWER,
                SubmissionStatus.TIME_LIMIT,
                SubmissionStatus.MEMORY_LIMIT,
                SubmissionStatus.RUNTIME_ERROR,
            ):
                cell["attempts_before_ac"] += 1
            # COMPILE_ERROR: theo ICPC thường KHÔNG tính penalty.
            # PENDING/JUDGING: bỏ qua.

        # 4. Dựng rows
        start = contest.start_at
        rows: list[LeaderboardRow] = []
        for user_id, user in users_by_id.items():
            row = LeaderboardRow(rank=0, user=user, cells=[])
            for cp in cps:
                cell_data = per_user_problem.get(
                    (user_id, cp.problem_id),
                    {"attempts_before_ac": 0, "first_ac_at": None, "best_score": 0},
                )
                attempts = cell_data["attempts_before_ac"]
                first_ac: datetime | None = cell_data["first_ac_at"]

                if first_ac is not None:
                    delta_min = int((first_ac - start).total_seconds() // 60)
                    row.cells.append(
                        ProblemCell(
                            letter=cp.letter,
                            status="accepted",
                            attempts=attempts + 1,
                            time_from_start_min=max(delta_min, 0),
                            score=cell_data["best_score"],
                        )
                    )
                    row.solved_count += 1
                    row.total_penalty_min += (
                        max(delta_min, 0) + attempts * contest.penalty_minutes
                    )
                    row.total_score += cell_data["best_score"]
                elif attempts > 0:
                    row.cells.append(
                        ProblemCell(letter=cp.letter, status="wrong", attempts=attempts)
                    )
                else:
                    row.cells.append(ProblemCell(letter=cp.letter, status="none"))
            rows.append(row)

        # 5. Sort + rank
        if contest.scoring_mode == ScoringMode.IOI:
            rows.sort(key=lambda r: (-r.total_score, r.user.username))
        else:
            rows.sort(
                key=lambda r: (
                    -r.solved_count,
                    r.total_penalty_min,
                    r.user.username,
                )
            )

        # 6. Đánh dấu "first_ac" (cell có first-AC sớm nhất cho mỗi bài)
        for cp in cps:
            best: tuple[datetime, UUID] | None = None
            for user_id in users_by_id:
                cell = per_user_problem.get((user_id, cp.problem_id))
                if (
                    cell
                    and cell["first_ac_at"] is not None
                    and (best is None or cell["first_ac_at"] < best[0])
                ):
                    best = (cell["first_ac_at"], user_id)
            if best is not None:
                # Update trong rows
                for row in rows:
                    if row.user.id == best[1]:
                        for c in row.cells:
                            if c.letter == cp.letter and c.status == "accepted":
                                c.status = "first_ac"
                        break

        for idx, row in enumerate(rows, start=1):
            row.rank = idx
        return rows


def contest_phase(contest: Contest) -> str:
    """Trả 'upcoming' | 'running' | 'ended' dựa trên `now()`."""
    now = datetime.now(UTC)
    if now < contest.start_at:
        return "upcoming"
    if now > contest.end_at:
        return "ended"
    return "running"
