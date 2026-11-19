"""Pipeline unit tests for Phase 2 Slice 5: Contextual Rewriter & Deterministic Calculator."""

from __future__ import annotations

from qnu.domains.rag.answer.calculator import CalculationRequest, evaluate_expression
from qnu.domains.rag.answer.decomposition import decompose_query
from qnu.domains.rag.answer.drafting import PROMPT_VERSION
from qnu.domains.rag.answer.intent_router import classify_intent
from qnu.domains.rag.answer.rewriter import rewrite_contextual_query
from qnu.domains.rag.answer.schemas import AnswerTrace


def test_multiturn_rewriting_then_intent_and_decomposition_pipeline():
    history = [
        {"question": "Xin chào trợ lý", "answer": "Chào bạn! Tôi có thể giúp gì cho bạn?"},
        {
            "question": "Thí sinh có mã hồ sơ 0012 muốn hỏi điều kiện xét tuyển và chỉ tiêu tuyển sinh như thế nào?",
            "answer": "Bạn muốn hỏi về ngành nào và năm nào?",
        },
    ]
    current_reply = "Ngành CNTT năm 2026 ạ"

    # Step 1: Multi-turn Rewriter synthesizes standalone query
    resolved_query, rewrite_trace = rewrite_contextual_query(current_reply, history)
    assert rewrite_trace["rewritten"] is True
    assert "0012" in resolved_query
    assert "CNTT" in resolved_query
    assert "2026" in resolved_query

    # Step 2: Intent router receives rewritten standalone query
    intent = classify_intent(resolved_query)
    assert intent in {"tabular_aggregation", "rule_reasoning", "direct_lookup"}

    # Step 3: Query decomposition preserves zero-prefixed 0012 and 2026
    sub_queries = decompose_query(resolved_query)
    assert 1 <= len(sub_queries) <= 3
    all_text = " ".join(sub_queries)
    assert "0012" in all_text
    assert "2026" in all_text


def test_calculator_missing_variables_reported_in_trace():
    calc_req = CalculationRequest(
        formula="0.45 * A + 0.35 * B + 0.20 * C",
        variables={"A": 24.0},  # Missing B and C
        preconditions=["minh_chung >= 0.8"],
    )
    result = evaluate_expression(calc_req)
    assert result.status == "missing_variables"
    assert "B" in result.missing_variables
    assert "C" in result.missing_variables
    assert "minh_chung" in result.missing_variables

    trace = AnswerTrace(prompt_version=PROMPT_VERSION)
    trace.calculator = result.model_dump(mode="json")
    assert trace.calculator["status"] == "missing_variables"
    assert trace.calculator["missing_variables"] == ["B", "C", "minh_chung"]


def test_calculator_precondition_and_weighted_evaluation_in_trace():
    calc_req = CalculationRequest(
        formula="0.45 * A + 0.35 * B + 0.20 * C",
        variables={"A": 24.0, "B": 26.0, "C": 28.0, "minh_chung": 0.85},
        preconditions=["minh_chung >= 0.8"],
        rounding=2,
    )
    result = evaluate_expression(calc_req)
    assert result.status == "success"
    assert result.evaluated_value == 25.5
    assert result.formatted_result == "25.5"

    trace = AnswerTrace(prompt_version=PROMPT_VERSION)
    trace.calculator = result.model_dump(mode="json")
    assert trace.calculator["status"] == "success"
    assert trace.calculator["evaluated_value"] == 25.5
