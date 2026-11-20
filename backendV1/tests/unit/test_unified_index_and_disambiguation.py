"""Tests for unified knowledge base indexing, year layer separation, and cross-doc disambiguation."""

from __future__ import annotations

from qnu.domains.knowledge.compilation.supplement import _rules
from qnu.domains.knowledge.index.facts import (
    project_table,
)
from qnu.domains.knowledge.index.hybrid import exact_anchors, lexical_expression
from qnu.domains.knowledge.index.row_cards import (
    DocumentCardMeta,
    render_projection_to_cards,
)
from qnu.domains.rag.answer.drafting import SYSTEM_PROMPT


def _cell(text: str, *, header: bool = False, evidence_id: str | None = None) -> dict:
    return {
        "text": text,
        "row_span": 1,
        "col_span": 1,
        "header": header,
        "evidence_id": evidence_id,
    }


# ==============================================================================
# NHÓM 1: Chuẩn hóa subject_name và hỗ trợ đa năm trên bảng
# ==============================================================================


def test_subject_name_prioritizes_tieu_chi_over_quantitative_column():
    """Verify Tiêu chí is chosen as subject_name even when description is long (>120 chars),

    and does NOT jump to the shorter 'Điểm thành phần' column.
    """
    long_tieu_chi = (
        "Có triển khai hệ thống quản lý học tập trực tuyến (LMS)/hệ thống quản lý nội dung học tập "
        "trực tuyến (LCMS) phục vụ đào tạo trực tuyến theo quy định của Bộ Giáo dục và Đào tạo."
    )
    table = {
        "row_count": 2,
        "column_count": 6,
        "rows": [
            [
                _cell("STT", header=True, evidence_id="h0"),
                _cell("Tiêu chí", header=True, evidence_id="h1"),
                _cell("Điểm tối đa", header=True, evidence_id="h2"),
                _cell("Điểm thành phần", header=True, evidence_id="h3"),
                _cell("Mức độ", header=True, evidence_id="h4"),
                _cell("Ghi chú, minh chứng", header=True, evidence_id="h5"),
            ],
            [
                _cell("1.3", evidence_id="r1_0"),
                _cell(long_tieu_chi, evidence_id="r1_1"),
                _cell("20", evidence_id="r1_2"),
                _cell("Tối đa 16 điểm, mỗi chức năng triển khai được tối đa 4 điểm.", evidence_id="r1_3"),
                _cell("Mức 1: dưới 8 điểm; Mức 2: 8-14 điểm; Mức 3: trên 14 điểm", evidence_id="r1_4"),
                _cell("Đường link, giải pháp LMS", evidence_id="r1_5"),
            ],
        ],
    }

    projected = project_table(
        table,
        table_id="tbl_qd4740",
        source_table_citation="ocr_qd4740:ev_p002_b001",
        title="Bộ chỉ số CĐS",
    )

    assert projected.has_header is True
    assert len(projected.facts) == 1
    fact = projected.facts[0]

    # Must be selected from Tiêu chí, truncated cleanly with '...'
    assert fact.subject_name is not None
    assert fact.subject_name.startswith("Có triển khai hệ thống quản lý học tập trực tuyến (LMS)")
    assert fact.subject_name.endswith("...")
    assert len(fact.subject_name) <= 120

    # Must NOT be selected from Điểm thành phần
    assert "Tối đa 16 điểm" not in fact.subject_name

    # Full text remains in attributes['Tiêu chí']
    assert fact.attributes["Tiêu chí"].raw.startswith("Có triển khai hệ thống quản lý")


