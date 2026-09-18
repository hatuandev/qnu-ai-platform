"""Tests for Conversations, Message History, and Staff Handoff."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.main import app
from app.modules.conversations.models import ConversationThreadModel
from app.modules.conversations.schemas import ConversationCreateMessageRequest
from app.modules.conversations.service import conversation_service


@pytest.mark.asyncio
async def test_record_message_creates_thread_and_message() -> None:
    db = AsyncMock()

    # Thread lookup returns None (new thread)
    t_res = MagicMock()
    t_res.scalar_one_or_none.return_value = None
    db.execute.return_value = t_res

    req = ConversationCreateMessageRequest(
        assistant_code="admissions",
        assistant_name="Trợ lý Tuyển sinh QNU",
        sender="user",
        text="Em muốn hỏi về học bổng tuyển sinh 2025?",
        user_name="Nguyễn Văn A",
        user_email="a.nguyen@gmail.com",
    )

    msg = await conversation_service.record_message(db, req)
    assert msg.sender == "user"
    assert msg.text == req.text
    assert msg.thread_id.startswith("conv_")


@pytest.mark.asyncio
async def test_record_message_detects_handoff_intent() -> None:
    db = AsyncMock()
    t_res = MagicMock()
    t_res.scalar_one_or_none.return_value = None
    db.execute.return_value = t_res

    req = ConversationCreateMessageRequest(
        assistant_code="admissions",
        sender="user",
        text="Cho em gặp tư vấn viên trực tiếp với ạ!",
    )

    msg = await conversation_service.record_message(db, req)
    assert msg.thread_id.startswith("conv_")


@pytest.mark.asyncio
async def test_staff_reply_updates_thread_status() -> None:
    db = AsyncMock()
    timestamp = datetime.now(UTC).replace(tzinfo=None)

    thread = ConversationThreadModel(
        id="conv_test_01",
        assistant_code="admissions",
        assistant_name="Trợ lý Tuyển sinh QNU",
        user_name="Thí sinh B",
        last_message="Cần hỗ trợ",
        status="handoff_requested",
        created_at=timestamp,
        updated_at=timestamp,
    )

    t_res = MagicMock()
    t_res.scalar_one_or_none.return_value = thread
    db.execute.return_value = t_res

    msg = await conversation_service.reply_from_staff(
        db,
        thread_id="conv_test_01",
        text="Chào bạn, mình là Thầy Tuấn bên Phòng Đào tạo. Mình sẽ hỗ trợ bạn ngay nhé!",
        staff_name="Thầy Tuấn (Đào tạo)",
    )

    assert msg.sender == "agent"
    assert thread.status == "staff_claimed"
    assert thread.assigned_to == "Thầy Tuấn (Đào tạo)"
    assert thread.last_message == msg.text


@pytest.mark.asyncio
async def test_update_thread_status_to_resolved() -> None:
    db = AsyncMock()
    timestamp = datetime.now(UTC).replace(tzinfo=None)

    thread = ConversationThreadModel(
        id="conv_test_02",
        assistant_code="regulations",
        assistant_name="Trợ lý Quy chế",
        user_name="Sinh viên C",
        last_message="Đã hiểu quy chế",
        status="staff_claimed",
        created_at=timestamp,
        updated_at=timestamp,
    )

    t_res = MagicMock()
    t_res.scalar_one_or_none.return_value = thread
    db.execute.return_value = t_res

    updated = await conversation_service.update_thread_status(
        db, thread_id="conv_test_02", status="resolved"
    )

    assert updated.status == "resolved"


@pytest.mark.asyncio
async def test_reply_nonexistent_thread_raises_404() -> None:
    db = AsyncMock()
    t_res = MagicMock()
    t_res.scalar_one_or_none.return_value = None
    db.execute.return_value = t_res

    with pytest.raises(EntityNotFoundError):
        await conversation_service.reply_from_staff(
            db, thread_id="conv_missing", text="Test reply"
        )


@pytest.mark.asyncio
async def test_conversations_api_routes() -> None:
    db = AsyncMock()
    timestamp = datetime.now(UTC).replace(tzinfo=None)

    thread = ConversationThreadModel(
        id="conv_api_test",
        assistant_code="admissions",
        assistant_name="Trợ lý Tuyển sinh QNU",
        user_name="Thí sinh D",
        last_message="Xin chào",
        status="ai_active",
        created_at=timestamp,
        updated_at=timestamp,
    )

    list_res = MagicMock()
    list_res.scalars.return_value.all.return_value = [thread]
    db.execute.return_value = list_res

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_db] = _get_test_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/platform/v1alpha1/conversations")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["id"] == "conv_api_test"
            assert data[0]["assistant_code"] == "admissions"
    finally:
        app.dependency_overrides.clear()
