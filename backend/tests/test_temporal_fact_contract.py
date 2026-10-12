"""Year belongs to a fact, never inherited from the filename/document date."""

import pytest

from app.modules.knowledge.services.source_artifact import build_source_artifact


def test_multilevel_year_and_method_stay_attached_to_cell():
    md = """| STT | Mã ngành | Tên ngành | 2023 | | 2024 | |
| --- | --- | --- | --- | --- | --- | --- |
| | | | Điểm trúng tuyển (THPT) | Điểm trúng tuyển (Học bạ) | Điểm trúng tuyển (THPT) | Điểm trúng tuyển (Học bạ) |
| 1 | 7140114 | Quản lý Giáo dục | 15 | 18 | 22.5 | 18 |
"""
    artifact = build_source_artifact(md, 1, {"issued_date": "2026-01-01"})
    facts = [f for f in artifact["facts"] if f["raw_data"].get("attribute_code") == "cutoff_score"]
    assert {(f["raw_data"]["temporal_context"]["year"], f["raw_data"]["qualifiers"]["method"], f["attribute_value"])
            for f in facts} == {(2023, "THPT", "15"), (2023, "Học bạ", "18"), (2024, "THPT", "22.5"), (2024, "Học bạ", "18")}


def test_numeric_conversion_identity_is_preserved():
    artifact = build_source_artifact("| IELTS | Điểm quy đổi |\n| --- | --- |\n| 6.0 | 9.0 |\n| 7.0 | 10.0 |", 1, {})
    assert any(f["entity_name"] == "IELTS 6.0" and f["attribute_value"] == "9.0" for f in artifact["facts"])
    from app.modules.rag.temporal_answer import decide_table_answer

    result = decide_table_answer("IELTS 6.0 quy đổi thành bao nhiêu điểm?", artifact["facts"])
    assert result["status"] == "supported"
    assert [claim["value"] for claim in result["claim_bindings"]] == ["9.0"]
    assert decide_table_answer("IELTS 6.0 quy đổi thành bao nhiêu điểm năm 2026?", artifact["facts"])["status"] == "missing"


def test_document_date_is_not_first_cited_date_or_filename():
    from app.modules.knowledge.services.temporal_metadata import extract_temporal_metadata

    result = extract_temporal_metadata("Gia Lai, ngày 15 tháng 12 năm 2025\n\n**Tuyển sinh 2026**\n\nCăn cứ Thông tư ngày 02 tháng 01 năm 2021", "Tuyển sinh 2026.docx")
    assert result["issued_date"]["value"] == "2025-12-15"
    assert result["issued_year"]["value"] == 2025
    assert result["filename_years"]["values"] == [2026]
    assert result["subject_years"]["values"] == [2026]


def test_partial_date_never_invents_january_first():
    from app.modules.knowledge.services.temporal_metadata import extract_temporal_metadata

    result = extract_temporal_metadata("Gia Lai, ngày ... tháng ... năm 2026\n\nCăn cứ văn bản ngày 2 tháng 1 năm 2024", "2026.pdf")
    assert result["issued_date"]["value"] is None
    assert result["issued_year"]["status"] == "proposed"
    blank = extract_temporal_metadata("Gia Lai, ngày tháng năm 2026")
    assert blank["issued_date"]["value"] is None
    assert blank["issued_year"]["value"] == 2026


@pytest.mark.asyncio
async def test_missing_year_answerability_does_not_call_model():
    from app.modules.rag.temporal_answer import decide_table_answer

    artifact = build_source_artifact("| Mã ngành | Tên ngành | Điểm chuẩn 2025 |\n| --- | --- | --- |\n| 7480201 | Công nghệ thông tin | 21.5 |", 1, {})
    result = decide_table_answer("Điểm chuẩn ngành Công nghệ thông tin năm 2026?", artifact["facts"])
    assert result["status"] == "missing"
    assert "21.5" not in result["answer"]


