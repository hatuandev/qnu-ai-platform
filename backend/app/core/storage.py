"""Storage Service Abstraction — Dual-driver support for Local Disk and S3/MinIO."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageDriver(ABC):
    """Abstract base class for storage drivers."""

    async def ensure_bucket(self) -> None:
        """Ensure the storage container/bucket exists (called on startup)."""

    @abstractmethod
    async def save(self, relative_path: str, data: bytes) -> str:
        """Save bytes data to storage and return public/accessible URL or identifier."""

    @abstractmethod
    async def get(self, relative_path: str) -> bytes | None:
        """Retrieve bytes from storage by relative path."""

    @abstractmethod
    async def delete(self, relative_path: str) -> bool:
        """Delete a file from storage."""

    @abstractmethod
    async def exists(self, relative_path: str) -> bool:
        """Check if file exists in storage."""


class LocalStorageDriver(StorageDriver):
    """Local filesystem driver for development without MinIO overhead."""

    def __init__(self, base_path: str = "./storage"):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        clean_rel = relative_path.lstrip("/\\")
        target = (self.base_path / clean_rel).resolve()
        if not str(target).startswith(str(self.base_path)):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return target

    async def ensure_bucket(self) -> None:
        await asyncio.to_thread(self.base_path.mkdir, parents=True, exist_ok=True)

    async def save(self, relative_path: str, data: bytes) -> str:
        target = self._resolve(relative_path)
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_bytes, data)
        logger.debug("Saved %d bytes locally to %s", len(data), target)
        return relative_path

    async def get(self, relative_path: str) -> bytes | None:
        target = self._resolve(relative_path)
        is_file = await asyncio.to_thread(target.is_file)
        if not is_file:
            return None
        return await asyncio.to_thread(target.read_bytes)

    async def delete(self, relative_path: str) -> bool:
        target = self._resolve(relative_path)
        is_file = await asyncio.to_thread(target.is_file)
        if is_file:
            await asyncio.to_thread(target.unlink)
            return True
        return False

    async def exists(self, relative_path: str) -> bool:
        target = self._resolve(relative_path)
        return await asyncio.to_thread(target.is_file)


class S3StorageDriver(StorageDriver):
    """S3-compatible object storage driver (AWS S3, MinIO, Cloudflare R2)."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        import boto3
        from botocore.config import Config

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name=region,
            use_ssl=secure,
        )

    async def ensure_bucket(self) -> None:
        """Check or create S3 bucket asynchronously without blocking startup."""
        def _check():
            try:
                self.s3_client.head_bucket(Bucket=self.bucket)
            except Exception:
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket)
                    logger.info("Created S3 bucket: %s", self.bucket)
                except Exception as exc:
                    logger.warning("Could not auto-create S3 bucket %s: %s", self.bucket, exc)

        await asyncio.to_thread(_check)

    async def save(self, relative_path: str, data: bytes) -> str:
        clean_key = relative_path.lstrip("/\\")
        await asyncio.to_thread(
            self.s3_client.put_object,
            Bucket=self.bucket,
            Key=clean_key,
            Body=data,
        )
        logger.debug("Saved %d bytes to S3: %s/%s", len(data), self.bucket, clean_key)
        return clean_key

    async def get(self, relative_path: str) -> bytes | None:
        clean_key = relative_path.lstrip("/\\")

        def _fetch():
            try:
                response = self.s3_client.get_object(Bucket=self.bucket, Key=clean_key)
                return response["Body"].read()
            except Exception as exc:
                logger.debug("S3 object not found %s: %s", clean_key, exc)
                return None

        return await asyncio.to_thread(_fetch)

    async def delete(self, relative_path: str) -> bool:
        clean_key = relative_path.lstrip("/\\")

        def _delete():
            try:
                self.s3_client.delete_object(Bucket=self.bucket, Key=clean_key)
                return True
            except Exception as exc:
                logger.error("Failed to delete S3 object %s: %s", clean_key, exc)
                return False

        return await asyncio.to_thread(_delete)

    async def exists(self, relative_path: str) -> bool:
        clean_key = relative_path.lstrip("/\\")

        def _check():
            try:
                self.s3_client.head_object(Bucket=self.bucket, Key=clean_key)
                return True
            except Exception:
                return False

        return await asyncio.to_thread(_check)


def get_storage_driver() -> StorageDriver:
    """Factory creating the configured storage driver (Local or S3)."""
    if settings.STORAGE_DRIVER.lower() == "s3":
        return S3StorageDriver(
            endpoint_url=settings.S3_ENDPOINT,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            bucket=settings.S3_BUCKET,
            secure=settings.S3_SECURE,
            region=settings.S3_REGION,
        )
    return LocalStorageDriver(base_path=settings.LOCAL_STORAGE_PATH)


storage_service = get_storage_driver()

