"""Unit tests for multi-turn session context, user fact extraction, and follow-up query rewriting."""

from qnu.domains.conversations.memory import (
    extract_safe_conversation_memory,
    extract_user_session_facts,
)
from qnu.domains.conversations.prefilter import classify_turn
from qnu.domains.rag.answer.drafting import messages_for
from qnu.domains.rag.answer.rewriter import rewrite_contextual_query
from qnu.domains.rag.answer.schemas import EvidenceSource


class DummyTurn:
    def __init__(
        self,
        turn_no: int,
        question: str,
        status: str = "completed",
        result: dict | None = None,
        resolved_question: str | None = None,
    ):
        self.turn_no = turn_no
        self.question = question
        self.status = status
        self.result = result
        self.resolved_question = resolved_question


def test_extract_user_session_facts():
    turn1 = DummyTurn(
        turn_no=1,
        question="Chào bạn, mình tên là Tuấn, học sinh lớp 12 thi được 25.5 điểm khối A00 muốn tìm hiểu ngành Công nghệ thông tin năm 2026.",
        status="completed",
        result={"status": "answered", "answer": "Chào bạn Tuấn! Mình có thể hỗ trợ bạn tìm hiểu về ngành CNTT."},
    )
    facts = extract_user_session_facts([turn1])
    assert facts["user_name"] == "Tuấn"
    assert facts["user_role"] == "học sinh lớp 12"
    assert facts["user_score"] == "25.5"
    assert facts["user_combination"] == "A00"
    assert facts["target_major"] == "Công nghệ thông tin"
    assert facts["target_year"] == "2026"
    assert "Tên: Tuấn" in facts["summary"]
    assert "Mức điểm: 25.5" in facts["summary"]


def test_session_facts_survives_sliding_window():
    """Ensure user facts declared in Turn 1 persist even when sliding window drops Turn 1."""
    turn1 = DummyTurn(
        turn_no=1,
        question="Em tên là Hà, em đạt 23 điểm tổ hợp D01.",
        status="completed",
        result={"status": "answered", "answer": "Chào Hà, mình đã nhận thông tin của bạn."},
    )
    turn2 = DummyTurn(
        turn_no=2,
        question="Học phí theo Quyết định 4740 là bao nhiêu?",
        status="completed",
        result={"status": "answered", "answer": "Học phí theo QĐ 4740 là 15 triệu/kỳ."},
    )
    turn3 = DummyTurn(
        turn_no=3,
        question="Thế còn chỉ tiêu xét tuyển của ngành Sư phạm Toán?",
        status="completed",
        result={"status": "answered", "answer": "Chỉ tiêu là 100 sinh viên."},
    )
    turn4 = DummyTurn(
        turn_no=4,
        question="Kế hoạch 130 quy định thời gian nộp hồ sơ khi nào?",
        status="completed",
        result={"status": "answered", "answer": "Thời gian nộp hồ sơ từ tháng 5 đến tháng 7."},
    )

    all_turns = [turn1, turn2, turn3, turn4]
    # Sliding window only keeps the last 2 turns (turn3, turn4)
    recent_rows = [turn3, turn4]

    memory = extract_safe_conversation_memory(recent_rows, all_turns=all_turns)
    assert memory["session_facts"]["user_name"] == "Hà"
    assert memory["session_facts"]["user_score"] == "23"
    assert memory["session_facts"]["user_combination"] == "D01"
    assert "Tên: Hà" in memory["summary_text"]
    assert "Mức điểm: 23 (tổ hợp D01)" in memory["summary_text"]


def test_prefilter_acknowledgment_with_history():
    """Short acknowledgments must be classified as social even when history is present."""
    phrases = [
        "tôi biết rồi",
        "tôi hiểu rồi",
        "mình hiểu rồi",
        "em hiểu rồi",
        "dạ em hiểu rồi",
        "dạ rõ rồi",
        "ok rồi",
        "cảm ơn bạn",
        "cảm ơn trợ lý",
        "thanks",
        "ok",
    ]
    for phrase in phrases:
        hint = classify_turn(phrase, has_history=True)
        assert hint["verdict"] == "social", f"Failed for phrase: {phrase}"


def test_rewrite_user_score_followup():
    """Follow-up questions on user score should rewrite with user_score and target_major."""
    conv_memory = {
        "session_facts": {
            "user_name": "Tuấn",
            "user_score": "24.5",
            "user_combination": "A00",
            "target_major": "Công nghệ thông tin",
            "target_major_code": "7480201",
            "target_year": "2026",
            "summary": "Tên: Tuấn. Mức điểm: 24.5 (tổ hợp A00). Ngành quan tâm: Công nghệ thông tin (mã 7480201).",
        },
        "active_document": "Đề án Tuyển sinh 2026",
    }
    history = [
        ("Tôi muốn hỏi ngành Công nghệ thông tin", "Ngành Công nghệ thông tin có mã 7480201."),
    ]
    q = "Vậy với mức điểm của tôi thì sao?"
    resolved, trace = rewrite_contextual_query(q, history, conversation_memory=conv_memory)
    assert trace["rewritten"] is True
    assert trace["mode"] == "user_score_followup"
    assert "Công nghệ thông tin" in resolved
    assert "24.5" in resolved
    assert "A00" in resolved
    assert "7480201" in resolved


def test_drafting_messages_for_includes_session_facts():
    """Drafting payload must carry user_session_facts in dialogue_context."""
    source = EvidenceSource(
        evidence_id="E1",
        chunk_id="chk_1",
        document_id="doc_1",
        version_id="ver_1",
        publication_decision_id="dec_1",
        score=0.95,
        kind="prose",
        source_title="Đề án Tuyển sinh",
        text="Ngành Công nghệ thông tin mã 7480201 điểm sàn xét tuyển là 20.0 điểm.",
        citations={"page": 5},
        structure={},
    )
    conv_memory = {
        "session_facts": {
            "user_name": "Anh Tuấn",
            "user_score": "24.5",
            "summary": "Tên: Anh Tuấn. Mức điểm: 24.5.",
        },
        "active_document": "Đề án Tuyển sinh",
    }
    msgs = messages_for(
        "Vậy với mức điểm của tôi thì sao?",
        [source],
        conversation_memory=conv_memory,
    )
    import json

    user_payload = json.loads(msgs[1].content)
    assert "dialogue_context" in user_payload
    assert "user_session_facts" in user_payload["dialogue_context"]
    assert user_payload["dialogue_context"]["user_session_facts"]["user_name"] == "Anh Tuấn"
    assert user_payload["dialogue_context"]["user_session_facts"]["user_score"] == "24.5"
