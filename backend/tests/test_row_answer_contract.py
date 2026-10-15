"""Row/cell answering: exact coordinates, same-source scope, no model-authored values."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.rag.row_answer_contract import MetricScope
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from tests.test_rag_rows_stage3 import fixture_source


def context(name="Quản lý giáo dục", suffix="a"):
    from app.modules.rag.source_rows import source_rows

    markdown = fixture_source()[0].canonical_markdown + "\n\n1. Điều kiện chung giữ nguyên.\n\nKý hiệu –: không xét tuyển."
    rows = source_rows(*fixture_source(markdown, suffix), f"Điểm sàn ngành {name} năm 2026?")
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="c", tenant_id="tt", workspace_id="ww",
                                 binding_revisions={"binding_" + suffix: "index_" + suffix})
    req = AskRequest(question=f"Điểm sàn ngành {name} năm 2026 là bao nhiêu?", collection_id="c", tenant_id="tt", workspace_id="ww",
                     preferred_provider_id="configured", preferred_model_name="arbitrary/model", module_code="admissions",
                     runtime_policy={"persona_scope": {"persona": "Configured institution", "allowed_topics": ["Topic"]}})
    return rows, req, snapshot


def test_catalog_coordinates_include_all_methods_and_original_headers():
    from app.modules.rag.row_answer_contract import build_catalog

    rows, _, snapshot = context()
    catalog = build_catalog(rows, snapshot)
    numeric = [cell for cell in catalog.cells.values() if cell.value in {"15", "18", "600"}]
    assert [cell.value for cell in numeric] == ["15", "18", "600", "15"]
    assert all(cell.header and cell.references for cell in numeric)
    assert all(ref["quote"] for cell in numeric for ref in cell.references)


def test_wrong_pinned_index_is_not_silently_accepted():
    from app.modules.rag.row_answer_contract import build_catalog

    rows, _, snapshot = context()
    snapshot.binding_revisions = {"binding_a": "other_revision"}
    with pytest.raises(AppException) as error:
        build_catalog(rows, snapshot)
    assert error.value.code == "ROW_ANSWER_SOURCE_INVALID"


@pytest.mark.asyncio
async def test_selected_cells_render_source_values_not_any_draft_prose():
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import RowAudit, RowSelection, build_catalog

    rows, req, snapshot = context()
    catalog = build_catalog(rows, snapshot)
    ids = [key for key, cell in catalog.cells.items() if cell.value in {"15", "18", "600"}]
    scope = [key for key, block in catalog.contexts.items() if "năm 2026" in block.text]
    notes = [key for key, block in catalog.contexts.items() if "Điều kiện chung" in block.text]
    selection = RowSelection(status="selected", cell_ids=ids, scope_ids=scope, note_ids=notes)
    audit = RowAudit(compatible=True, complete=True, required_cell_ids=ids, required_context_ids=scope + notes,
                    scope_supported=True)
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(side_effect=[MetricScope(context_ids=scope), selection, audit])) as model:
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert response.status == "answered"
    assert all(value in response.answer for value in ["15", "18", "600", "Điều kiện chung"])
    assert len(response.answer_decision["cells"]) == 4
    assert response.citations and all(cite.canonical_hash and cite.span_start is not None for cite in response.citations)
    assert model.await_count == 3
    assert all(call.args[1].preferred_model_name == req.preferred_model_name for call in model.call_args_list)
    assert all(call.args[4]["assistant_scope"]["persona"] == "Configured institution" for call in model.call_args_list)


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", ["foreign_context", "invented_cell", "missing_cell", "scope_rejected", "conflict"])
async def test_invalid_or_incomplete_selection_never_reaches_free_generation(problem):
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import RowAudit, RowSelection, build_catalog

    rows, req, snapshot = context()
    other, _, _ = context(suffix="b")
    snapshot.binding_revisions["binding_b"] = "index_b"
    catalog = build_catalog(rows + other, snapshot)
    ids = [key for key, cell in catalog.cells.items() if cell.row_id == "r0" and cell.value in {"15", "18", "600"}]
    scope = [key for key, block in catalog.contexts.items() if block.binding_id == "binding_a" and "năm 2026" in block.text]
    selection = RowSelection(status="selected", cell_ids=ids, scope_ids=scope)
    audit = RowAudit(compatible=True, complete=True, required_cell_ids=ids, required_context_ids=scope, scope_supported=True)
    if problem == "foreign_context":
        selection.scope_ids = [key for key, block in catalog.contexts.items() if block.binding_id == "binding_b"]
    elif problem == "invented_cell":
        selection.cell_ids = ["invented"]
    elif problem == "missing_cell":
        selection.cell_ids = ids[:1]
    elif problem == "scope_rejected":
        audit.scope_supported = False
    else:
        audit.conflict = True
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(side_effect=[MetricScope(context_ids=scope), selection, audit])):
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows + other)
    assert response.status == "insufficient_context"
    assert response.answer_decision["status"] != "supported"
    assert response.citations == []  # Do not publish an unverified subset as an answer.


@pytest.mark.asyncio
async def test_provider_failure_is_not_a_fabricated_table_or_plain_answer():
    from app.modules.rag.row_answer import answer_from_rows

    rows, req, snapshot = context()
    outage = AppException("upstream unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)
    with (patch("app.modules.rag.row_answer.structured_call", AsyncMock(side_effect=outage)),
          pytest.raises(AppException) as error):
        await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert error.value is outage


@pytest.mark.asyncio
async def test_explicit_historical_column_cannot_become_requested_year():
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import RowAudit, RowSelection, build_catalog
    from app.modules.rag.source_rows import source_rows

    rows, req, snapshot = context()
    source, index, binding, chunks = fixture_source(fixture_source()[0].canonical_markdown.replace(
        "Phương thức xét điểm thi TN. THPT", "2024 - Phương thức xét điểm thi TN. THPT"))
    rows = source_rows(source, index, binding, chunks, req.question)
    catalog = build_catalog(rows, snapshot)
    ids = [key for key, cell in catalog.cells.items() if "2024" in cell.header]
    scope = [key for key, block in catalog.contexts.items() if "năm 2026" in block.text]
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(side_effect=[
        MetricScope(context_ids=scope),
        RowSelection(status="selected", cell_ids=ids, scope_ids=scope),
        RowAudit(compatible=True, complete=True, required_cell_ids=ids, scope_supported=True)])):
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert response.status == "insufficient_context" and not response.citations


@pytest.mark.asyncio
async def test_row_rejection_is_returned_without_free_generation_or_cache():
    from types import SimpleNamespace

    from app.modules.rag.schemas import AskResponse
    from app.modules.rag.service import RagService

    rows, req, snapshot = context()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={})
    rejected = AskResponse(status="insufficient_context", answer="Chưa đủ căn cứ.")
    with (patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot)),
          patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.hybrid_retriever.retrieve", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.load_row_anchors", AsyncMock(return_value=rows)),
          patch("app.modules.rag.service.answer_from_rows", AsyncMock(return_value=rejected)) as cell_answer,
          patch("app.modules.rag.service.modelops_service.generate", AsyncMock()) as generate,
          patch("app.modules.rag.service.semantic_cache.set", AsyncMock()) as cache):
        result = await RagService().ask(db, req)
    assert result is rejected and cell_answer.await_count == 1
    generate.assert_not_awaited()
    cache.assert_not_awaited()


def test_condition_branches_and_page_continuations_remain_source_bound():
    from app.modules.rag.row_answer_contract import (
        RowSelection,
        build_catalog,
        close_context,
        render_cells,
    )
    from app.modules.rag.source_rows import source_rows

    rows, _, snapshot = context()
    markdown = fixture_source()[0].canonical_markdown + (
        "\n\n1. Điều kiện bắt đầu chưa kết thúc\n\n<!-- Trang 3 -->\n"
        "và nối tiếp đầy đủ.\n\n2. Quy định áp dụng cho các đối tượng nêu dưới đây với đầy đủ điều kiện cụ thể "
        "trong từng nhánh, không áp dụng nhầm ngoại lệ giữa các đối tượng khác nhau:\n\n"
        "a) Điều kiện thứ nhất, trừ b.\n\nb) Ngoại lệ thứ hai."
    )
    rows = source_rows(*fixture_source(markdown), "Điểm sàn Quản lý giáo dục 2026?")
    catalog = build_catalog(rows, snapshot)
    cells = [key for key, cell in catalog.cells.items() if cell.value == "18"]
    notes = [key for key, block in catalog.contexts.items()
             if block.text.startswith("a)") or block.text.startswith("và nối")]
    closed = close_context(RowSelection(status="selected", cell_ids=cells, note_ids=notes), catalog)
    answer, _, refs = render_cells(closed, catalog)
    assert "1. Điều kiện bắt đầu" in answer and "và nối tiếp đầy đủ." in answer
    assert "2. Quy định áp dụng" in answer and "b) Ngoại lệ thứ hai." in answer
    assert {ref["source_revision_id"] for ref in refs} == {"source_a"}


@pytest.mark.asyncio
async def test_dash_cells_are_preserved_without_inventing_negative_policy():
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import RowAudit, RowSelection, build_catalog

    rows, req, snapshot = context("Sư phạm Toán học")
    catalog = build_catalog(rows, snapshot)
    ids = [key for key, cell in catalog.cells.items() if cell.value in {"20", "–"}]
    scope = [key for key, block in catalog.contexts.items() if "năm 2026" in block.text]
    notes = [key for key, block in catalog.contexts.items() if "Ký hiệu" in block.text]
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(side_effect=[
        MetricScope(context_ids=scope),
        RowSelection(status="selected", cell_ids=ids, scope_ids=scope, note_ids=notes),
        RowAudit(compatible=True, complete=True, scope_supported=True,
                 required_cell_ids=ids, required_context_ids=scope + notes)])):
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert response.status == "answered"
    assert [cell["value"] for cell in response.answer_decision["cells"]] == ["20", "–", "–", "20"]
    assert "Ký hiệu –: không xét tuyển." in response.answer


@pytest.mark.asyncio
async def test_numeric_not_applicable_does_not_bypass_audit_into_free_generation():
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import RowSelection

    rows, req, snapshot = context()
    from app.modules.rag.row_answer_contract import build_catalog

    catalog = build_catalog(rows, snapshot)
    scope = [key for key, block in catalog.contexts.items() if "năm 2026" in block.text]
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(side_effect=[
        MetricScope(context_ids=scope), RowSelection(status="not_applicable")])):
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert response is not None and response.status == "insufficient_context"


def test_empty_siblings_preserved_but_never_invent_nonempty_missing_values():
    from app.modules.rag.row_answer_contract import RowSelection, build_catalog, close_empty_cells

    rows, _, snapshot = context("Sư phạm Toán học")
    catalog = build_catalog(rows, snapshot)
    ends = [key for key, cell in catalog.cells.items() if cell.value == "20"]
    closed = close_empty_cells(RowSelection(status="selected", cell_ids=ends), catalog)
    assert [catalog.cells[key].value for key in closed.cell_ids] == ["20", "–", "–", "20"]
    rows, _, snapshot = context()
    catalog = build_catalog(rows, snapshot)
    ends = [key for key, cell in catalog.cells.items() if cell.value == "15"]
    closed = close_empty_cells(RowSelection(status="selected", cell_ids=ends), catalog)
    assert [catalog.cells[key].value for key in closed.cell_ids] == ["15", "15"]


def test_standalone_legend_does_not_inherit_nearest_unrelated_completed_rule():
    from app.modules.rag.row_answer_contract import (
        RowSelection,
        build_catalog,
        close_context,
        render_cells,
    )
    from app.modules.rag.source_rows import source_rows

    _, _, snapshot = context()
    markdown = fixture_source()[0].canonical_markdown + (
        "\n\n1. Quy định cho bảng.\n\n2. Quy định cho nhóm khác đã kết thúc.\n\nKý hiệu –: không xét tuyển."
    )
    rows = source_rows(*fixture_source(markdown), "Quản lý giáo dục 2026?")
    catalog = build_catalog(rows, snapshot)
    ids = [key for key, cell in catalog.cells.items() if cell.value == "18"]
    notes = [key for key, block in catalog.contexts.items() if "Ký hiệu" in block.text]
    answer, _, _ = render_cells(close_context(RowSelection(status="selected", cell_ids=ids, note_ids=notes), catalog), catalog)
    assert "Ký hiệu –" in answer and "Quy định cho nhóm khác" not in answer


@pytest.mark.asyncio
async def test_auditor_cannot_add_unknown_cells_or_see_first_selection():
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import RowAudit, RowSelection, build_catalog

    rows, req, snapshot = context()
    catalog = build_catalog(rows, snapshot)
    ids = [key for key, cell in catalog.cells.items() if cell.value in {"15", "18", "600"}]
    scope = [key for key, block in catalog.contexts.items() if "năm 2026" in block.text]
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(side_effect=[
        MetricScope(context_ids=scope),
        RowSelection(status="selected", cell_ids=ids, scope_ids=scope),
        RowAudit(compatible=True, complete=True, scope_supported=True,
                 required_cell_ids=ids + ["invented"], required_context_ids=scope)])) as model:
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert response.status == "insufficient_context" and response.citations == []
    audit_payload = model.call_args_list[2].args[4]
    assert "selection" not in audit_payload
    assert all("value" in cell for table in audit_payload["tables"] for cell in table["cells"])


@pytest.mark.asyncio
async def test_request_scope_must_match_pinned_snapshot_before_model_call():
    from app.modules.rag.row_answer import answer_from_rows

    rows, req, snapshot = context()
    req.tenant_id = "other-tenant"
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock()) as model, pytest.raises(AppException) as error:
        await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert error.value.code == "ROW_ANSWER_SCOPE_MISMATCH"
    model.assert_not_awaited()
