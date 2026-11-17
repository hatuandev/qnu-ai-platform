"""Cell selection, geometric headers and provenance across unrelated table domains."""

import copy
import json
from types import SimpleNamespace

import pytest

from qnu.domains.knowledge.index.table_layout import layout, quality
from qnu.domains.rag.answer.cells import catalog, materialize
from qnu.domains.rag.answer.drafting import messages_for, parse_answer
from qnu.domains.rag.answer.packing import pack_messages
from qnu.domains.rag.answer.schemas import EvidenceSource
from qnu.domains.rag.answer.table_selection import select_catalog
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


def test_wrapped_alphanumeric_identifier_keeps_the_following_name_as_subject():
    s = source(
        [["No.", "Reference", "Name", "Capacity"], ["1", "120045\nAB", "West laboratory", "30"]]
    )
    cells = catalog([s])
    result = materialize(parse_answer(selected("E1:r1:k3"), [s]), [s], cells)
    assert result.statements[0].text == "West laboratory — Capacity: 30"
    assert any(
        cell["cell_id"] == "E1:r1:k1" and cell["value"] == "120045\nAB"
        for cell in cells["tables"][0]["cells"]
    )


def test_row_group_with_its_own_code_column_keeps_the_child_name():
    s = source(
        [
            ["Nhóm", "Mã CT", "Chương trình", "Chỉ tiêu"],
            ["Kỹ thuật", "0201", "Cơ điện tử", "30"],
            ["0202", "Tự động hóa", "42"],
        ],
        widths={(1, 0): (2, 1)},
        columns=4,
    )
    cells = catalog([s])
    result = materialize(parse_answer(selected("E1:r2:k3"), [s]), [s], cells)
    assert result.statements[0].text == "Kỹ thuật / Tự động hóa — Chỉ tiêu: 42"


def test_enumeration_can_choose_a_row_name_without_copying_an_unrequested_number():
    s = source([["Name", "Capacity"], ["West laboratory", "30"]])
    cells = catalog([s], include_names=True)
    payload = json.loads(messages_for("Which places?", [s], table_cells=cells)[-1].content)
    row = payload["tables"][0]["rows"][0]
    assert row["name_id"] == "E1:r1:k0"
    draft = parse_answer(selected(row["name_id"]), [s])
    result = materialize(draft, [s], cells)
    assert result.statements[0].text == "West laboratory"
    assert result.statements[0].evidence_ids == ["E1"]


def test_wrapped_list_cell_renders_both_proven_fragments_once():
    left = source([["Name", "Options"], ["West", "(A, B)"]], table="ocr:left")
    right = source([["", "(C, D)"]], headers=0, key="E2", table="ocr:right")
    sources = [left, right]
    cells = catalog(
        sources,
        [
            {
                "chunk_id": "E2",
                "support_ids": ["E1"],
                "header": "ocr:left",
                "previous": "ocr:left",
            }
        ],
    )
    question = "What options are available?"
    scoped = select_catalog(cells, sources, question, [], data_years={2031})
    scoped_answer = materialize(parse_answer(selected("E2:r0:k1"), sources), sources, scoped)
    assert [item.text for item in scoped_answer.statements] == ["West — Options: (C, D)"]
    cells = select_catalog(cells, sources, question, [])
    draft = parse_answer(selected("E2:r0:k1"), sources)
    draft.lookups.extend(parse_answer(selected("E1:r1:k1"), sources).lookups)
    result = materialize(draft, sources, cells)
    assert [item.text for item in result.statements] == ["West — Options: (A, B)\n(C, D)"]
    assert set(result.statements[0].evidence_ids) == {"E1", "E2"}


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
    with pytest.raises(AppException) as exc:
        materialize(parse_answer(selected("E999:r1:k1"), [s]), [s], catalog([s]))
    assert exc.value.code == "answer_cell_invalid"
    assert exc.value.title == "Ô bảng mô hình chọn không hợp lệ"
    assert exc.value.validation_issues == [
        {"path": ["lookups", 0, "cell_id"], "type": "not_in_catalog"}
    ]
    value = json.loads(selected("E1:r1:k1"))
    value["lookups"] *= 2
    report = {}
    draft = materialize(parse_answer(json.dumps(value), [s]), [s], catalog([s]), report=report)
    assert len(draft.statements) == 1
    assert report["rejected_lookups"] == [{"path": ["lookups", 1, "cell_id"], "type": "duplicate"}]


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
    assert table["rows"] == [{"row": "r1", "subject": "Alpha", "cells": {"E1:r1:k1": "18"}}]
    server = catalog([s])["tables"][0]["cells"][0]
    assert server["cell_id"] == "E1:r1:k1" and server["source_cells"]


def test_compact_prompt_rows_still_materialize_from_full_server_cell_ids():
    rows = [["Name", "Price"]] + [[f"Item {i}", str(100 + i)] for i in range(12)]
    sources = [source(rows, key=f"E{i}", table=f"ocr:t{i}") for i in range(1, 6)]
    cells = catalog(sources)
    payload = json.loads(messages_for("Price?", sources)[-1].content)
    assert [table["rows"][0] for table in payload["tables"]] == [
        {"row": "r1", "subject": "Item 0", "cells": {f"E{i}:r1:k1": "100"}}
        for i in range(1, 6)
    ]
    assert all(
        key.endswith(":k1")
        for table in payload["tables"]
        for row in table["rows"]
        for key in row["cells"]
    )
    answer = materialize(
        parse_answer(selected("E3:r1:k1"), sources),
        sources,
        cells,
    )
    assert answer.statements[0].text == "Item 0 — Price: 100"
    assert answer.statements[0].evidence_ids == ["E3"]


def test_large_table_family_preserves_sources_and_respects_envelope_budget():
    rows = [["H1", "H2", "H3", "H4", "H5", "H6"]] + [
        [f"Program {i}", "10", "20", "30", "40", "50"] for i in range(12)
    ]
    sources = [source(rows, key=f"ich_{i:012x}", table=f"ocr:ev{i:04d}") for i in range(5)]
    req = SimpleNamespace(
        question="Ngưỡng 15.00 áp dụng cho những trường hợp nào?", context_max_bytes=16000
    )
    messages, cells, _evidence, size, skipped = pack_messages(req, sources, {})
    assert skipped == []
    assert size <= req.context_max_bytes
    assert {table["evidence_id"] for table in cells["tables"]} == {
        source.chunk_id for source in sources
    }
    payload = json.loads(messages[-1].content)
    assert payload["tables"][0]["rows"][0] == {
        "row": "r1",
        "subject": "Program 0",
        "name_id": "ich_000000000000:r1:k0",
        "cells": {f"ich_000000000000:r1:k{i}": str(i * 10) for i in range(1, 6)},
    }
    req.context_max_bytes = size - 1
    with pytest.raises(AppException) as exc:
        pack_messages(req, sources, {})
    assert exc.value.code == "answer_context_budget_exceeded"


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
    monkeypatch.setattr(service, "attach_source_text", AsyncMock())
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
    assert exc.value.code == "answer_table_value_not_extractive"


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
