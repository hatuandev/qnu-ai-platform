"""Page adjacency alone never proves a table continuation or its headers."""

import copy
from types import SimpleNamespace

import pytest

from qnu.domains.knowledge.metadata import MetadataFilter
from qnu.domains.rag.answer.table_context import dependencies
from qnu.domains.rag.answer.table_support import supports


def cell(text):
    return {"text": text, "row_span": 1, "col_span": 1, "header": False}


def document():
    def page(n, rows):
        return {
            "page_number": n,
            "extraction_method": "native",
            "blocks": [
                {
                    "evidence_id": f"t{n}",
                    "requires_review": False,
                    "bbox": {
                        "units": "normalized_0_1",
                        "x0": 0.1,
                        "x1": 0.9,
                        "y0": 0.5 if n == 1 else 0.05,
                        "y1": 0.96,
                    },
                    "table": {
                        "status": "parsed",
                        "column_count": 3,
                        "rows": [[cell(v) for v in row] for row in rows],
                    },
                }
            ],
        }

    return {
        "ocr_run_id": "run",
        "pages": [
            page(1, [["Index", "Program", "Limit"], ["1", "Alpha", "7"], ["2", "Beta", "8"]]),
            page(2, [["", "", "continued note"], ["3", "Gamma", "9"], ["4", "Delta", "10"]]),
            page(3, [["5", "Epsilon", "11"], ["6", "Zeta", "12"]]),
        ],
    }


def test_numbered_native_flow_exposes_header_and_partial_row_dependencies_without_mutation():
    doc = document()
    original = copy.deepcopy(doc)
    result = dependencies(doc)
    assert result["run:t2"]["header"] == "run:t1"
    assert result["run:t2"]["previous"] == "run:t1"
    assert result["run:t3"]["chain"] == ["run:t1", "run:t2", "run:t3"]
    assert result["run:t3"]["previous"] is None
    assert doc == original


@pytest.mark.parametrize(
    "change",
    [
        "gap",
        "reset",
        "width",
        "not_at_boundary",
        "heading",
        "ocr",
        "spans",
        "review",
    ],
)
def test_same_column_count_and_adjacent_pages_do_not_bypass_other_checks(change):
    doc = document()
    second = doc["pages"][1]
    block = second["blocks"][0]
    if change == "gap":
        second["page_number"] = 8
    elif change == "reset":
        block["table"]["rows"][1][0]["text"] = "1"
        block["table"]["rows"][2][0]["text"] = "2"
    elif change == "width":
        block["bbox"]["x1"] = 0.7
    elif change == "not_at_boundary":
        block["bbox"]["y0"] = 0.3
    elif change == "heading":
        second["blocks"].insert(0, {"text": "An independent table"})
    elif change == "ocr":
        second["extraction_method"] = "ocr"
    elif change == "spans":
        block["table"]["rows"][1][1]["col_span"] = 2
    else:
        block["requires_review"] = True
    assert "run:t2" not in dependencies(doc)
    assert "run:t3" not in dependencies(doc)


def test_sources_never_share_a_chain():
    first, second = document(), document()
    second["ocr_run_id"] = "other"
    assert all(k.startswith("run:") for k in dependencies(first))
    assert all(v["header"].startswith("other:") for v in dependencies(second).values())


def test_support_selection_stays_in_bound_input_and_respects_metadata():
    def row(key, binding, ref, indices):
        return SimpleNamespace(
            id=key,
            chunk_id=key,
            input_id=binding,
            structure={
                "source_table_citation": ref,
                "row_indices": indices,
            },
        )

    primary = row("selected", "input-a", "run:t2", [0, 1])
    header = row("header", "input-a", "run:t1", [0, 1])
    tail = row("tail", "input-a", "run:t1", [4, 5])
    foreign = row("foreign", "input-b", "run:t1", [0])
    link = dependencies(document())["run:t2"]
    selected, links = supports(
        [primary], [primary, foreign, header, tail], {("input-a", "run:t2"): link}, MetadataFilter()
    )
    assert set(selected) == {"header", "tail"}
    assert links[0]["support_ids"] == ["header", "tail"]
    assert supports(
        [primary],
        [primary, foreign, header, tail],
        {("input-a", "run:t2"): link},
        MetadataFilter(data_year=2040),
    ) == ({}, [])
