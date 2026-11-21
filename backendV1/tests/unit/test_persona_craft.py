"""Unit tests for AI Persona crafting schemas and parser."""

import pytest
from pydantic import ValidationError

from qnu.domains.assistants.schemas import PersonaCraftRequest, PersonaCraftResponse
from qnu.domains.assistants.service import _parse_persona_craft_json
from qnu.platform.errors import AppException


def test_parse_persona_craft_json_clean():
    payload = {
        "name": "Trợ lý Tuyển sinh QNU 2026",
        "description": "Hỗ trợ thí sinh tra cứu thông tin tuyển sinh.",
        "persona": "Bạn là Trợ lý Tuyển sinh Trường Đại học Quy Nhơn...",
        "suggested_prompts": ["Điểm chuẩn 2025 là bao nhiêu?"],
    }
    raw = '{"name": "Trợ lý Tuyển sinh QNU 2026", "description": "Hỗ trợ thí sinh tra cứu thông tin tuyển sinh.", "persona": "Bạn là Trợ lý Tuyển sinh Trường Đại học Quy Nhơn...", "suggested_prompts": ["Điểm chuẩn 2025 là bao nhiêu?"]}'
    res = _parse_persona_craft_json(raw)
    assert res == payload


def test_parse_persona_craft_json_markdown_fence():
    raw = """```json
{
  "name": "Trợ lý Tuyển sinh QNU",
  "description": "Tư vấn tuyển sinh",
  "persona": "Persona content",
  "suggested_prompts": ["Câu 1", "Câu 2"]
}
```"""
    res = _parse_persona_craft_json(raw)
    assert res["name"] == "Trợ lý Tuyển sinh QNU"
    assert len(res["suggested_prompts"]) == 2


def test_parse_persona_craft_json_embedded_in_text():
    raw = """Dưới đây là kết quả cấu hình trợ lý được tạo:
{
  "name": "Trợ lý Khảo thí",
  "description": "Hỗ trợ khảo thí",
  "persona": "Persona",
  "suggested_prompts": ["Lịch thi?"]
}
Hy vọng giúp ích cho bạn!"""
    res = _parse_persona_craft_json(raw)
    assert res["name"] == "Trợ lý Khảo thí"
    assert res["suggested_prompts"] == ["Lịch thi?"]


def test_parse_persona_craft_json_invalid():
    with pytest.raises(AppException) as exc_info:
        _parse_persona_craft_json("Đây không phải là JSON nào cả.")
    assert exc_info.value.code == "persona_craft_invalid"


def test_persona_craft_request_validation():
    req = PersonaCraftRequest(
        topic="Tuyển sinh đại học 2026",
        target_audience="Thí sinh",
        tone="Thân thiện",
    )
    assert req.topic == "Tuyển sinh đại học 2026"
    assert req.name is None

    with pytest.raises(ValidationError):
        PersonaCraftRequest(topic="a")  # min_length is 2


def test_persona_craft_response_model():
    resp = PersonaCraftResponse(
        name="Trợ lý QNU",
        description="Mô tả",
        persona="Chỉ dẫn",
        suggested_prompts=["Q1", "Q2"],
    )
    assert resp.name == "Trợ lý QNU"
    assert len(resp.suggested_prompts) == 2
