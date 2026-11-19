"""Unit tests for Data Handoff Guards and Fallbacks across backendV1 layers.

Covers:
- Priority 1: Safe publication.content access (source_tables/tables, citations/index) in chunking & metadata.
- Priority 2: Safe handling of empty/None structures in table_support, structure_context, and cells.
- Priority 3: Safe unclosed <phan_tich> handling in reasoning, and entity/year preservation in decomposition.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from qnu.domains.knowledge.index.chunking import build_chunks
from qnu.domains.knowledge.metadata import _table_entry, target_refs
from qnu.domains.rag.answer.cells import _ref as cells_ref
from qnu.domains.rag.answer.decomposition import decompose_query, needs_decomposition
from qnu.domains.rag.answer.reasoning import split_reasoning_and_answer
from qnu.domains.rag.answer.structure_context import _owners
from qnu.domains.rag.answer.table_support import _support_link

# --- Priority 1 Tests ---

def test_chunking_safe_content_fallbacks():
    """Verify build_chunks does not crash with KeyError when content has no source_tables or uses index."""
    content = {
        "title": "Tài liệu không có bảng",
        "index": {
            "ocr_1:ev_1": {"page": 1, "bbox": [0, 0, 100, 100]},
        },
        "sections": [
            {
                "heading": "Mục 1",
                "paragraphs": [
                    {
                        "text": "Nội dung đoạn văn bản thông thường.",
                        "citations": ["ocr_1:ev_1"],
                    }
                ],
            }
        ],
        # Omits "source_tables" and "citations"
    }

    chunks = build_chunks(content, documents=[], maximum=2000)
    assert len(chunks) == 1
    assert chunks[0].kind == "paragraph"
    assert "Nội dung đoạn văn bản thông thường." in chunks[0].text
    assert "ocr_1:ev_1" in chunks[0].citations


def test_metadata_table_entry_safe_fallback():
    """Verify _table_entry handles content without source_tables without raising KeyError."""
    content_no_tables = {"title": "Doc", "citations": {}}
    assert _table_entry(content_no_tables, "tab_1") is None

    content_legacy_tables = {
        "title": "Doc",
        "tables": [{"citation": "tab_1", "table": {"column_count": 3}}],
    }
    assert _table_entry(content_legacy_tables, "tab_1") is not None


def test_metadata_target_refs_index_fallback():
    """Verify target_refs handles content using 'index' instead of 'citations'."""
    content_with_index = {
        "index": {"c1": {}, "c2": {}},
    }
    refs = target_refs(content_with_index, "document")
    assert refs == {"c1", "c2"}


# --- Priority 2 Tests ---

def test_table_support_empty_row_indices_guard():
    """Verify _support_link handles options with empty row_indices without ValueError: min() arg is an empty sequence."""
    source = MagicMock()
    source.id = "chk_src"
    source.input_id = "inp_1"
    source.structure = {"source_table_citation": "tab_1", "row_indices": [0, 1]}

    # Mock chunk with empty row_indices list
    empty_row_chunk = MagicMock()
    empty_row_chunk.id = "chk_empty"
    empty_row_chunk.structure = {"row_indices": []}

    tables = {
        ("inp_1", "hdr_1"): [empty_row_chunk],
    }
    relationships = {
        ("inp_1", "tab_1"): {"header": "hdr_1", "previous": None},
    }

    # Must return None safely instead of crashing with ValueError: min() arg is an empty sequence
    res = _support_link(source, tables, relationships, scopes=[])
    assert res is None


def test_structure_context_none_identity_guard():
    """Verify _owners handles document with identity=None without AttributeError."""
    row = MagicMock()
    row.input_id = "inp_1"
    row.id = "chk_1"
    row.citations = {
        "ev_1": {
            "run_id": "ocr_1",
            "revision_id": "rev_1",
        }
    }

    doc_with_none_identity = {
        "ocr_run_id": "ocr_1",
        "identity": None,  # Can occur in JSON when optional field is null
    }

    owners = _owners([row], "inp_1", doc_with_none_identity)
    assert "ev_1" in owners
    assert owners["ev_1"] == ["chk_1"]


def test_cells_none_structure_guard():
    """Verify cells _ref handles source with structure=None gracefully."""
    source = MagicMock()
    source.structure = None
    source.citations = {"tab_1:ev_1"}

    pos = MagicMock()
    pos.cell = {"evidence_id": "ev_1"}

    ref = cells_ref(source, pos)
    assert ref is None


# --- Priority 3 Tests ---

def test_reasoning_closed_phan_tich():
    """Well-formed <phan_tich>...</phan_tich> separates reasoning and answer."""
    raw = (
        "<phan_tich>\n1. Issue: Check rule.\n2. Rule: R1.\n"
        "3. App: A1.\n4. Concl: C1.\n</phan_tich>\n"
        '{"status":"answered","statements":[{"text":"Answer","evidence_ids":["E1"]}]}'
    )
    reasoning, clean_answer = split_reasoning_and_answer(raw)
    assert "1. Issue: Check rule." in reasoning
    assert clean_answer.startswith('{"status":"answered"')
    assert "<phan_tich>" not in clean_answer


def test_reasoning_unclosed_phan_tich_with_json():
    """Unclosed <phan_tich> followed by JSON extracts reasoning and preserves JSON user answer."""
    raw = (
        "<phan_tich>\n1. Issue: Question about score.\n"
        "2. Rule: PT2 regulation.\n"
        "3. Application: Score 15 is for group 1.\n"
        "4. Conclusion: Not applicable for group 2.\n"
        '{"status":"answered","statements":[{"text":"Không thể dùng điểm.","evidence_ids":["E1"]}]}'
    )
    reasoning, clean_answer = split_reasoning_and_answer(raw)
    assert "1. Issue: Question about score." in reasoning
    assert "4. Conclusion: Not applicable for group 2." in reasoning
    assert clean_answer.startswith('{"status":"answered"')
    data = json.loads(clean_answer)
    assert data["status"] == "answered"
    assert data["statements"][0]["text"] == "Không thể dùng điểm."


def test_reasoning_unclosed_phan_tich_with_conclusion_line():
    """Unclosed <phan_tich> in text format splits at Conclusion line, never returning blank answer."""
    raw = (
        "<phan_tich>\n1. Vấn đề: Thí sinh hỏi về chuyển tổ hợp môn.\n"
        "2. Quy định: Đề án tuyển sinh 2024 Điều 4.\n"
        "3. Áp dụng: Tổ hợp xét tuyển phải theo đúng mã ngành.\n"
        "4. Kết luận: Không được dùng tổ hợp khác.\n\n"
        "Chào bạn, theo quy định đề án tuyển sinh, bạn không thể sử dụng kết quả tổ hợp môn này."
    )
    reasoning, clean_answer = split_reasoning_and_answer(raw)
    assert "1. Vấn đề" in reasoning
    assert "4. Kết luận" in reasoning
    assert "Chào bạn, theo quy định" in clean_answer
    assert "<phan_tich>" not in clean_answer


def test_reasoning_fallback_avoids_empty_answer():
    """If <phan_tich> is present with no tags and no standard markers, never leaves clean_user_answer blank."""
    raw = "<phan_tich> Câu trả lời duy nhất của model không có thẻ đóng và không có bước."
    _reasoning, clean_answer = split_reasoning_and_answer(raw)
    assert clean_answer == "Câu trả lời duy nhất của model không có thẻ đóng và không có bước."


def test_decomposition_preserves_major_codes_and_years():
    """Verify decompose_query enriches subsequent clauses with major, codes, and years from parent query."""
    q = "Ngành Sư phạm Toán 7140209 năm 2024 có chỉ tiêu bao nhiêu và nếu xét học bạ thì điểm sàn là mấy?"
    assert needs_decomposition(q) is True
    sub_queries = decompose_query(q)
    assert len(sub_queries) == 2
    # Clause 1 retains its full text
    assert "Ngành Sư phạm Toán 7140209 năm 2024" in sub_queries[0]
    # Clause 2 inherits major, code, and year
    assert "Sư phạm Toán" in sub_queries[1]
    assert "7140209" in sub_queries[1]
    assert "2024" in sub_queries[1]
    assert "xét học bạ thì điểm sàn là mấy" in sub_queries[1]


def test_decomposition_does_not_override_clause_own_year():
    """Verify decompose_query does not overwrite a clause's own year if already present."""
    q = "Ngành Công nghệ thông tin 7480201 năm 2024 có học phí bao nhiêu, còn năm 2025 thì sao?"
    assert needs_decomposition(q) is True
    sub_queries = decompose_query(q)
    assert len(sub_queries) >= 2
    # Clause 2 has year 2025, should inherit major and code, but retain 2025
    assert "Công nghệ thông tin" in sub_queries[1]
    assert "7480201" in sub_queries[1]
    assert "2025" in sub_queries[1]


def test_decomposition_preserves_short_zero_prefixed_code():
    """Verify decompose_query preserves codes starting with 0 like 0012 or 01."""
    q = "Mã ngành 0012 năm 2024 xét theo phương thức nào và nếu nộp hồ sơ đợt 01 thì cần gì?"
    sub_queries = decompose_query(q)
    assert len(sub_queries) >= 1
    # Check that codes are not stripped or mangled
    assert any("0012" in sq for sq in sub_queries)
