"""Tests for Suggestion Perspective Enforcement & Multi-turn Entity Hijacking Prevention."""

from __future__ import annotations

import pytest

from app.modules.rag.composer import (
    convert_or_filter_suggestion_perspective,
    extract_suggested_questions,
)
from app.modules.rag.query_router import query_classifier
from app.modules.workflows.nodes.query_rewrite_node import (
    extract_entity_from_text,
    resolve_multiturn_query,
)


def test_convert_or_filter_suggestion_perspective_inverted_general():
    """Verify that inverted question with indefinite major converts to general user question."""
    cand = "Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"
    res = convert_or_filter_suggestion_perspective(cand)
    assert res == "Các ngành của trường xét tuyển những tổ hợp môn nào?"


def test_convert_or_filter_suggestion_perspective_specific_major():
    """Verify that inverted question with specific major extracts the major name properly."""
    cand = "Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành Công nghệ thông tin không?"
    res = convert_or_filter_suggestion_perspective(cand)
    assert res == "Tổ hợp môn xét tuyển của ngành Công Nghệ Thông Tin gồm những môn nào?"


def test_convert_or_filter_suggestion_perspective_tuition_and_scholarship():
    """Verify tuition and scholarship inverted questions convert to direct queries."""
    tuition = "Bạn có quan tâm đến học phí năm 2026 của trường không?"
    assert (
        convert_or_filter_suggestion_perspective(tuition)
        == "Mức học phí năm 2026 của trường là bao nhiêu?"
    )

    scholarship = "Bạn có muốn tìm hiểu thêm về chính sách học bổng không?"
    assert (
        convert_or_filter_suggestion_perspective(scholarship)
        == "Chính sách học bổng của trường như thế nào?"
    )


def test_convert_or_filter_suggestion_perspective_polite_junk_filtered():
    """Verify unconvertible conversational polite junk is filtered out (returns None)."""
    junk = "Bạn có muốn mình chia sẻ gì thêm không?"
    assert convert_or_filter_suggestion_perspective(junk) is None

    polite = "Nếu bạn muốn tìm hiểu thì cứ hỏi mình nhé!"
    assert convert_or_filter_suggestion_perspective(polite) is None


def test_convert_or_filter_suggestion_perspective_preserves_valid_user_queries():
    """Verify that normal questions written from user perspective are preserved intact."""
    valid_1 = "Tổ hợp môn xét tuyển ngành Công nghệ thông tin gồm những môn nào?"
    assert convert_or_filter_suggestion_perspective(valid_1) == valid_1

    valid_2 = "Chỉ tiêu tuyển sinh năm 2026 của trường là bao nhiêu?"
    assert convert_or_filter_suggestion_perspective(valid_2) == valid_2


def test_extract_suggested_questions_cleans_inverted_perspective_in_block():
    """Verify extract_suggested_questions sanitizes inverted suggestions from explicit block."""
    raw = (
        "Chào bạn, năm 2026 Trường Đại học Quy Nhơn áp dụng các phương thức tuyển sinh chính như sau:\n"
        "| Phương thức 1 | 100 | Xét tuyển kết quả thi THPT |\n\n"
        "[GỢI Ý]:\n"
        '- "Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"\n'
        '- "Chỉ tiêu tuyển sinh năm 2026 của trường là bao nhiêu?"'
    )
    body, sugs = extract_suggested_questions(raw)
    assert "[GỢI Ý]" not in body
    assert "Phương thức 1" in body
    assert len(sugs) == 2
    assert sugs[0] == "Các ngành của trường xét tuyển những tổ hợp môn nào?"
    assert sugs[1] == "Chỉ tiêu tuyển sinh năm 2026 của trường là bao nhiêu?"
    # Ensure zero occurrences of "Bạn có muốn" in suggestions
    assert not any("Bạn có muốn" in s for s in sugs)


