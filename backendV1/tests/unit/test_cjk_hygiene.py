"""Unit tests for CJK (Chinese character) hygiene and sanitizer."""

import pytest

from qnu.domains.conversations.routing import messages_for
from qnu.domains.rag.answer.hygiene import (
    clean_model_answer,
    clean_text,
    has_cjk,
    looks_foreign,
    sanitize_cjk,
)
from qnu.domains.rag.answer.schemas import ModelAnswer, Statement


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Xin chào bạn, mình là Trợ lý Tuyển sinh QNU.", False),
        ("Dạ không có chi, chúc bạn một ngày tốt lành!", False),
        ("Toán, Lý, Hóa (khối A00)", False),
        ("Hồ sơ xét tuyển năm 2026: 12345 đợt 1.", False),
        ("Dạ bạn không cần客气", True),
        ("不用谢", True),
        ("好的", True),
        ("谢谢 bạn nhé", True),
        ("Tiếng Việt xen chữ 汉字", True),
    ],
)
def test_has_cjk(text: str, expected: bool):
    assert has_cjk(text) is expected


@pytest.mark.parametrize(
    ("input_text", "expected_output", "expected_cjk_found"),
    [
        (
            "Dạ bạn không cần客气, mình luôn sẵn sàng hỗ trợ bạn.",
            "Dạ bạn không cần khách sáo, mình luôn sẵn sàng hỗ trợ bạn.",
            True,
        ),
        (
            "Dạ bạn không cần 客气, mình luôn sẵn sàng hỗ trợ bạn.",
            "Dạ bạn không cần khách sáo, mình luôn sẵn sàng hỗ trợ bạn.",
            True,
        ),
        (
            "不用谢！Chúc bạn đạt kết quả tốt.",
            "không có chi! Chúc bạn đạt kết quả tốt.",
            True,
        ),
        (
            "不用客气，mình luôn ở đây.",
            "không có chi, mình luôn ở đây.",
            True,
        ),
        (
            "好的, mình đã ghi nhận thông tin của bạn.",
            "dạ vâng, mình đã ghi nhận thông tin của bạn.",
            True,
        ),
        (
            "Dạ vâng, không có gì đâu bạn nhé!",
            "Dạ vâng, không có gì đâu bạn nhé!",
            False,
        ),
        (
            "Chúc bạn thuận lợi trong kỳ thi tuyển sinh năm 2026!",
            "Chúc bạn thuận lợi trong kỳ thi tuyển sinh năm 2026!",
            False,
        ),
    ],
)
def test_sanitize_cjk(input_text: str, expected_output: str, expected_cjk_found: bool):
    output, cjk_found = sanitize_cjk(input_text)
    assert output == expected_output
    assert cjk_found is expected_cjk_found
    assert not has_cjk(output)


def test_sanitize_cjk_strips_residual_cjk_characters():
    text = "Dạ thông tin này 测试 là chính xác."
    cleaned, cjk_found = sanitize_cjk(text)
    assert cjk_found is True
    assert not has_cjk(cleaned)
    assert cleaned == "Dạ thông tin này là chính xác."


def test_looks_foreign_flags_cjk():
    assert looks_foreign("Dạ bạn không cần客气 nhé.") is True
    assert looks_foreign("Xin chào bạn, mình có thể giúp gì cho bạn?") is False


def test_clean_text_cleans_cjk_and_reports_flag():
    dirty = "Dạ bạn không cần客气, chúc bạn thành công!"
    cleaned, flags = clean_text(dirty)
    assert cleaned == "Dạ bạn không cần khách sáo, chúc bạn thành công!"
    assert flags["cjk_removed"] is True
    assert flags["reasoning_removed"] is False

    clean = "Dạ không có chi, chúc bạn thành công!"
    cleaned2, flags2 = clean_text(clean)
    assert cleaned2 == clean
    assert flags2["cjk_removed"] is False


def test_clean_model_answer_cleans_cjk_and_reports_count():
    answer = ModelAnswer(
        status="answered",
        statements=[
            Statement(text="Dạ bạn không cần客气.", evidence_ids=["E1"]),
            Statement(text="Trường tuyển sinh 55 ngành năm 2026.", evidence_ids=["E2"]),
        ],
        message="谢谢!",
        lookups=[],
        assessment=[],
    )
    cleaned_answer, report = clean_model_answer(answer, "ok em cảm ơn")
    assert cleaned_answer.statements[0].text == "Dạ bạn không cần khách sáo."
    assert cleaned_answer.statements[1].text == "Trường tuyển sinh 55 ngành năm 2026."
    assert cleaned_answer.message == "cảm ơn bạn!"
    assert report["cjk_removed"] == 2
    assert not has_cjk(cleaned_answer.statements[0].text)
    assert not has_cjk(cleaned_answer.message)


def test_routing_system_prompt_demands_pure_vietnamese():
    messages = messages_for(
        "ok em cảm ơn",
        [],
        [],
        {"name": "Tuyển sinh", "persona": "Trợ lý thân thiện."},
    )
    system_content = messages[0].content
    assert "NGÔN NGỮ PHẢN HỒI" in system_content
    assert "100% tiếng Việt" in system_content
    assert "TUYỆT ĐỐI KHÔNG dùng từ ngữ, cụm từ hoặc ký tự tiếng Trung" in system_content
    assert "courtesy" in system_content
