"""Re-enqueue các submission bị kẹt ở PENDING / JUDGING quá lâu.

Trường hợp xảy ra:
  - Worker crash giữa chừng (không ACK message ⇒ về lại queue, nhưng nếu queue
    bị purge hoặc message bị xoá thủ công thì submission sẽ mồ côi).
  - Enum/migration mismatch khiến worker không update được verdict.

Cách dùng:
  uv run python scripts/requeue_stuck_submissions.py [--older-than-sec 60] [--dry-run]

Logic:
  - Quét `submissions` có `status IN ('PENDING','JUDGING')` và `updated_at` cũ hơn
    ngưỡng (mặc định 60s).
  - Gửi lại message `{"submission_id": "<uuid>"}` vào SQS judge queue.
  - Không ghi đè status — worker sẽ tự `mark_judging` khi nhận message.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "web"))

import boto3  # noqa: E402
import psycopg  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def _sync_dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def find_stuck(dsn: str, older_than_sec: int) -> list[tuple[str, str, datetime]]:
    threshold = datetime.now(tz=timezone.utc) - timedelta(seconds=older_than_sec)
    sql = """
        SELECT id::text, status, updated_at
          FROM submissions
         WHERE status IN ('PENDING', 'JUDGING')
           AND updated_at < %s
         ORDER BY updated_at ASC
    """
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, (threshold,))
        return list(cur.fetchall())


def requeue(settings, submission_ids: list[str]) -> None:
    sqs = boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    for sid in submission_ids:
        sqs.send_message(
            QueueUrl=settings.sqs_judge_queue_url,
            MessageBody=json.dumps({"submission_id": sid}),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--older-than-sec",
        type=int,
        default=60,
        help="Chỉ requeue submission mà updated_at cũ hơn ngưỡng này (s). Default: 60.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ liệt kê, không gửi SQS.",
    )
    args = parser.parse_args()

    settings = get_settings()
    dsn = _sync_dsn(settings.sync_database_url)
    stuck = find_stuck(dsn, args.older_than_sec)

    if not stuck:
        print(f"✓ Không có submission nào kẹt > {args.older_than_sec}s.")
        return

    print(f"⚠ Tìm thấy {len(stuck)} submission kẹt:")
    for sid, status, updated in stuck:
        print(f"  - {sid}  status={status}  updated_at={updated.isoformat()}")

    if args.dry_run:
        print("(dry-run) Không gửi lại SQS.")
        return

    if not settings.sqs_judge_queue_url:
        print("✗ SQS_JUDGE_QUEUE_URL chưa set, bỏ qua.", file=sys.stderr)
        sys.exit(1)

    requeue(settings, [sid for sid, *_ in stuck])
    print(f"✓ Đã gửi lại {len(stuck)} message vào {settings.sqs_judge_queue_url}")


if __name__ == "__main__":
    main()
