"""S3/MinIO blob store (boto3 executed in a worker thread)."""

from __future__ import annotations

import asyncio
import hashlib

from qnu.platform.config import Settings
from qnu.platform.errors import Conflict
from qnu.ports.blob_store import BlobObject


class S3BlobStore:
    driver = "s3"

    def __init__(self, settings: Settings) -> None:
        import boto3

        self._bucket = settings.S3_BUCKET
        self._endpoint = settings.S3_ENDPOINT
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            use_ssl=settings.S3_SECURE,
        )

    async def put_bytes(self, key: str, payload: bytes, content_type: str | None = None) -> str:
        extra = {"ContentType": content_type} if content_type else {}
        await asyncio.to_thread(
            self._client.put_object, Bucket=self._bucket, Key=key, Body=payload, **extra
        )
        return key

    async def get_bytes(self, key: str) -> bytes:
        def _get() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()

        return await asyncio.to_thread(_get)

    async def exists(self, key: str) -> bool:
        def _head() -> bool:
            from botocore.exceptions import ClientError

            try:
                self._client.head_object(Bucket=self._bucket, Key=key)
                return True
            except ClientError as exc:
                if str(exc.response.get("Error", {}).get("Code")) in {
                    "404",
                    "NoSuchKey",
                    "NotFound",
                }:
                    return False
                raise

        return await asyncio.to_thread(_head)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)

    async def purge(self, key: str) -> None:
        """Exact-key version removal; a delete marker alone is not permanent deletion."""

        def remove():
            versions = []
            for page in self._client.get_paginator("list_object_versions").paginate(
                Bucket=self._bucket,
                Prefix=key,
            ):
                versions.extend(
                    {"Key": key, "VersionId": item["VersionId"]}
                    for field in ("Versions", "DeleteMarkers")
                    for item in page.get(field, [])
                    if item["Key"] == key
                )
                if len(versions) > 10000:
                    raise Conflict(
                        "Quá nhiều phiên bản object để xóa một lượt.", code="purge_version_limit"
                    )
            for offset in range(0, len(versions), 1000):
                response = self._client.delete_objects(
                    Bucket=self._bucket,
                    Delete={
                        "Objects": versions[offset : offset + 1000],
                        "Quiet": True,
                    },
                )
                if response.get("Errors"):
                    raise Conflict(
                        "Storage chưa xóa hết phiên bản object.", code="purge_storage_failed"
                    )
            # No versions means it is already absent; deleting without VersionId
            # would create a fresh delete marker on a versioned bucket.

        await asyncio.to_thread(remove)

    @property
    def target_hash(self) -> str:
        return hashlib.sha256(
            (self.driver + ":" + self._endpoint + ":" + self._bucket).encode()
        ).hexdigest()

    async def list_objects(self, prefix: str, limit: int = 10000) -> list[BlobObject]:
        def scan():
            result = []
            for page in self._client.get_paginator("list_objects_v2").paginate(
                Bucket=self._bucket, Prefix=prefix
            ):
                for item in page.get("Contents", []):
                    result.append(
                        BlobObject(item["Key"], item["Size"], item["LastModified"], item["ETag"])
                    )
                    if len(result) > limit:
                        raise Conflict(
                            "Inventory vượt giới hạn; chưa xóa tệp.", code="storage_inventory_limit"
                        )
            return result

        return await asyncio.to_thread(scan)

    async def delete_if_unchanged(self, item: BlobObject, sha256: str) -> str:
        def remove():
            from botocore.exceptions import ClientError

            try:
                response = self._client.get_object(
                    Bucket=self._bucket, Key=item.key, IfMatch=item.version
                )
                payload = response["Body"].read()
                if len(payload) != item.size or hashlib.sha256(payload).hexdigest() != sha256:
                    return "changed"
                # Fail closed if a deployed S3 implementation lacks conditional delete.
                self._client.delete_object(Bucket=self._bucket, Key=item.key, IfMatch=item.version)
                return "deleted"
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code"))
                if code in {"404", "NoSuchKey"}:
                    return "absent"
                if code in {"412", "PreconditionFailed"}:
                    return "changed"
                raise

        return await asyncio.to_thread(remove)
