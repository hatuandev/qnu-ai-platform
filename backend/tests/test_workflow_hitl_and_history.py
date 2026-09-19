"""Tests for Workflow Human-In-The-Loop (HITL) approval handshake and Multi-Turn Conversation History."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.assistants.models import AssistantModel
from app.modules.assistants.schemas import AssistantChatRequest
from app.modules.assistants.service import assistant_service
from app.modules.conversations.models import ConversationMessageModel
from app.modules.rag.schemas import AskRequest
from app.modules.rag.service import rag_service
from app.modules.workflows.compiler import workflow_compiler
from app.modules.workflows.schemas import (
    WorkflowDagSpec,
    WorkflowExecuteResponse,
    WorkflowNodeSpec,
)


@pytest.mark.asyncio
async def test_chat_handles_workflow_paused_for_approval():
    """Verify chat() returns paused_for_approval status and informative message instead of falling back to no-answer."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_exec = MagicMock()
    mock_exec.scalar.return_value = 0
    mock_db.execute.return_value = mock_exec

    mock_assistant = AssistantModel(
        id="ast_drafting_test",
        code="drafting",
        name="Trợ lý Soạn thảo QNU",
        tenant_id="tenant_qnu",
        system_prompt="Trợ lý soạn thảo văn bản chính thức của QNU.",
        collection_id="col_drafting",
        is_active=True,
        workflow_id="wf_drafting",
        published_workflow_version_id="v1_published",
        config={
            "guardrails": {"no_answer_message": "Tôi chưa có dữ liệu chính thức."},
        },
    )

    mock_workflow_resp = WorkflowExecuteResponse(
        execution_id="exec_12345",
        workflow_id="wf_drafting",
        status="paused_for_approval",
        outputs={
            "checkpoint": "node_export",
            "action_required": "Xuất văn bản hành chính theo Nghị định 30/2020/NĐ-CP",
            "approval_id": "appr_998877",
            "tool_name": "export_administrative_document",
        },
        latency_ms=150.0,
    )

    req = AssistantChatRequest(
        message="Soạn thảo thông báo nghỉ lễ 30/4",
        conversation_id="conv_hitl_test",
    )

    with (
        patch.object(assistant_service, "get_assistant", new_callable=AsyncMock) as mock_get_asst,
        patch("app.modules.assistants.service.workflow_service.execute", new_callable=AsyncMock) as mock_wf_exec,
        patch("app.modules.conversations.service.conversation_service.record_message", new_callable=AsyncMock),
        patch.object(assistant_service, "_get_recent_conversation_history", new_callable=AsyncMock) as mock_hist,
    ):
        mock_get_asst.return_value = mock_assistant
        mock_wf_exec.return_value = mock_workflow_resp
        mock_hist.return_value = []

        resp = await assistant_service.chat(mock_db, "drafting", req)

        assert resp.status == "paused_for_approval"
        assert "appr_998877" in resp.answer
        assert "Chờ phê duyệt (Human-in-the-loop)" in resp.answer
        assert resp.execution_id == "exec_12345"


