"""Judge worker entrypoint — SQS long-poll → chấm → cập nhật DB.

Phase 1: dùng `LocalSandbox` stub (luôn Accepted giả). Phase 2 sẽ thay bằng
`IsolateSandbox` chạy thật trong Linux cgroup.
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
from worker.sandbox import LocalSandbox, RunResult, Sandbox

log = structlog.get_logger()


class JudgeWorker:
    """Consume submission từ SQS, gọi Sandbox, ghi verdict xuống DB.

    Dependency Inversion: nhận `Sandbox` + `SubmissionDAO` qua constructor
    để test có thể truyền fake.
    """

    def __init__(self, settings: WorkerSettings, sandbox: Sandbox, dao: SubmissionDAO) -> None:
        self._settings = settings
        self._sandbox = sandbox
        self._dao = dao
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
        status, run_res = await self._judge(row)

        await asyncio.to_thread(
            self._dao.update_verdict,
            sid,
            status,
            run_res.time_used_ms,
            run_res.memory_used_kb,
            run_res.stdout or run_res.stderr or None,
        )
        log.info(
            "judged",
            submission_id=str(sid),
            status=status,
            time_ms=run_res.time_used_ms,
            mem_kb=run_res.memory_used_kb,
        )
        await self._delete(message)

    async def _judge(self, row: SubmissionRow) -> tuple[str, RunResult]:
        """Compile + run bằng Sandbox. Trả (status, last_run_result).

        Hiện `LocalSandbox` luôn trả Accepted stub — chỉ là placeholder để
        pipeline end-to-end chạy được.
        """

        compile_res = await self._sandbox.compile(
            source_path=row.source_code, language=row.language
        )
        if compile_res.exit_code != 0:
            return "compile_error", compile_res

        run_res = await self._sandbox.run(
            binary_path="/tmp/stub",
            stdin_path="/dev/null",
            time_limit_ms=row.time_limit_ms,
            memory_limit_kb=row.memory_limit_kb,
        )
        if run_res.timed_out:
            return "time_limit", run_res
        if run_res.exit_code != 0:
            return "runtime_error", run_res
        return "accepted", run_res

    async def _delete(self, message: dict[str, Any]) -> None:
        await asyncio.to_thread(
            self._sqs.delete_message,
            QueueUrl=self._settings.sqs_judge_queue_url,
            ReceiptHandle=message["ReceiptHandle"],
        )


async def _amain() -> None:
    settings = get_settings()
    dao = SubmissionDAO(settings.sync_database_url)
    worker = JudgeWorker(settings=settings, sandbox=LocalSandbox(), dao=dao)

    loop = asyncio.get_running_loop()
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