def test_query_router_excludes_placeholder_words_from_target_entities():
    """Indefinite terms like 'cụ thể nào', 'nào đó' must never become target_entities."""
    query = "Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"
    analysis = query_classifier.analyze(query)
    assert "Cụ Thể Nào" not in analysis.target_entities
    assert "Cụ Thể" not in analysis.target_entities
    assert len(analysis.target_entities) == 0


def test_extract_entity_from_text_excludes_placeholder_words():
    """Indefinite placeholder phrases must not be extracted as major entities."""
    text = "Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"
    entity = extract_entity_from_text(text)
    assert entity is None

    # Real major must still be extracted
    real_text = "ngành Công nghệ thông tin cần những môn học nào để xét tuyển"
    real_entity = extract_entity_from_text(real_text)
    assert real_entity is not None
    assert "Công nghệ thông tin" in real_entity


def test_resolve_multiturn_query_does_not_hijack_unrelated_history():
    """Verify that a general question does not inherit unrelated entities from prior turns."""
    history = [
        {"role": "user", "content": "xin chào cho tôi biết phương thức tuyển sinh năm 2026"},
        {
            "role": "assistant",
            "content": "Chào bạn, năm 2026 trường áp dụng các phương thức tuyển sinh chính như sau...",
        },
    ]
    query = "Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"
    resolved = resolve_multiturn_query(query, history)
    # Since neither history turn has a specific major, resolved must be None (not forced)
    assert resolved is None


def test_count_subject_matches_does_not_blend_different_combos():
    """Verify that multiple subjects must match within the SAME combination."""
    from app.modules.rag.facts import count_subject_matches

    # Major with (Toán, Văn, Anh) and (Văn, Anh, Hóa) does NOT have (Toán, Anh, Hóa)
    mixed_value = "(Toán, Văn, Anh), (Văn, Anh, Hóa), (Văn, Sử, Địa)"
    queried = ["toán", "hóa", "tiếng anh"]

    # Each single combo has at most 2 matches (Toán+Anh in combo 1, Anh+Hóa in combo 2)
    assert count_subject_matches(mixed_value, queried) == 2

    # Major with true (Toán, Anh, Hóa) has 3 matches
    full_value = "(Toán, Lý, Hóa), (Toán, Anh, Hóa), (Toán, Văn, Anh)"
    assert count_subject_matches(full_value, queried) == 3


def test_extract_suggested_questions_filters_echo_of_current_query():
    """Verify that a suggestion echoing the user's current question is filtered out."""
    current_q = "Phương thức xét tuyển học bạ của trường áp dụng cho những ngành nào?"
    raw = (
        "Phương thức xét tuyển học bạ 3 năm THPT áp dụng cho tất cả các ngành đại trà chính quy, "
        "ngoại trừ khối ngành Sư phạm.\n\n"
        "[GỢI Ý]:\n"
        '- "Phương thức xét tuyển học bạ áp dụng cho những ngành nào?"\n'
        '- "Hồ sơ xét tuyển học bạ năm 2026 cần những giấy tờ gì?"'
    )
    _body, sugs = extract_suggested_questions(raw, current_query=current_q)
    assert len(sugs) == 1
    assert sugs[0] == "Hồ sơ xét tuyển học bạ năm 2026 cần những giấy tờ gì?"
    assert "Phương thức xét tuyển học bạ áp dụng cho những ngành nào?" not in sugs


def test_extract_suggested_questions_and_sanitize_strips_giz_artifacts():
    """Verify that broken header artifacts like [GIZ]: or [GỢI Ý]: are stripped from text."""
    from app.modules.rag.composer import sanitize_rag_answer

    raw_with_giz = (
        "Ngoài ra, trường còn thực hiện Xét tuyển thẳng và ưu tiên xét tuyển theo Quy chế.\n\n"
        "[GIZ]:\n"
        "[GỢI Ý]:\n"
        '- "Phương thức 1 xét tuyển theo kết quả thi THPT hoạt động thế nào?"\n'
        '- "Hồ sơ xét tuyển học bạ gồm những giấy tờ gì?"'
    )
    body, sugs = extract_suggested_questions(raw_with_giz)
    assert "[GIZ]" not in body
    assert "[GỢI Ý]" not in body
    sanitized = sanitize_rag_answer(body)
    assert "[GIZ]" not in sanitized
    assert "[GỢI Ý]" not in sanitized
    assert len(sugs) == 2