@pytest.mark.asyncio
async def test_chat_stream_yields_approval_required_event():
    """Verify chat_stream() yields event: approval_required with approval_id when paused_for_approval."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_exec = MagicMock()
    mock_exec.scalar.return_value = 0
    mock_db.execute.return_value = mock_exec

    mock_assistant = AssistantModel(
        id="ast_bloom_test",
        code="question-bank",
        name="Trợ lý Ngân hàng câu hỏi QNU",
        tenant_id="tenant_qnu",
        system_prompt="Trợ lý câu hỏi và ma trận đề thi Bloom.",
        collection_id="col_bloom",
        is_active=True,
        workflow_id="wf_bloom",
        published_workflow_version_id="v1_bloom",
        config={},
    )

    mock_workflow_resp = WorkflowExecuteResponse(
        execution_id="exec_bloom_1",
        workflow_id="wf_bloom",
        status="paused_for_approval",
        paused_node_id="node_export_bloom",
        outputs={
            "checkpoint": "node_export_bloom",
            "action_required": "Xuất ma trận đề thi chuẩn Bloom",
            "approval_id": "appr_bloom_001",
            "tool_name": "export_exam_matrix",
        },
        latency_ms=180.0,
    )

    req = AssistantChatRequest(
        message="Xuất ma trận đề thi môn CSDL sang file Excel",
        conversation_id="conv_bloom_test",
        stream=True,
    )

    with (
        patch.object(assistant_service, "get_assistant", new_callable=AsyncMock) as mock_get_asst,
        patch("app.modules.assistants.service.workflow_service.execute", new_callable=AsyncMock) as mock_wf_exec,
        patch("app.modules.conversations.service.conversation_service.record_message", new_callable=AsyncMock),
        patch.object(assistant_service, "_get_recent_conversation_history", new_callable=AsyncMock) as mock_hist,
    ):
        mock_get_asst.return_value = mock_assistant
        mock_wf_exec.return_value = mock_workflow_resp
        mock_hist.return_value = []

        events = []
        async for chunk in assistant_service.chat_stream(mock_db, "question-bank", req):
            events.append(chunk)

        # Confirm approval_required event was yielded
        approval_events = [e for e in events if "event: approval_required" in e]
        assert len(approval_events) == 1
        assert "appr_bloom_001" in approval_events[0]
        assert "export_exam_matrix" in approval_events[0]

        # Confirm token stream contains approval notice
        token_events = [e for e in events if "event: token" in e]
        assert len(token_events) > 0

        # Confirm done event contains status paused_for_approval
        done_events = [e for e in events if "event: done" in e]
        assert len(done_events) == 1
        assert "paused_for_approval" in done_events[0]


@pytest.mark.asyncio
async def test_get_recent_conversation_history_fetches_and_formats_in_chronological_order():
    """Verify _get_recent_conversation_history retrieves and formats messages correctly."""
    mock_db = AsyncMock()

    # DB returns newest first (DESC)
    m1 = ConversationMessageModel(id="m1", thread_id="conv_1", sender="assistant", text="Điểm chuẩn là 24.5")
    m2 = ConversationMessageModel(id="m2", thread_id="conv_1", sender="user", text="Điểm chuẩn CNTT bao nhiêu?")

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [m1, m2]
    mock_db.execute.return_value = mock_res

    history = await assistant_service._get_recent_conversation_history(mock_db, "conv_1", limit=6)

    # Should be reversed to chronological order
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Điểm chuẩn CNTT bao nhiêu?"}
    assert history[1] == {"role": "assistant", "content": "Điểm chuẩn là 24.5"}


@pytest.mark.asyncio
async def test_rag_service_injects_history_into_llm_messages():
    """Verify rag_service.ask prepends conversation history before current user query in LLM prompt."""
    mock_db = AsyncMock()

    ask_req = AskRequest(
        question="Thế còn học phí của ngành đó?",
        collection_id="col_admissions",
        module_code="admissions",
        history=[
            {"role": "user", "content": "Ngành CNTT mã ngành là gì?"},
            {"role": "assistant", "content": "Ngành Công nghệ Thông tin có mã 7480201."},
        ],
    )

    mock_llm_resp = MagicMock()
    mock_llm_resp.content = "Học phí ngành CNTT khoảng 15-18 triệu đồng/năm."
    mock_llm_resp.provider = "openai"
    mock_llm_resp.total_tokens = 60

    with (
        patch("app.modules.rag.service.semantic_cache.get", new_callable=AsyncMock, return_value=None),
        patch("app.modules.rag.service.semantic_cache.set", new_callable=AsyncMock),
        patch("app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock) as mock_ret,
        patch("app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock) as mock_facts,
        patch("app.modules.rag.service.modelops_service.generate", new_callable=AsyncMock) as mock_gen,
    ):
        from app.modules.rag.schemas import SearchResultItem

        candidate = SearchResultItem(
            chunk_id="chk_1",
            document_id="doc_1",
            content="Học phí Trường ĐH Quy Nhơn năm 2026 dao động từ 15-18 triệu đồng.",
            score=0.85,
            rank=1,
            title="Đề án Tuyển sinh QNU 2026",
        )
        mock_ret.return_value = [candidate]
        mock_facts.return_value = []
        mock_gen.return_value = mock_llm_resp

        resp = await rag_service.ask(mock_db, ask_req)

        assert resp.status == "answered"
        assert mock_gen.called
        call_req = mock_gen.call_args[0][1]

        # Verify LLM request messages contain the history items
        roles = [m.role for m in call_req.messages]
        contents = [m.content for m in call_req.messages]

        assert "system" in roles
        assert any("Ngành CNTT mã ngành là gì?" in c for c in contents)
        assert any("Ngành Công nghệ Thông tin có mã 7480201." in c for c in contents)
        assert any("Thế còn học phí của ngành đó?" in c for c in contents)


def test_workflow_compiler_warns_on_approval_tool():
    """Verify workflow compiler warns when an api_caller node uses a tool requiring HITL approval."""
    dag_spec = WorkflowDagSpec(
        entry_node_id="node_start",
        nodes=[
            WorkflowNodeSpec(
                id="node_start",
                type="chat_input",
                config={},
            ),
            WorkflowNodeSpec(
                id="node_export_nd30",
                type="api_caller",
                config={
                    "tool_id": "export_administrative_document",
                    "on_error": "fail_workflow",
                },
            ),
            WorkflowNodeSpec(
                id="node_output",
                type="output_chat",
                config={},
            ),
        ],
        edges=[
            {"source": "node_start", "target": "node_export_nd30"},
            {"source": "node_export_nd30", "target": "node_output"},
        ],
        policies={"max_steps": 10},
    )

    report = workflow_compiler.validate(dag_spec)

    approval_warnings = [
        issue for issue in report.issues if issue.code == "workflow_tool_requires_approval_info"
    ]
    assert len(approval_warnings) == 1
    assert "export_administrative_document" in approval_warnings[0].message
    assert approval_warnings[0].severity == "warning"
