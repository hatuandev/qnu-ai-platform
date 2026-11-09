"""Table/paragraph preservation and source mapping, without testing a learned model."""

import pytest

from qnu.domains.knowledge.compilation.schemas import DRAFT_PARAGRAPH_TEXT_LIMIT
from qnu.domains.knowledge.index.chunking import build_chunks
from qnu.domains.knowledge.source_sections import reading_groups
from qnu.platform.errors import AppException


def fixture(rows=4):
    run = "ocr-example"
    table_rows = []
    for i in range(rows):
        table_rows.append(
            [
                {
                    "text": value,
                    "evidence_id": f"ev-cell-{i}-{j}",
                    "header": i == 0,
                    "row_span": 1,
                    "col_span": 1,
                }
                for j, value in enumerate(
                    ["Chỉ tiêu", "2023", "2024"]
                    if i == 0
                    else [f"Chỉ tiêu {i}", "0" if i == 1 else "", "-" if i == 1 else str(i * 20)]
                )
            ]
        )
    table = {"status": "parsed", "row_count": rows, "column_count": 3, "rows": table_rows}
    evidence = {"ev-table": {"page": 1}, "ev-note": {"page": 1}, "ev-text": {"page": 1}}
    for row in table_rows:
        for cell in row:
            evidence[cell["evidence_id"]] = {"page": 1}
    citations = {run + ":" + k: v for k, v in evidence.items()}
    documents = [
        {
            "ocr_run_id": run,
            "pages": [
                {
                    "page_number": 1,
                    "blocks": [
                        {"evidence_id": "ev-table", "text": "raw table", "label": "Table"},
                        {
                            "evidence_id": "ev-note",
                            "text": "Ghi chú: giữ nguyên dấu gạch.",
                            "label": "Footnote",
                        },
                    ],
                }
            ],
        }
    ]
    content = {
        "title": "Phụ lục",
        "citations": citations,
        "sections": [
            {
                "heading": "Dữ liệu",
                "paragraphs": [
                    {"text": "Đoạn văn nguồn có dẫn chứng.", "citations": [run + ":ev-text"]}
                ],
            }
        ],
        "source_tables": [{"citation": run + ":ev-table", "page_number": 1, "table": table}],
    }
    return content, documents


def test_table_fragments_repeat_headers_keep_values_notes_and_all_rows():
    content, documents = fixture(20)
    chunks = build_chunks(content, documents, 1800)
    tables = [c for c in chunks if c.kind == "table"]
    assert len(tables) > 1
    selected = set()
    for chunk in tables:
        assert len(chunk.text.encode()) <= 1800
        assert chunk.structure["row_indices"][0] == 0
        assert "Ghi chú" in chunk.text and "ocr-example:ev-note" in chunk.citations
        selected.update(chunk.structure["row_indices"])
    assert selected == set(range(20))
    texts = [cell["text"] for c in tables for row in c.structure["rows"] for cell in row]
    assert "0" in texts and "-" in texts and "" in texts


def test_oversized_rowspan_group_splits_with_anchor_context_and_marker():
    content, documents = fixture(10)
    table = content["source_tables"][0]["table"]
    table["rows"][1][0]["row_span"] = 8
    chunks = build_chunks(content, documents, 1800)
    tables = [c for c in chunks if c.kind == "table"]
    marked = [c for c in tables if "rowspan_split" in c.structure]
    assert len(marked) > 1
    assert all(len(c.text.encode()) <= 1800 for c in tables)
    assert [c.structure["rowspan_split"]["part"] for c in marked] == list(range(len(marked)))
    assert all(c.structure["rowspan_split"]["parts"] == len(marked) for c in marked)
    assert all(c.structure["rowspan_split"]["group_start_row"] == 1 for c in marked)
    assert marked[0].structure["row_indices"][:2] == [0, 1]
    for later in marked[1:]:
        assert later.structure["row_indices"][:2] == [0, 1]
    assert {row for c in tables for row in c.structure["row_indices"]} == set(range(10))
    recovered = {}
    for chunk in tables:
        assert "Ghi chú" in chunk.text and "ocr-example:ev-note" in chunk.citations
        for row in chunk.structure["rows"]:
            for cell in row:
                recovered[cell["evidence_id"]] = cell
                assert "ocr-example:" + cell["evidence_id"] in chunk.citations
    assert recovered == {cell["evidence_id"]: cell for row in table["rows"] for cell in row}


def test_indivisible_row_inside_an_oversized_group_is_still_rejected():
    content, documents = fixture(10)
    table = content["source_tables"][0]["table"]
    table["rows"][1][0]["row_span"] = 8
    table["rows"][3][1]["text"] = "Nội dung " * 1000
    with pytest.raises(AppException) as exc:
        build_chunks(content, documents, 1800)
    assert exc.value.code == "index_table_group_too_large"


