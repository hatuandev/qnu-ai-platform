"""Table/paragraph preservation and source mapping, without testing a learned model."""

import pytest

from qnu.domains.knowledge.index.chunking import build_chunks
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


def test_rowspan_group_is_kept_or_rejected_never_split_silently():
    content, documents = fixture(10)
    table = content["source_tables"][0]["table"]
    table["rows"][1][0]["row_span"] = 8
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
