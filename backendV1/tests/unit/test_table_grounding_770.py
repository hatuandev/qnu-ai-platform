"""Cell selection, geometric headers and provenance across unrelated table domains."""

import copy
import json

import pytest

from qnu.domains.knowledge.index.table_layout import layout, quality
from qnu.domains.rag.answer.cells import catalog, materialize
from qnu.domains.rag.answer.drafting import messages_for, parse_answer
from qnu.domains.rag.answer.schemas import EvidenceSource
from qnu.platform.errors import AppException


def source(rows, *, headers=1, widths=None, key="E1", table="ocr:t", columns=None):
    cells = [
        [
            {
                "text": text,
                "row_span": 1,
                "col_span": 1,
                "header": i < headers,
                "evidence_id": f"{table}-{i}-{j}",
            }
            for j, text in enumerate(row)
        ]
        for i, row in enumerate(rows)
    ]
    for (i, j), (rs, cs) in (widths or {}).items():
        cells[i][j].update(row_span=rs, col_span=cs)
    refs = {
        table.split(":", 1)[0] + ":" + c["evidence_id"]: {"page": 1} for row in cells for c in row
    }
    return EvidenceSource(
        evidence_id=key,
        chunk_id=key,
        document_id="doc",
        version_id="v",
        publication_decision_id="published",
        kind="table",
        score=1,
        text="raw table",
        citations={table: {"page": 1}, **refs},
        structure={
            "source_table_citation": table,
            "original_row_count": len(rows),
            "original_column_count": columns or len(rows[-1]),
            "rows": cells,
            "row_indices": list(range(len(rows))),
        },
    )


def selected(cell_id):
    return json.dumps({"status": "answered", "statements": [], "lookups": [{"cell_id": cell_id}]})


@pytest.mark.parametrize(
    "rows,column,value",
    [
        ([["Item", "In stock", "On order"], ["Motor", "0", "-"]], 1, "0"),
        ([["Item", "In stock", "On order"], ["Motor", "0", "-"]], 2, "-"),
        ([["Dịch vụ", "Giá", "Đơn vị"], ["Hiệu chuẩn", "12,67", "nghìn đồng"]], 1, "12,67"),
        ([["Department", "2028", "2029"], ["Research", "20", "22"]], 2, "22"),
    ],
)
def test_backend_copies_selected_source_value_without_model_numbers(rows, column, value):
    s = source(rows)
    original = copy.deepcopy(s)
    cells = catalog([s])
    draft = parse_answer(selected(f"E1:r1:k{column}"), [s])
    answer = materialize(draft, [s], cells)
    assert answer.statements[0].text == f"{rows[1][0]} — {rows[0][column]}: {value}"
    assert answer.statements[0].evidence_ids == ["E1"]
    assert s == original


def test_multi_level_headers_follow_physical_span_not_cell_list_index():
    s = source(
        [["Item", "Revenue"], ["2028", "2029"], ["Pump", "100", "200"]],
        headers=2,
        widths={(0, 0): (2, 1), (0, 1): (1, 2)},
    )
    cells = catalog([s])
    assert cells["tables"][0]["fields"] == {
        "0": ["Item"],
        "1": ["Revenue", "2028"],
        "2": ["Revenue", "2029"],
    }
    assert len(cells["tables"][0]["cells"]) == 2
    answer = materialize(parse_answer(selected("E1:r2:k2"), [s]), [s], cells)
    assert answer.statements[0].text == "Pump — Revenue / 2029: 200"


def test_rowspan_carries_original_subject_and_citation_without_filling_source():
    s = source(
        [["Item", "Phase", "Cost"], ["Pump", "Build", "10"], ["Repair", "5"]],
        widths={(1, 0): (2, 1)},
        columns=3,
    )
    cells = catalog([s])
    target = next(c for c in cells["tables"][0]["cells"] if c["cell_id"] == "E1:r2:k2")
    assert target["column"] == 2 and target["subject"] == "Pump / Repair"
    assert "ocr:ocr:t-1-0" in target["source_cells"]


@pytest.mark.parametrize("change", ["unknown_header", "missing_proof", "span", "holes"])
def test_ambiguous_or_invalid_table_has_no_selectable_values(change):
    s = source([["Name", "Price"], ["Alpha", "18"]])
    if change == "unknown_header":
        for c in s.structure["rows"][0]:
            c["header"] = False
    elif change == "missing_proof":
        s.citations.clear()
    elif change == "span":
        s.structure["rows"][1][0]["col_span"] = 3
    else:
        s.structure["rows"][1].pop()
    assert not [c for t in catalog([s])["tables"] for c in t["cells"]]
    with pytest.raises(AppException, match="Ô được chọn") as exc:
        materialize(parse_answer(selected("E1:r1:k1"), [s]), [s], catalog([s]))
    assert exc.value.code == "answer_cell_invalid"


