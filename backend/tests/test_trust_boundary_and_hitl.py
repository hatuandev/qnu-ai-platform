"""Test suite for Phase E: Trust Boundary, Dev Access Gate & HITL Approval.

Verifies:
1. Server-Signed Session Cookie contains full actor claims (actor_id, display_name, session_version).
2. Side-effect tools strictly enforce HITL approval via WorkflowApprovalRequest.
3. Client-side bypass attempts (e.g. is_approved=True in params) are completely eliminated.
4. Payload hash mismatch rejection (parameters tampering detection).
5. Expired approval rejection.
6. Atomic consumption (status="consumed") and replay attack rejection.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import decode_access_token
from app.main import app
from app.modules.tools.schemas import ToolExecuteRequest
from app.modules.tools.service import ToolService
from app.modules.workflows.models import WorkflowApprovalRequest
from app.modules.workflows.schemas import WorkflowApprovalDecisionRequest
from app.modules.workflows.service import WorkflowService

settings = get_settings()


@pytest.mark.asyncio
async def test_auth_session_cookie_actor_claims():
    """Verify session cookie contains actor_id, display_name, session_version."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            "/platform/v1alpha1/auth/login",
            json={"access_key": settings.DEV_ACCESS_PASSWORD},
        )
        assert login_resp.status_code == 200
        data = login_resp.json()
        assert data["authenticated"] is True
        actor = data["actor"]
        assert actor["actor_id"] == "act_admin_qnu"
        assert actor["display_name"] == "Cán bộ Quản trị QNU"
        assert actor["session_version"] == "v1"
        assert actor["role"] == "admin"

        # Verify decoded JWT payload
        cookie_val = login_resp.cookies.get("qnu_session")
        assert cookie_val is not None
        payload = decode_access_token(cookie_val)
        assert payload["actor_id"] == "act_admin_qnu"
        assert payload["display_name"] == "Cán bộ Quản trị QNU"
        assert payload["session_version"] == "v1"
        assert payload["tenant_id"] == "tenant_qnu"
        assert payload["workspace_id"] == "workspace_qnu"

        # Verify /auth/me returns updated actor info
        me_resp = await client.get("/platform/v1alpha1/auth/me")
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["actor"]["actor_id"] == "act_admin_qnu"
        assert me_data["actor"]["display_name"] == "Cán bộ Quản trị QNU"


