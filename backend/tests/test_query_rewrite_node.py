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


def test_fast_rule_normalize_subject_combo_paraphrase():
    """Ambiguous 'mon hoc' queries must expand to 'to hop mon' without double expansion."""
    from app.modules.workflows.nodes.query_rewrite_node import expand_subject_combo_paraphrase

    bug_query = "bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?"
    expanded = fast_rule_normalize(bug_query)
    assert "tổ hợp môn nào" in expanded
    assert "tổ hợp tổ hợp" not in expanded
    assert "Công nghệ thông tin" in expanded

    # HSG / direct admission queries must stay untouched to keep Phu luc 1 routing
    hsg_query = "Danh sách học sinh giỏi được tuyển thẳng ngành Công nghệ thông tin?"
    assert expand_subject_combo_paraphrase(hsg_query) == hsg_query

    # Date mentions must not be mangled
    assert fast_rule_normalize("Hôm nay là ngày 20 tháng 11") == "Hôm nay là ngày 20 tháng 11"


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


def test_is_context_dependent_query():
    """Verify that standalone questions are recognized as independent of conversation history."""
    from app.modules.workflows.nodes.query_rewrite_node import is_context_dependent_query

    # Standalone queries should NOT depend on history
    assert not is_context_dependent_query("Phương thức xét tuyển của trường gồm những gì?")
    assert not is_context_dependent_query("Học phí ngành Sư phạm Toán học là bao nhiêu?")
    assert not is_context_dependent_query("Quy định đăng ký ký túc xá cho sinh viên năm nhất?")
    assert not is_context_dependent_query("Điều kiện nhận học bổng khuyến khích học tập là gì?")

    # Follow-ups and anaphora queries MUST depend on history
    assert is_context_dependent_query("học phí ngành này")
    assert is_context_dependent_query("thế còn ngành đó?")
    assert is_context_dependent_query("có tôi muốn")
    assert is_context_dependent_query("tiếp đi")
    assert is_context_dependent_query("bao nhiêu?")


@pytest.mark.asyncio
async def test_query_rewrite_standalone_query_not_hijacked_by_history():
    """Verify that a standalone question is not corrupted by previous multi-turn history."""
    from app.modules.workflows.nodes.query_rewrite_node import is_context_dependent_query

    handler = QueryRewriteNodeHandler()
    spec = WorkflowNodeSpec(
        id="query_rewrite_1",
        type="query.rewrite",
        config={"use_fast_rules": True, "use_llm": True},
    )
    fake_db = AsyncMock()
    user_query = "Phương thức xét tuyển của trường gồm những gì?"
    history = [
        {"role": "user", "content": "các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học"},
        {
            "role": "assistant",
            "content": "Dưới đây là các ngành xét tuyển tổ hợp Toán, Tiếng Anh, Hóa học: Công nghệ thông tin...",
        },
    ]
    ctx = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id="conv_123",
        inputs={
            "message": user_query,
            "conversation_history": history,
        },
        db=fake_db,
    )

    # Standalone check must be False
    assert not is_context_dependent_query(user_query)

    # Even if LLM erroneously bleeds history into candidate, defensive guards MUST reject it
    mock_hijacked_response = LLMGenerateResponse(
        content="Các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học tại Trường Đại học Quy Nhơn gồm những ngành nào?",
        provider="gemini",
        model="gemini-2.5-flash",
    )

    with patch(
        "app.modules.workflows.nodes.query_rewrite_node.modelops_service.generate",
        new=AsyncMock(return_value=mock_hijacked_response),
    ):
        res = await handler.execute(spec, ctx)

    assert res.status == "completed"
    # The output MUST preserve the user's intended question without bleeding previous subjects
    assert ctx.node_data["normalized_query"] == user_query
    assert ctx.node_data["user_message"] == user_query


@pytest.mark.asyncio
async def test_query_rewrite_defensive_guard_rejects_dropped_intent():
    """Verify that if LLM replaces intent (e.g. 'học phí' -> 'điểm chuẩn'), it is rejected."""
    handler = QueryRewriteNodeHandler()
    spec = WorkflowNodeSpec(
        id="query_rewrite_1",
        type="query.rewrite",
        config={"use_fast_rules": True, "use_llm": True},
    )
    fake_db = AsyncMock()
    user_query = "học phí ngành Sư phạm Toán học"
    ctx = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"message": user_query},
        db=fake_db,
    )

    # LLM hallucinates and switches from tuition fee to benchmark score
    mock_switched_response = LLMGenerateResponse(
        content="Điểm chuẩn ngành Sư phạm Toán học năm 2024 là bao nhiêu?",
        provider="gemini",
        model="gemini-2.5-flash",
    )

    with patch(
        "app.modules.workflows.nodes.query_rewrite_node.modelops_service.generate",
        new=AsyncMock(return_value=mock_switched_response),
    ):
        res = await handler.execute(spec, ctx)

    assert res.status == "completed"
    # Must fallback because 'học phí' intent was dropped
    assert "học phí" in ctx.node_data["normalized_query"].lower()

