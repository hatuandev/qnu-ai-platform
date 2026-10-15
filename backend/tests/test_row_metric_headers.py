"""Metric proof must retain source headers, even with a generic table introduction."""

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.rag.row_answer import _metric_payload, answer_from_rows
from app.modules.rag.row_answer_contract import MetricScope, RowAudit, RowSelection, build_catalog
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.source_rows import source_rows
from tests.test_rag_rows_stage3 import fixture_source

QUESTION = "Điểm chuẩn ngành Ngành Alpha và Ngành Beta các năm gần nhất là bao nhiêu?"
MARKDOWN = """<!-- Trang 1 -->

11. Thông tin về tuyển sinh của 2 năm gần nhất

| STT | Mã ngành | Tên ngành | 2024 - Điểm trúng tuyển | 2025 - Điểm trúng tuyển | 2025 - Chỉ tiêu |
| --- | --- | --- | --- | --- | --- |
| 1 | 7123456 | Ngành Alpha | 23.75 | 24.25 | 80 |
| 2 | 7654321 | Ngành Beta | 17.25 | 18.75 | 120 |
"""


def history_context(markdown=MARKDOWN):
    rows = source_rows(*fixture_source(markdown), QUESTION)
    snapshot = RetrievalSnapshot(snapshot_id="history", collection_id="cc", tenant_id="tt",
                                 workspace_id="ww", binding_revisions={"binding_a": "index_a"})
    req = AskRequest(question=QUESTION, collection_id="cc", tenant_id="tt", workspace_id="ww",
                     module_code="admissions", preferred_model_name="configured/model")
    return rows, req, snapshot, build_catalog(rows, snapshot)


@pytest.mark.asyncio
async def test_generic_intro_retains_header_metric_and_years_without_cell_values():
    rows, req, _, catalog = history_context()
    assert len(rows) == 2
    header_ids = [key for key, block in catalog.contexts.items() if block.text.startswith("|")]
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(
            return_value=MetricScope(context_ids=header_ids))) as model:
        payload = await _metric_payload(AsyncMock(), req, catalog)
    introductions = {item["id"]: item["text"] for item in model.call_args.args[4]["introductions"]}
    assert set(header_ids).issubset(introductions)
    assert all("2025 - Điểm trúng tuyển" in introductions[key] for key in header_ids)
    assert not any("23.75" in text or "18.75" in text for text in introductions.values())
    assert payload is not None and len(payload["tables"]) == 2
    assert all(row["source_revision_id"] == "source_a" for row in payload["tables"])


@pytest.mark.asyncio
async def test_shared_header_keeps_both_rows_but_not_identical_text_from_another_source():
    rows, req, snapshot, _ = history_context()
    other = source_rows(*fixture_source(MARKDOWN, suffix="b"), QUESTION)
    snapshot.binding_revisions["binding_b"] = "index_b"
    catalog = build_catalog(rows + other, snapshot)
    first_header = next(key for key, block in catalog.contexts.items() if block.text.startswith("|"))
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(
            return_value=MetricScope(context_ids=[first_header]))):
        payload = await _metric_payload(AsyncMock(), req, catalog)
    assert payload is not None and len(payload["tables"]) == 2
    assert {row["entity"] for row in payload["tables"]} == {"Ngành Alpha", "Ngành Beta"}
    assert {row["source_revision_id"] for row in payload["tables"]} == {"source_a"}


@pytest.mark.asyncio
async def test_two_entities_and_historical_columns_render_exact_coordinates():
    rows, req, snapshot, catalog = history_context()
    headers = [key for key, block in catalog.contexts.items() if block.text.startswith("|")]
    cells = [key for key, cell in catalog.cells.items() if "Điểm trúng tuyển" in cell.header]
    selection = RowSelection(status="selected", cell_ids=cells, scope_ids=headers)
    audit = RowAudit(compatible=True, scope_supported=True, complete=True,
                     required_cell_ids=cells, required_context_ids=headers)
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(
            side_effect=[MetricScope(context_ids=headers), selection, audit])):
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert response.status == "answered"
    assert {cell["entity"] for cell in response.answer_decision["cells"]} == {"Ngành Alpha", "Ngành Beta"}
    assert [cell["value"] for cell in response.answer_decision["cells"]] == ["23.75", "24.25", "17.25", "18.75"]
    assert "Chỉ tiêu |" not in response.answer
    assert "2024 - Điểm trúng tuyển" in response.answer and "2025 - Điểm trúng tuyển" in response.answer
    assert all(cite.source_revision_id == "source_a" and cite.canonical_hash for cite in response.citations)


@pytest.mark.asyncio
@pytest.mark.parametrize("metric_ids", [[], ["not-a-source-context"]])
async def test_headers_do_not_authorize_a_missing_metric_or_unknown_context(metric_ids):
    rows, req, snapshot, _ = history_context()
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(
            return_value=MetricScope(context_ids=metric_ids))) as model:
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert response.status == "insufficient_context" and response.citations == []
    assert response.answer_decision["reason"] == "ROW_METRIC_SCOPE_UNRESOLVED"
    assert model.await_count == 1


@pytest.mark.asyncio
async def test_one_entity_missing_still_rejects_instead_of_claiming_complete_answer():
    rows, req, snapshot, catalog = history_context(MARKDOWN.rsplit("| 2 |", 1)[0])
    headers = [key for key, block in catalog.contexts.items() if block.text.startswith("|")]
    cells = [key for key, cell in catalog.cells.items() if "Điểm trúng tuyển" in cell.header]
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(side_effect=[
            MetricScope(context_ids=headers),
            RowSelection(status="selected", cell_ids=cells, scope_ids=headers),
            RowAudit(compatible=True, scope_supported=True, complete=False, required_cell_ids=cells,
                     missing_constraints=["Thiếu điểm trúng tuyển Ngành Beta."])])):
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows)
    assert response.status == "insufficient_context" and response.citations == []
    assert "Ngành Beta" in response.answer


@pytest.mark.asyncio
@pytest.mark.parametrize("foreign", [False, True])
async def test_audit_can_complete_context_only_for_selected_source_rows(foreign):
    rows, req, snapshot, catalog = history_context()
    other = source_rows(*fixture_source(MARKDOWN, suffix="b"), QUESTION)
    snapshot.binding_revisions["binding_b"] = "index_b"
    catalog = build_catalog(rows + other, snapshot)
    headers = [key for key, block in catalog.contexts.items()
               if block.binding_id == "binding_a" and block.text.startswith("|")]
    cells = [key for key, cell in catalog.cells.items()
             if cell.row_id in {"r0", "r1"} and "Điểm trúng tuyển" in cell.header]
    extra = [key for key, block in catalog.contexts.items()
             if block.binding_id == ("binding_b" if foreign else "binding_a") and "11." in block.text]
    with patch("app.modules.rag.row_answer.structured_call", AsyncMock(side_effect=[
            MetricScope(context_ids=headers),
            RowSelection(status="selected", cell_ids=cells, scope_ids=headers),
            RowAudit(compatible=True, scope_supported=True, complete=True,
                     required_cell_ids=cells, required_context_ids=headers + extra)])):
        response = await answer_from_rows(AsyncMock(), req, snapshot, rows + other)
    assert response.status == ("insufficient_context" if foreign else "answered")
    if not foreign:
        assert "11. Thông tin" in response.answer
        assert all(cite.source_revision_id == "source_a" for cite in response.citations)