@pytest.mark.asyncio
async def test_rag_runtime_missing_year_blocks_model_and_retrieval():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
    from app.modules.rag.service import RagService

    fact = SimpleNamespace(id="fact", entity_name="Công nghệ thông tin", attribute_name="Điểm chuẩn 2025",
                           attribute_value="21.5", raw_data={"entity_code": "7480201"}, binding_id="binding", index_revision_id="index")
    snapshot = RetrievalSnapshot(snapshot_id="snapshot", collection_id="collection", binding_revisions={"binding": "index"})
    with patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot)), \
         patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[fact])), \
         patch("app.modules.rag.service.hybrid_retriever.retrieve", AsyncMock()) as retrieval, \
         patch("app.modules.rag.service.modelops_service.generate", AsyncMock()) as model:
        result = await RagService().ask(None, AskRequest(question="Điểm chuẩn Công nghệ thông tin năm 2026?", collection_id="collection", module_code="admissions"))
    assert result.status == "insufficient_context"
    assert result.answer_decision["status"] == "missing"
    assert "21.5" not in result.answer
    model.assert_not_awaited()
    retrieval.assert_not_awaited()


def test_invalid_date_does_not_become_a_confirmed_year():
    from app.modules.knowledge.services.temporal_metadata import extract_temporal_metadata

    metadata = extract_temporal_metadata("Gia Lai, ngày 31 tháng 2 năm 2026")
    assert metadata["issued_date"]["value"] is None
    assert metadata["issued_year"]["value"] is None


def test_unknown_header_span_does_not_forward_fill_year():
    from app.modules.knowledge.services.table_context import header_paths

    paths = header_paths([["Ngành", "2023", "", "2024", ""], ["", "A", "B", "C", "D"]])
    assert paths[2] == ["B"]
    assert paths[4] == ["D"]


def test_supported_year_renders_actual_methods_and_conflicts_refuse():
    from app.modules.rag.temporal_answer import decide_table_answer

    md = "| Mã ngành | Tên ngành | Điểm chuẩn 2024 (THPT) | Điểm chuẩn 2024 (Học bạ) |\n| --- | --- | --- | --- |\n| 7480201 | Công nghệ thông tin | 16.5 | 20 |"
    facts = build_source_artifact(md, 1, {})["facts"]
    result = decide_table_answer("Điểm chuẩn Công nghệ thông tin 2024?", facts)
    assert result["status"] == "supported"
    assert {claim["method"] for claim in result["claim_bindings"]} == {"THPT", "Học bạ"}
    assert decide_table_answer("Điểm chuẩn Công nghệ thông tin 2024?", facts + [{**facts[0], "attribute_value": "22"}])["status"] == "conflict"


def test_comparison_keeps_supported_year_and_marks_missing_year():
    from app.modules.rag.temporal_answer import decide_table_answer

    facts = build_source_artifact("| Mã ngành | Tên ngành | Điểm chuẩn 2025 |\n| --- | --- | --- |\n| 7480201 | Công nghệ thông tin | 21.5 |", 1, {})["facts"]
    result = decide_table_answer("So sánh điểm chuẩn Công nghệ thông tin năm 2025 và 2026", facts)
    assert result["status"] == "missing"
    assert result["claim_bindings"][0]["year"] == 2025
    assert result["missing_constraints"] == [{"attribute": "cutoff_score", "year": 2026}]
    assert "2026 | — | Chưa đủ căn cứ" in result["answer"]
    interval = decide_table_answer("Điểm chuẩn Công nghệ thông tin 2024–2026?", facts)
    assert interval["status"] == "ambiguous"
    assert interval["claim_bindings"] == []


def test_cross_page_table_requires_contiguous_row_identity_not_only_width():
    md = """<!-- Trang 11 -->
| STT | Mã ngành | Tên ngành | Điểm chuẩn 2024 | Điểm chuẩn 2025 |
| --- | --- | --- | --- | --- |
| 31 | 7460112 | Toán ứng dụng | 15 | 19.5 |
| 32 | 7480103 | Kỹ thuật phần mềm | 15 | 19.5 |
| --- | --- | --- | --- | --- |

<!-- Trang 12 -->
33 | 7480201 | Công nghệ thông tin | 16.5 | 21.5 |
| 34 | 7520401 | Vật lý kỹ thuật | 0 | 18.25 |
"""
    artifact = build_source_artifact(md, 12, {})
    target = [fact for fact in artifact["facts"] if fact["raw_data"].get("entity_code") == "7480201"]
    assert {fact["raw_data"]["temporal_context"]["year"] for fact in target} == {2024, 2025}
    assert {fact["raw_data"]["page_number"] for fact in target} == {12}
    assert not any(fact["raw_data"].get("entity_code") == "7480201" for fact in build_source_artifact(md.replace("33 |", "40 |"), 12, {})["facts"])


