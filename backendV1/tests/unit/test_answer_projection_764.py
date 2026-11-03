"""Answer compaction must preserve evidence, including fallback and merged cells."""

import copy
import json

from qnu.domains.rag.answer.context import evidence_size
from qnu.domains.rag.answer.drafting import PROMPT_VERSION, compact_evidence_item, messages_for
from qnu.domains.rag.answer.schemas import EvidenceSource


def source(text, structure):
    return EvidenceSource(
        evidence_id="E20",
        chunk_id="chunk",
        document_id="doc",
        version_id="version",
        publication_decision_id="decision",
        score=1,
        kind="table",
        text=text,
        citations={},
        structure=structure,
    )


def test_unparsed_table_keeps_raw_text_and_status():
    item = source("Bảng chưa dựng: Alpha 12; Beta 34", {"table_status": "unparsed"})
    sent = json.loads(messages_for("Question", [item])[-1].content)["evidence"][0]
    assert sent["text"] == item.text
    assert sent["structure"] == item.structure


def test_compaction_retains_merged_cells_and_table_identity_without_duplicate_json():
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
    raw = "Title\n" + json.dumps(structure, ensure_ascii=False, sort_keys=True)
    item = source(raw, {**structure, "context": {"parent": "table:ocr:table"}})
    original = copy.deepcopy(item)
    sent = compact_evidence_item(item)
    assert sent["structure"] == item.structure
    assert sent["text"] == "Title\nrow[0]: Header\nrow[1]: Group | 12\nrow[2]: 34"
    assert item == original
    assert evidence_size(item) == len(json.dumps(sent, ensure_ascii=False).encode()) + 2
    old = {
        "evidence_id": item.evidence_id,
        "kind": item.kind,
        "text": item.text,
        "structure": item.structure,
    }
    assert len(json.dumps(sent)) < len(json.dumps(old))


def test_arbitrary_json_in_table_text_is_not_removed():
    item = source('Title {"note":"keep"}\nRaw table', {"rows": [[{"text": "12"}]]})
    assert compact_evidence_item(item)["text"] == item.text


def test_new_answer_contract_has_a_distinct_prompt_version():
    assert PROMPT_VERSION == "qnu.rag.answer/v15"
