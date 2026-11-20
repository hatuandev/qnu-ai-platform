"""Unit tests for Safe Conversational Memory."""

from __future__ import annotations

from qnu.domains.conversations.memory import extract_safe_conversation_memory


def test_extract_memory_from_answered_turns():
    turns = [
        {
            "turn_no": 1,
            "status": "completed",
            "question": "Tiêu chí 1.7 theo Quyết định 4740/QĐ-BGDĐT tính điểm như thế nào?",
            "resolved_question": "Tiêu chí 1.7 theo Quyết định 4740/QĐ-BGDĐT tính điểm như thế nào?",
            "result": {
                "status": "answered",
                "statements": [
                    {
                        "text": "Tiêu chí 1.7 có điểm tối đa là 10 điểm, gồm mức bắt buộc 5 điểm và nâng cao 5 điểm.",
                        "evidence_ids": ["E1"],
                    }
                ],
                "sources": [{"title": "Quyết định 4740/QĐ-BGDĐT", "evidence_id": "E1"}],
            },
        },
        {
            "turn_no": 2,
            "status": "completed",
            "question": "Còn Tiêu chí 1.8 thì sao?",
            "resolved_question": "Tiêu chí 1.8 tính điểm và mức độ theo Quyết định 4740/QĐ-BGDĐT như thế nào?",
            "result": {
                "status": "answered",
                "statements": [
                    {
                        "text": "Tiêu chí 1.8 quy định về hệ thống đào tạo trực tuyến với điểm tối đa 10 điểm.",
                        "evidence_ids": ["E2"],
                    }
                ],
                "sources": [{"title": "Quyết định 4740/QĐ-BGDĐT", "evidence_id": "E2"}],
            },
        },
    ]

    mem = extract_safe_conversation_memory(turns)

    assert mem["active_document"] == "Quyết định 4740/QĐ-BGDĐT"
    assert "Tiêu chí 1.7" in mem["active_entities"]
    assert "Tiêu chí 1.8" in mem["active_entities"]
    assert mem["last_entity"] == "Tiêu chí 1.8"
    assert mem["prior_entity"] == "Tiêu chí 1.7"
    assert len(mem["grounded_conclusions"]) == 2
    assert "10 điểm" in mem["grounded_conclusions"][0]["conclusion"]
    assert "đào tạo trực tuyến" in mem["grounded_conclusions"][1]["conclusion"]
    assert "Văn bản đang trao đổi" in mem["summary_text"]


def test_strictly_ignores_insufficient_evidence_and_failed_turns():
    turns = [
        {
            "turn_no": 1,
            "status": "completed",
            "question": "Nhiệm vụ 2 trong Kế hoạch 130/KH-ĐHQN thời gian thực hiện khi nào?",
            "resolved_question": "Thời gian thực hiện của Nhiệm vụ 2 theo Kế hoạch 130/KH-ĐHQN?",
            "result": {
                "status": "answered",
                "statements": [
                    {
                        "text": "Nhiệm vụ 2 được thực hiện từ tháng 01/2026 đến tháng 03/2026.",
                        "evidence_ids": ["E1"],
                    }
                ],
                "sources": [{"title": "Kế hoạch 130/KH-ĐHQN", "evidence_id": "E1"}],
            },
        },
        {
            "turn_no": 2,
            "status": "completed",
            "question": "Trường có tuyển thẳng giải nhất cờ vua quốc tế không?",
            "resolved_question": "Trường có tuyển thẳng giải nhất cờ vua quốc tế không?",
            "result": {
                "status": "insufficient_evidence",
                "statements": [],
                "message": "Tài liệu hiện tại chưa có thông tin về tuyển thẳng giải cờ vua.",
            },
        },
        {
            "turn_no": 3,
            "status": "failed",
            "question": "Câu hỏi gặp sự cố",
            "result": None,
        },
    ]

    mem = extract_safe_conversation_memory(turns)

    # Active doc and last entity must come ONLY from turn 1 (answered)
    assert mem["active_document"] == "Kế hoạch 130/KH-ĐHQN"
    assert mem["last_entity"] == "Nhiệm vụ 2"
    assert mem["prior_entity"] is None
    # Grounded conclusions must only contain turn 1, strictly NOT turn 2 (insufficient) or turn 3 (failed)
    assert len(mem["grounded_conclusions"]) == 1
    assert "tháng 01/2026" in mem["grounded_conclusions"][0]["conclusion"]
    assert not any("cờ vua" in c["conclusion"] for c in mem["grounded_conclusions"])


def test_empty_turns():
    mem = extract_safe_conversation_memory([])
    assert mem["active_document"] is None
    assert mem["active_entities"] == []
    assert mem["last_entity"] is None
    assert mem["prior_entity"] is None
    assert mem["grounded_conclusions"] == []
    assert mem["summary_text"] is None