def test_numeric_prose_cannot_bypass_table_cell_selection():
    s = source([["Name", "Price"], ["Alpha", "18"]])
    draft = parse_answer(
        json.dumps(
            {
                "status": "answered",
                "statements": [{"text": "Alpha costs 25.", "evidence_ids": ["E1"]}],
            }
        ),
        [s],
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_cell_selection_required"


def test_forged_or_duplicate_selection_is_rejected():
    s = source([["Name", "Price"], ["Alpha", "18"]])
    with pytest.raises(AppException):
        materialize(parse_answer(selected("E999:r1:k1"), [s]), [s], catalog([s]))
    value = json.loads(selected("E1:r1:k1"))
    value["lookups"] *= 2
    with pytest.raises(AppException):
        materialize(parse_answer(json.dumps(value), [s]), [s], catalog([s]))


def test_borrowed_header_and_carried_subject_require_same_published_identity():
    head = source(
        [["Index", "Name", "Condition"], ["1", "Alpha", "-"], ["2", "Beta", "first part"]],
        headers=0,
        key="E2",
        table="ocr:head",
    )
    body = source(
        [["", "", "note >= 7"], ["3", "Gamma", "8"], ["4", "Delta", "9"]],
        headers=0,
        table="ocr:next",
    )
    link = {
        "chunk_id": "E1",
        "header": "ocr:head",
        "previous": "ocr:head",
        "support_ids": ["E2"],
        "basis": "native_numbered_table_boundary/v1",
    }
    cells = catalog([body, head], [link])
    answer = materialize(parse_answer(selected("E1:r0:k2"), [body, head]), [body, head], cells)
    assert answer.statements[0].text == "Beta — Condition: note >= 7"
    assert set(answer.statements[0].evidence_ids) == {"E1", "E2"}
    assert any(
        cell["subject"] == "Beta" and cell["value"] == "first part"
        for table in cells["tables"]
        if table["evidence_id"] == "E2"
        for cell in table["cells"]
    )
    head.version_id = "different-version"
    assert catalog([body, head], [link])["tables"][0]["evidence_id"] != "E1"


def test_source_instructions_do_not_bypass_plain_text_output_guard():
    s = source([["Name", "Price"], ["Alpha", "<script>alert(1)</script>"]])
    with pytest.raises(AppException) as exc:
        materialize(parse_answer(selected("E1:r1:k1"), [s]), [s], catalog([s]))
    assert exc.value.code == "answer_source_text_invalid"


def test_layout_quality_and_compact_prompt_keep_server_catalog():
    s = source([["Name", "Price"], ["Alpha", "18"]])
    assert quality(s.structure)["status"] == "structured"
    assert len(layout(s.structure)[0]) == 4
    payload = json.loads(messages_for("Price?", [s])[-1].content)
    assert "structure" not in payload["evidence"][0]
    table = payload["tables"][0]
    assert table["id"] == "E1"
    assert table["columns"] == {"k0": "Name", "k1": "Price"}
    assert table["rows"] == [{"subject": "Alpha", "cells": {"E1:r1:k1": "18"}}]
    server = catalog([s])["tables"][0]["cells"][0]
    assert server["cell_id"] == "E1:r1:k1" and server["source_cells"]


@pytest.mark.asyncio
async def test_catalog_envelope_budget_is_checked_before_provider_dispatch(monkeypatch):
    from unittest.mock import AsyncMock

    from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
    from qnu.domains.rag.answer import service
    from qnu.domains.rag.answer.schemas import AnswerRequest

    rows = [["Name", "Price"]] + [[f"Item {i}", str(100 + i)] for i in range(20)]
    s = source(rows)
    result = SearchResponse(
        index_run_id="idx",
        generation=1,
        status="results",
        hits=[SearchHit.model_validate(s.model_dump(exclude={"evidence_id"}))],
        eligible_documents=1,
    )
    monkeypatch.setattr(service, "search", AsyncMock(return_value=result))
    monkeypatch.setattr(service, "expand_context", AsyncMock(return_value=(result, {})))
    prepare = AsyncMock()
    monkeypatch.setattr(service, "prepare_chat_request", prepare)
    with pytest.raises(AppException) as exc:
        await service.answer(
            None,
            None,
            None,
            None,
            None,
            None,
            "ws",
            "col",
            AnswerRequest(question="Price?", context_max_bytes=256),
        )
    assert exc.value.code == "answer_context_budget_exceeded"
    prepare.assert_not_called()


def test_ingestion_quality_and_dependencies_are_derived_not_source_rewrites():
    from qnu.domains.knowledge.index.chunking import CHUNKER_VERSION, build_chunks
    from tests.unit.test_index_chunking_647 import fixture

    content, documents = fixture()
    original = copy.deepcopy((content, documents))
    chunks = build_chunks(content, documents, 1800)
    assert CHUNKER_VERSION == "qnu.published-chunks/v6"
    assert all(
        c.structure["reading_quality"]["status"] == "structured"
        for c in chunks
        if c.kind == "table"
    )
    assert (content, documents) == original


def test_unparsed_table_does_not_allow_fabricated_numeric_prose():
    s = source([["Name", "Price"], ["Alpha", "18"]])
    s.structure = {"table_status": "unparsed"}
    value = {"status": "answered", "statements": [{"text": "Alpha: 999", "evidence_ids": ["E1"]}]}
    with pytest.raises(AppException) as exc:
        materialize(parse_answer(json.dumps(value), [s]), [s], catalog([s]))
    assert exc.value.code == "answer_cell_selection_required"


def test_rowspan_values_and_new_cells_never_share_a_lookup_id():
    s = source(
        [["Group", "Item", "Amount", "Rate"], ["West", "Pump", "10", "3"], ["Valve", "4"]],
        widths={(1, 0): (2, 1), (1, 2): (2, 1)},
        columns=4,
    )
    cells = catalog([s])["tables"][0]["cells"]
    ids = [c["cell_id"] for c in cells]
    assert len(ids) == len(set(ids))
    assert next(c for c in cells if c["cell_id"] == "E1:r2:k2")["value"] == "10"
    assert next(c for c in cells if c["cell_id"] == "E1:r2:k3")["value"] == "4"
