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
    db.add = MagicMock()

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
    db.add = MagicMock()
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
    db.add = MagicMock()
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
    db.add = MagicMock()
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


@pytest.mark.asyncio
async def test_record_feedback_vote_and_stats() -> None:
    """Votes persist for online eval; stats aggregate up-rate honestly."""
    from app.modules.conversations.schemas import FeedbackVoteRequest

    db = AsyncMock()
    db.add = MagicMock()

    async def _touch_refresh(obj):
        obj.created_at = datetime.now(UTC).replace(tzinfo=None)

    db.refresh = AsyncMock(side_effect=_touch_refresh)

    # Anonymous vote (no thread) is accepted
    req = FeedbackVoteRequest(assistant_code="admissions", vote="up", question="q?", answer="a.")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("uuid.uuid4", lambda: MagicMock(hex="a" * 32))
        vote = await conversation_service.record_feedback(db, req)
    assert vote.vote == "up"
    assert vote.thread_id is None

    # Unknown thread is rejected loudly instead of silently stored
    t_res = MagicMock()
    t_res.scalar_one_or_none.return_value = None
    db.execute.return_value = t_res
    bad_req = FeedbackVoteRequest(
        thread_id="conv_missing", assistant_code="admissions", vote="down"
    )
    with pytest.raises(EntityNotFoundError):
        await conversation_service.record_feedback(db, bad_req)

    # Stats: 10 total, 7 up -> 0.7 rate
    total_res = MagicMock()
    total_res.scalar_one.return_value = 10
    up_res = MagicMock()
    up_res.scalar_one.return_value = 7
    db.execute.side_effect = [total_res, up_res]
    stats = await conversation_service.feedback_stats(db, assistant_code="admissions")
    assert (stats.total, stats.up, stats.down, stats.up_rate) == (10, 7, 3, 0.7)

    # Empty inbox reports zero rate instead of crashing
    empty_res = MagicMock()
    empty_res.scalar_one.return_value = 0
    db.execute.side_effect = [empty_res, empty_res]
    empty_stats = await conversation_service.feedback_stats(db)
    assert (empty_stats.total, empty_stats.up_rate) == (0, 0.0)


@pytest.mark.asyncio
async def test_feedback_trend_and_samples() -> None:
    """Trend buckets votes per day; samples surface newest downs for review."""
    from datetime import UTC, datetime, timedelta

    db = AsyncMock()
    now = datetime.now(UTC).replace(tzinfo=None)
    rows_res = MagicMock()
    rows_res.all.return_value = [
        ("up", now),
        ("down", now - timedelta(days=1)),
        ("down", now - timedelta(days=1)),
    ]
    db.execute.return_value = rows_res

    trend = await conversation_service.feedback_trend(db, days=14)
    assert trend.days == 14
    assert [p.date for p in trend.points] == sorted(p.date for p in trend.points)
    assert sum(p.up + p.down for p in trend.points) == 3

    # Days clamp to [1, 90]
    clamped = await conversation_service.feedback_trend(db, days=500)
    assert clamped.days == 90

    sample_rows = MagicMock()
    sample_rows.all.return_value = []
    db.execute.return_value = sample_rows
    assert await conversation_service.feedback_samples(db, vote="down") == []
