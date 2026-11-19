"""Unit tests for DN-02 (Answer parsing, self-healing & repair instructions) and DN-03 (Multi-turn conversion & context preservation)."""

from __future__ import annotations

from unittest.mock import MagicMock

from qnu.domains.rag.answer.drafting import (
    REPAIR_INSTRUCTIONS,
    _extract_json_text,
    parse_answer,
)
from qnu.domains.rag.answer.rewriter import rewrite_contextual_query
from qnu.domains.rag.answer.schemas import EvidenceSource


def _dummy_source(evidence_id: str) -> EvidenceSource:
    source = MagicMock(spec=EvidenceSource)
    source.evidence_id = evidence_id
    return source


# ---------------------------------------------------------------------------
# DN-02 Tests: drafting.py, JSON normalization, bracket citations, self-healing
# ---------------------------------------------------------------------------


def test_dn02_extract_json_text_removes_code_fences_and_outer_prose():
    raw_markdown = """```json
{
  "status": "answered",
  "statements": [{"text": "Dữ liệu mẫu", "evidence_ids": ["E1"]}],
  "lookups": [],
  "assessment": [],
  "message": null
}
```"""
    cleaned = _extract_json_text(raw_markdown)
    assert cleaned.startswith("{")
    assert cleaned.endswith("}")
    assert "```" not in cleaned

    outer_prose = """Dưới đây là kết quả:
{
  "status": "answered",
  "statements": [{"text": "Dữ liệu mẫu", "evidence_ids": ["E1"]}],
  "lookups": [],
  "assessment": [],
  "message": null
}
Hy vọng giúp ích cho bạn."""
    cleaned_prose = _extract_json_text(outer_prose)
    assert cleaned_prose.startswith("{")
    assert cleaned_prose.endswith("}")


def test_dn02_parse_answer_strips_inline_bracket_citations():
    sources = [_dummy_source("E1"), _dummy_source("E2")]
    content = """<phan_tich>
Bước 1: Quy định gốc...
</phan_tich>
```json
{
  "status": "answered",
  "statements": [
    {
      "text": "Chứng chỉ VSTEP Bậc 5 được quy đổi thành 10.0 điểm môn Tiếng Anh [E1] và áp dụng cho PT2 [E2].",
      "evidence_ids": ["E1"]
    }
  ],
  "lookups": [],
  "assessment": [{"label": "Quy đổi", "status": "covered", "evidence_ids": ["E1", "E2"]}],
  "message": null
}
```"""
    model_answer = parse_answer(content, sources)
    stmt = model_answer.statements[0]
    # Inline bracket citations stripped from prose
    assert "[E1]" not in stmt.text
    assert "[E2]" not in stmt.text
    assert "Chứng chỉ VSTEP Bậc 5 được quy đổi thành 10.0 điểm môn Tiếng Anh" in stmt.text
    # Evidence IDs include merged allowed citations
    assert "E1" in stmt.evidence_ids
    assert "E2" in stmt.evidence_ids


def test_dn02_parse_answer_detects_hallucinated_citation_for_repair():
    sources = [_dummy_source("E1")]
    content = """{
  "status": "answered",
  "statements": [
    {
      "text": "Nội dung có căn cứ",
      "evidence_ids": ["E1", "E99"]
    }
  ],
  "lookups": [],
  "assessment": [],
  "message": null
}"""
    import pytest

    from qnu.platform.errors import AppException

    with pytest.raises(AppException) as exc:
        parse_answer(content, sources)
    # Triggers answer_citation_invalid so appeal repair loop can be invoked
    assert exc.value.code == "answer_citation_invalid"
    assert exc.value.code in REPAIR_INSTRUCTIONS


def test_dn02_parse_answer_self_heals_empty_statements_to_insufficient():
    sources = [_dummy_source("E1")]
    content = """{
  "status": "answered",
  "statements": [],
  "lookups": [],
  "assessment": [],
  "message": "Không tìm thấy thông tin phù hợp trong tài liệu."
}"""
    model_answer = parse_answer(content, sources)
    assert model_answer.status == "insufficient_evidence"
    assert model_answer.message == "Không tìm thấy thông tin phù hợp trong tài liệu."


def test_dn02_repair_instructions_include_schema_and_citation_errors():
    assert "answer_response_invalid" in REPAIR_INSTRUCTIONS
    assert "answer_citation_invalid" in REPAIR_INSTRUCTIONS
    assert "JSON" in REPAIR_INSTRUCTIONS["answer_response_invalid"]
    assert "evidence_ids" in REPAIR_INSTRUCTIONS["answer_citation_invalid"]


# ---------------------------------------------------------------------------
# DN-03 Tests: rewriter.py multi-turn conversion scale & context continuity
# ---------------------------------------------------------------------------


def test_dn03_vstep_conversion_scale_continuity_turn2():
    history = [
        {
            "question": "Năm 2026, chứng chỉ VSTEP bậc mấy thì được quy đổi thành điểm 10 môn Tiếng Anh và được áp dụng cho phương thức xét tuyển nào?",
            "answer": "Theo quy định năm 2026, chứng chỉ VSTEP Bậc 5 được quy đổi thành 10.0 điểm môn Tiếng Anh áp dụng cho phương thức xét tuyển sớm (PT2, PT4).",
        }
    ]
    follow_up = "Còn 7.0 và có được dùng cho phương thức xét học bạ không?"

    resolved, trace = rewrite_contextual_query(follow_up, history)
    assert trace["rewritten"] is True
    assert trace["mode"] == "conversion_continuity"
    assert "VSTEP" in resolved
    assert "7.0" in resolved
    assert "học bạ" in resolved
    assert "2026" in resolved


def test_dn03_multiturn_certificate_topic_inheritance_across_3_turns():
    history = [
        {
            "question": "Quy định quy đổi chứng chỉ ngoại ngữ IELTS năm 2026 tại trường như thế nào?",
            "answer": "Trường áp dụng bảng quy đổi điểm chứng chỉ IELTS sang điểm môn Tiếng Anh cho các phương thức xét tuyển.",
        },
        {
            "question": "IELTS 6.5 được bao nhiêu điểm?",
            "answer": "Chứng chỉ IELTS 6.5 được quy đổi thành 9.0 điểm môn Tiếng Anh.",
        },
    ]
    follow_up = "Còn 7.0 và có được dùng cho phương thức xét học bạ không?"

    resolved, trace = rewrite_contextual_query(follow_up, history)
    assert trace["rewritten"] is True
    assert trace["mode"] == "conversion_continuity"
    # Inherits IELTS from earlier turn, not lost at turn 3
    assert "IELTS" in resolved
    assert "7.0" in resolved
    assert "học bạ" in resolved
    assert "2026" in resolved
