"""Guard row preservation and the identity of spatially scoped PDF evidence."""

import copy

import pytest

from app.modules.knowledge.normalization.qnu_markdown import QnuBlock, QnuSourceLocation
from app.modules.knowledge.parsers.pdf_structure import (
    _collect_page_legends,
    _link_symbol_legends,
    build_pdf_document,
)
from app.modules.knowledge.parsers.pdf_tables import native_table, table_blocks


def _text(text, box):
    return {"bbox": box, "lines": [{"spans": [{"text": text, "size": 11}]}]}


def _page(tables, blocks=()):
    return {"page": 1, "native": {
        "page": 1, "width": 100, "height": 100,
        "bbox_space": "pymupdf_unrotated_points",
        "tables": tables, "layout": {"blocks": list(blocks)},
    }}


def _build(page):
    return build_pdf_document({"pages": [page]}, filename="fixture.pdf", sha256="a" * 64)


@pytest.mark.parametrize("candidate", ["merged_body", "gap", "multiple_rows"])
def test_native_header_proposals_keep_every_unverified_row(candidate):
    raw = {
        "bbox": [0, 0, 100, 30],
        "matrix": [["Alpha", "North"], ["Beta", "South"]],
        "cell_boxes": [[[0, 0, 50, 10], [50, 0, 100, 10]],
                       [[0, 10, 50, 20], [50, 10, 100, 20]]],
        "header": {"names": ["Alpha", "North"], "bbox": [0, 0, 100, 10], "external": False},
    }
    if candidate == "merged_body":
        raw["matrix"][1] = ["Beta", None]
        raw["cell_boxes"][1] = [[0, 10, 100, 20], None]
    elif candidate == "gap":
        raw["cell_boxes"][1] = [[0, 13, 50, 23], [50, 13, 100, 23]]
    else:
        raw["proposed_header_depth"] = 2
        raw["matrix"].append(["01", "0"])
        raw["cell_boxes"].append([[0, 20, 50, 30], [50, 20, 100, 30]])
    before = copy.deepcopy(raw)
    doc = _build(_page([raw]))
    table = next(b for b in doc.blocks if b.type == "table")
    rows = [b for b in doc.blocks if b.type == "table_row"]
    assert len(rows) == len(raw["matrix"])
    assert rows[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert rows[0].attributes["fields"]["c02"]["raw"] == "North"
    assert all(c["header_path"] == [] for c in table.attributes["columns"])
    assert any(f.code == "table_header_unresolved" for f in table.quality_flags)
    assert table.source_data["table"]["raw_native"] == before == raw
    if candidate == "merged_body":
        assert rows[1].attributes["field_origins"]["c02"]["column_id"] == "c01"
        assert rows[1].attributes["field_sources"]["c02"]["bbox"] == [0, 10, 100, 20]


def test_external_numeric_headers_do_not_consume_data_rows():
    raw = {"bbox": [0, 10, 100, 30], "matrix": [["001", "0"], ["002", ""]],
           "header": {"external": True, "names": ["2025", "2026"], "bbox": [0, 0, 100, 10]}}
    doc = _build(_page([raw]))
    table = next(b for b in doc.blocks if b.type == "table")
    assert [c["header_path"] for c in table.attributes["columns"]] == [["2025"], ["2026"]]
    rows = [b for b in doc.blocks if b.type == "table_row"]
    assert len(rows) == 2
    assert rows[0].attributes["fields"]["c01"]["raw"] == "001"
    assert rows[0].attributes["fields"]["c02"]["raw"] == "0"


def test_duplicate_legend_text_keeps_each_tables_own_source_identity():
    line = 'Symbol "–": value is not applicable.'
    tables = []
    for left, right in [(0, 40), (60, 100)]:
        mid = (left + right) / 2
        tables.append({"bbox": [left, 30, right, 60], "matrix": [["01", "–"]],
                       "cell_boxes": [[[left, 30, mid, 60], [mid, 30, right, 60]]],
                       "header": {"external": True, "names": ["Ref", "Value"]}})
    doc = _build(_page(tables, [_text(line, [0, 65, 40, 70]), _text(line, [60, 65, 100, 70])]))
    for index in (0, 1):
        row = next(b for b in doc.blocks if b.type == "table_row"
                   and b.source_locations[0].locator.startswith(f"pdf:page:1/native/table/{index}/"))
        note = next(b for b in doc.blocks
                    if b.source_locations[0].locator == f"pdf:page:1/native/block/{index}")
        assert row.attributes["fields"]["c02"]["state"] == "present"
        assert row.context_refs == [note.id]
        flag = next(f for f in row.quality_flags if f.code == "cell_symbol_defined")
        assert flag.related_block_ids == [note.id]


def test_native_fallback_does_not_deduplicate_legends_at_different_locations():
    line = 'Symbol "–": value is not applicable.'
    page = _page([], [_text(line, [0, 65, 40, 70]), _text(line, [60, 65, 100, 70])])
    selected = [{"text": line, "bbox": [0, 65, 40, 70], "locator": "pdf:page:1/native/block/0"}]
    candidates = _collect_page_legends(selected, page)
    assert {c["locator"] for c in candidates} == {
        "pdf:page:1/native/block/0", "pdf:page:1/native/block/1"}


def test_other_column_table_does_not_block_legend_association():
    line = 'Symbol "–": value is not applicable.'
    tables = [
        {"bbox": [0, 30, 40, 60], "matrix": [["01", "–"]],
         "cell_boxes": [[[0, 30, 20, 60], [20, 30, 40, 60]]],
         "header": {"external": True, "names": ["Ref", "Value"]}},
        {"bbox": [60, 62, 100, 80], "matrix": [["02", "x"]],
         "header": {"external": True, "names": ["Ref", "Value"]}},
    ]
    doc = _build(_page(tables, [_text(line, [0, 65, 40, 70])]))
    row = next(b for b in doc.blocks if b.type == "table_row"
               and b.attributes["fields"]["c01"]["raw"] == "01")
    assert row.attributes["fields"]["c02"]["state"] == "present"


@pytest.mark.parametrize("problem", ["missing", "duplicate", "wrong_locator", "wrong_page"])
def test_legend_resolution_requires_one_canonical_source_match(problem):
    line = 'Symbol "–": value is not applicable.'
    entry = {"symbol": "–", "page": 1, "line": line, "locator": "right/legend",
             "bbox": [60, 65, 100, 70]}
    raw = {"matrix": [["01", "–"]],
           "cell_boxes": [[[60, 30, 80, 60], [80, 30, 100, 60]]],
           "header": {"external": True, "names": ["Ref", "Value"]}}
    row = table_blocks(native_table(raw), block_id="table", parent_id=None,
                       location=QnuSourceLocation(page=1, locator="right/table"), section_path=[],
                       engine="native", symbol_definitions={"–": entry})[1]
    note = QnuBlock(id="note", type="note", body=line,
                    source_locations=[QnuSourceLocation(page=1, locator="right/legend")])
    if problem == "missing":
        notes = []
    elif problem == "duplicate":
        notes = [note, note.model_copy(update={"id": "duplicate"}, deep=True)]
    elif problem == "wrong_locator":
        note.source_locations[0].locator = "left/legend"
        notes = [note]
    else:
        note.source_locations[0].page = 2
        notes = [note]
    _link_symbol_legends([row, *notes])
    assert row.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert not row.context_refs
    assert not row.attributes["symbol_definitions"]
    assert row.attributes["symbol_definition_candidates"]["c02"] == entry
    assert not any(f.code == "cell_symbol_defined" for f in row.quality_flags)
