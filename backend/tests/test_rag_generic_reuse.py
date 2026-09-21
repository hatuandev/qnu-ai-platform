"""Tests for generic reusable RAG + DAG behavior across any new assistant."""

from __future__ import annotations

import pytest

from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.query_router import QueryIntent, query_classifier
from app.modules.rag.service import build_generic_system_instruction, is_refusal_answer
from app.modules.workflows.nodes.query_rewrite_node import fast_rule_normalize
from app.modules.workflows.schemas import WorkflowDagSpec, WorkflowNodeSpec
from app.modules.workflows.service import workflow_service


def test_query_classifier_supports_library_and_drafting_packs() -> None:
    """Library and drafting queries must route Fact-First without code changes."""
    lib_analysis = query_classifier.analyze(
        "Giáo trình Giải tích 1 nhà xuất bản Giáo dục năm 2023 ở kệ nào?",
        module_code="library",
    )
    assert lib_analysis.is_fact_first is True
    assert lib_analysis.intent in (QueryIntent.MIXED, QueryIntent.EXACT_FACT)

    drafting_analysis = query_classifier.analyze(
        "Quyết định số 2699/QĐ-ĐHQN ngày ban hành khi nào?",
        module_code="drafting",
    )
    assert drafting_analysis.is_fact_first is True


def test_query_classifier_unknown_module_uses_generic_signals() -> None:
    """Unknown future assistants fall back to generic money/year/decision signals."""
    generic_exact = query_classifier.analyze(
        "Mức hỗ trợ 3.5 triệu mỗi tháng năm 2025 là bao nhiêu?",
        module_code="dormitory_brand_new",
    )
    assert generic_exact.is_fact_first is True

    generic_narrative = query_classifier.analyze(
        "Xin chào, bạn có khỏe không?",
        module_code="dormitory_brand_new",
    )
    assert generic_narrative.intent == QueryIntent.NARRATIVE
    assert generic_narrative.is_fact_first is False


def test_query_classifier_mon_hoc_maps_to_subject_combinations() -> None:
    """Ambiguous 'mon hoc ... xet tuyen' must route Fact-First with subject_combinations."""
    bug_analysis = query_classifier.analyze(
        "bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?",
        module_code="admissions",
    )
    assert bug_analysis.is_fact_first is True
    assert "7480201" in bug_analysis.entity_codes
    assert "subject_combinations" in bug_analysis.fact_attributes
    assert "tổ hợp môn" in bug_analysis.keywords

    # Direct admission (HSG / tuyen thang) must NOT be forced to subject_combinations
    hsg_analysis = query_classifier.analyze(
        "Danh sách học sinh giỏi được tuyển thẳng ngành Công nghệ thông tin?",
        module_code="admissions",
    )
    assert "7480201" in hsg_analysis.entity_codes
    assert "subject_combinations" not in hsg_analysis.fact_attributes


def test_query_classifier_extracts_subjects_for_reverse_combo_lookup() -> None:
    """'Which programs have Toan-Anh-Hoa?' must yield subject names for recall."""
    reverse = query_classifier.analyze(
        "các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học",
        module_code="admissions",
    )
    assert reverse.is_fact_first is True
    assert "subject_combinations" in reverse.fact_attributes
    assert "toán" in reverse.subject_names
    assert "hóa" in reverse.subject_names
    assert "tiếng anh" in reverse.subject_names
    assert "anh" not in reverse.subject_names

    # Bare pronouns and HSG queries must not produce subjects
    pronoun = query_classifier.analyze(
        "anh cho em hỏi học phí là bao nhiêu?",
        module_code="admissions",
    )
    assert pronoun.subject_names == []

    hsg = query_classifier.analyze(
        "Danh sách học sinh giỏi được tuyển thẳng ngành Công nghệ thông tin?",
        module_code="admissions",
    )
    assert hsg.subject_names == []
    assert "subject_combinations" not in hsg.fact_attributes


def test_scope_history_by_topic_drops_stale_turns() -> None:
    """Independent new questions must not inherit unrelated older answers."""
    from app.modules.rag.query_router import scope_history_by_topic

    history = [
        {"role": "user", "content": "học phí ngành Kế toán là bao nhiêu?"},
        {"role": "assistant", "content": "Học phí ngành Kế toán là 15 triệu."},
        {"role": "user", "content": "trường áp dụng những phương thức xét tuyển nào?"},
        {"role": "assistant", "content": "Phương thức 1: thi THPT..."},
    ]
    reverse = query_classifier.analyze(
        "các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học",
        module_code="admissions",
    )
    scoped = scope_history_by_topic(history, reverse)
    # Latest turn preserved for continuity, stale Kế toán turn dropped
    assert len(scoped) <= 4
    assert scoped[-2:] == history[-2:]
    assert all("Kế toán" not in str(m.get("content", "")) for m in scoped)

    # Same-topic follow-ups keep overlapping turns; empty history stays honest
    same_topic = query_classifier.analyze(
        "học phí ngành Kế toán năm 2026?", module_code="admissions"
    )
    assert len(scope_history_by_topic(history, same_topic)) >= 2
    assert scope_history_by_topic([], reverse) == []
    assert scope_history_by_topic(None, reverse) == []


