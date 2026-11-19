"""Unit tests for Phase 2 Slice 5: Rule Constraints & Negation Cards."""

from __future__ import annotations

from qnu.domains.rag.answer.rule_constraints import (
    RuleConstraints,
    extract_constraints_for_sources,
    extract_rule_constraints_from_text,
    format_rule_constraints,
)
from qnu.domains.rag.answer.schemas import EvidenceSource


def test_rule_constraints_formatting():
    rc = RuleConstraints(
        applies_to="Hồ sơ đánh giá tổng hợp Q",
        preconditions=["Đủ >= 80% chứng cứ bắt buộc", "A, B, C đều có giá trị xác thực"],
        exceptions=["Phụ lục II.2 cho phép biên bản xác minh trực tuyến tạm thời <= 30 ngày với nhóm B"],
        prohibitions=["Không đặt biến thiếu bằng 0", "Không áp dụng ngoại lệ nhóm B cho nhóm A"],
    )
    formatted = format_rule_constraints(rc)
    assert "[RÀNG BUỘC QUY CHẾ]" in formatted
    assert "[/RÀNG BUỘC QUY CHẾ]" in formatted
    assert "Phạm vi áp dụng: Hồ sơ đánh giá tổng hợp Q" in formatted
    assert "Điều kiện bắt buộc: Đủ >= 80% chứng cứ" in formatted
    assert "Ngoại lệ: Phụ lục II.2 cho phép" in formatted
    assert "Điều cấm / Loại trừ: Không đặt biến thiếu bằng 0" in formatted


def test_extract_rule_constraints_from_text():
    text = (
        "Quy chế này áp dụng cho thí sinh đăng ký xét tuyển đại học chính quy năm 2026. "
        "Thí sinh phải có điểm học bạ 3 môn đạt từ 24.0 trở lên và có chứng chỉ tiếng Anh. "
        "Trừ trường hợp thí sinh có giải quốc tế được đặc cách tuyển thẳng. "
        "Tuyệt đối không được sử dụng kết quả thi thử để thay thế và không áp dụng ngoại lệ cho các ngành Sư phạm."
    )
    rc = extract_rule_constraints_from_text(text)
    assert rc is not None
    assert "thí sinh đăng ký xét tuyển đại học chính quy năm 2026" in rc.applies_to
    assert any("phải có điểm học bạ" in p or "đạt từ" in p for p in rc.preconditions)
    assert any("Trừ trường hợp" in e or "được đặc cách" in e for e in rc.exceptions)
    assert any("không được" in pr or "không áp dụng" in pr for pr in rc.prohibitions)


def test_extract_constraints_for_sources_structured_and_unstructured():
    s_structured = EvidenceSource(
        evidence_id="E1",
        chunk_id="ich_1",
        document_id="cdoc_1",
        version_id="cver_1",
        publication_decision_id="pdec_1",
        score=1.0,
        kind="paragraph",
        text="Văn bản quy định đối với sinh viên chính quy.",
        citations={},
        structure={
            "rule_constraints": {
                "applies_to": "Sinh viên khóa 2026",
                "preconditions": ["Điểm rèn luyện tốt"],
                "exceptions": ["Ngoại lệ hoãn xét điểm"],
                "prohibitions": ["Không cho phép nợ học phí"],
            }
        },
    )
    s_unstructured = EvidenceSource(
        evidence_id="E2",
        chunk_id="ich_2",
        document_id="cdoc_2",
        version_id="cver_2",
        publication_decision_id="pdec_2",
        score=1.0,
        kind="paragraph",
        text="Quy định áp dụng cho hồ sơ xét tuyển sớm. Thí sinh phải có điểm thi tốt nghiệp. Trừ trường hợp tuyển thẳng. Nghiêm cấm làm giả giấy tờ.",
        citations={},
        structure={},
    )
    results = extract_constraints_for_sources([s_structured, s_unstructured])
    assert len(results) == 2
    assert results[0]["evidence_id"] == "E1"
    assert results[0]["constraints"]["applies_to"] == "Sinh viên khóa 2026"
    assert results[1]["evidence_id"] == "E2"
    assert "Nghiêm cấm làm giả giấy tờ" in str(results[1]["constraints"]["prohibitions"])
