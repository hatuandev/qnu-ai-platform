"""Tests for Assistant Versioning, Snapshots, and 1-Click Rollback."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.main import app
from app.modules.assistants.models import AssistantModel, AssistantVersionModel
from app.modules.assistants.seeder import STANDARD_ASSISTANTS
from app.modules.assistants.service import assistant_service


def _sample_assistant(code: str = "admissions") -> AssistantModel:
    template = next(item for item in STANDARD_ASSISTANTS if item["code"] == code)
    timestamp = datetime.now(UTC).replace(tzinfo=None)
    return AssistantModel(
        id=f"ast_{code}_test",
        code=code,
        name=str(template["name"]),
        description=str(template["description"]),
        avatar_url=str(template["avatar_url"]),
        category=str(template["category"]),
        system_prompt=str(template["system_prompt"]),
        workflow_id=str(template["workflow_id"]),
        collection_id=str(template["collection_id"]),
        is_active=True,
        tenant_id="tenant_qnu",
        config=dict(template["config"]),
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_create_version_snapshot() -> None:
    assistant = _sample_assistant()
    db = AsyncMock()

    count_result = MagicMock()
    count_result.scalar.return_value = 0
    db.execute.return_value = count_result

    ver = await assistant_service._create_version_snapshot(
        db, assistant, change_summary="Bản khởi tạo v1.0", created_by="admin"
    )

    assert ver.assistant_id == assistant.id
    assert ver.version_number == "v1.0"
    assert ver.change_summary == "Bản khởi tạo v1.0"
    assert ver.snapshot_data["name"] == assistant.name
    assert ver.snapshot_data["system_prompt"] == assistant.system_prompt


@pytest.mark.asyncio
async def test_get_versions_list() -> None:
    assistant = _sample_assistant()
    timestamp = datetime.now(UTC).replace(tzinfo=None)

    v1 = AssistantVersionModel(
        id="asv_001",
        assistant_id=assistant.id,
        assistant_code=assistant.code,
        version_number="v1.0",
        change_summary="Khởi tạo",
        snapshot_data={"name": "V1 Name"},
        created_by="admin",
        created_at=timestamp,
    )
    v2 = AssistantVersionModel(
        id="asv_002",
        assistant_id=assistant.id,
        assistant_code=assistant.code,
        version_number="v1.1",
        change_summary="Cập nhật prompt",
        snapshot_data={"name": "V2 Name"},
        created_by="admin",
        created_at=timestamp,
    )

    db = AsyncMock()
    # First query is _get_record
    record_result = MagicMock()
    record_result.scalar_one_or_none.return_value = assistant
    # Second query is get versions
    versions_result = MagicMock()
    versions_result.scalars.return_value.all.return_value = [v2, v1]

    db.execute.side_effect = [record_result, versions_result]

    versions = await assistant_service.get_versions(db, assistant.code)
    assert len(versions) == 2
    assert versions[0].version_number == "v1.1"
    assert versions[1].version_number == "v1.0"


@pytest.mark.asyncio
async def test_rollback_version_restores_state() -> None:
    assistant = _sample_assistant()
    assistant.system_prompt = "Prompt mới đã bị thay đổi"

    timestamp = datetime.now(UTC).replace(tzinfo=None)
    target_ver = AssistantVersionModel(
        id="asv_target",
        assistant_id=assistant.id,
        assistant_code=assistant.code,
        version_number="v1.0",
        change_summary="Bản chuẩn ban đầu",
        snapshot_data={
            "name": "Trợ lý Tuyển sinh Chuẩn",
            "description": "Mô tả chuẩn",
            "system_prompt": "Prompt chuẩn ban đầu cần khôi phục",
            "config": {"sample_questions": ["Câu hỏi 1?"]},
        },
        created_by="admin",
        created_at=timestamp,
    )

    db = AsyncMock()
    record_result = MagicMock()
    record_result.scalar_one_or_none.return_value = assistant

    ver_result = MagicMock()
    ver_result.scalar_one_or_none.return_value = target_ver

    count_result = MagicMock()
    count_result.scalar.return_value = 2

    db.execute.side_effect = [record_result, ver_result, count_result]

    resp = await assistant_service.rollback_version(db, assistant.code, "asv_target")

    assert assistant.name == "Trợ lý Tuyển sinh Chuẩn"
    assert assistant.system_prompt == "Prompt chuẩn ban đầu cần khôi phục"
    assert resp.restored_version == "v1.0"
    assert resp.current_version == "v1.2"
    assert "thành công" in resp.message


@pytest.mark.asyncio
async def test_rollback_version_not_found_raises() -> None:
    assistant = _sample_assistant()
    db = AsyncMock()

    record_result = MagicMock()
    record_result.scalar_one_or_none.return_value = assistant

    ver_result = MagicMock()
    ver_result.scalar_one_or_none.return_value = None

    db.execute.side_effect = [record_result, ver_result]

    with pytest.raises(EntityNotFoundError):
        await assistant_service.rollback_version(db, assistant.code, "asv_invalid")


@pytest.mark.asyncio
async def test_versions_api_endpoints() -> None:
    assistant = _sample_assistant()
    timestamp = datetime.now(UTC).replace(tzinfo=None)

    v1 = AssistantVersionModel(
        id="asv_test_api",
        assistant_id=assistant.id,
        assistant_code=assistant.code,
        version_number="v1.0",
        change_summary="Khởi tạo",
        snapshot_data={"name": assistant.name, "system_prompt": assistant.system_prompt},
        created_by="admin",
        created_at=timestamp,
    )

    db = AsyncMock()
    rec_res = MagicMock()
    rec_res.scalar_one_or_none.return_value = assistant

    vers_res = MagicMock()
    vers_res.scalars.return_value.all.return_value = [v1]

    db.execute.side_effect = [rec_res, vers_res]

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_db] = _get_test_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/platform/v1alpha1/assistants/{assistant.code}/versions")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["version_number"] == "v1.0"
    finally:
        app.dependency_overrides.clear()