def test_long_paragraph_keeps_heading_and_all_words_with_original_citations():
    content, documents = fixture()
    content["source_tables"] = []
    words = [f"từ{i}" for i in range(100)]
    content["sections"][0]["paragraphs"][0]["text"] = " ".join(words)
    chunks = build_chunks(content, documents, 120)
    recovered = []
    for chunk in chunks:
        assert chunk.text.startswith("Phụ lục\nDữ liệu\n")
        assert list(chunk.citations) == ["ocr-example:ev-text"]
        recovered += chunk.text.split("\n", 2)[2].split()
    assert recovered == words


@pytest.mark.parametrize("status", ["parsed", "unsupported"])
def test_index_omits_only_exact_table_copy_with_no_paragraph_metadata(status):
    content, documents = fixture()
    entry = content["source_tables"][0]
    table = entry["table"]
    table["status"] = status
    flat_text = "\n".join(" | ".join(cell["text"] for cell in row) for row in table["rows"])
    documents[0]["pages"][0]["blocks"][0]["text"] = flat_text
    table_ref = entry["citation"]
    summary = "Chỉ tiêu trong bảng áp dụng cho nhiều năm."
    paragraphs = content["sections"][0]["paragraphs"]
    paragraphs.extend(
        [
            {"text": flat_text, "citations": [table_ref]},
            {"text": summary, "citations": [table_ref]},
            {"text": flat_text, "citations": [table_ref, "ocr-example:ev-note"]},
            {"text": flat_text, "citations": [table_ref]},
        ]
    )
    annotations = [{"target": "paragraph:0:4", "values": {"data_year": 2024}, "evidence": []}]

    chunks = build_chunks(content, documents, 3000, annotations)

    prose = {c.structure["context"]["position"]: c for c in chunks if c.kind == "paragraph"}
    assert set(prose) == ({0, 2, 3, 4} if status == "parsed" else {0, 1, 2, 3, 4})
    assert summary in prose[2].text
    assert prose[4].structure["retrieval_metadata"] == annotations
    assert any(c.kind == "table" and table_ref in c.citations for c in chunks)
    assert paragraphs[1]["text"] == flat_text


def test_index_omits_every_literal_part_of_a_long_parsed_table():
    content, documents = fixture(35)
    entry = content["source_tables"][0]
    for row in entry["table"]["rows"][1:]:
        row[0]["text"] += " dài" * 155
    flat_text = "\n".join(
        " | ".join(cell["text"] for cell in row) for row in entry["table"]["rows"]
    )
    assert len(flat_text) > DRAFT_PARAGRAPH_TEXT_LIMIT
    documents[0]["pages"][0]["blocks"][0]["text"] = flat_text
    content["sections"][0]["paragraphs"] = [
        {
            "text": flat_text[start : start + DRAFT_PARAGRAPH_TEXT_LIMIT],
            "citations": [entry["citation"]],
        }
        for start in range(0, len(flat_text), DRAFT_PARAGRAPH_TEXT_LIMIT)
    ]

    chunks = build_chunks(content, documents, 3000)

    assert {chunk.kind for chunk in chunks} == {"table"}
    assert {row for chunk in chunks for row in chunk.structure["row_indices"]} == set(range(35))


def test_both_compiler_modes_share_source_headings_without_changing_draft_or_citations():
    content, documents = fixture()
    blocks = documents[0]["pages"][0]["blocks"]
    blocks.insert(0, {"evidence_id": "ev-intro", "text": "Giới thiệu."})
    blocks.insert(1, {"evidence_id": "ev-title", "text": "2. Quy đổi điểm:"})
    blocks.insert(2, {"evidence_id": "ev-text", "text": "Nội dung nguồn."})
    blocks.insert(3, {"evidence_id": "ev-item", "text": "c. Điều kiện để xác định"})
    content["citations"]["ocr-example:ev-intro"] = {"page": 1}
    blocks[4]["table"] = content["source_tables"][0]["table"]
    section = content["sections"][0]
    section["paragraphs"].append({"text": "Một ô nguồn.", "citations": ["ocr-example:ev-cell-1-1"]})
    section["paragraphs"].append({"text": "Giới thiệu.", "citations": ["ocr-example:ev-intro"]})
    expected = [
        {"heading": "2. Quy đổi điểm:", "paragraphs": [(0, 0), (0, 1)]},
        {"heading": "Trang 1", "paragraphs": [(0, 2)]},
    ]
    for heading in ("Bản tóm tắt", "Nguồn 1 · Phần 1"):
        section["heading"] = heading
        assert reading_groups(content, documents) == expected
        chunks = build_chunks(content, documents, 3000)
        for chunk in chunks[:2] + chunks[3:]:
            assert "2. Quy đổi điểm:" in chunk.text
            assert chunk.structure["context"]["source_heading_citation"] == "ocr-example:ev-title"
        assert list(chunks[1].citations) == ["ocr-example:ev-cell-1-1"]
        assert section["heading"] == heading
        tight = build_chunks(content, documents, 1800)[-1]
        assert tight.structure["context"]["heading"] == "2. Quy đổi điểm:"
        assert tight.structure["rows"] == chunks[-1].structure["rows"]
    section["paragraphs"][0]["citations"].append("ocr-example:ev-intro")
    assert reading_groups(content, documents)[0]["heading"] == section["heading"]
