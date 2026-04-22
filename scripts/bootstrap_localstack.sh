#!/usr/bin/env bash
# Tạo SQS queue + S3 bucket trên LocalStack thông qua container.
# Idempotent: chạy lại nhiều lần không lỗi.
set -euo pipefail

CONTAINER="${LOCALSTACK_CONTAINER:-oj_localstack}"
QUEUE_NAME="${QUEUE_NAME:-oj-judge-queue}"
BUCKET_NAME="${S3_BUCKET:-oj-local}"

echo "→ Waiting for LocalStack container '$CONTAINER'..."
for _ in $(seq 1 30); do
  if docker exec "$CONTAINER" awslocal sqs list-queues > /dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "→ Creating SQS queue: $QUEUE_NAME"
docker exec "$CONTAINER" awslocal sqs create-queue --queue-name "$QUEUE_NAME" > /dev/null || true
QUEUE_URL=$(docker exec "$CONTAINER" awslocal sqs get-queue-url --queue-name "$QUEUE_NAME" --query QueueUrl --output text)
echo "   queue url: $QUEUE_URL"

echo "→ Creating S3 bucket: $BUCKET_NAME"
docker exec "$CONTAINER" awslocal s3 mb "s3://$BUCKET_NAME" 2>/dev/null || true

echo "✓ LocalStack ready."
echo "  SQS_JUDGE_QUEUE_URL=$QUEUE_URL"
echo "  S3_BUCKET=$BUCKET_NAME"