@pytest.mark.asyncio
async def test_lookup_facts_excludes_major_specific_facts_on_general_queries():
    """When no entity is queried, major-specific facts must not hijack the question."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from app.modules.rag.facts import fact_layer

    major_fact = SimpleNamespace(
        entity_name="Công nghệ thông tin (mã ngành: 7480201)",
        attribute_name="Phương thức xét tuyển 2026",
        attribute_value="Phương thức 1, 2, 3, 4",
    )
    general_fact = SimpleNamespace(
        entity_name="Trường Đại học Quy Nhơn",
        attribute_name="Phương thức xét tuyển 2026",
        attribute_value="Gồm 5 phương thức tuyển sinh chính thức",
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [major_fact, general_fact]
    mock_db.execute.return_value = mock_res

    # Query without entity_codes or subject_names
    rows = await fact_layer.lookup_facts(
        mock_db,
        "col_admissions",
        keywords=["phương thức", "tuyển sinh"],
        limit=5,
    )
    # Only the general fact survives; major-specific CNTT fact is excluded
    assert len(rows) == 1
    assert rows[0].entity_name == "Trường Đại học Quy Nhơn"


def test_count_subject_matches_semicolon_delimited():
    """Verify that combos without parentheses delimited by semicolons are evaluated independently."""
    from app.modules.rag.facts import count_subject_matches

    # Combo 1: Toán, Văn, Anh; Combo 2: Văn, Anh, Hóa
    val = "Toán - Văn - Tiếng Anh; Ngữ văn - Tiếng Anh - Hóa học"
    # User queries: Toán, Tiếng Anh, Hóa học
    score = count_subject_matches(val, ["toán", "tiếng anh", "hóa học"])
    # Max in combo 1 is 2 (Toán, Anh), max in combo 2 is 2 (Anh, Hóa) -> score must be 2, NOT 3!
    assert score == 2


def test_extract_suggested_questions_cleans_bold_giz_tag():
    """Verify that bold bracket tags like **[GIZ]:** or **[GỢI Ý]** are stripped without leaking into UI."""
    from app.modules.rag.composer import extract_suggested_questions

    raw = "Chào bạn! Đây là nội dung tư vấn.\n\n**[GIZ]:**"
    body, sugs = extract_suggested_questions(raw)
    assert body == "Chào bạn! Đây là nội dung tư vấn."
    assert sugs == []


@pytest.mark.asyncio
async def test_lookup_facts_keeps_major_facts_when_target_entities_present():
    """When target_entities specifically names a major, its facts must be returned."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from app.modules.rag.facts import fact_layer

    major_fact = SimpleNamespace(
        entity_name="Công nghệ thông tin",
        entity_type="admissions_major",
        attribute_name="Phương thức xét tuyển 2026",
        attribute_value="Phương thức 1, 2, 3, 4",
        raw_data={"major_code": "7480201"},
    )
    other_major_fact = SimpleNamespace(
        entity_name="Sư phạm Toán học",
        entity_type="admissions_major",
        attribute_name="Phương thức xét tuyển 2026",
        attribute_value="Phương thức 1, 2",
        raw_data={"major_code": "7140209"},
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [major_fact, other_major_fact]
    mock_db.execute.return_value = mock_res

    rows = await fact_layer.lookup_facts(
        mock_db,
        "col_admissions",
        keywords=["phương thức", "tuyển sinh"],
        target_entities=["Công nghệ thông tin"],
        limit=5,
    )
    # Major fact for CNTT is retained; Sư phạm Toán is filtered out
    assert len(rows) == 1
    assert rows[0].entity_name == "Công nghệ thông tin"

