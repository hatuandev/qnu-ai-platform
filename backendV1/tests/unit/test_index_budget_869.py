"""Embedding budgets replace the old implicit 3000-byte index cap without losing cells."""

import pytest

from qnu.domains.knowledge.index.chunking import build_chunks
from qnu.domains.knowledge.index.contextual import contextual_size, enrich, original_text
from qnu.platform.config import Settings
from qnu.platform.errors import AppException
from tests.unit.test_index_chunking_647 import fixture


def test_chunk_size_has_no_implicit_operator_cap(monkeypatch):
    monkeypatch.delenv("INDEX_CHUNK_MAX_BYTES", raising=False)
    assert Settings(_env_file=None).INDEX_CHUNK_MAX_BYTES is None


@pytest.mark.parametrize("contextual", [False, True])
def test_large_row_keeps_all_cells_headers_notes_and_citations(contextual):
    content, documents = fixture(12)
    table = content["source_tables"][0]["table"]
    table["rows"][1][0]["text"] = "Nội dung ô dài có dấu tiếng Việt. " * 120
    with pytest.raises(AppException) as old:
        build_chunks(content, documents, 3000)
    assert old.value.code == "index_table_group_too_large"

    maximum = 8192 - 32
    sizing = {"size": contextual_size(content, documents)} if contextual else {}
    original = build_chunks(content, documents, maximum, **sizing)
    chunks = original
    if contextual:
        chunks = enrich(chunks, content, documents, maximum)
        assert all(original_text(c) == old.text for c, old in zip(chunks, original, strict=True))
    tables = [chunk for chunk in chunks if chunk.kind == "table"]
    assert all(len(chunk.text.encode("utf-8")) <= maximum for chunk in chunks)
    recovered = {}
    for chunk in tables:
        assert chunk.structure["row_indices"][0] == 0
        assert "Ghi chú" in chunk.text and "ocr-example:ev-note" in chunk.citations
        for row in chunk.structure["rows"]:
            for cell in row:
                recovered[cell["evidence_id"]] = cell
                assert "ocr-example:" + cell["evidence_id"] in chunk.citations
    assert recovered == {cell["evidence_id"]: cell for row in table["rows"] for cell in row}


def test_contextual_paragraph_splits_using_actual_heading_metadata_and_glossary():
    content, documents = fixture()
    content["source_tables"] = []
    documents[0]["pages"][0]["blocks"].append(
        {"evidence_id": "ev-text", "text": "Hải dương học (HDH)."}
    )
    paragraph = content["sections"][0]["paragraphs"][0]
    words = ["HDH", *[f"nội_dung_{i}" for i in range(300)], "HDH"]
    paragraph["text"] = " ".join(words)
    annotations = [
        {"target": "paragraph:0:0", "values": {"data_year": 2031}, "evidence": []}
    ]
    chunks = build_chunks(
        content, documents, 1200, annotations, size=contextual_size(content, documents)
    )
    enriched = enrich(chunks, content, documents, 1200)
    assert len(enriched) > 1
    assert all(len(c.text.encode("utf-8")) <= 1200 for c in enriched)
    assert [word for c in enriched for word in original_text(c).split("\n", 2)[2].split()] == words
    assert all(c.structure["retrieval_metadata"] == annotations for c in enriched)
    assert all(list(c.citations) == ["ocr-example:ev-text"] for c in enriched)


def test_indivisible_table_still_reports_model_input_overflow():
    content, documents = fixture()
    content["source_tables"][0]["table"]["rows"][1][0]["text"] = "Nội dung " * 1000
    with pytest.raises(AppException) as exc:
        build_chunks(content, documents, 8160, size=contextual_size(content, documents))
    assert exc.value.code == "index_table_group_too_large"
