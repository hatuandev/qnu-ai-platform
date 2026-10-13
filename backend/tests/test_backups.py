"""Real encrypted filesystem archives and authorization/error-path regressions."""

import io
import json
import os
import tarfile
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.exceptions import InvalidTag
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.config import settings
from app.core.exceptions import AppException, register_exception_handlers
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.backups import service
from app.modules.backups.archive import extract_verified, safe_name, write_archive
from app.modules.backups.catalogue import load_record, record_path, save_record
from app.modules.backups.encryption import EncryptedWriter, decrypt_stream
from app.modules.backups.models import BackupRecord
from app.modules.backups.processes import run_command
from app.modules.backups.router import installation_admin, router


@pytest.fixture
def backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_DIRECTORY", str(tmp_path / "backups"))
    return tmp_path


def record():
    now = datetime.now(UTC)
    return BackupRecord(
        id="bkp_" + uuid4().hex,
        created_at=now,
        updated_at=now,
        actor_id="test-admin",
        correlation_id="test-backup",
    )


def fixture_archive(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("Dữ liệu đã duyệt: chỉ tiêu và học phí.\n", encoding="utf-8")
    output = tmp_path / "test.qnubak"
    password = "fixture-password-only"
    write_archive(
        output,
        password,
        {"local/documents/source.txt": source},
        {"format": "qnu-backup-v1"},
        {"SECRET_KEY": "fixture-not-a-real-key"},
    )
    target = tmp_path / "extracted"
    target.mkdir()
    return output, target, password, source


def test_encrypted_archive_roundtrip_and_secret_escrow(tmp_path):
    output, target, password, source = fixture_archive(tmp_path)
    assert b"fixture-not-a-real-key" not in output.read_bytes()
    manifest = extract_verified(output, target, password, 1024 * 1024)
    assert (target / "local/documents/source.txt").read_bytes() == source.read_bytes()
    assert (
        json.loads((target / "secrets.json").read_text())["SECRET_KEY"] == "fixture-not-a-real-key"
    )
    assert manifest["inventory"]["local/documents/source.txt"]["size"] == source.stat().st_size


def test_wrong_password_fails_closed(tmp_path):
    output, target, _, _ = fixture_archive(tmp_path)
    with pytest.raises(InvalidTag):
        extract_verified(output, target, "wrong-password-123", 1024 * 1024)


@pytest.mark.parametrize("mutation", ["truncated_byte", "truncated_frame", "bit_flip", "extra"])
def test_encrypted_corruption_rejected(tmp_path, mutation):
    output, target, password, _ = fixture_archive(tmp_path)
    data = bytearray(output.read_bytes())
    if mutation == "truncated_byte":
        data = data[:-1]
    elif mutation == "truncated_frame":
        data = data[:-20]
    elif mutation == "bit_flip":
        data[48] ^= 1
    else:
        data += b"extra"
    output.write_bytes(data)
    with pytest.raises((ValueError, InvalidTag)):
        extract_verified(output, target, password, 1024 * 1024)


def test_archive_expansion_budget(tmp_path):
    output, target, password, _ = fixture_archive(tmp_path)
    with pytest.raises(ValueError, match="dung lượng"):
        extract_verified(output, target, password, 1)


@pytest.mark.parametrize(
    "name", ["../file", "/file", "C:/file", "a\\..\\file", "a/../file", "a/./file", "a//file", ""]
)
def test_path_traversal_rejected(name):
    with pytest.raises(ValueError):
        safe_name(name)


def test_large_encrypted_stream_roundtrip(tmp_path):
    payload = os.urandom(3 * 1024 * 1024 + 251)
    output = tmp_path / "large.qnubak"
    with output.open("xb") as destination:
        writer = EncryptedWriter(destination, "random-fixture-password")
        writer.write(payload)
        writer.finish()
    result = io.BytesIO()
    with output.open("rb") as source:
        decrypt_stream(source, result, "random-fixture-password")
    assert result.getvalue() == payload


def test_archive_link_rejected(tmp_path):
    packed = io.BytesIO()
    with tarfile.open(fileobj=packed, mode="w:gz") as archive:
        link = tarfile.TarInfo("link")
        link.type, link.linkname = tarfile.SYMTYPE, "../outside"
        archive.addfile(link)
    encrypted = tmp_path / "link.qnubak"
    with encrypted.open("xb") as destination:
        writer = EncryptedWriter(destination, "link-fixture-password")
        writer.write(packed.getvalue())
        writer.finish()
    target = tmp_path / "target"
    target.mkdir()
    with pytest.raises(ValueError, match="liên kết"):
        extract_verified(encrypted, target, "link-fixture-password", 1024 * 1024)
    assert not (tmp_path / "outside").exists()


def test_catalogue_no_password_and_bad_id(backup_dir):
    entry = record()
    save_record(entry)
    assert load_record(entry.id).id == entry.id
    assert "passphrase" not in record_path(entry.id).read_text(encoding="utf-8")
    with pytest.raises(AppException):
        load_record("../../.env")


@pytest.mark.asyncio
async def test_abandoned_process_not_reported_as_success(backup_dir):
    entry = record()
    entry.status = "running"
    save_record(entry)
    raw = json.loads(record_path(entry.id).read_text(encoding="utf-8"))
    raw["updated_at"] = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()
    record_path(entry.id).write_text(json.dumps(raw), encoding="utf-8")
    result = await service.catalogue()
    assert result.items[0].status == "failed" and result.items[0].verified_at is None


@pytest.mark.asyncio
async def test_anonymous_dev_admin_cannot_backup():
    request = Request({"type": "http", "headers": []})
    actor = AuthActor(username="admin", roles=["AI.Admin"], permissions=["ai.access.admin"])
    with pytest.raises(AppException) as error:
        await installation_admin(request, actor)
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_non_admin_even_with_permission_is_denied():
    request = Request({"type": "http", "headers": [(b"authorization", b"Bearer fixture")]})
    actor = AuthActor(username="staff", roles=["AI.Editor"], permissions=["ai.system.backup"])
    with pytest.raises(AppException) as error:
        await installation_admin(request, actor)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_missing_tool_and_nonzero_exit_do_not_fake_success(tmp_path):
    import sys

    with pytest.raises(FileNotFoundError):
        await run_command([str(tmp_path / "does-not-exist.exe")])
    with pytest.raises(AppException) as error:
        await run_command([sys.executable, "-c", "raise SystemExit(7)"])
    assert error.value.code == "BACKUP_TOOL_FAILED"


@pytest.mark.asyncio
async def test_short_password_never_echoed_in_response(backup_dir):
    entry = record()
    with pytest.raises(AppException) as error:
        await service.launch(entry, "short")
    assert "short" not in str(error.value)
    assert not record_path(entry.id).exists()


@pytest.mark.asyncio
async def test_download_requires_scoped_cookie(backup_dir):
    entry = record()
    entry.sha256, entry.status = "fixture-hash", "completed"
    save_record(entry)
    record_path(entry.id, ".qnubak").write_bytes(b"encrypted-fixture")
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix=settings.API_PREFIX)
    app.dependency_overrides[get_current_actor] = lambda: AuthActor(
        username="admin", roles=["AI.Admin"]
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        path = settings.API_PREFIX + "/backups/" + entry.id
        assert (await client.get(path + "/download")).status_code == 401
        ticket = await client.post(
            path + "/download-ticket", headers={"Authorization": "Bearer fixture"}
        )
        assert ticket.status_code == 200 and "HttpOnly" in ticket.headers["set-cookie"]
        downloaded = await client.get(path + "/download")
        assert downloaded.status_code == 200 and downloaded.content == b"encrypted-fixture"
        wrong = jwt.encode(
            {
                "backup_id": "wrong",
                "aud": "qnu-backup-download",
                "exp": datetime.now(UTC) + timedelta(seconds=30),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        response = await client.get(
            path + "/download", headers={"cookie": "qnu_backup_download=" + wrong}
        )
        assert response.status_code == 401
