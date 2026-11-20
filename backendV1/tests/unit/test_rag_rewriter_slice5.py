"""Unit tests for Phase 2 Slice 5: Multi-turn Contextual Query Rewriter."""

from __future__ import annotations

from qnu.domains.rag.answer.rewriter import rewrite_contextual_query


def test_rewrite_single_turn_or_empty_history():
    q = "Ngành Công nghệ thông tin học phí bao nhiêu?"
    # No history
    res, trace = rewrite_contextual_query(q, None)
    assert res == q
    assert not trace["rewritten"]
    assert trace["reason"] == "insufficient_history"

    # History < 2 turns
    res2, trace2 = rewrite_contextual_query(q, [{"question": "Chào bạn", "answer": "Chào bạn!"}])
    assert res2 == q
    assert not trace2["rewritten"]
    assert trace2["reason"] == "insufficient_history"


def test_rewrite_clarification_response():
    history = [
        {"question": "Xin chào", "answer": "Chào bạn! Tôi có thể giúp gì cho bạn?"},
        {
            "question": "Điều kiện xét tuyển và chỉ tiêu như thế nào?",
            "answer": "Bạn muốn hỏi về ngành nào và năm nào?",
        },
    ]
    user_reply = "Ngành CNTT năm 2026 ạ"
    resolved, trace = rewrite_contextual_query(user_reply, history)

    assert trace["rewritten"] is True
    assert trace["mode"] == "clarification_synthesis"
    assert "Điều kiện xét tuyển và chỉ tiêu" in resolved
    assert "CNTT" in resolved
    assert "2026" in resolved


def test_rewrite_anaphora_replacement():
    history = [
        {"question": "Xin chào", "answer": "Chào bạn!"},
        {
            "question": "Điểm chuẩn ngành Công nghệ thông tin năm 2026 là bao nhiêu?",
            "answer": "Điểm chuẩn ngành Công nghệ thông tin năm 2026 là 25.5 điểm.",
        },
    ]
    follow_up = "Thế còn học phí ngành đó như thế nào?"
    resolved, trace = rewrite_contextual_query(follow_up, history)

    assert trace["rewritten"] is True
    assert trace["mode"] == "anaphora_substitution"
    assert "ngành đó" not in resolved
    assert "Công nghệ thông tin" in resolved


def test_rewrite_preserves_identifiers_and_zero_prefixes():
    history = [
        {"question": "Xin chào", "answer": "Chào bạn!"},
        {
            "question": "Thí sinh có mã hồ sơ 0012 và mã ngành 7480201 có được xét tuyển không?",
            "answer": "Bạn muốn hỏi về phương thức nào hay năm nào?",
        },
    ]
    follow_up = "Phương thức xét học bạ năm 2026"
    resolved, trace = rewrite_contextual_query(follow_up, history)

    assert trace["rewritten"] is True
    assert "0012" in trace["preserved_codes"]
    assert "7480201" in trace["preserved_codes"]
    assert "0012" in resolved
    assert "7480201" in resolved


def test_rewrite_no_hallucination_of_unmentioned_facts():
    history = [
        {"question": "Xin chào", "answer": "Chào bạn!"},
        {
            "question": "Quy định về học bổng khuyến khích học tập",
            "answer": "Bạn muốn hỏi điều kiện xét học bổng loại nào?",
        },
    ]
    follow_up = "Loại xuất sắc"
    resolved, trace = rewrite_contextual_query(follow_up, history)

    assert trace["rewritten"] is True
    assert "học bổng khuyến khích học tập" in resolved
    assert "Loại xuất sắc" in resolved
    # Verify no external unmentioned school/year was invented
    assert "Đại học Bách Khoa" not in resolved
    assert "2024" not in resolved


def test_rewrite_task_codes_and_anaphoric_noun_phrases():
    # Test case matching C9_T1 -> C9_T2 on complex task documents
    history = [
        {
            "question": "Nhiệm vụ NV-30 đối soát những gì và có điều kiện gì?",
            "answer": "NV-30 có nhiệm vụ đối soát nhật ký ngoại lệ liên nguồn với 7 thành phần...",
        }
    ]
    follow_up = "Phần thứ tư và phần thứ sáu của hồ sơ nghiệm thu này quy định gì, có áp dụng cho nhóm I không?"
    resolved, trace = rewrite_contextual_query(follow_up, history)

    assert trace["rewritten"] is True
    assert trace["mode"] == "anaphora_substitution"
    assert "hồ sơ nghiệm thu NV-30" in resolved
    assert "NV-30" in trace["preserved_codes"]

    # Test short codes like NV-01, CT-06
    history2 = [
        {
            "question": "Mã trạng thái CT-06 có ý nghĩa gì?",
            "answer": "CT-06 đang ở trạng thái chờ quy ước.",
        }
    ]
    follow_up2 = "Nhiệm vụ này ai chịu trách nhiệm?"
    resolved2, trace2 = rewrite_contextual_query(follow_up2, history2)
    assert trace2["rewritten"] is True
    assert "CT-06" in resolved2


