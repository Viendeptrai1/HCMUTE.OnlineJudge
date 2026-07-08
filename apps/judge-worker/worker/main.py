"""Judge worker entrypoint — SQS long-poll → compile → chấm từng testcase → verdict.

Phase 1 dùng `LocalSandbox` chạy subprocess trực tiếp trên host (g++/python3).
Phase 2 sẽ swap sang `IsolateSandbox` cách ly thật.
"""

from __future__ import annotations

import asyncio
import json
import signal
from typing import Any
from uuid import UUID

import boto3
import structlog

from worker.config import WorkerSettings, get_settings
from worker.db import SubmissionDAO, SubmissionRow
from worker.judge import Judge, JudgeOutcome
from worker.sandbox import LocalSandbox, Sandbox
from worker.storage import S3SourceFetcher

log = structlog.get_logger()

_VERDICT_MESSAGE_MAX = 8 * 1024


def _truncate_message(msg: str | None) -> str | None:
    """Cap verdict_message để tránh vỡ DB / payload quá lớn."""
    if msg is None:
        return None
    if len(msg) <= _VERDICT_MESSAGE_MAX:
        return msg
    head = _VERDICT_MESSAGE_MAX - 64
    return msg[:head] + "\n…[truncated]"


class JudgeWorker:
    """Consume submission từ SQS, gọi Judge, ghi verdict xuống DB.

    Dependency Inversion: nhận `Sandbox` + `SubmissionDAO` qua constructor
    để test có thể truyền fake.
    """

    def __init__(
        self,
        settings: WorkerSettings,
        sandbox: Sandbox,
        dao: SubmissionDAO,
        source_fetcher: S3SourceFetcher | None = None,
    ) -> None:
        self._settings = settings
        self._judge = Judge(sandbox)
        self._dao = dao
        self._source_fetcher = source_fetcher
        self._running = True
        self._sqs = boto3.client(
            "sqs",
            region_name=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    def stop(self) -> None:
        self._running = False

    async def run(self) -> None:
        if not self._settings.sqs_judge_queue_url:
            log.warning("queue_url_empty", hint="Set SQS_JUDGE_QUEUE_URL in .env")
            return

        log.info("worker_started", queue=self._settings.sqs_judge_queue_url)
        while self._running:
            try:
                await self._poll_once()
            except Exception as e:
                log.error("poll_error", error=str(e))
                await asyncio.sleep(1)

    async def _poll_once(self) -> None:
        response: dict[str, Any] = await asyncio.to_thread(
            self._sqs.receive_message,
            QueueUrl=self._settings.sqs_judge_queue_url,
            MaxNumberOfMessages=self._settings.poll_max_messages,
            WaitTimeSeconds=self._settings.poll_wait_seconds,
        )
        messages = response.get("Messages", [])
        for message in messages:
            await self._handle_message(message)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        body = json.loads(message.get("Body", "{}"))
        submission_id = body.get("submission_id")
        if not submission_id:
            log.warning("bad_message", body=body)
            await self._delete(message)
            return

        sid = UUID(submission_id)
        log.info("submission_received", submission_id=str(sid))

        row = await asyncio.to_thread(self._dao.fetch, sid)
        if row is None:
            log.warning("submission_not_found", submission_id=str(sid))
            await self._delete(message)
            return

        await asyncio.to_thread(self._dao.mark_judging, sid)

        testcases = await asyncio.to_thread(self._dao.fetch_testcases, row.problem_id)
        outcome = await self._judge_submission(row, testcases)

        await asyncio.to_thread(
            self._dao.update_verdict,
            sid,
            outcome.status,
            outcome.time_used_ms,
            outcome.memory_used_kb,
            _truncate_message(outcome.message),
        )
        log.info(
            "judged",
            submission_id=str(sid),
            status=outcome.status,
            time_ms=outcome.time_used_ms,
            mem_kb=outcome.memory_used_kb,
            testcases=len(testcases),
        )
        await self._delete(message)

    async def _judge_submission(
        self,
        row: SubmissionRow,
        testcases: list,  # list[TestcaseRow] — tránh import vòng
    ) -> JudgeOutcome:
        source = row.source_code
        # Nếu submission có source_key thì ưu tiên đọc từ S3 (chuẩn bị cho tương lai
        # khi `source_code` column có thể nullable).
        if row.source_key and self._source_fetcher is not None:
            try:
                source = await asyncio.to_thread(self._source_fetcher.fetch, row.source_key)
                log.info("source_from_s3", key=row.source_key, len=len(source))
            except Exception as e:
                log.warning("s3_fetch_failed", error=str(e), fallback="db")
        return await self._judge.judge(
            source=source,
            language=row.language.lower(),
            testcases=testcases,
            time_limit_ms=row.time_limit_ms,
            memory_limit_kb=row.memory_limit_kb,
        )

    async def _delete(self, message: dict[str, Any]) -> None:
        await asyncio.to_thread(
            self._sqs.delete_message,
            QueueUrl=self._settings.sqs_judge_queue_url,
            ReceiptHandle=message["ReceiptHandle"],
        )


async def _amain() -> None:
    settings = get_settings()
    dao = SubmissionDAO(settings.sync_database_url)
    fetcher = S3SourceFetcher(
        bucket=settings.s3_bucket,
        region=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        access_key=settings.aws_access_key_id,
        secret_key=settings.aws_secret_access_key,
    )
    worker = JudgeWorker(
        settings=settings,
        sandbox=LocalSandbox(),
        dao=dao,
        source_fetcher=fetcher,
    )

    loop = asyncio.get_running_loop()
    import sys
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, worker.stop)

    await worker.run()


def main() -> None:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ]
    )
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