def test_named_identity_next_to_code_is_not_a_repeated_group_label():
    md = "| Nhóm | Tên ngành | Mã ngành |\n| --- | --- | --- |\n| Toán | Toán ứng dụng | 7460112 |\n| Toán | Sư phạm Toán học | 7140209 |"
    artifact = build_source_artifact(md, 1, {})
    assert artifact["issues"] == []
    assert {fact["entity_name"] for fact in artifact["facts"]} == {"Toán ứng dụng", "Sư phạm Toán học"}


@pytest.mark.asyncio
async def test_dag_no_answer_and_output_cannot_upgrade_missing_decision():
    from app.modules.workflows.nodes.base import WorkflowContext
    from app.modules.workflows.nodes.no_answer_node import OutputNoAnswerNodeHandler
    from app.modules.workflows.nodes.output_chat_node import OutputChatNodeHandler
    from app.modules.workflows.schemas import WorkflowNodeSpec

    decision = {"status": "missing", "answer": "Chưa đủ căn cứ cho năm được hỏi."}
    context = WorkflowContext(workflow_id="fixture", tenant_id="fixture", conversation_id=None, inputs={},
                              node_data={"answer_decision": decision, "rag_status": "insufficient_context"})
    refusal = await OutputNoAnswerNodeHandler().execute(WorkflowNodeSpec(id="no", type="output.no_answer", config={"status": "answered"}), context)
    assert refusal.output["status"] == "insufficient_context"
    assert refusal.output["answer"] == decision["answer"]
    result = await OutputChatNodeHandler().execute(WorkflowNodeSpec(id="out", type="output.chat", config={"output_template": "21.5 điểm năm 2026"}), context)
    assert result.output["status"] == "insufficient_context"
    assert result.output["answer"] == decision["answer"]


@pytest.mark.asyncio
async def test_dag_rewrite_cannot_change_explicit_year():
    from unittest.mock import AsyncMock, patch

    from app.modules.workflows.nodes.base import WorkflowContext
    from app.modules.workflows.nodes.query_rewrite_node import (
        QueryRewriteNodeHandler,
        fast_rule_normalize,
    )
    from app.modules.workflows.schemas import WorkflowNodeSpec

    assert "ngày nào" in fast_rule_normalize("Đăng ký từ ngày nào năm 2026?")
    context = WorkflowContext(workflow_id="fixture", tenant_id="fixture", conversation_id=None,
                              db=AsyncMock(), inputs={"message": "Thời gian đăng ký năm 2026?"})
    handler = QueryRewriteNodeHandler()
    with patch.object(handler, "_rewrite_with_llm", AsyncMock(return_value="Thời gian đăng ký năm 2025?")) as rewrite:
        result = await handler.execute(WorkflowNodeSpec(id="rewrite", type="query.rewrite", config={"use_llm": True}), context)
    rewrite.assert_awaited_once()
    assert "2026" in result.output["normalized_query"]


@pytest.mark.asyncio
async def test_table_evidence_database_error_is_not_missing():
    from unittest.mock import AsyncMock

    from app.core.exceptions import AppException
    from app.modules.rag.schemas import RetrievalSnapshot
    from app.modules.rag.snapshot_fact_evidence import load_snapshot_table_evidence

    db = AsyncMock()
    db.execute.side_effect = ConnectionError("fixture DB unavailable")
    snapshot = RetrievalSnapshot(snapshot_id="fixture", collection_id="fixture", tenant_id="fixture", workspace_id="fixture", binding_revisions={"binding": "index"})
    with pytest.raises(AppException) as error:
        await load_snapshot_table_evidence(db, snapshot)
    assert error.value.code == "TABLE_EVIDENCE_UNAVAILABLE"