def test_rewrite_distinct_identifier_switch_no_entity_conflict():
    # Ca biên 2: When follow-up introduces a new criterion/code, avoid prepending previous turn entity
    history = [
        {
            "question": "Tiêu chí phát triển nguồn nhân lực chuyển đổi số (1.7) tính điểm và mức độ thế nào theo Quyết định 4740?",
            "answer": "Tiêu chí 1.7 có điểm tối đa là 10 điểm, gồm mức bắt buộc 5 điểm và nâng cao 5 điểm...",
        }
    ]
    follow_up = "Còn hệ thống hỗ trợ đào tạo trực tuyến (1.8) thì sao?"
    resolved, trace = rewrite_contextual_query(follow_up, history)

    assert trace["rewritten"] is True
    assert "1.8" in resolved
    # Must NOT contain the old criterion 1.7 or its previous entity name
    assert "1.7" not in resolved
    assert "nguồn nhân lực" not in resolved
    # Must preserve the topic/predicate and doc reference
    assert "tính điểm và mức độ" in resolved
    assert "4740" in resolved

    # Test code identifier switch: AM-0007 -> AM-0070
    history2 = [
        {
            "question": "Chương trình mã AM-0007 có điều kiện gì?",
            "answer": "AM-0007 yêu cầu đối chiếu chứng cứ thực hành...",
        }
    ]
    follow_up2 = "Còn AM-0070 thì sao?"
    resolved2, trace2 = rewrite_contextual_query(follow_up2, history2)
    assert trace2["rewritten"] is True
    assert "AM-0070" in resolved2
    assert "AM-0007" not in resolved2
    assert "AM-0007" not in trace2["preserved_codes"]


def test_rewrite_cross_turn_comparison():
    # Multi-turn sequence: Turn 1 (Criteria 1.7) -> Turn 2 (Criteria 1.8) -> Turn 3 (Comparison)
    history = [
        {
            "question": "Tiêu chí phát triển nguồn nhân lực chuyển đổi số (1.7) tính điểm và mức độ thế nào theo Quyết định 4740?",
            "answer": "Tiêu chí 1.7 có điểm tối đa là 10 điểm...",
        },
        {
            "question": "Còn hệ thống hỗ trợ đào tạo trực tuyến (1.8) thì sao?",
            "answer": "Tiêu chí 1.8 quy định mức tối đa 10 điểm...",
        },
    ]
    follow_up = "Tóm lại so với mục trước thì thế nào?"
    resolved, trace = rewrite_contextual_query(follow_up, history)

    assert trace["rewritten"] is True
    assert trace["mode"] == "cross_turn_comparison"
    assert "So sánh" in resolved
    assert "1.8" in resolved
    assert "1.7" in resolved
    assert "4740" in resolved


def test_rewrite_new_property_of_same_task():
    # Multi-turn: Turn 1 asks time of task -> Turn 2 asks responsible/coordinating unit
    history = [
        {
            "question": "Thời gian thực hiện nhiệm vụ 2 trong Kế hoạch 130/KH-ĐHQN là khi nào?",
            "answer": "Nhiệm vụ 2 được thực hiện từ tháng 01/2026 đến tháng 03/2026.",
        }
    ]
    follow_up = "Thế còn đơn vị nào chủ trì và phối hợp?"
    resolved, trace = rewrite_contextual_query(follow_up, history)

    assert trace["rewritten"] is True
    assert trace["mode"] == "property_followup"
    assert "đơn vị nào chủ trì và phối hợp" in resolved
    assert "Nhiệm vụ 2" in resolved
    assert "130/KH-ĐHQN" in resolved
    # Must NOT conflate with previous predicate "Thời gian thực hiện"
    assert "Thời gian thực hiện" not in resolved


def test_rewrite_anaphoric_clause_and_milestone():
    history = [
        {
            "question": "Kế hoạch 130/KH-ĐHQN quy định mốc thời gian hoàn thành tự đánh giá SAR là khi nào?",
            "answer": "Mốc hoàn thành báo cáo SAR là trước ngày 15/04/2026.",
        }
    ]
    follow_up = "Nếu xét theo mốc đó thì hồ sơ minh chứng cần gửi khi nào?"
    resolved, trace = rewrite_contextual_query(follow_up, history)

    assert trace["rewritten"] is True
    assert "130/KH-ĐHQN" in resolved
    assert "hồ sơ minh chứng" in resolved
