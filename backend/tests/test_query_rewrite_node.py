"""Unit tests for QueryRewriteNodeHandler and fast rule-based normalization."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.modelops.schemas import LLMGenerateResponse
from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.nodes.query_rewrite_node import (
    QueryRewriteNodeHandler,
    fast_rule_normalize,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


def test_fast_rule_normalize_contextual_typos():
    """Verify that contextual typos like 'ngày' -> 'ngành', 'học bà' -> 'học bạ' are corrected."""
    # "ngày" before major name
    res1 = fast_rule_normalize("học phí ngày công nghệ thông tin là bao nhiêu")
    assert "học phí ngành Công nghệ thông tin là bao nhiêu" == res1

    # "ngày" in admissions context
    res2 = fast_rule_normalize("chỉ tiêu ngày quản trị kinh doanh")
    assert "chỉ tiêu ngành Quản trị kinh doanh" == res2

    # "học bà thpt"
    res3 = fast_rule_normalize("xét học bà thpt như thế nào?")
    assert "xét học bạ THPT như thế nào?" == res3

    # "kí túc sá"
    res4 = fast_rule_normalize("chi phí ở kí túc sá bao nhiêu")
    assert "chi phí ở ký túc xá bao nhiêu" == res4

    # "điểm chuẫn" and acronyms
    res5 = fast_rule_normalize("điểm chuẫn ngành qtkd năm 2024")
    assert "điểm chuẩn ngành Quản trị kinh doanh năm 2024" == res5

    # "học bỗng"
    res6 = fast_rule_normalize("chính sách học bỗng của trường")
    assert "chính sách học bổng của trường" == res6


def test_fast_rule_normalize_preserves_correct_queries():
    """Verify that already correct queries are not mangled."""
    correct_query = "Học phí ngành Sư phạm Toán học là bao nhiêu?"
    assert fast_rule_normalize(correct_query) == correct_query

    calendar_query = "Hôm nay là ngày 20 tháng 11"
    # "ngày" followed by date should NOT become "ngành 20"
    assert fast_rule_normalize(calendar_query) == calendar_query


@pytest.mark.asyncio
async def test_query_rewrite_node_handler_rule_only():
    """Verify execution of QueryRewriteNodeHandler when only rule-based normalization runs."""
    handler = QueryRewriteNodeHandler()
    spec = WorkflowNodeSpec(
        id="query_rewrite_1",
        type="query.rewrite",
        config={"use_fast_rules": True, "use_llm": False},
    )
    ctx = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"message": "học phí ngày cntt"},
    )

    res = await handler.execute(spec, ctx)
    assert res.status == "completed"
    assert ctx.node_data["normalized_query"] == "học phí ngành Công nghệ thông tin"
    assert ctx.node_data["user_message"] == "học phí ngành Công nghệ thông tin"
    assert res.output["modified"] is True


@pytest.mark.asyncio
async def test_query_rewrite_node_handler_with_llm_success():
    """Verify execution of QueryRewriteNodeHandler when LLM rewrites the query."""
    handler = QueryRewriteNodeHandler()
    spec = WorkflowNodeSpec(
        id="query_rewrite_1",
        type="query.rewrite",
        config={"use_fast_rules": True, "use_llm": True},
    )
    fake_db = AsyncMock()
    ctx = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"message": "cho em hoi hoc phi ngay cntt voi a"},
        db=fake_db,
    )

    mock_llm_response = LLMGenerateResponse(
        content="Học phí ngành Công nghệ thông tin là bao nhiêu?",
        provider="gemini",
        model="gemini-2.5-flash",
    )

    with patch(
        "app.modules.workflows.nodes.query_rewrite_node.modelops_service.generate",
        new=AsyncMock(return_value=mock_llm_response),
    ):
        res = await handler.execute(spec, ctx)

    assert res.status == "completed"
    assert ctx.node_data["normalized_query"] == "Học phí ngành Công nghệ thông tin là bao nhiêu?"
    assert ctx.node_data["user_message"] == "Học phí ngành Công nghệ thông tin là bao nhiêu?"
    assert res.output["modified"] is True


@pytest.mark.asyncio
async def test_query_rewrite_node_handler_fallback_on_llm_error():
    """Verify that if LLM raises an error or times out, rule-based normalized query is preserved."""
    handler = QueryRewriteNodeHandler()
    spec = WorkflowNodeSpec(
        id="query_rewrite_1",
        type="query.rewrite",
        config={"use_fast_rules": True, "use_llm": True},
    )
    fake_db = AsyncMock()
    ctx = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"message": "học phí ngày cntt"},
        db=fake_db,
    )

    with patch(
        "app.modules.workflows.nodes.query_rewrite_node.modelops_service.generate",
        side_effect=RuntimeError("API Network Timeout"),
    ):
        res = await handler.execute(spec, ctx)

    assert res.status == "completed"
    assert ctx.node_data["normalized_query"] == "học phí ngành Công nghệ thông tin"
    assert res.output["modified"] is True


def test_fast_rule_normalize_academic_and_library_terms():
    """Verify that academic, regulation and library typos/acronyms are normalized."""
    res1 = fast_rule_normalize("quy định đăng ký tín chì và học phầm")
    assert "quy định đăng ký tín chỉ và học phần" == res1

    res2 = fast_rule_normalize("xét học bỗng theo đrl")
    assert "xét học bổng theo Điểm rèn luyện" == res2

    res3 = fast_rule_normalize("mượn giáo trinh và tài liêu thư viện")
    assert "mượn giáo trình và tài liệu thư viện" == res3


def test_get_node_instruction_and_prompt_building():
    """Verify that node instruction is resolved flexibly per workflow without hardcoded domains."""
    from app.modules.workflows.nodes.query_rewrite_node import (
        build_rewrite_prompt,
        get_node_instruction,
    )

    ctx_empty = WorkflowContext(
        workflow_id="wf_custom",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
    )

    # 1. Explicit custom instruction configured directly on the node
    custom_inst = "Chuẩn hóa câu hỏi ký túc xá: mở rộng KTX, SV, làm rõ loại phòng ở."
    inst1 = get_node_instruction(ctx_empty, {"instruction": custom_inst})
    assert inst1 == custom_inst

    prompt1 = build_rewrite_prompt("phòng ktx giá bao nhiêu", inst1)
    assert custom_inst in prompt1
    assert "QUY TẮC BẮT BUỘC" in prompt1
    assert "phòng ktx giá bao nhiêu" in prompt1

    # 2. Template with custom {query} placeholder
    template_prompt = "Rewrite this query for examination office: {query}"
    prompt2 = build_rewrite_prompt("lịch thi k45", template_prompt)
    assert prompt2 == "Rewrite this query for examination office: lịch thi k45"

    # 3. Domain helper shorthand
    inst3 = get_node_instruction(ctx_empty, {"domain": "khảo thí"})
    assert "khảo thí" in inst3
    assert "Trường Đại học Quy Nhơn" in inst3

    # 4. Universal fallback for any custom workflow
    inst4 = get_node_instruction(ctx_empty, {})
    assert "Bạn là trợ lý chuẩn hóa câu hỏi cho Trường Đại học Quy Nhơn" in inst4
