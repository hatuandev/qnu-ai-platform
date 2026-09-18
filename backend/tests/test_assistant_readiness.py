"""Tests for Assistant Readiness Engine, Publish Gate, and 1-Click Clone."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import AppException, EntityAlreadyExistsError
from app.main import app
from app.modules.assistants.models import AssistantModel
from app.modules.assistants.readiness import readiness_engine
from app.modules.assistants.schemas import (
    AssistantCloneRequest,
)
from app.modules.assistants.seeder import STANDARD_ASSISTANTS
from app.modules.assistants.service import assistant_service


def _sample_assistant(code: str = "admissions", is_active: bool = False) -> AssistantModel:
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
        is_active=is_active,
        tenant_id="tenant_qnu",
        config=template["config"],
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_readiness_engine_evaluates_standard_assistant():
    mock_db = AsyncMock()
    # Mock knowledge collection query & document count query
    col_exec_res = MagicMock()
    col_exec_res.scalar_one_or_none.return_value = MagicMock()

    doc_count_res = MagicMock()
    doc_count_res.scalar_one.return_value = 5

    eval_run_res = MagicMock()
    eval_run_res.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [col_exec_res, doc_count_res, eval_run_res]

    assistant = _sample_assistant("admissions")
    readiness = await readiness_engine.evaluate_readiness(mock_db, assistant)

    assert readiness.assistant_code == "admissions"
    assert len(readiness.checks) == 5
    assert readiness.overall_readiness_score >= 70
    assert readiness.is_ready_for_publish is True


@pytest.mark.asyncio
async def test_readiness_engine_flags_blocker_when_no_collection():
    mock_db = AsyncMock()
    eval_run_res = MagicMock()
    eval_run_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = eval_run_res

    assistant = _sample_assistant("admissions")
    assistant.collection_id = ""

    readiness = await readiness_engine.evaluate_readiness(mock_db, assistant)

    assert readiness.is_ready_for_publish is False
    assert len(readiness.blockers) > 0
    assert any("Kho tri thức" in b for b in readiness.blockers)


@pytest.mark.asyncio
async def test_publish_assistant_raises_422_when_blocked():
    mock_db = AsyncMock()
    assistant = _sample_assistant("admissions", is_active=False)
    assistant.collection_id = ""  # Will trigger blocker

    get_res = MagicMock()
    get_res.scalar_one_or_none.return_value = assistant

    eval_res = MagicMock()
    eval_res.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [get_res, eval_res]

    with pytest.raises(AppException) as exc_info:
        await assistant_service.publish_assistant(mock_db, "admissions")

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "assistant_not_ready_for_publish"


@pytest.mark.asyncio
async def test_clone_assistant_creates_new_record():
    mock_db = AsyncMock()
    source = _sample_assistant("admissions")

    # Mock _get_record -> returns source
    get_res = MagicMock()
    get_res.scalar_one_or_none.return_value = source

    # Mock code check -> none (code is unique)
    check_res = MagicMock()
    check_res.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [get_res, check_res]

    req = AssistantCloneRequest(
        new_code="cntt_admissions",
        new_name="Trợ lý Tuyển sinh Khoa CNTT",
        new_description="Tư vấn tuyển sinh chuyên biệt cho Khoa CNTT",
    )

    cloned = await assistant_service.clone_assistant(mock_db, "admissions", req)

    assert cloned.code == "cntt_admissions"
    assert cloned.name == "Trợ lý Tuyển sinh Khoa CNTT"
    assert cloned.is_active is False
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_clone_assistant_rejects_duplicate_code():
    mock_db = AsyncMock()
    source = _sample_assistant("admissions")

    get_res = MagicMock()
    get_res.scalar_one_or_none.return_value = source

    existing_res = MagicMock()
    existing_res.scalar_one_or_none.return_value = MagicMock()  # Already exists

    mock_db.execute.side_effect = [get_res, existing_res]

    req = AssistantCloneRequest(
        new_code="admissions",
        new_name="Duplicate Name",
    )

    with pytest.raises(EntityAlreadyExistsError):
        await assistant_service.clone_assistant(mock_db, "admissions", req)


@pytest.mark.asyncio
async def test_readiness_api_endpoint():
    mock_db = AsyncMock()
    assistant = _sample_assistant("regulations")

    get_res = MagicMock()
    get_res.scalar_one_or_none.return_value = assistant

    col_res = MagicMock()
    col_res.scalar_one_or_none.return_value = MagicMock()

    doc_count_res = MagicMock()
    doc_count_res.scalar_one.return_value = 3

    eval_run_res = MagicMock()
    eval_run_res.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [get_res, col_res, doc_count_res, eval_run_res]

    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db_override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/platform/v1alpha1/assistants/regulations/readiness")
            assert resp.status_code == 200
            data = resp.json()
            assert data["assistant_code"] == "regulations"
            assert "checks" in data
            assert len(data["checks"]) == 5
            assert "overall_readiness_score" in data
    finally:
        app.dependency_overrides.pop(get_db, None)
