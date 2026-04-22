"""Business logic cho Testcase."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.testcases.models import Testcase
from app.modules.testcases.repository import TestcaseRepository
from app.modules.testcases.schemas import TestcaseCreate, TestcaseUpdate


class TestcaseService:
    def __init__(self, repo: TestcaseRepository) -> None:
        self._repo = repo

    async def list_for_problem(self, problem_id: UUID) -> Sequence[Testcase]:
        return await self._repo.list_by_problem(problem_id)

    async def list_samples(self, problem_id: UUID) -> list[Testcase]:
        tcs = await self._repo.list_by_problem(problem_id)
        return [tc for tc in tcs if tc.is_sample]

    async def create(self, problem_id: UUID, data: TestcaseCreate) -> Testcase:
        tc = Testcase(
            problem_id=problem_id,
            input_text=data.input_text,
            expected_output=data.expected_output,
            is_sample=data.is_sample,
            score=data.score,
            order_index=data.order_index,
        )
        return await self._repo.add(tc)

    async def update(self, tc_id: UUID, data: TestcaseUpdate) -> Testcase | None:
        tc = await self._repo.get(tc_id)
        if tc is None:
            return None
        updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        return await self._repo.update(tc, updates)

    async def delete(self, tc_id: UUID) -> None:
        await self._repo.delete(tc_id)
