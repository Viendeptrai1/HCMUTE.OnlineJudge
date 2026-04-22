"""S3 source fetch cho worker."""

from __future__ import annotations

import boto3


class S3SourceFetcher:
    def __init__(
        self,
        bucket: str,
        region: str,
        endpoint_url: str | None,
        access_key: str,
        secret_key: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def fetch(self, key: str) -> str:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read().decode("utf-8")
