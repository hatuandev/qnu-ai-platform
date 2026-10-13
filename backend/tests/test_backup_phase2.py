"""Phase two safety gates exercised with real files; no application data is touched."""

import asyncio
import os
import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.backups.archive import write_archive
from app.modules.backups.catalogue import list_records, record_path, save_record, sha256_file
from app.modules.backups.management import remove_backup, retention_candidates
from app.modules.backups.models import BackupRecord
from app.modules.backups.policy import BackupPolicy, load_policy, save_policy
from app.modules.backups.scheduler import next_occurrence, read_schedule_password


@pytest.mark.asyncio
async def test_import_requires_admin_and_remains_unverified(isolated):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core.exceptions import register_exception_handlers
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.auth.schemas import AuthActor
    from app.modules.backups.router import router

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix=settings.API_PREFIX)
    app.dependency_overrides[get_current_actor] = lambda: AuthActor(
        username="fixture", roles=["AI.Admin"]
    )
    original = entry(verified=True)
    payload = record_path(original.id, ".qnubak").read_bytes()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        url = settings.API_PREFIX + "/backups/import"
        assert (await client.post(url, content=payload)).status_code == 401
        response = await client.post(
            url, content=payload, headers={"Authorization": "Bearer fixture"}
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "unverified" and data["verified_at"] is None and data["pinned"]
        assert data["id"] != original.id and data["sha256"] == original.sha256
        assert record_path(data["id"], ".qnubak").read_bytes() == payload
        bad = await client.post(
            url, content=b"not-an-archive", headers={"Authorization": "Bearer fixture"}
        )
        assert bad.status_code == 400
        assert not list(record_path(original.id).parent.glob("*.partial"))


def test_external_secret_is_never_read_from_backup_source(isolated, monkeypatch):
    secret = record_path("bkp_" + "a" * 32).parent / "secret.txt"
    secret.write_text("fixture-secret-password", encoding="utf-8")
    monkeypatch.setattr(settings, "BACKUP_SCHEDULE_SECRET_FILE", str(secret.resolve()))
    with pytest.raises(AppException):
        read_schedule_password()


def test_release_mismatch_blocks_restore_before_any_container(monkeypatch):
    from app.modules.backups.compatibility import check_restore_compatibility

    monkeypatch.setenv("APP_IMAGE_TAG", "fixture-release-2")
    with pytest.raises(AppException) as error:
        check_restore_compatibility(
            {
                "format": "qnu-backup-v1",
                "database": {"major": 16, "schema": ["fixture"]},
                "qdrant": {"collections": []},
                "release": "fixture-release-1",
            }
        )
    assert error.value.code == "BACKUP_RELEASE_MISMATCH"


@pytest.mark.asyncio
async def test_corrupted_local_archive_never_becomes_successful_remote_copy(isolated):
    from app.modules.backups.remote import transfer

    record = entry(verified=True)
    record_path(record.id, ".qnubak").write_bytes(b"corrupted-file")
    with pytest.raises(AppException) as error:
        await transfer(
            record,
            BackupPolicy(
                remote_enabled=True, endpoint="http://127.0.0.1:1", bucket="fixture-backups"
            ),
        )
    assert error.value.code == "BACKUP_LOCAL_CORRUPT" and record.verified_at is None


@pytest.mark.asyncio
async def test_remote_secret_failure_keeps_good_local_archive(isolated, monkeypatch):
    from app.modules.backups.remote import transfer

    monkeypatch.setattr(settings, "BACKUP_REMOTE_CREDENTIALS_FILE", "")
    record = entry(verified=True)
    await transfer(
        record,
        BackupPolicy(remote_enabled=True, endpoint="http://127.0.0.1:1", bucket="fixture-backups"),
    )
    assert record.remote_status == "failed" and record.verified_at
    assert record_path(record.id, ".qnubak").is_file()
    assert "enc:v1" not in (record.remote_error or "")


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_DIRECTORY", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    return tmp_path


def entry(days=0, verified=False):
    now = datetime.now(UTC) - timedelta(days=days)
    record = BackupRecord(
        id="bkp_" + uuid4().hex,
        created_at=now,
        updated_at=now,
        actor_id="fixture",
        correlation_id="fixture",
        status="failed",
    )
    if verified:
        path = record_path(record.id, ".qnubak")
        source = path.parent / "fixture.txt"
        source.write_text("Dữ liệu mẫu", encoding="utf-8")
        write_archive(
            path,
            "fixture-password-424",
            {"local/documents/test.txt": source},
            {"format": "qnu-backup-v1"},
            {},
        )
        record.status, record.sha256, record.verified_at = "completed", sha256_file(path), now
        record.size_bytes = path.stat().st_size
    save_record(record)
    return record


def test_last_good_and_running_backups_cannot_be_removed(isolated):
    record = entry(verified=True)
    with pytest.raises(AppException, match="cuối cùng"):
        asyncio.run(remove_backup(record.id, "fixture", "test-delete"))
    record.status = "running"
    save_record(record)
    with pytest.raises(AppException):
        asyncio.run(remove_backup(record.id, "fixture", "test-delete"))
    assert record_path(record.id, ".qnubak").exists()


def test_failed_record_is_removed_with_recoverable_audit(isolated):
    record = entry()
    result = asyncio.run(remove_backup(record.id, "fixture", "test-delete"))
    assert result["recoverable"] is True
    assert not list_records()
    assert (record_path(record.id).parent / ".trash" / record.id / "record.json").is_file()


def test_retention_never_drops_last_good_pinned_or_uncopied(isolated):
    newest, pinned, old = entry(0, True), entry(100, True), entry(110, True)
    pinned.pinned = True
    policy = BackupPolicy(retention_enabled=True, keep_daily=1, keep_weekly=1, keep_monthly=1)
    candidates = retention_candidates([newest, pinned, old], policy, datetime.now(UTC))
    assert newest.id not in candidates and pinned.id not in candidates
    policy.remote_enabled = True
    assert not retention_candidates([newest, pinned, old], policy, datetime.now(UTC))


def test_policy_defaults_off_and_no_password_is_stored(isolated):
    assert not load_policy().schedule_enabled and not load_policy().remote_enabled
    policy = BackupPolicy(schedule_enabled=False, hour=2, minute=30)
    save_policy(policy)
    assert load_policy().hour == 2
    with pytest.raises(ValueError):
        BackupPolicy(remote_enabled=True, endpoint="http://user:secret@example.test", bucket="test")


def test_next_schedule_is_future_with_explicit_timezone():
    policy = BackupPolicy(hour=2, minute=30, utc_offset_minutes=420)
    now = datetime(2026, 10, 13, 20, 0, tzinfo=UTC)
    assert next_occurrence(policy, now) == datetime(2026, 10, 14, 19, 30, tzinfo=UTC)


def test_schedule_without_external_secret_fails_closed(isolated, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_SCHEDULE_SECRET_FILE", "")
    with pytest.raises(AppException):
        read_schedule_password()


@pytest.mark.skipif(os.name != "nt", reason="Windows atomic replace against an open reader")
def test_windows_catalogue_write_waits_for_brief_reader(isolated):
    record = entry()
    reader = record_path(record.id).open("rb")
    timer = threading.Timer(0.15, reader.close)
    timer.start()
    try:
        record.stage = "New stage"
        save_record(record)
    finally:
        timer.join()
        reader.close()
