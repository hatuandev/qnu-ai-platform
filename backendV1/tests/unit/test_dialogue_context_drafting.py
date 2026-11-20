"""Unit tests for dialogue_context integration in drafting.py."""

from __future__ import annotations

import json

from qnu.domains.rag.answer.drafting import messages_for
from qnu.domains.rag.answer.schemas import EvidenceSource


def test_messages_for_includes_dialogue_context_when_provided():
    sources = [
        EvidenceSource(
            evidence_id="E1",
            chunk_id="chk_1",
            document_id="doc_1",
            version_id="v1",
            publication_decision_id="pub_1",
            score=0.95,
            kind="text",
            text="Nhiệm vụ 2 thực hiện từ tháng 01/2026 đến tháng 03/2026 do Phòng Đào tạo chủ trì.",
            citations={"source_title": "Kế hoạch 130/KH-ĐHQN"},
            structure=None,
            source_title="Kế hoạch 130/KH-ĐHQN",
        )
    ]

    conv_memory = {
        "active_document": "Kế hoạch 130/KH-ĐHQN",
        "last_entity": "Nhiệm vụ 2",
        "prior_entity": "Nhiệm vụ 1",
        "grounded_conclusions": [
            {
                "question": "Thời gian thực hiện nhiệm vụ 2",
                "conclusion": "Từ tháng 01/2026 đến tháng 03/2026",
            }
        ],
        "summary_text": "Văn bản đang trao đổi: Kế hoạch 130/KH-ĐHQN. Mục vừa đối chiếu: Nhiệm vụ 2",
    }

    messages = messages_for(
        "Đơn vị nào chủ trì và phối hợp?",
        sources,
        resolved_question="Đơn vị nào chủ trì và phối hợp của Nhiệm vụ 2 theo Kế hoạch 130/KH-ĐHQN?",
        conversation_memory=conv_memory,
    )

    assert len(messages) == 2
    system_msg = messages[0].content
    user_payload = json.loads(messages[1].content)

    # 1. System prompt must emphasize dialogue_context constraints
    assert "dialogue_context" in system_msg
    assert "TUYỆT ĐỐI KHÔNG DÙNG LÀM BẰNG CHỨNG DỮ KIỆN" in system_msg
    assert "evidence được cấp cho lượt hiện tại" in system_msg

    # 2. User payload must include dialogue_context with verified fields
    assert "dialogue_context" in user_payload
    d_ctx = user_payload["dialogue_context"]
    assert d_ctx["active_document"] == "Kế hoạch 130/KH-ĐHQN"
    assert d_ctx["prior_entity"] == "Nhiệm vụ 2"
    assert d_ctx["comparison_entity"] == "Nhiệm vụ 1"
    assert "Từ tháng 01/2026 đến tháng 03/2026" in d_ctx["prior_conclusions"][0]
    assert "Văn bản đang trao đổi" in d_ctx["flow_summary"]


def test_messages_for_omits_dialogue_context_when_empty():
    sources = [
        EvidenceSource(
            evidence_id="E1",
            chunk_id="chk_1",
            document_id="doc_1",
            version_id="v1",
            publication_decision_id="pub_1",
            score=0.9,
            kind="text",
            text="Điều 1 quy định phạm vi điều chỉnh.",
            citations={"source_title": "Quyết định 4740/QĐ-BGDĐT"},
            structure=None,
            source_title="Quyết định 4740/QĐ-BGDĐT",
        )
    ]

    messages = messages_for(
        "Điều 1 quy định gì?",
        sources,
        conversation_memory=None,
    )

    user_payload = json.loads(messages[1].content)
    assert "dialogue_context" not in user_payload

