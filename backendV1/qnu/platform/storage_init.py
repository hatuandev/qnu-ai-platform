"""Create the configured S3 bucket when missing (deployment bootstrap)."""

from __future__ import annotations

import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from qnu.platform.config import get_settings

_MISSING_BUCKET_CODES = {"404", "NoSuchBucket", "NotFound"}


def _bucket_missing(error: ClientError) -> bool:
    code = str(error.response.get("Error", {}).get("Code", ""))
    return code in _MISSING_BUCKET_CODES


def main() -> int:
    settings = get_settings()
    if settings.STORAGE_DRIVER != "s3":
        print("storage-init: STORAGE_DRIVER is not s3; nothing to do")
        return 0

    client = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        use_ssl=settings.S3_SECURE,
    )

    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
        print(f"storage-init: bucket ready ({settings.S3_BUCKET})")
        return 0
    except ClientError as error:
        if not _bucket_missing(error):
            code = error.response.get("Error", {}).get("Code", "unknown")
            print(f"storage-init: bucket check failed ({code})", file=sys.stderr)
            return 1
    except BotoCoreError as error:
        print(f"storage-init: bucket check failed ({type(error).__name__})", file=sys.stderr)
        return 1

    try:
        client.create_bucket(Bucket=settings.S3_BUCKET)
    except (ClientError, BotoCoreError) as error:
        print(f"storage-init: bucket create failed ({type(error).__name__})", file=sys.stderr)
        return 1

    print(f"storage-init: bucket created ({settings.S3_BUCKET})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
