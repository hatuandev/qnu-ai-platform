"""Tests for the deployment storage bucket bootstrap."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError

from qnu.platform import storage_init


class _FakeS3:
    def __init__(self, head_error: ClientError | None = None) -> None:
        self._head_error = head_error
        self.created: list[str] = []

    def head_bucket(self, *, Bucket: str) -> None:
        if self._head_error is not None:
            raise self._head_error

    def create_bucket(self, *, Bucket: str) -> None:
        self.created.append(Bucket)


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "synthetic"}}, "HeadBucket")


def _settings(**overrides: object) -> SimpleNamespace:
    values = {
        "STORAGE_DRIVER": "s3",
        "S3_ENDPOINT": "http://synthetic:9000",
        "S3_ACCESS_KEY": "synthetic-access",
        "S3_SECRET_KEY": "synthetic-secret",
        "S3_BUCKET": "synthetic-bucket",
        "S3_SECURE": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_existing_bucket_is_not_recreated(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeS3()
    monkeypatch.setattr(storage_init, "get_settings", lambda: _settings())
    monkeypatch.setattr(storage_init.boto3, "client", lambda *args, **kwargs: fake)

    assert storage_init.main() == 0
    assert fake.created == []


def test_missing_bucket_is_created(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeS3(head_error=_client_error("NoSuchBucket"))
    monkeypatch.setattr(storage_init, "get_settings", lambda: _settings())
    monkeypatch.setattr(storage_init.boto3, "client", lambda *args, **kwargs: fake)

    assert storage_init.main() == 0
    assert fake.created == ["synthetic-bucket"]


def test_access_denied_fails_without_create(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeS3(head_error=_client_error("AccessDenied"))
    monkeypatch.setattr(storage_init, "get_settings", lambda: _settings())
    monkeypatch.setattr(storage_init.boto3, "client", lambda *args, **kwargs: fake)

    assert storage_init.main() == 1
    assert fake.created == []


def test_local_storage_skips_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(storage_init, "get_settings", lambda: _settings(STORAGE_DRIVER="local"))
    monkeypatch.setattr(
        storage_init.boto3, "client", lambda *args, **kwargs: calls.append(object())
    )

    assert storage_init.main() == 0
    assert calls == []
