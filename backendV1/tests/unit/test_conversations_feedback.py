"""Unit tests for conversation turn feedback contract and state transitions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from qnu.domains.conversations.history import set_feedback
from qnu.domains.conversations.models import Conversation, ConversationTurn
from qnu.domains.conversations.schemas import TurnFeedbackRequest, TurnResponse
from qnu.domains.identity.actor import AuthActor
from qnu.platform.errors import EntityNotFound


def test_turn_feedback_request_validation():
    # Valid like
    req = TurnFeedbackRequest(rating="like")
    assert req.rating == "like"
    assert req.reason is None

    # Valid dislike with reason
    req_dislike = TurnFeedbackRequest(
        rating="dislike", reason="Thông tin chưa chính xác với văn bản gốc"
    )
    assert req_dislike.rating == "dislike"
    assert req_dislike.reason == "Thông tin chưa chính xác với văn bản gốc"

    # Valid clear / null
    req_clear = TurnFeedbackRequest(rating=None, reason=None)
    assert req_clear.rating is None

    # Invalid rating
    with pytest.raises(ValidationError):
        TurnFeedbackRequest(rating="super_like")  # type: ignore

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        TurnFeedbackRequest(rating="like", extra_field="forbidden")  # type: ignore

    # Reason too long (> 500 chars)
    with pytest.raises(ValidationError):
        TurnFeedbackRequest(rating="dislike", reason="a" * 501)


def test_turn_response_serialization_with_feedback():
    data = {
        "id": "turn_123",
        "conversation_id": "conv_456",
        "turn_no": 1,
        "question": "Quy định điều kiện xét tuyển?",
        "resolved_question": None,
        "metadata_filter": {},
        "history_turn_ids": [],
        "status": "completed",
        "error_code": None,
        "result": None,
        "feedback": {
            "rating": "dislike",
            "reason": "Sai nguồn trích dẫn hoặc bảng đối chiếu",
            "updated_at": "2026-11-22T12:00:00Z",
        },
        "rewrite_trace": None,
        "source_status": "current",
        "source_status_reason": None,
        "created_at": "2026-11-22T11:59:00Z",
        "finished_at": "2026-11-22T12:00:00Z",
    }
    resp = TurnResponse.model_validate(data)
    assert resp.feedback is not None
    assert resp.feedback["rating"] == "dislike"
    assert resp.feedback["reason"] == "Sai nguồn trích dẫn hoặc bảng đối chiếu"


@pytest.mark.asyncio
async def test_set_feedback_like_and_clear():
    fake_actor = AuthActor(
        actor_id="user_1",
        username="testuser",
        actor_type="user",
        roles=["member"],
        workspaces=["ws_test"],
    )
    fake_conv = MagicMock(spec=Conversation)
    fake_conv.id = "conv_1"
    fake_conv.document_ids = None

    fake_turn = MagicMock(spec=ConversationTurn)
    fake_turn.id = "turn_1"
    fake_turn.conversation_id = "conv_1"
    fake_turn.feedback = None

    db = AsyncMock()
    db.scalar.return_value = fake_turn
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    blob = MagicMock()
    vectors = MagicMock()

    with (
        patch("qnu.domains.conversations.history.owned", new=AsyncMock(return_value=fake_conv)),
        patch("qnu.domains.conversations.history.expire", new=AsyncMock()),
        patch(
            "qnu.domains.conversations.history.readable",
            new=AsyncMock(side_effect=lambda _db, _b, _v, _a, turn, _docs: turn),
        ),
    ):
        # 1. Set like
        req_like = TurnFeedbackRequest(rating="like")
        await set_feedback(
            db, blob, vectors, fake_actor, "ws_test", "conv_1", "turn_1", req_like
        )
        assert fake_turn.feedback is not None
        assert fake_turn.feedback["rating"] == "like"
        assert fake_turn.feedback["reason"] is None
        assert "updated_at" in fake_turn.feedback

        # 2. Clear feedback
        req_clear = TurnFeedbackRequest(rating=None)
        await set_feedback(
            db, blob, vectors, fake_actor, "ws_test", "conv_1", "turn_1", req_clear
        )
        assert fake_turn.feedback is None


@pytest.mark.asyncio
async def test_set_feedback_not_found():
    fake_actor = AuthActor(
        actor_id="user_1",
        username="testuser",
        actor_type="user",
        roles=["member"],
        workspaces=["ws_test"],
    )
    fake_conv = MagicMock(spec=Conversation)
    fake_conv.id = "conv_1"
    fake_conv.document_ids = None

    db = AsyncMock()
    db.scalar.return_value = None  # turn not found

    blob = MagicMock()
    vectors = MagicMock()

    with (
        patch("qnu.domains.conversations.history.owned", new=AsyncMock(return_value=fake_conv)),
        patch("qnu.domains.conversations.history.expire", new=AsyncMock()),
    ):
        with pytest.raises(EntityNotFound) as exc_info:
            await set_feedback(
                db,
                blob,
                vectors,
                fake_actor,
                "ws_test",
                "conv_1",
                "turn_nonexistent",
                TurnFeedbackRequest(rating="like"),
            )
        assert exc_info.value.code == "conversation_turn_not_found"
