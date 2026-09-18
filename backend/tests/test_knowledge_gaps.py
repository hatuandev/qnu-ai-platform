"""Unit Tests for Knowledge Gap Inbox & Active Learning Remediation."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.modules.evaluation.models import KnowledgeGapRecord
from app.modules.evaluation.schemas import KnowledgeGapResolveRequest
from app.modules.evaluation.service import evaluation_service


@pytest.mark.asyncio
async def test_record_gap_creates_new_record():
    mock_db = AsyncMock()
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_res

    gap = await evaluation_service.record_gap(
        mock_db,
        assistant_code="admissions",
        collection_id="col_admissions",
        question="Điều kiện xét tuyển thẳng diện học sinh giỏi tỉnh là gì?",
    )

    assert gap is not None
    assert gap.assistant_code == "admissions"
    assert gap.frequency == 1
    assert gap.status == "pending"
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_record_gap_increments_frequency_for_duplicate():
    mock_db = AsyncMock()
    existing_gap = KnowledgeGapRecord(
        id="gap_123",
        assistant_code="admissions",
        collection_id="col_admissions",
        question="Học phí ngành Sư phạm Toán là bao nhiêu?",
        frequency=1,
        status="pending",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = existing_gap
    mock_db.execute.return_value = exec_res

    gap = await evaluation_service.record_gap(
        mock_db,
        assistant_code="admissions",
        collection_id="col_admissions",
        question="Học phí ngành Sư phạm Toán là bao nhiêu?",
    )

    assert gap is not None
    assert gap.frequency == 2
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_record_gap_ignores_short_or_empty_question():
    mock_db = AsyncMock()
    gap = await evaluation_service.record_gap(
        mock_db,
        assistant_code="admissions",
        question="alo?",
    )
    assert gap is None


@pytest.mark.asyncio
async def test_resolve_gap_updates_status():
    mock_db = AsyncMock()
    existing_gap = KnowledgeGapRecord(
        id="gap_456",
        assistant_code="regulations",
        collection_id="col_regulations",
        question="Quy định đăng ký học cải thiện điểm?",
        frequency=3,
        status="pending",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = existing_gap
    mock_db.execute.return_value = exec_res

    req = KnowledgeGapResolveRequest(
        status="resolved",
        resolution_notes="Đã nạp văn bản Quyết định số 123/QĐ-ĐHQN về đào tạo tín chỉ.",
        resolved_by="chuyen_vien_khao_thi",
    )

    resolved = await evaluation_service.resolve_gap(mock_db, "gap_456", req)

    assert resolved.id == "gap_456"
    assert resolved.status == "resolved"
    assert resolved.resolution_notes == req.resolution_notes
    assert resolved.resolved_by == "chuyen_vien_khao_thi"
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_gap_inbox_api_endpoints():
    mock_db = AsyncMock()
    existing_gap = KnowledgeGapRecord(
        id="gap_789",
        assistant_code="library",
        collection_id="col_library",
        question="Cách gia hạn mượn sách giáo trình trực tuyến qua cổng thư viện?",
        frequency=5,
        status="pending",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    list_res = MagicMock()
    list_res.scalars.return_value.all.return_value = [existing_gap]

    single_res = MagicMock()
    single_res.scalar_one_or_none.return_value = existing_gap

    mock_db.execute.side_effect = [list_res, single_res]

    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db_override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. GET /gap-inbox
            get_resp = await client.get("/platform/v1alpha1/evaluation/gap-inbox")
            assert get_resp.status_code == 200
            items = get_resp.json()
            assert len(items) == 1
            assert items[0]["id"] == "gap_789"
            assert items[0]["frequency"] == 5

            # 2. PATCH /gap-inbox/{gap_id}
            patch_resp = await client.patch(
                "/platform/v1alpha1/evaluation/gap-inbox/gap_789",
                json={
                    "status": "resolved",
                    "resolution_notes": "Đã cập nhật hướng dẫn mượn tài liệu số 2026.",
                },
            )
            assert patch_resp.status_code == 200
            patch_data = patch_resp.json()
            assert patch_data["status"] == "resolved"
            assert "resolution_notes" in patch_data
    finally:
        app.dependency_overrides.pop(get_db, None)
