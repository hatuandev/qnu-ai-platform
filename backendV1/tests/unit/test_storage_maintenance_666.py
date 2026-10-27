"""Conditional deletion and honest inventory errors at storage adapter boundaries."""

import hashlib
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from qnu.adapters.storage.local import LocalBlobStore
from qnu.adapters.storage.s3 import S3BlobStore
from qnu.ports.blob_store import BlobObject


@pytest.mark.asyncio
async def test_s3_outage_is_not_reported_as_missing_object():
    blob = object.__new__(S3BlobStore)
    blob._bucket = "test-bucket"
    blob._client = Mock()
    blob._client.head_object.side_effect = ClientError({"Error": {"Code": "503"}}, "HeadObject")
    with pytest.raises(ClientError):
        await blob.exists("test-key")


@pytest.mark.asyncio
async def test_local_conditional_delete_preserves_changed_bytes(tmp_path):
    blob = LocalBlobStore(str(tmp_path))
    await blob.put_bytes("scope/derived/item", b"before")
    old = (await blob.list_objects("scope/"))[0]
    await blob.put_bytes(old.key, b"after")
    assert await blob.delete_if_unchanged(old, hashlib.sha256(b"before").hexdigest()) == "changed"
    assert await blob.get_bytes(old.key) == b"after"
    new = (await blob.list_objects("scope/"))[0]
    assert await blob.delete_if_unchanged(new, hashlib.sha256(b"after").hexdigest()) == "deleted"
    assert await blob.delete_if_unchanged(new, hashlib.sha256(b"after").hexdigest()) == "absent"


@pytest.mark.asyncio
async def test_s3_delete_is_conditional_and_rejects_concurrent_change():
    blob = object.__new__(S3BlobStore)
    blob._bucket = "test-bucket"
    blob._client = Mock()
    blob._client.get_object.return_value = {"Body": BytesIO(b"derived")}
    blob._client.delete_object.side_effect = ClientError(
        {"Error": {"Code": "PreconditionFailed"}}, "DeleteObject"
    )
    item = BlobObject("scope/item", 7, datetime.now(UTC), '"old-etag"')
    assert await blob.delete_if_unchanged(item, hashlib.sha256(b"derived").hexdigest()) == "changed"
    blob._client.delete_object.assert_called_once_with(
        Bucket="test-bucket", Key=item.key, IfMatch=item.version
    )
