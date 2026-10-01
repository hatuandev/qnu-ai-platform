"""Unit tests for Phase 3: Schema Anchor Invariant, CoVe Prompting & Scaffolding Sanitizer."""

from app.modules.rag.composer import (
    SYSTEM_PROMPT_TEMPLATE,
    answer_format_planner,
    sanitize_rag_answer,
)
from app.modules.rag.service import build_generic_system_instruction


def test_sanitize_rag_answer_cleans_internal_scaffolding():
    """Verify sanitize_rag_answer strips raw prompt scaffolding and cleans inline reference tags."""
    raw_text = (
        "Căn cứ vào Bảng Số Liệu [2], Bảng Số Liệu [4] và Bảng Số Liệu [5] để trả lời câu hỏi của người dùng như sau:\n\n"
        "| **Trình độ học vị** | **Giảng viên cơ hữu** | **Giảng viên thỉnh giảng** |\n"
        "| --- | --- | --- |\n"
        "| **Giáo sư, Tiến sĩ** | 2 | 1 |\n"
        "| **Tiến sĩ** | 383 | 33 |\n\n"
        "Lưu ý: Số liệu được tổng hợp từ Bảng Số Liệu [2] và Bảng Số Liệu [4] của trường."
    )
    cleaned = sanitize_rag_answer(raw_text)

    # 1. Leading scaffolding line must be removed
    assert not cleaned.startswith("Căn cứ vào Bảng Số Liệu")
    assert "| **Trình độ học vị** |" in cleaned

    # 2. Raw bracket references like Bảng Số Liệu [2] must be sanitized
    assert "Bảng Số Liệu [2]" not in cleaned
    assert "Bảng Số Liệu [4]" not in cleaned
    assert "Bảng Số Liệu [5]" not in cleaned


def test_schema_anchor_rules_in_system_prompt_and_format_planner():
    """Verify that Schema Anchor & CoVe rules exist in SYSTEM_PROMPT_TEMPLATE and format instructions."""
    # 1. Check SYSTEM_PROMPT_TEMPLATE
    assert "Schema Anchor & Chain-of-Verification" in SYSTEM_PROMPT_TEMPLATE
    assert "Tọa độ Thời gian / Năm áp dụng" in SYSTEM_PROMPT_TEMPLATE
    assert "Tọa độ Cột & Thuộc tính" in SYSTEM_PROMPT_TEMPLATE

    # 2. Check build_generic_system_instruction
    sys_inst = build_generic_system_instruction("admissions", None)
    assert "Schema Anchor & Chain-of-Verification" in sys_inst
    assert "Tọa độ Thời gian" in sys_inst
    assert "Tọa độ Cột & Hàng" in sys_inst

    # 3. Check markdown_table format instructions
    table_inst = answer_format_planner.get_format_instructions("markdown_table")
    assert "ĐỐI SOÁT TỌA ĐỘ BẢNG" in table_inst
    assert "Chỉ tiêu" in table_inst
    assert "Thực hiện" in table_inst
