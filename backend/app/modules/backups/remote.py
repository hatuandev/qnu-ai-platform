"""Copy encrypted archives only; full S3 readback hash, not multipart ETag guessing."""

import hashlib
from datetime import UTC, datetime

from app.core.exceptions import AppException
from app.modules.backups.catalogue import record_path, save_record, sha256_file
from app.modules.backups.errors import BackupIntegrityError
from app.modules.backups.offload import finish_thread
from app.modules.backups.policy import BackupPolicy, remote_credentials


def s3_client(policy: BackupPolicy):
    import boto3
    from botocore.config import Config

    credentials = remote_credentials()
    return boto3.client(
        "s3",
        endpoint_url=policy.endpoint,
        region_name=policy.region,
        aws_access_key_id=credentials["access_key"],
        aws_secret_access_key=credentials["secret_key"],
        aws_session_token=credentials["session_token"],
        config=Config(
            signature_version="s3v4",
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 2},
        ),
    )


def copy_verified(record, policy: BackupPolicy) -> None:
    from boto3.s3.transfer import TransferConfig

    if not policy.remote_enabled:
        raise AppException("Chưa bật nơi lưu S3/MinIO ngoài máy.", code="BACKUP_REMOTE_DISABLED")
    path = record_path(record.id, ".qnubak")
    if not record.verified_at or not record.sha256 or sha256_file(path) != record.sha256:
        record.verified_at = None
        raise AppException(
            "Bản local đã bị thay đổi; không tiếp tục chuyển hoặc coi là toàn vẹn.",
            code="BACKUP_LOCAL_CORRUPT",
        )
    client = s3_client(policy)
    key = "/".join(
        part for part in (policy.prefix, record.id + "-" + record.sha256 + ".qnubak") if part
    )
    record.remote_status, record.remote_error = "copying", None
    record.remote_verified_at = record.remote_sha256 = None
    record.stage, record.stage_started_at = "Chuyển bản mã hóa tới S3/MinIO", datetime.now(UTC)
    record.processed_bytes, record.total_bytes = 0, path.stat().st_size
    save_record(record)

    def progress(count):
        record.processed_bytes += count
        save_record(record)

    try:
        client.upload_file(
            str(path),
            policy.bucket,
            key,
            ExtraArgs={"Metadata": {"sha256": record.sha256, "backup-id": record.id}},
            Callback=progress,
            Config=TransferConfig(use_threads=False),
        )
        record.stage, record.stage_started_at = (
            "Đọc lại và đối soát bản S3/MinIO",
            datetime.now(UTC),
        )
        record.processed_bytes = 0
        save_record(record)
        head = client.head_object(Bucket=policy.bucket, Key=key)
        parameters = {"Bucket": policy.bucket, "Key": key}
        if head.get("VersionId"):
            parameters["VersionId"] = head["VersionId"]
        else:
            parameters["IfMatch"] = head["ETag"]
        response = client.get_object(**parameters)
        digest = hashlib.sha256()
        try:
            for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
                digest.update(chunk)
                record.processed_bytes += len(chunk)
        finally:
            response["Body"].close()
        if sha256_file(path) != record.sha256:
            record.verified_at = None
            raise AppException(
                "Bản local đã thay đổi trong lúc chuyển S3.", code="BACKUP_LOCAL_CORRUPT"
            )
        if digest.hexdigest() != record.sha256 or record.processed_bytes != path.stat().st_size:
            raise BackupIntegrityError("Checksum bản S3/MinIO không khớp bản local.")
        record.remote_status, record.remote_sha256 = "verified", record.sha256
        record.remote_verified_at = datetime.now(UTC)
        record.remote_version_id = head.get("VersionId")
        record.remote_location = policy.bucket + "/" + key
    finally:
        client.close()


async def transfer(record, policy: BackupPolicy) -> None:
    try:
        await finish_thread(copy_verified, record, policy)
    except Exception as exc:
        if isinstance(exc, AppException) and exc.code == "BACKUP_LOCAL_CORRUPT":
            raise
        record.remote_status = "failed"
        record.remote_error = (
            exc.message
            if isinstance(exc, AppException)
            else "Chuyển/kiểm chứng S3 thất bại ("
            + type(exc).__name__
            + "). Bản local vẫn được giữ."
        )
    finally:
        save_record(record)