def test_multi_year_horizontal_table_projection():
    """Verify table with horizontal multi-year columns (2024 & 2025) preserves year prefixes

    and records data_years = [2024, 2025] in table and fact metadata.
    """
    table = {
        "row_count": 2,
        "column_count": 7,
        "rows": [
            [
                _cell("STT", header=True, evidence_id="h0"),
                _cell("Mã ngành", header=True, evidence_id="h1"),
                _cell("Tên ngành", header=True, evidence_id="h2"),
                _cell("2024 > Chỉ tiêu", header=True, evidence_id="h3"),
                _cell("2024 > Điểm trúng tuyển", header=True, evidence_id="h4"),
                _cell("2025 > Chỉ tiêu", header=True, evidence_id="h5"),
                _cell("2025 > Điểm trúng tuyển", header=True, evidence_id="h6"),
            ],
            [
                _cell("16", evidence_id="r1_0"),
                _cell("7140249", evidence_id="r1_1"),
                _cell("Sư phạm Lịch sử Địa lý", evidence_id="r1_2"),
                _cell("27", evidence_id="r1_3"),
                _cell("27.15", evidence_id="r1_4"),
                _cell("112", evidence_id="r1_5"),
                _cell("26.4", evidence_id="r1_6"),
            ],
        ],
    }

    projected = project_table(
        table,
        table_id="tbl_ts2026",
        source_table_citation="ocr_ts:ev_p011_b014",
        title="Thông tin tuyển sinh 2 năm gần nhất",
    )

    assert projected.data_years == [2024, 2025]
    assert len(projected.facts) == 1
    fact = projected.facts[0]

    assert fact.subject_code == "7140249"
    assert fact.subject_name == "Sư phạm Lịch sử Địa lý"
    assert fact.data_years == [2024, 2025]
    assert fact.data_year is None

    # Attribute keys keep full hierarchical year prefix
    assert fact.attributes["2024 > Chỉ tiêu"].raw == "27"
    assert fact.attributes["2024 > Điểm trúng tuyển"].raw == "27.15"
    assert fact.attributes["2025 > Chỉ tiêu"].raw == "112"
    assert fact.attributes["2025 > Điểm trúng tuyển"].raw == "26.4"

    # RowCard projection check
    doc_meta = DocumentCardMeta(title="Thông tin Tuyển sinh 2026", doc_year=2026)
    cards = render_projection_to_cards(projected, document_meta=doc_meta)
    assert len(cards) == 1
    card = cards[0]
    assert card.data_years == [2024, 2025]
    assert "Dữ liệu năm: 2024, 2025" in card.text
    assert "2024 > Chỉ tiêu: 27" in card.text
    assert "2025 > Điểm trúng tuyển: 26.4" in card.text


# ==============================================================================
# NHÓM 2: Phân biệt các lớp năm (issued_year vs applicable_years vs data_years)
# ==============================================================================


def test_issued_year_ignores_legal_basis_can_cu_and_signature_block():
    """Verify compilation _rules ignores years in 'Căn cứ...' lines and signature blocks."""
    # 1. Legal basis referencing older decrees
    quote_legal = (
        "Căn cứ Luật Giáo dục đại học số 08/2012/QH13; "
        "Căn cứ Nghị định số 99/2019/NĐ-CP ngày 30 tháng 12 năm 2019 của Chính phủ; "
        "Căn cứ Quyết định số 4740/QĐ-BGDĐT ngày 30 tháng 12 năm 2022 của Bộ GD&ĐT."
    )
    candidates_legal = _rules("ev_p001_b002", quote_legal, boundary=True)
    issued_legal = [c.value for c in candidates_legal if c.field == "issued_year"]
    assert issued_legal == [], "Legal basis must not yield issued_year"

    # 2. Signature block at document end
    quote_sig = (
        "Nơi nhận: Như Điều 3; Lưu: VT, ĐBCL. "
        "KT. BỘ TRƯỞNG - THỨ TRƯỞNG "
        "Hoàng Minh Sơn, ký ngày 30 tháng 12 năm 2022"
    )
    candidates_sig = _rules("ev_p010_b099", quote_sig, boundary=True)
    issued_sig = [c.value for c in candidates_sig if c.field == "issued_year"]
    assert issued_sig == [], "Signature block must not yield document issued_year"

    # 3. Genuine document header date line
    quote_valid = "Hà Nội, ngày 15 tháng 01 năm 2026"
    candidates_valid = _rules("ev_p001_b001", quote_valid, boundary=True)
    issued_valid = [c.value for c in candidates_valid if c.field == "issued_year"]
    assert 2026 in issued_valid


# ==============================================================================
# NHÓM 3: Chống nhiễu liên tài liệu và tách bạch nguồn
# ==============================================================================


def test_exact_anchors_and_lexical_expression_preserve_codes_and_phrases():
    """Verify phrase matching and exact code preservation for cross-doc disambiguation."""
    # Anchors preserve codes and IDs
    anchors = exact_anchors("Phương thức tuyển sinh mã 7140249 và mã 0012")
    assert "7140249" in anchors
    assert "0012" in anchors

    # Lexical expression generates bigram phrases
    expr = lexical_expression("phương thức tuyển sinh", phrases=True)
    assert '"phương thức"' in expr or '"phương thức tuyển"' in expr or '"tuyển sinh"' in expr


def test_drafting_prompt_contains_multi_source_separation_directive():
    """Verify SYSTEM_PROMPT contains the explicit instruction for separating multiple sources

    when the user query is ambiguous or uses generic terminology.
    """
    assert "TÁCH BẠCH NGUỒN KHI CÂU HỎI MƠ HỒ" in SYSTEM_PROMPT
    assert "BẮT BUỘC trình bày tách bạch rõ từng văn bản nguồn" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG trộn lẫn nội dung giữa các văn bản" in SYSTEM_PROMPT
