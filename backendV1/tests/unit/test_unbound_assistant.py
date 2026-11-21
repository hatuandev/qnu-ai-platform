"""Unit tests for Assistants and Conversations without knowledge collections (Pure LLM mode)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qnu.domains.assistants.models import Assistant
from qnu.domains.assistants.schemas import AssistantReadiness
from qnu.domains.assistants.service import assistant_readiness
from qnu.domains.conversations.models import Conversation, ConversationTurn
from qnu.domains.conversations.schemas import ConversationCreate, DirectReply
from qnu.domains.conversations.service import create as create_conversation
from qnu.domains.identity.actor import AuthActor
from qnu.ports.chat_model import ChatRequest, ChatResult, ProviderExecution


@pytest.mark.asyncio
async def test_assistant_readiness_without_collections_is_ready():
    """An assistant without collections should report readiness 'ready'."""
    assistant = Assistant(
        id="ast_unbound",
        workspace_id="ws_default",
        name="Trợ lý Trò chuyện Trực tiếp",
        persona="Bạn là trợ lý thân thiện.",
        collection_id=None,
        is_active=True,
        revision=1,
    )
    # mock collection_ids property / binding
    assistant.collection_ids = []

    db = AsyncMock()
    blob = MagicMock()
    actor = AuthActor(user_id="user_1", username="user_1", email="user@qnu.edu.vn", roles=["admin"])

    with patch(
        "qnu.domains.assistants.service.get_assistant",
        new=AsyncMock(return_value=assistant),
    ):
        readiness: AssistantReadiness = await assistant_readiness(
            db, blob, actor, "ws_default", "ast_unbound"
        )
        assert readiness.status == "ready"
        assert readiness.collections == []
        assert readiness.published_document_count == 0
        assert readiness.served_document_count == 0
        assert readiness.sync_status == "not_applicable"


@pytest.mark.asyncio
async def test_create_conversation_without_collections_succeeds():
    """Creating a conversation with an unbound assistant should succeed without error."""
    assistant = Assistant(
        id="ast_unbound",
        workspace_id="ws_default",
        name="Trợ lý Trò chuyện",
        description="Mô tả trợ lý",
        persona="System persona",
        collection_id=None,
        is_active=True,
        revision=1,
        top_k=5,
        history_turns=3,
        max_output_tokens=500,
        rag_policy={
            "retrieval_mode": "dense",
            "candidate_k": 10,
            "rrf_k": 60,
            "scope_resolution": "explicit",
            "context_window": 3,
            "context_max_bytes": 16000,
            "verification_mode": "off",
        },
    )
    assistant.collection_ids = []

    db = AsyncMock()
    actor = AuthActor(
        user_id="user_1",
        username="user_1",
        actor_id="user_1",
        email="user@qnu.edu.vn",
        roles=["member"],
    )
    req = ConversationCreate(assistant_id="ast_unbound", title="Cuộc trò chuyện mới")

    with patch(
        "qnu.domains.conversations.service.get_assistant",
        new=AsyncMock(return_value=assistant),
    ), patch(
        "qnu.domains.conversations.service.record_workspace_event",
        new=AsyncMock(),
    ):
        conv: Conversation = await create_conversation(db, actor, "ws_default", req)
        assert conv.assistant_id == "ast_unbound"
        assert conv.collection_id == ""
        assert conv.assistant_snapshot["collection_ids"] == []


@pytest.mark.asyncio
async def test_direct_llm_turn_execution():
    """When an assistant has no collections, execution routes directly to LLM."""
    from qnu.domains.conversations.execution import _direct_llm_turn

    db = AsyncMock()
    # mock scalars for previous turns
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    db.scalars.return_value = scalars_mock

    actor = AuthActor(
        user_id="user_1",
        username="user_1",
        actor_id="user_1",
        email="user@qnu.edu.vn",
        roles=["member"],
    )
    conversation = Conversation(
        id="cnv_test",
        workspace_id="ws_default",
        collection_id="",
        assistant_id="ast_unbound",
        assistant_revision=1,
        assistant_snapshot={
            "persona": "Bạn là trợ lý giải đáp học vụ.",
            "history_turns": 3,
            "max_output_tokens": 500,
            "collection_ids": [],
        },
        owner_ref="user:user_1",
        title="Test",
    )
    turn = ConversationTurn(
        id="turn_1",
        conversation_id="cnv_test",
        workspace_id="ws_default",
        collection_id="",
        turn_no=1,
        question="Quy chế đào tạo tín chỉ là gì?",
        status="running",
    )

    mock_chat = AsyncMock()
    mock_chat.complete.return_value = ChatResult(
        provider="qwen",
        model="qwen3.8-27b-q4",
        content="Quy chế đào tạo tín chỉ là phương thức đào tạo mềm dẻo...",
        total_tokens=42,
        prompt_tokens=20,
        completion_tokens=22,
    )

    mock_runtime = MagicMock()
    mock_runtime.inference_configuration_hash.return_value = "hash123"
    mock_runtime.provider_id = "prov_qwen"
    mock_runtime.model_name = "qwen3.8-27b-q4"

    mock_budget = MagicMock()
    mock_budget.total_reserved_tokens = 500

    mock_usage = MagicMock()
    mock_usage.id = "usage_1"

    mock_request = ChatRequest(
        endpoint="http://modelops",
        model="qwen3.8-27b-q4",
        max_output_tokens=500,
        timeout_seconds=60,
        api_key="sk-test",
        execution=ProviderExecution(workspace_id="ws_default", provider_id="prov_qwen"),
    )

    with patch(
        "qnu.domains.conversations.execution.prepare_chat_request",
        new=AsyncMock(return_value=(mock_runtime, mock_request, mock_budget)),
    ), patch(
        "qnu.domains.conversations.execution.usage_service.reserve",
        new=AsyncMock(return_value=mock_usage),
    ), patch(
        "qnu.domains.conversations.execution.usage_service.settle",
        new=AsyncMock(),
    ):
        reply: DirectReply = await _direct_llm_turn(
            db, actor, "ws_default", conversation, turn, mock_chat, "prov_qwen"
        )
        assert reply.status == "direct_reply"
        assert reply.route == "direct_chat"
        assert "Quy chế đào tạo tín chỉ" in reply.answer
        assert turn.rewrite_trace["mode"] == "direct_llm"
        assert turn.rewrite_trace["model_name"] == "qwen3.8-27b-q4"


@pytest.mark.asyncio
async def test_owned_conversation_without_collection():
    """owned() must not attempt to load_collection when conversation has no collection."""
    from qnu.domains.conversations.access import owned

    db = AsyncMock()
    actor = AuthActor(
        user_id="user_1",
        username="user_1",
        actor_id="user_1",
        email="user@qnu.edu.vn",
        roles=["member"],
    )
    conv = Conversation(
        id="cnv_test",
        workspace_id="ws_default",
        collection_id="",
        assistant_id="ast_unbound",
        assistant_revision=1,
        assistant_snapshot={"persona": "Test", "collection_ids": []},
        owner_ref="user:user_1",
        title="Test",
    )
    db.scalar.return_value = conv

    with patch(
        "qnu.domains.conversations.access.resolve_workspace_access",
        new=AsyncMock(),
    ), patch(
        "qnu.domains.conversations.access.require_available",
        new=AsyncMock(),
    ), patch(
        "qnu.domains.conversations.access.load_collection",
        new=AsyncMock(),
    ) as mock_load_collection:
        res = await owned(db, actor, "ws_default", "cnv_test")
        assert res.id == "cnv_test"
        # load_collection MUST NOT be called because collection_id is empty
        mock_load_collection.assert_not_called()


@pytest.mark.asyncio
async def test_direct_llm_multi_turn_with_resolved_context():
    """Multi-turn direct LLM chat uses resolved standalone question and json_mode=False."""
    from qnu.domains.conversations.execution import _direct_llm_turn

    db = AsyncMock()
    # Turn 1: completed turn
    turn_1 = ConversationTurn(
        id="turn_1",
        conversation_id="cnv_test",
        workspace_id="ws_default",
        collection_id="",
        turn_no=1,
        question="xin chào",
        status="completed",
        result={
            "id": "turn_1",
            "route": "greeting",
            "answer": "Chào bạn, mình là Trợ lý Tư vấn Quy chế.",
            "status": "direct_reply",
        },
    )
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [turn_1]
    db.scalars.return_value = scalars_mock

    actor = AuthActor(
        user_id="user_1",
        username="user_1",
        actor_id="user_1",
        email="user@qnu.edu.vn",
        roles=["member"],
    )
    conversation = Conversation(
        id="cnv_test",
        workspace_id="ws_default",
        collection_id="",
        assistant_id="ast_unbound",
        assistant_revision=1,
        assistant_snapshot={
            "persona": "Bạn là trợ lý giải đáp học vụ.",
            "history_turns": 3,
            "max_output_tokens": 500,
            "collection_ids": [],
        },
        owner_ref="user:user_1",
        title="Test Multi-Turn",
    )
    # Turn 2: has resolved_question
    turn_2 = ConversationTurn(
        id="turn_2",
        conversation_id="cnv_test",
        workspace_id="ws_default",
        collection_id="",
        turn_no=2,
        question="bạn biết mã trường đại học quy nhơn ko ?",
        resolved_question="Mã trường của Trường Đại học Quy Nhơn là gì?",
        status="running",
    )

    mock_chat = AsyncMock()
    mock_chat.complete.return_value = ChatResult(
        provider="qwen",
        model="qwen3.8-27b-q4",
        content="Mã tuyển sinh của Trường Đại học Quy Nhơn là QNU.",
        total_tokens=50,
        prompt_tokens=30,
        completion_tokens=20,
    )

    mock_runtime = MagicMock()
    mock_runtime.inference_configuration_hash.return_value = "hash123"
    mock_runtime.provider_id = "prov_qwen"
    mock_runtime.model_name = "qwen3.8-27b-q4"

    mock_budget = MagicMock()
    mock_budget.total_reserved_tokens = 500

    mock_usage = MagicMock()
    mock_usage.id = "usage_2"

    mock_request = ChatRequest(
        endpoint="http://modelops",
        model="qwen3.8-27b-q4",
        max_output_tokens=500,
        timeout_seconds=60,
        api_key="sk-test",
        json_mode=False,
        execution=ProviderExecution(workspace_id="ws_default", provider_id="prov_qwen"),
    )

    with patch(
        "qnu.domains.conversations.execution.prepare_chat_request",
        new=AsyncMock(return_value=(mock_runtime, mock_request, mock_budget)),
    ) as mock_prepare, patch(
        "qnu.domains.conversations.execution.usage_service.reserve",
        new=AsyncMock(return_value=mock_usage),
    ), patch(
        "qnu.domains.conversations.execution.usage_service.settle",
        new=AsyncMock(),
    ):
        reply: DirectReply = await _direct_llm_turn(
            db, actor, "ws_default", conversation, turn_2, mock_chat, "prov_qwen"
        )
        assert reply.status == "direct_reply"
        assert reply.route == "direct_chat"
        assert "QNU" in reply.answer
        assert reply.answer != "{}"
        # Verify prepare_chat_request was called with json_mode=False
        _, kwargs = mock_prepare.call_args
        assert kwargs.get("json_mode") is False
        # Verify messages sent to chat model contained the clarified resolved_question
        sent_messages = mock_prepare.call_args[0][3]
        user_messages = [m for m in sent_messages if m.role == "user"]
        assert any("Mã trường của Trường Đại học Quy Nhơn là gì?" in m.content for m in user_messages)


@pytest.mark.asyncio
async def test_direct_llm_turn_empty_json_defense():
    """If the LLM returns an empty JSON '{}', defense converts it to pedagogical prose."""
    from qnu.domains.conversations.execution import _direct_llm_turn

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    db.scalars.return_value = scalars_mock

    actor = AuthActor(
        user_id="user_1",
        username="user_1",
        actor_id="user_1",
        email="user@qnu.edu.vn",
        roles=["member"],
    )
    conversation = Conversation(
        id="cnv_test",
        workspace_id="ws_default",
        collection_id="",
        assistant_id="ast_unbound",
        assistant_revision=1,
        assistant_snapshot={
            "persona": "Bạn là trợ lý giải đáp học vụ.",
            "collection_ids": [],
        },
        owner_ref="user:user_1",
        title="Test Defense",
    )
    turn = ConversationTurn(
        id="turn_defense",
        conversation_id="cnv_test",
        workspace_id="ws_default",
        collection_id="",
        turn_no=1,
        question="câu hỏi",
        status="running",
    )

    mock_chat = AsyncMock()
    # Model returns "{}"
    mock_chat.complete.return_value = ChatResult(
        provider="qwen",
        model="qwen3.8-27b-q4",
        content="{}",
        total_tokens=2,
        prompt_tokens=1,
        completion_tokens=1,
    )

    mock_runtime = MagicMock()
    mock_runtime.inference_configuration_hash.return_value = "hash123"
    mock_runtime.provider_id = "prov_qwen"
    mock_runtime.model_name = "qwen3.8-27b-q4"

    mock_budget = MagicMock()
    mock_budget.total_reserved_tokens = 500

    mock_usage = MagicMock()
    mock_usage.id = "usage_defense"

    mock_request = ChatRequest(
        endpoint="http://modelops",
        model="qwen3.8-27b-q4",
        max_output_tokens=500,
        timeout_seconds=60,
        api_key="sk-test",
        json_mode=False,
    )

    with patch(
        "qnu.domains.conversations.execution.prepare_chat_request",
        new=AsyncMock(return_value=(mock_runtime, mock_request, mock_budget)),
    ), patch(
        "qnu.domains.conversations.execution.usage_service.reserve",
        new=AsyncMock(return_value=mock_usage),
    ), patch(
        "qnu.domains.conversations.execution.usage_service.settle",
        new=AsyncMock(),
    ):
        reply: DirectReply = await _direct_llm_turn(
            db, actor, "ws_default", conversation, turn, mock_chat, "prov_qwen"
        )
        assert reply.status == "direct_reply"
        assert reply.route == "direct_chat"
        assert reply.answer != "{}"
        assert len(reply.answer) > 10


