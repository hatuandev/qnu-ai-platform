"""Unit tests for ConditionRouteNodeHandler — Syntactic Invariants & Micro-LLM Hybrid Routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.modelops.schemas import LLMGenerateResponse
from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.nodes.condition_route_node import (
    ConditionRouteNodeHandler,
    _is_pure_greeting,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


@pytest.fixture
def route_spec() -> WorkflowNodeSpec:
    return WorkflowNodeSpec(
        id="route_intent",
        type="condition.route",
        config={
            "rules": [
                {
                    "id": "greet_rule",
                    "match": {"intent": r"\b(?:xin\s+chào|chào|hi|hello)\b"},
                    "to": "greeting_node",
                },
                {
                    "id": "admissions_faq_rule",
                    "match": {"intent": r"\b(?:tuyển\s+sinh|xét\s+tuyển|ngành)\b"},
                    "to": "faq_node",
                },
            ],
            "default_node": "rag_answer_node",
        },
    )


def test_is_pure_greeting_syntactic_invariants():
    tokens = ["xin chào", "chào", "hi", "hello"]

    # 1. Pure greetings -> True
    assert _is_pure_greeting("Xin chào", tokens) is True
    assert _is_pure_greeting("Chào bạn", tokens) is True
    assert _is_pure_greeting("Chào thầy cô ạ!", tokens) is True
    assert _is_pure_greeting("Hi QNU AI bot!", tokens) is True
    assert _is_pure_greeting("Hello em", tokens) is True

    # 2. Contains question mark '?' -> Always False
    assert _is_pure_greeting("Chào bạn?", tokens) is False
    assert _is_pure_greeting("Xin chào?", tokens) is False

    # 3. Hybrid messages: Greeting + Substantive question -> Always False
    assert _is_pure_greeting("Chào bạn, cho mình hỏi học phí ngành CNTT là bao nhiêu?", tokens) is False
    assert _is_pure_greeting("Em chào thầy cô, điểm chuẩn năm nay thế nào ạ", tokens) is False
    assert _is_pure_greeting("Chào bot, mình muốn tìm hiểu về xét tuyển học bạ", tokens) is False

    # 4. Pure questions without greeting -> Always False
    assert _is_pure_greeting("Chỉ tiêu ngành Sư phạm Toán là bao nhiêu", tokens) is False
    assert _is_pure_greeting("Ký túc xá có còn chỗ không", tokens) is False

    # 5. Generalized university organizational morphology (no hardcoding needed)
    assert _is_pure_greeting("Kính chào Phòng Khảo thí và Đảm bảo chất lượng ạ!", tokens) is True
    assert _is_pure_greeting("Xin chào Viện Đào tạo Quốc tế!", tokens) is True
    assert _is_pure_greeting("Chào Khoa Công nghệ Thông tin", tokens) is True
    assert _is_pure_greeting("Chào Ban Tuyển sinh ĐH Quy Nhơn", tokens) is True
    assert _is_pure_greeting("Chào Thư viện QNU ạ", tokens) is True
    assert _is_pure_greeting("Chào Đoàn Thanh niên trường", tokens) is True



@pytest.mark.asyncio
async def test_condition_route_pure_greeting(route_spec):
    handler = ConditionRouteNodeHandler()
    ctx = WorkflowContext(
        workflow_id="wf_admissions",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
        node_data={"user_message": "Xin chào Trợ lý ảo ĐH Quy Nhơn ạ!"},
    )
    result = await handler.execute(route_spec, ctx)
    assert result.status == "completed"
    assert result.next_node_override == "greeting_node"
    assert result.output["matched_rule_id"] == "greet_rule"


@pytest.mark.asyncio
async def test_condition_route_hybrid_greeting_and_question(route_spec):
    handler = ConditionRouteNodeHandler()
    # User greets AND asks a question about majors -> should NOT route to greeting!
    ctx = WorkflowContext(
        workflow_id="wf_admissions",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
        node_data={"user_message": "Chào bạn, cho mình hỏi năm nay trường có những ngành nào?"},
    )
    result = await handler.execute(route_spec, ctx)
    assert result.status == "completed"
    # Matches admissions_faq_rule via regex evaluation ('ngành'), never greeting_node!
    assert result.next_node_override == "faq_node"
    assert result.output["matched_rule_id"] == "admissions_faq_rule"


@pytest.mark.asyncio
async def test_condition_route_micro_llm_disambiguation(route_spec):
    handler = ConditionRouteNodeHandler()
    # An ambiguous/slang question that doesn't match regex tokens but has semantic intent
    ctx = WorkflowContext(
        workflow_id="wf_admissions",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
        node_data={"user_message": "Cho mình xin chỉ tiêu vào sư phạm toán với"},
        db=AsyncMock(),
    )

    mock_llm_resp = LLMGenerateResponse(
        content='{"rule_id": "admissions_faq_rule", "confidence": 0.92}',
        model="gemini-2.5-flash",
        provider="prov_gemini",
    )

    with patch("app.modules.workflows.nodes.condition_route_node.modelops_service.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_resp
        result = await handler.execute(route_spec, ctx)

        assert result.status == "completed"
        assert result.next_node_override == "faq_node"
        assert result.output["matched_rule_id"] == "admissions_faq_rule"


@pytest.mark.asyncio
async def test_condition_route_micro_llm_timeout_fallback(route_spec):
    handler = ConditionRouteNodeHandler()
    ctx = WorkflowContext(
        workflow_id="wf_admissions",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
        node_data={"user_message": "Cơ hội việc làm sau khi ra trường thế nào"},
        db=AsyncMock(),
    )

    with patch("app.modules.workflows.nodes.condition_route_node.modelops_service.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = TimeoutError("LLM call timed out")
        result = await handler.execute(route_spec, ctx)

        assert result.status == "completed"
        # Gracefully falls back to default node
        assert result.next_node_override == "rag_answer_node"
