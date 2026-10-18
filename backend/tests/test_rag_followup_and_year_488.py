"""Real service routing with controlled I/O, not a new vocabulary for test questions."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.rag.schemas import AskRequest, AskResponse, RetrievalSnapshot
from app.modules.rag.service import RagService
from app.modules.rag.temporal_answer import decide_table_answer

QUESTION = "Ngành Sư phạm Toán học năm 2026 xét tuyển những tổ hợp môn nào?"


def unknown_fact():
    return {"id": "unknown-cell", "entity_name": "Sư phạm Toán học", "attribute_name": "Tổ hợp môn xét tuyển",
            "attribute_value": "(Toán, Lý, Hóa)", "binding_id": "binding", "index_revision_id": "index",
            "raw_data": {"attribute_code": "subject_combinations", "entity_code": "7140209",
                         "temporal_context": {"type": "unknown"}}}


def test_unknown_year_is_not_absent_data_and_never_promoted():
    result = decide_table_answer(QUESTION, [unknown_fact()])
    assert result["status"] == "missing" and result["reason"] == "DATA_YEAR_UNVERIFIED"
    assert result["unscoped_fact_ids"] == ["unknown-cell"]
    assert result["claim_bindings"] == []
    assert "chưa xác minh" in result["answer"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["explain", "reformat"])
async def test_non_enumeration_reformats_against_current_evidence_not_history(mode):
    previous = "Những phương thức tuyển sinh năm 2026 là gì?"
    req = AskRequest(question="Giải thích gọn hơn nhé", collection_id="collection", assistant_code="admissions")
    resolution = {"mode": mode, "antecedent_question": previous, "current_question": req.question}
    with (patch("app.modules.rag.conversation_resolution.resolve_followup", AsyncMock(return_value=(req, resolution))),
          patch("app.modules.rag.conversation_acts.answer_dialogue_act", AsyncMock(return_value=None)),
          patch.object(RagService, "_ask", AsyncMock(return_value=AskResponse(status="answered", answer="Verified"))) as call):
        result = await RagService().ask(AsyncMock(), req)
    rebuilt = call.await_args.args[1]
    assert rebuilt.question == previous and rebuilt.original_question == previous
    assert "TRÌNH BÀY" in rebuilt.system_prompt
    assert result.answer_decision["presentation_revalidated"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("supported", [True, False])
async def test_unknown_fact_uses_linked_rows_without_changing_stored_year(supported):
    fact = unknown_fact()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={})
    snap = RetrievalSnapshot(snapshot_id="snapshot", collection_id="collection", binding_revisions={"binding": "index"})
    response = AskResponse(status="answered" if supported else "insufficient_context", answer="Source-bound row answer")
    with (patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snap)),
          patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[fact])),
          patch("app.modules.rag.snapshot_fact_evidence.load_snapshot_table_evidence", AsyncMock(return_value=[])),
          patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.load_row_anchors", AsyncMock(return_value=[object()])),
          patch("app.modules.rag.service.answer_from_rows", AsyncMock(return_value=response)) as reader,
          patch("app.modules.rag.service.modelops_service.generate", AsyncMock()) as generate):
        result = await RagService().ask(db, AskRequest(question=QUESTION, collection_id="collection"))
    reader.assert_awaited_once()
    generate.assert_not_awaited()
    assert result.status == ("answered" if supported else "insufficient_context")
    if not supported:
        assert result.answer_decision["reason"] == "DATA_YEAR_UNVERIFIED"
        assert "Chào bạn" not in result.answer and "Hotline" not in result.answer
    assert fact["raw_data"]["temporal_context"]["type"] == "unknown"


@pytest.mark.asyncio
async def test_revalidation_outage_is_not_clarification():
    req = AskRequest(question="Giải thích gọn hơn nhé", collection_id="collection")
    with (patch("app.modules.rag.conversation_resolution.resolve_followup", AsyncMock(return_value=(req,
                {"mode": "reformat", "antecedent_question": "Phương thức năm 2026?"}))),
          patch("app.modules.rag.conversation_acts.answer_dialogue_act", AsyncMock(return_value=None)),
          patch.object(RagService, "_ask", AsyncMock(side_effect=AppException("Unavailable", code="DOWN", status_code=503))),
          pytest.raises(AppException) as error):
        await RagService().ask(AsyncMock(), req)
    assert error.value.status_code == 503


def test_row_scope_pruning_never_promotes_an_older_year_or_unknown_id():
    from app.modules.rag.row_answer_contract import (
        RowSelection,
        build_catalog,
        retain_scoped_cells,
        validate_selection,
    )
    from app.modules.rag.source_rows import source_rows
    from tests.test_rag_rows_stage3 import fixture_source

    question = "Điểm sàn ngành Quản lý giáo dục năm 2026?"
    current = source_rows(*fixture_source(suffix="a"), question)
    markdown = fixture_source()[0].canonical_markdown.replace("2026", "2025")
    old = source_rows(*fixture_source(markdown, "b"), question)
    snap = RetrievalSnapshot(snapshot_id="s", collection_id="c", binding_revisions={"binding_a": "index_a", "binding_b": "index_b"})
    catalog = build_catalog([*current, *old], snap)
    selection = RowSelection(status="selected", cell_ids=list(catalog.cells), scope_ids=list(catalog.contexts))
    kept = retain_scoped_cells(selection, catalog, question)
    assert kept.cell_ids and len(kept.cell_ids) < len(selection.cell_ids)
    assert all(catalog.cells[key].references[0]["binding_id"] == "binding_a" for key in kept.cell_ids)
    validate_selection(kept, catalog, question)
    forged = selection.model_copy(update={"cell_ids": ["fake"]})
    with pytest.raises(ValueError):
        validate_selection(retain_scoped_cells(forged, catalog, question), catalog, question)


def test_source_value_variants_preserve_accents_but_ignore_tuple_order():
    from app.modules.rag.row_answer_contract import (
        RowCatalog,
        RowSelection,
        SourceCell,
        source_value_variants,
    )

    catalog = RowCatalog(rows={"a": {"entity_code": "123"}, "b": {"entity_code": "123"}}, cells={
        "a": SourceCell("a", "Programme", "Tổ hợp môn xét tuyển", "(Alpha, Beta, Gamma)", []),
        "b": SourceCell("b", "Programme", "TỔ HỢP MÔN XÉT TUYỂN", "(Gamma, Alpha, Beta)", []),
    })
    selection = RowSelection(status="selected", cell_ids=["a", "b"])
    assert not source_value_variants(selection, catalog, "Programme năm 2026")
    catalog.cells["b"].value = "(Gamma, Alphá, Beta)"
    assert source_value_variants(selection, catalog, "Programme năm 2026")
    assert not source_value_variants(selection, catalog, "Programme năm 2025 và 2026")
    catalog.rows["b"]["entity_code"] = "456"
    assert not source_value_variants(selection, catalog, "Programme năm 2026")
    catalog.rows["b"]["entity_code"] = ""
    assert source_value_variants(selection, catalog, "Programme năm 2026")
    catalog.cells["b"].header = "TỔ HỢP MÔN XÉT TUYỀN"
    assert source_value_variants(selection, catalog, "Programme năm 2026")
    catalog.cells["a"].header += " (PT1)"
    catalog.cells["b"].header += " (PT2)"
    assert not source_value_variants(selection, catalog, "Programme năm 2026")
