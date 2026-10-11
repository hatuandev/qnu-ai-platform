"""Pages and facts must follow actual boundaries, including after Markdown edits."""

from app.modules.knowledge.chunker import get_chunker
from app.modules.knowledge.facts import FactExtractor
from app.modules.knowledge.services.source_pages import (
    canonical_pages,
    chunk_source_pages,
    manifest_page_count,
    normalize_source_pages,
)


def test_structured_ocr_pages_keep_real_char_counts_and_fact_pages():
    pages = [
        {"page_number": 1, "extracted_text": "# Giới thiệu\nNội dung trang đầu."},
        {"page_number": 2, "extracted_text": "| Ngành | Chỉ tiêu |\n| --- | --- |\n| Công nghệ thông tin | 150 |"},
    ]
    markdown, manifest = normalize_source_pages("flattened", 2, pages)
    assert "<!-- Trang 2 -->" in markdown
    assert manifest[0]["chars"] != manifest[1]["chars"]
    records = canonical_pages(markdown, 2)
    facts = FactExtractor().extract_from_verified_markdown_pages(records, "collection", "binding")
    assert facts
    assert all(fact["raw_data"]["page_number"] == 2 for fact in facts)
    chunks = chunk_source_pages(get_chunker("SemanticChunker"), markdown, manifest_page_count(manifest))
    assert any(chunk.page_number == 2 for chunk in chunks if "150" in chunk.content)


def test_unmapped_multipage_text_never_invents_page_one():
    markdown, manifest = normalize_source_pages("Không có ranh giới trang", 3)
    assert manifest == [{"page": None, "chars": len(markdown)}]
    assert canonical_pages(markdown, 3)[0]["page_number"] is None
    assert canonical_pages(markdown, manifest_page_count(manifest))[0]["page_number"] is None
    chunks = chunk_source_pages(get_chunker("SemanticChunker"), markdown, manifest_page_count(manifest))
    assert chunks and all(chunk.page_number is None for chunk in chunks)


def test_edit_rebuilds_manifest_and_preserves_page_markers():
    markdown, manifest = normalize_source_pages("<!-- Trang 2 -->\nNội dung sửa lại", 3)
    assert manifest == [{"page": 2, "chars": len("Nội dung sửa lại")}]
    assert canonical_pages(markdown)[0]["page_number"] == 2


def test_blank_first_page_does_not_shift_second_page():
    markdown, manifest = normalize_source_pages("", 2, [
        {"page_number": 1, "extracted_text": ""},
        {"page_number": 2, "extracted_text": "Nội dung trang hai"},
    ])
    assert manifest[0] == {"page": 1, "chars": 0}
    assert canonical_pages(markdown)[1]["page_number"] == 2
