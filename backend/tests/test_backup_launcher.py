"""Real runner launch on Windows Selector (Uvicorn reload) and portable default loops."""

import asyncio
import sys
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.backups import service
from app.modules.backups.archive import write_archive
from app.modules.backups.catalogue import load_record, record_path, save_record, sha256_file
from app.modules.backups.models import BackupRecord
from app.modules.backups.router import router


@pytest.fixture
def encrypted_fixture(tmp_path, monkeypatch):
    directory = str(tmp_path / "backups")
    monkeypatch.setattr(settings, "BACKUP_DIRECTORY", directory)
    monkeypatch.setenv("BACKUP_DIRECTORY", directory)
    monkeypatch.setenv("BACKUP_MIN_FREE_BYTES", "0")
    # Verify must work without touching any real database, Redis, files or vector server.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://fixture:fixture@127.0.0.1:1/fixture")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    now = datetime.now(UTC)
    record = BackupRecord(
        id="bkp_" + uuid4().hex,
        created_at=now,
        updated_at=now,
        actor_id="fixture-admin",
        correlation_id="fixture-launcher",
        operation="verify",
    )
    save_record(record)
    data = tmp_path / "reviewed.md"
    data.write_text("Dữ liệu đã duyệt, không dùng nguồn thật.", encoding="utf-8")
    password = "Mật-khẩu-thử-nghiệm-420"
    archive = record_path(record.id, ".qnubak")
    write_archive(
        archive,
        password,
        {"local/documents/reviewed.md": data},
        {"format": "qnu-backup-v1"},
        {"SECRET_KEY": "fixture-key-only"},
    )
    record.sha256, record.size_bytes = sha256_file(archive), archive.stat().st_size
    record.status = "completed"
    save_record(record)
    return record, password


async def launch_and_check(record, password):
    record.status = "queued"
    launched = await service.launch(record, password)
    assert launched.id == record.id
    await wait_and_check(record, password)


async def wait_and_check(record, password):
    for _ in range(200):
        result = await asyncio.to_thread(load_record, record.id)
        if result.status in ("completed", "failed"):
            assert result.status == "completed", result.error
            assert result.verified_at is not None
            assert password not in record_path(record.id).read_text(encoding="utf-8")
            break
        await asyncio.sleep(0.1)
    else:
        raise AssertionError("Independent fixture runner did not complete")
    await asyncio.gather(*service._waiters)
    assert not service._waiters


async def http_verify_and_check(record, password):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix=settings.API_PREFIX)
    app.dependency_overrides[get_current_actor] = lambda: AuthActor(
        username="fixture-admin", roles=["AI.Admin"]
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            settings.API_PREFIX + "/backups/" + record.id + "/verify",
            json={"passphrase": password, "confirmation": "VERIFY"},
            headers={"Authorization": "Bearer fixture-only"},
        )
        assert response.status_code == 202, response.text
        assert password not in response.text
    await wait_and_check(record, password)


def test_http_202_and_runner_complete_on_portable_loop(encrypted_fixture):
    asyncio.run(http_verify_and_check(*encrypted_fixture))


@pytest.mark.skipif(sys.platform != "win32", reason="HTTP on actual Windows reload event loop")
def test_http_202_and_runner_complete_on_windows_selector(encrypted_fixture):
    loop = asyncio.SelectorEventLoop()
    try:
        loop.run_until_complete(http_verify_and_check(*encrypted_fixture))
    finally:
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


@pytest.mark.skipif(sys.platform != "win32", reason="Actual Windows SelectorEventLoop")
def test_real_backup_runner_starts_under_windows_selector(encrypted_fixture):
    loop = asyncio.SelectorEventLoop()
    try:
        loop.run_until_complete(launch_and_check(*encrypted_fixture))
    finally:
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


def test_real_backup_runner_starts_under_default_platform_loop(encrypted_fixture):
    asyncio.run(launch_and_check(*encrypted_fixture))


def test_real_spawn_failure_is_recorded_without_password(encrypted_fixture, tmp_path, monkeypatch):
    from app.core.exceptions import AppException

    record, password = encrypted_fixture
    monkeypatch.setattr(sys, "executable", str(tmp_path / "missing-python"))

    async def check_failure():
        with pytest.raises(AppException) as error:
            await service.launch(record, password)
        assert error.value.code == "BACKUP_LAUNCH_FAILED"
        assert error.value.status_code == 503
        assert "FileNotFoundError" in str(error.value)
        result = load_record(record.id)
        assert result.status == "failed" and result.history[-1].status == "failed"
        assert password not in record_path(record.id).read_text(encoding="utf-8")
        assert password not in str(error.value)
        assert not service._waiters

    asyncio.run(check_failure())


@pytest.mark.skipif(sys.platform != "win32", reason="Demonstrate the unsupported Windows API")
def test_windows_selector_really_has_no_asyncio_subprocess_support():
    loop = asyncio.SelectorEventLoop()
    try:
        with pytest.raises(NotImplementedError):
            loop.run_until_complete(
                asyncio.create_subprocess_exec(
                    sys.executable, "-c", "print(1)", stdout=asyncio.subprocess.DEVNULL
                )
            )
    finally:
        loop.close()
