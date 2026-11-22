"""Answer compaction must preserve evidence, including fallback and merged cells."""

import copy
import json

from qnu.domains.rag.answer.cells import catalog, prompt_catalog
from qnu.domains.rag.answer.context import evidence_size
from qnu.domains.rag.answer.drafting import (
    PROMPT_VERSION,
    compact_evidence_item,
    messages_for,
    name_repair_schema,
    output_schema,
)
from qnu.domains.rag.answer.schemas import EvidenceSource


def source(text, structure, citations=None):
    return EvidenceSource(
        evidence_id="E20",
        chunk_id="chunk",
        document_id="doc",
        version_id="version",
        publication_decision_id="decision",
        score=1,
        kind="table",
        text=text,
        citations=citations or {},
        structure=structure,
    )


def test_unparsed_table_keeps_raw_text_and_status():
    item = source("Bảng chưa dựng: Alpha 12; Beta 34", {"table_status": "unparsed"})
    sent = json.loads(messages_for("Question", [item])[-1].content)["evidence"][0]
    assert sent["text"] == item.text
    assert sent["table_status"] == "unparsed"
    assert "structure" not in sent


def test_merged_cells_keep_values_and_server_geometry_without_duplicate_json():
    structure = {
        "source_table_citation": "ocr:table",
        "original_row_count": 3,
        "original_column_count": 2,
        "row_indices": [0, 1, 2],
        "page_notes": [],
        "rows": [
            [{"text": "Header", "col_span": 2, "row_span": 1, "header": True}],
            [
                {"text": "Group", "col_span": 1, "row_span": 2, "header": False},
                {"text": "12", "col_span": 1, "row_span": 1, "header": False},
            ],
            [{"text": "34", "col_span": 1, "row_span": 1, "header": False}],
        ],
    }
    citations = {"ocr:table": {"page": 1}}
    for i, row in enumerate(structure["rows"]):
        for j, cell in enumerate(row):
            cell["evidence_id"] = f"t-{i}-{j}"
            citations[f"ocr:t-{i}-{j}"] = {"page": 1}
    raw = "Title\n" + json.dumps(structure, ensure_ascii=False, sort_keys=True)
    item = source(raw, {**structure, "context": {"parent": "table:ocr:table"}}, citations)
    original = copy.deepcopy(item)
    sent = compact_evidence_item(item)
    assert sent["id"] == item.evidence_id
    assert sent["text"].startswith("Title")
    assert "row[1]: Group | 12" in sent["text"]
    assert "source_table_citation" not in sent["text"]
    assert "structure" not in sent
    assert item == original
    assert evidence_size(item) == len(json.dumps(sent, ensure_ascii=False).encode()) + 2
    cells = catalog([item])
    view = prompt_catalog(cells)
    table = view["tables"][0]
    assert table["id"] == item.evidence_id
    assert table["columns"] == {"k0": "Header", "k1": "Header"}
    rendered = json.dumps(table["rows"])
    assert "12" in rendered and "34" in rendered
    assert "source_cells" not in rendered and "row_span" not in rendered
    assert cells["tables"][0]["cells"][0]["source_cells"]


def test_arbitrary_json_in_table_text_is_not_removed():
    item = source('Title {"note":"keep"}\nRaw table', {"rows": [[{"text": "12"}]]})
    assert compact_evidence_item(item)["text"] == item.text


def test_new_answer_contract_has_a_distinct_prompt_version():
    assert PROMPT_VERSION in ("qnu.rag.answer/v40", "qnu.rag.answer/v42")


def test_list_repair_only_allows_proven_names_and_leaves_original_schema_intact():
    cells = {
        "tables": [
            {
                "cells": [
                    {"cell_id": "E1:r1:k0", "row_name": True},
                    {"cell_id": "E1:r1:k1"},
                ]
            }
        ]
    }
    original = output_schema()
    repair = name_repair_schema(original, cells)
    assert repair["properties"]["statements"]["maxItems"] == 0
    assert repair["$defs"]["CellSelection"]["properties"]["cell_id"]["enum"] == ["E1:r1:k0"]
    assert original["properties"]["statements"]["maxItems"] != 0
    assert name_repair_schema(original, {"tables": []}) is None


def test_reading_join_keeps_exact_adjacent_passages_and_both_citations():
    left = source("Inspection opens from", {}, {"ocr:a": {}}).model_copy(
        update={
            "evidence_id": "E1",
            "kind": "paragraph",
            "source_passages": [
                {
                    "citation": "ocr:a",
                    "text": "A notice follows. Inspection opens from",
                    "position": "2",
                }
            ],
        }
    )
    right = left.model_copy(
        update={
            "evidence_id": "E2",
            "chunk_id": "second",
            "citations": {"ocr:b": {}},
            "source_passages": [
                {"citation": "ocr:b", "text": "day 4 to day 9.", "position": "3"}
            ],
        }
    )
    payload = json.loads(messages_for("When is inspection open?", [right, left])[-1].content)
    assert payload["joins"] == [
        {"ids": ["E1", "E2"], "text": "Inspection opens from day 4 to day 9."}
    ]
    right.source_passages[0]["position"] = "4"
    assert "joins" not in json.loads(messages_for("When?", [right, left])[-1].content)


def test_prompt_requires_partial_answers_when_any_requirement_is_grounded():
    from qnu.domains.rag.answer.drafting import SYSTEM_PROMPT

    assert "Chỉ cần MỘT yêu cầu có căn cứ" in SYSTEM_PROMPT
    assert "Không được trả insufficient_evidence khi evidence đã chứa dữ kiện" in SYSTEM_PROMPT
    assert "Một phần có căn cứ, phần còn lại thiếu (vẫn bắt buộc answered)" in SYSTEM_PROMPT


def test_prompt_allows_verbatim_prose_only_for_unselectable_tables():
    from qnu.domains.rag.answer.drafting import SYSTEM_PROMPT

    assert "Bảng trong unselectable không có ô để chọn" in SYSTEM_PROMPT
    assert "chép nguyên văn giá trị nhìn thấy trong text" in SYSTEM_PROMPT
    assert "Số của bảng trong tables chỉ đi qua lookups" in SYSTEM_PROMPT


def test_prompt_requires_co_citing_sibling_fragments_and_verbatim_enumeration():
    from qnu.domains.rag.answer.drafting import SYSTEM_PROMPT

    assert (
        "Mỗi số trong statement phải hiện trong text của ít nhất một id được dẫn" in SYSTEM_PROMPT
    )
    assert "phải dẫn kèm id của mảnh đó" in SYSTEM_PROMPT
    assert "không trả lookups cho bảng unselectable" in SYSTEM_PROMPT
    assert "không abstain chỉ vì phải liệt kê nhiều tên" in SYSTEM_PROMPT
    assert "12,5 không viết 12.5" in SYSTEM_PROMPT


def test_prompt_answers_symbol_definitions_from_narrative_and_all_grounded_parts():
    from qnu.domains.rag.answer.drafting import SYSTEM_PROMPT

    assert (
        "bảng không chọn được ô không phải lý do abstain khi văn bản đã có căn cứ" in SYSTEM_PROMPT
    )
    assert "điều, khoản hoặc chú thích văn bản đã định nghĩa rõ" in SYSTEM_PROMPT
    assert "trả lời đủ từng ý có căn cứ, kể cả ý nằm ở bảng hoặc chú thích khác" in SYSTEM_PROMPT
    assert "không bỏ ý đã có nguồn chỉ vì tập trung vào ý chính" in SYSTEM_PROMPT
