"""Verify the shadow prefilter never claims more certainty than routing can confirm."""

import pytest

from qnu.domains.conversations.prefilter import (
    VERSION,
    classify_turn,
    compare_route,
)


@pytest.mark.parametrize(
    ("question", "verdict"),
    [
        ("Xin chào", "social"),
        ("Cảm ơn bạn rất nhiều", "social"),
        ("Cảm ơn bạn đã tư vấn", "social"),
        ("Tạm biệt", "social"),
        ("Học phí ngành Công nghệ thông tin là bao nhiêu?", "knowledge"),
        ("Trường có những ngành nào?", "knowledge"),
        ("Thời gian xét tuyển năm 2026 là khi nào?", "knowledge"),
        ("Cho tôi biết quy định về hồ sơ", "knowledge"),
        ("Bạn tên gì?", "ambiguous"),
        ("Học phí", "ambiguous"),
        ("Giúp tôi", "ambiguous"),
        ("Cảm ơn bạn, học phí bao nhiêu?", "knowledge"),
    ],
)
def test_verdicts(question, verdict):
    result = classify_turn(question, has_history=False)
    assert result["version"] == VERSION
    assert result["verdict"] == verdict
    assert result["confidence"] == ("none" if verdict == "ambiguous" else "high")


@pytest.mark.parametrize(
    "question",
    ["Học phí ngành Công nghệ thông tin là bao nhiêu?", "Xin chào", "Bạn tên gì?"],
)
def test_history_always_makes_the_hint_ambiguous(question):
    result = classify_turn(question, has_history=True)
    assert result["verdict"] == "ambiguous"
    assert "history_present" in result["signals"]


@pytest.mark.parametrize(
    ("verdict", "route", "agrees"),
    [
        ("knowledge", "knowledge", True),
        ("knowledge", "greeting", False),
        ("social", "greeting", True),
        ("social", "courtesy", True),
        ("social", "knowledge", False),
        ("ambiguous", "knowledge", None),
        ("ambiguous", "protected_request", None),
    ],
)
def test_compare_route(verdict, route, agrees):
    assert compare_route(verdict, route) is agrees
