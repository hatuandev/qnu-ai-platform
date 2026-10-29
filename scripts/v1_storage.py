"""V1 storage readiness and explicit local preparation; never mutates remote S3."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

if TYPE_CHECKING:
    from qnu.platform.config import Settings


def local_minio(settings: Settings) -> bool:
    endpoint = urlsplit(settings.S3_ENDPOINT)
    return (
        endpoint.scheme == "http"
        and endpoint.hostname in {"localhost", "127.0.0.1", "::1"}
        and endpoint.port == 9000
        and endpoint.path in {"", "/"}
        and not endpoint.username
        and not endpoint.password
        and not endpoint.query
        and not endpoint.fragment
    )


def validate(settings: Settings) -> tuple[bool, str]:
    if settings.STORAGE_DRIVER == "local":
        return (
            True,
            "Local storage selected; existing storage location will be preserved",
        )
    if (
        not settings.S3_ACCESS_KEY
        or not settings.S3_SECRET_KEY
        or not settings.S3_BUCKET
    ):
        return (
            False,
            "S3 requires S3_ACCESS_KEY, S3_SECRET_KEY and S3_BUCKET in the selected configuration",
        )
    try:
        endpoint = urlsplit(settings.S3_ENDPOINT)
        _ = endpoint.port  # Validate malformed ports before constructing an SDK client.
    except ValueError:
        return False, "Invalid S3_ENDPOINT host or port"
    if (
        endpoint.scheme not in {"http", "https"}
        or not endpoint.hostname
        or endpoint.username
        or endpoint.password
        or endpoint.query
        or endpoint.fragment
    ):
        return (
            False,
            "Invalid S3_ENDPOINT; use an HTTP(S) storage endpoint without credentials",
        )
    return (
        True,
        "S3 configuration present; connection and permissions still need checking",
    )


def s3_client(settings: Settings):
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        use_ssl=settings.S3_SECURE,
        config=Config(
            connect_timeout=3,
            read_timeout=5,
            retries={"max_attempts": 1},
            s3={"addressing_style": "path"},
        ),
    )


def storage_error(exc: Exception) -> tuple[bool, str]:
    if isinstance(exc, ClientError):
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchBucket", "NotFound"}:
            return (
                False,
                "S3 bucket missing; run v1-infra-up for local MinIO or ask the remote storage administrator",
            )
        if code in {
            "403",
            "AccessDenied",
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
        }:
            return (
                False,
                "S3 authentication/permission failed; check credentials and bucket permissions",
            )
    return (
        False,
        "Storage unavailable; check storage service, endpoint, credentials and filesystem permissions",
    )


def check_storage_sync(settings: Settings) -> tuple[bool, str]:
    ok, detail = validate(settings)
    if not ok:
        return ok, detail
    try:
        if settings.STORAGE_DRIVER == "local":
            root = Path(settings.LOCAL_STORAGE_PATH).resolve()
            ancestor = root
            while not ancestor.exists():
                if ancestor.parent == ancestor:
                    return (
                        False,
                        "Local storage volume is unavailable; check LOCAL_STORAGE_PATH",
                    )
                ancestor = ancestor.parent
            if not ancestor.is_dir() or not os.access(ancestor, os.W_OK | os.X_OK):
                return (
                    False,
                    "Local storage path is not a writable directory; check LOCAL_STORAGE_PATH and permissions",
                )
            return (
                True,
                "Local storage path accessible (read-only check; no test file written)",
            )
        client = s3_client(settings)
        try:
            client.head_bucket(Bucket=settings.S3_BUCKET)
            return (
                True,
                "S3 endpoint, credentials and bucket accessible (read-only; write permission not probed)",
            )
        finally:
            client.close()
    except (BotoCoreError, ClientError, OSError, ValueError) as exc:
        return storage_error(exc)


async def check_storage(settings: Settings) -> tuple[bool, str]:
    return await asyncio.to_thread(check_storage_sync, settings)


def prepare_local_storage(settings: Settings) -> tuple[bool, str]:
    ok, detail = validate(settings)
    if not ok:
        return ok, detail
    try:
        if settings.STORAGE_DRIVER == "local":
            root = Path(settings.LOCAL_STORAGE_PATH).resolve()
            root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=root) as probe:
                probe.write(b"qnu-v1-storage-check")
                probe.seek(0)
                if probe.read() != b"qnu-v1-storage-check":
                    raise OSError("Storage verification mismatch")
            return True, "Local storage write/read verified; temporary file removed"
        if not local_minio(settings):
            ok, detail = check_storage_sync(settings)
            return ok, "Remote S3 left unchanged. " + detail
        return prepare_minio(settings)
    except (BotoCoreError, ClientError, OSError, ValueError) as exc:
        return storage_error(exc)


def prepare_minio(settings: Settings) -> tuple[bool, str]:
    client = s3_client(settings)
    try:
        try:
            client.head_bucket(Bucket=settings.S3_BUCKET)
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code")) not in {
                "404",
                "NoSuchBucket",
                "NotFound",
            }:
                raise
            try:
                client.create_bucket(Bucket=settings.S3_BUCKET)
            except ClientError as race:
                if (
                    race.response.get("Error", {}).get("Code")
                    != "BucketAlreadyOwnedByYou"
                ):
                    raise
                client.head_bucket(Bucket=settings.S3_BUCKET)
        key = f".qnu/v1-infra-check/{uuid4().hex}"
        version = None
        try:
            response = client.put_object(
                Bucket=settings.S3_BUCKET, Key=key, Body=b"qnu-v1-storage-check"
            )
            version = response.get("VersionId")
            response = client.get_object(Bucket=settings.S3_BUCKET, Key=key)
            try:
                if response["Body"].read() != b"qnu-v1-storage-check":
                    raise OSError("Storage verification mismatch")
            finally:
                response["Body"].close()
        finally:
            deletion = {"VersionId": version} if version else {}
            client.delete_object(Bucket=settings.S3_BUCKET, Key=key, **deletion)
        return (
            True,
            "Local MinIO bucket ready; write/read/delete verified; existing objects preserved",
        )
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--prepare-local", action="store_true")
    args = parser.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backendV1"))
    try:
        from qnu.platform.config import get_settings

        settings = get_settings()
        ok, detail = (
            validate(settings) if args.validate else prepare_local_storage(settings)
        )
    except (BotoCoreError, ClientError, OSError, ValueError):
        ok, detail = (
            False,
            "Storage setup failed; check the selected configuration (no secrets printed)",
        )
    print(f"[{'OK' if ok else 'FAIL'}] storage: {detail}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