@pytest.mark.asyncio
async def test_side_effect_tool_requires_approval_rejects_missing_approval():
    """Side effect tool must raise tool_requires_approval when approval_id is absent."""
    service = ToolService()
    mock_db = AsyncMock()

    req = ToolExecuteRequest(
        tool_name="export_administrative_document",
        parameters={
            "document_type": "THÔNG BÁO",
            "title": "Thông báo kiểm tra an toàn hệ thống",
            "body_paragraphs": ["Nội dung kiểm tra."],
        },
        approval_id=None,
    )

    with pytest.raises(AppException) as exc_info:
        await service.execute_tool(mock_db, req)

    assert exc_info.value.code == "tool_requires_approval"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_side_effect_tool_rejects_client_bypass_flag():
    """Client attempting to bypass approval via body flags (is_approved: true) must be rejected."""
    service = ToolService()
    mock_db = AsyncMock()

    # Client tries to smuggle is_approved or approved_by in parameters
    req = ToolExecuteRequest(
        tool_name="export_administrative_document",
        parameters={
            "document_type": "THÔNG BÁO",
            "title": "Bypass Test",
            "body_paragraphs": ["Test bypass."],
            "is_approved": True,
            "approved_by": "hacker_admin",
        },
        approval_id=None,
    )

    with pytest.raises(AppException) as exc_info:
        await service.execute_tool(mock_db, req)

    assert exc_info.value.code == "tool_requires_approval"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_side_effect_tool_rejects_pending_approval():
    """Tool execution must be rejected if approval is still pending."""
    service = ToolService()
    mock_db = AsyncMock()

    raw_params = {
        "document_type": "THÔNG BÁO",
        "title": "Thông báo chờ duyệt",
        "body_paragraphs": ["Nội dung chờ."],
    }
    payload_str = json.dumps(raw_params, sort_keys=True, ensure_ascii=False)
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    approval_rec = WorkflowApprovalRequest(
        id="appr_pending_123",
        execution_id="exec_test_01",
        checkpoint_id="chk_export",
        node_id="node_export",
        tool_name="export_administrative_document",
        payload_hash=payload_hash,
        status="pending",
        requested_by="act_admin_qnu",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = approval_rec
    mock_db.execute.return_value = mock_res

    req = ToolExecuteRequest(
        tool_name="export_administrative_document",
        parameters=raw_params,
        approval_id="appr_pending_123",
    )

    with pytest.raises(AppException) as exc_info:
        await service.execute_tool(mock_db, req)

    assert exc_info.value.code == "approval_pending"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_side_effect_tool_rejects_payload_hash_mismatch():
    """Tool execution must be rejected if parameters were modified after approval."""
    service = ToolService()
    mock_db = AsyncMock()

    original_params = {
        "document_type": "THÔNG BÁO",
        "title": "Văn bản gốc đã được duyệt",
        "body_paragraphs": ["Nội dung gốc."],
    }
    original_str = json.dumps(original_params, sort_keys=True, ensure_ascii=False)
    original_hash = hashlib.sha256(original_str.encode("utf-8")).hexdigest()

    approval_rec = WorkflowApprovalRequest(
        id="appr_approved_123",
        execution_id="exec_test_01",
        checkpoint_id="chk_export",
        node_id="node_export",
        tool_name="export_administrative_document",
        payload_hash=original_hash,
        status="approved",
        requested_by="act_admin_qnu",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = approval_rec
    mock_db.execute.return_value = mock_res

    # Attacker tampers with title parameter
    tampered_params = dict(original_params)
    tampered_params["title"] = "Văn bản ĐÃ BỊ THAY ĐỔI"

    req = ToolExecuteRequest(
        tool_name="export_administrative_document",
        parameters=tampered_params,
        approval_id="appr_approved_123",
    )

    with pytest.raises(AppException) as exc_info:
        await service.execute_tool(mock_db, req)

    assert exc_info.value.code == "approval_payload_mismatch"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_side_effect_tool_rejects_expired_approval():
    """Tool execution must be rejected if approval has expired."""
    service = ToolService()
    mock_db = AsyncMock()

    raw_params = {
        "document_type": "THÔNG BÁO",
        "title": "Thông báo hết hạn",
        "body_paragraphs": ["Nội dung."],
    }
    payload_str = json.dumps(raw_params, sort_keys=True, ensure_ascii=False)
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    # Expired 2 hours ago
    approval_rec = WorkflowApprovalRequest(
        id="appr_expired_123",
        execution_id="exec_test_01",
        checkpoint_id="chk_export",
        node_id="node_export",
        tool_name="export_administrative_document",
        payload_hash=payload_hash,
        status="approved",
        requested_by="act_admin_qnu",
        expires_at=datetime.now(UTC) - timedelta(hours=2),
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = approval_rec
    mock_db.execute.return_value = mock_res

    req = ToolExecuteRequest(
        tool_name="export_administrative_document",
        parameters=raw_params,
        approval_id="appr_expired_123",
    )

    with pytest.raises(AppException) as exc_info:
        await service.execute_tool(mock_db, req)

    assert exc_info.value.code == "approval_expired"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_side_effect_tool_atomic_consumption_and_replay_prevention(tmp_path, monkeypatch):
    """Tool executes successfully, marks approval as 'consumed', and rejects replay."""
    monkeypatch.setattr(
        "app.modules.tools.builtin.document_exporter.settings.LOCAL_STORAGE_PATH",
        str(tmp_path),
    )
    service = ToolService()
    mock_db = AsyncMock()

    raw_params = {
        "document_type": "THÔNG BÁO",
        "title": "Thông báo hợp lệ",
        "body_paragraphs": ["Nội dung đã duyệt."],
        "signer_title": "HIỆU TRƯỞNG",
        "signer_name": "PGS.TS. Đỗ Ngọc Mỹ",
    }
    payload_str = json.dumps(raw_params, sort_keys=True, ensure_ascii=False)
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    approval_rec = WorkflowApprovalRequest(
        id="appr_valid_123",
        execution_id="exec_test_01",
        checkpoint_id="chk_export",
        node_id="node_export",
        tool_name="export_administrative_document",
        payload_hash=payload_hash,
        status="approved",
        requested_by="act_admin_qnu",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = approval_rec
    mock_db.execute.return_value = mock_res

    req = ToolExecuteRequest(
        tool_name="export_administrative_document",
        parameters=raw_params,
        approval_id="appr_valid_123",
    )

    # 1. First execution succeeds
    result = await service.execute_tool(mock_db, req)
    assert result.status == "success"
    assert result.result["status"] == "generated"
    assert result.result["standard"] == "Decree 30/2020/ND-CP"

    # Verify atomic consumption
    assert approval_rec.status == "consumed"
    mock_db.commit.assert_awaited()

    # 2. Replay attack: calling again with now 'consumed' approval
    with pytest.raises(AppException) as exc_info:
        await service.execute_tool(mock_db, req)

    assert exc_info.value.code == "approval_already_consumed"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_decide_approval_rejects_expired():
    """WorkflowService.decide_approval must reject deciding on an expired request."""
    service = WorkflowService()
    mock_db = AsyncMock()

    expired_rec = WorkflowApprovalRequest(
        id="appr_expired_decision",
        execution_id="run_test_02",
        checkpoint_id="chk_01",
        node_id="node_export",
        tool_name="export_exam_matrix",
        payload_hash="somehash",
        status="pending",
        requested_by="act_admin_qnu",
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = expired_rec
    mock_db.execute.return_value = mock_res

    decision_req = WorkflowApprovalDecisionRequest(
        approved=True,
        decided_by="act_admin_qnu",
        decision_reason="Phê duyệt muộn",
    )

    with pytest.raises(AppException) as exc_info:
        await service.decide_approval(mock_db, "run_test_02", "appr_expired_decision", decision_req)

    assert exc_info.value.code == "approval_expired"
    assert exc_info.value.status_code == 403