def test_citation_guard_generic_no_answer_for_new_modules() -> None:
    """New modules get polite generic refusal; known modules keep curated templates."""
    assert "0256.3846.156" in citation_guard.get_no_answer_response("admissions")
    assert "Thư viện" in citation_guard.get_no_answer_response("library")

    generic_msg = citation_guard.get_no_answer_response("ktx_dormitory")
    assert "Trường Đại học Quy Nhơn" in generic_msg

    named_msg = citation_guard.get_no_answer_response("ktx_dormitory", assistant_name="Ký túc xá")
    assert "Ký túc xá" in named_msg


def test_generic_system_instruction_uses_module_contact() -> None:
    """System prompt builder must be reusable and honor custom prompts."""
    custom = "Bạn là trợ lý KTX thân thiện."
    assert build_generic_system_instruction("ktx", custom) == custom

    admissions_prompt = build_generic_system_instruction("admissions", None)
    assert "0256.3846.156" in admissions_prompt
    assert "Zero Hallucination" in admissions_prompt

    generic_prompt = build_generic_system_instruction("brand_new_module", None)
    assert "Zero Hallucination" in generic_prompt
    assert "0256.3846.156" not in generic_prompt


def test_refusal_detection_is_domain_agnostic() -> None:
    """Refusal detection must not depend on admissions-only keywords."""
    library_answer = "Theo thư viện, giáo trình Giải tích có 5 bản ở kệ A12."
    assert is_refusal_answer(library_answer, has_evidence=True) is False

    refusal = "Thông tin này hiện chưa có trong tài liệu chính thức."
    assert is_refusal_answer(refusal, has_evidence=False) is True
    assert is_refusal_answer(refusal, has_evidence=True) is False


def test_fast_rule_normalize_supports_custom_acronyms() -> None:
    """New assistants can inject abbreviations via custom_acronyms without code edits."""
    base = fast_rule_normalize("phòng ktx giá bao nhiêu")
    assert "ký túc xá" in base.lower()

    custom = fast_rule_normalize(
        "đăng ký ở ktx nova",
        extra_acronyms={r"\bnova\b": "Nova Dormitory"},
    )
    assert "Nova Dormitory" in custom


def test_fork_workflow_injects_bindings_for_new_assistant() -> None:
    """Fork must inject collection, module, prompt and rewrite instruction."""
    base_spec = WorkflowDagSpec(
        entry_node_id="chat_input",
        nodes=[
            WorkflowNodeSpec(id="chat_input", type="input.chat"),
            WorkflowNodeSpec(
                id="knowledge_answer",
                type="core.knowledge.answer",
                config={"module_code": "general"},
            ),
            WorkflowNodeSpec(id="query_rewrite", type="query.rewrite", config={}),
        ],
        edges=[],
    )
    injected = workflow_service._inject_assistant_bindings(
        base_spec,
        module_code="dormitory",
        collection_id="col_dormitory",
        system_prompt="Bạn là trợ lý KTX.",
        rewrite_instruction="Chuẩn hóa câu hỏi KTX.",
    )
    nodes_by_id = {node.id: node for node in injected.nodes}
    assert nodes_by_id["knowledge_answer"].config["module_code"] == "dormitory"
    assert nodes_by_id["knowledge_answer"].config["collection_id"] == "col_dormitory"
    assert nodes_by_id["knowledge_answer"].config["system_prompt"] == "Bạn là trợ lý KTX."
    assert nodes_by_id["query_rewrite"].config["instruction"] == "Chuẩn hóa câu hỏi KTX."


@pytest.mark.asyncio
async def test_base_template_is_valid_and_reusable() -> None:
    """Generic base workflow template must pass publication validation."""
    from app.modules.workflows.compiler import workflow_compiler

    spec = await workflow_service.get_workflow_spec(None, "_base-assistant")
    report = workflow_compiler.validate(spec)
    assert report.is_valid, f"Base template invalid: {report.issues}"
    node_types = {node.type for node in spec.nodes}
    assert "query.rewrite" in node_types
    assert "core.knowledge.answer" in node_types
    assert "guard.citation_policy" in node_types


@pytest.mark.asyncio
async def test_rag_answer_node_fails_closed_for_unknown_without_collection() -> None:
    """RAG node must fail closed instead of leaking admissions data to new assistants."""
    from unittest.mock import AsyncMock

    from app.core.exceptions import AppException
    from app.modules.workflows.nodes.base import WorkflowContext
    from app.modules.workflows.nodes.rag_answer_node import RAGAnswerNodeHandler

    handler = RAGAnswerNodeHandler()
    spec = WorkflowNodeSpec(id="knowledge_answer", type="core.knowledge.answer", config={})
    ctx = WorkflowContext(
        workflow_id="brand-new-assistant",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"message": "Xin chào"},
        db=AsyncMock(),
    )
    with pytest.raises(AppException) as exc_info:
        await handler.execute(spec, ctx)
    assert exc_info.value.code == "workflow_missing_collection"
