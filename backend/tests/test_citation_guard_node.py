"""Unit tests for CitationGuardNodeHandler — Number Hallucination Detection & Groundedness."""

from __future__ import annotations

import pytest

from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.nodes.citation_guard_node import (
    CitationGuardNodeHandler,
    _detect_number_hallucinations,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


@pytest.fixture
def citation_guard_spec() -> WorkflowNodeSpec:
    return WorkflowNodeSpec(
        id="guard_node",
        type="policy.citation_guard",
        config={
            "require_citation_for_answer": True,
            "accepted_statuses": ["answered", "success"],
            "invalid_route": "ungrounded",
        },
    )


def test_detect_number_hallucinations_logic():
    context_text = "điểm chuẩn ngành công nghệ thông tin năm 2026 là 24.5 điểm, chỉ tiêu 150 sinh viên."

    # Case 1: All numbers present in context (2026, 24.5, 150) -> No hallucination
    answer_valid = "Theo đề án tuyển sinh năm 2026, ngành Công nghệ thông tin lấy 24.5 điểm và tuyển 150 chỉ tiêu."
    assert _detect_number_hallucinations(answer_valid, context_text) == []

    # Case 2: Hallucinated cutoff score (28.75) not in context -> Flagged
    answer_hallucinated = "Ngành Công nghệ thông tin năm 2026 lấy 28.75 điểm."
    unsupported = _detect_number_hallucinations(answer_hallucinated, context_text)
    assert "28.75" in unsupported

    # Case 3: Comma vs dot notation (24,5 vs 24.5) -> Supported, not flagged
    answer_comma = "Điểm chuẩn ngành CNTT là 24,5 điểm."
    assert _detect_number_hallucinations(answer_comma, context_text) == []

    # Case 4: Official Hotline numbers -> Not flagged
    answer_with_hotline = "Vui lòng liên hệ Hotline 0256.3846.156 để biết thêm chi tiết."
    assert _detect_number_hallucinations(answer_with_hotline, context_text) == []

    # Case 5: Thousand-separated numbers (e.g. tuition fees 15.000.000 VNĐ)
    ctx_tuition = "học phí dự kiến là 15.000.000 vnđ/năm đối với khối ngành kỹ thuật."
    answer_tuition = "Học phí ngành CNTT là 15.000.000 VNĐ/năm."
    assert _detect_number_hallucinations(answer_tuition, ctx_tuition) == []

    answer_fake_tuition = "Học phí ngành CNTT là 18.000.000 VNĐ/năm."
    unsupported_tuition = _detect_number_hallucinations(answer_fake_tuition, ctx_tuition)
    assert "18.000.000" in unsupported_tuition



@pytest.mark.asyncio
async def test_citation_guard_blocks_numerical_hallucination(citation_guard_spec):
    handler = CitationGuardNodeHandler()

    # Context has 24.5, but LLM hallucinates 29.0
    ctx = WorkflowContext(
        workflow_id="wf_admissions",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
        node_data={
            "rag_answer": "Điểm chuẩn ngành Kỹ thuật phần mềm là 29.0 điểm.",
            "citations": [
                {
                    "source_id": "De_an_2026.pdf",
                    "title": "Đề án Tuyển sinh 2026",
                    "quote": "Ngành Kỹ thuật phần mềm xét tuyển với điểm chuẩn là 24.5 điểm.",
                }
            ],
            "rag_status": "answered",
        },
    )

    result = await handler.execute(citation_guard_spec, ctx)

    assert result.status == "completed"
    assert result.output["is_grounded"] is False
    assert result.selected_port == "ungrounded"
    assert "29.0" in result.output["unsupported_numbers"]


@pytest.mark.asyncio
async def test_citation_guard_approves_grounded_answer(citation_guard_spec):
    handler = CitationGuardNodeHandler()

    # Exact numbers matching citation quote
    ctx = WorkflowContext(
        workflow_id="wf_admissions",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
        node_data={
            "rag_answer": "Theo Đề án 2026, ngành Sư phạm Toán lấy điểm chuẩn 26.5 với 80 chỉ tiêu.",
            "citations": [
                {
                    "source_id": "De_an_2026.pdf",
                    "title": "Đề án Tuyển sinh 2026",
                    "quote": "Sư phạm Toán học: chỉ tiêu 80, điểm chuẩn 26.5 điểm.",
                }
            ],
            "rag_status": "answered",
        },
    )

    result = await handler.execute(citation_guard_spec, ctx)

    assert result.status == "completed"
    assert result.output["is_grounded"] is True
    assert result.selected_port == "grounded"
    assert result.output["unsupported_numbers"] == []


@pytest.mark.asyncio
async def test_citation_guard_rejects_missing_citations(citation_guard_spec):
    handler = CitationGuardNodeHandler()

    ctx = WorkflowContext(
        workflow_id="wf_admissions",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
        node_data={
            "rag_answer": "Thông tin về học phí đang cập nhật.",
            "citations": [],
            "rag_status": "answered",
        },
    )

    result = await handler.execute(citation_guard_spec, ctx)

    assert result.status == "completed"
    assert result.output["is_grounded"] is False
    assert result.selected_port == "ungrounded"
