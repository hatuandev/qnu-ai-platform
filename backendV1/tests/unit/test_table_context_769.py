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
    doc["pages"][1]["blocks"][0]["bbox"]["y1"] = 0.884
    original = copy.deepcopy(doc)
    result = dependencies(doc)
    assert result["run:t2"]["header"] == "run:t1"
    assert result["run:t2"]["previous"] == "run:t1"
    assert result["run:t3"]["chain"] == ["run:t1", "run:t2", "run:t3"]
    assert result["run:t3"]["previous"] is None
    assert doc == original


def test_retrieving_last_row_also_selects_its_verified_continuation():
    def row(key, ref, indices, total):
        return SimpleNamespace(
            id=key,
            chunk_id=key,
            input_id="input",
            structure={
                "source_table_citation": ref,
                "row_indices": indices,
                "original_row_count": total,
            },
        )

    header = row("header", "run:t1", [0, 1], 3)
    tail = row("tail", "run:t1", [2], 3)
    head = row("head", "run:t2", [0, 1], 3)
    links = {("input", ref): link for ref, link in dependencies(document()).items()}

    selected, resolved = supports([tail], [header, tail, head], links, MetadataFilter())
    assert set(selected) == {"header", "tail", "head"}
    continuation = next(link for link in resolved if link["chunk_id"] == head.id)
    assert continuation["previous"] == "run:t1"
    assert set(continuation["support_ids"]) == {"header", "tail"}
    selected, _ = supports([header], [header, tail, head], links, MetadataFilter())
    assert "head" not in selected
    head.structure["retrieval_metadata"] = [{"values": {"data_year": 2032}}]
    for chunk in (header, tail):
        chunk.structure["retrieval_metadata"] = [{"values": {"data_year": 2031}}]
    selected, _ = supports([tail], [header, tail, head], links, MetadataFilter(data_year=2031))
    assert "head" not in selected


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


def test_partial_row_with_its_own_subject_cannot_borrow_previous_subject():
    doc = document()
    doc["pages"][1]["blocks"][0]["table"]["rows"][0][1]["text"] = "Different subject"
    link = dependencies(doc)["run:t2"]
    assert link["header"] == "run:t1"
    assert link["previous"] is None


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
    for entry, year in [(primary, 2031), (header, 2031), (tail, 2032)]:
        entry.structure["retrieval_metadata"] = [{"values": {"data_year": year}}]
    assert supports(
        [primary],
        [primary, header, tail],
        {("input-a", "run:t2"): link},
        MetadataFilter(),
        [MetadataFilter(data_year=2031), MetadataFilter(data_year=2032)],
    ) == ({}, [])
