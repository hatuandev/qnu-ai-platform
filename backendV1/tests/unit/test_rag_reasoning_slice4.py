"""Unit tests for Phase 2 Slice 4: IRAC 4-step reasoning, query decomposition, intent router, and row card chunking."""

from __future__ import annotations

import json

import pytest

from qnu.domains.knowledge.index.row_cards import (
    RowCard,
    build_row_card_chunks,
    row_card_to_chunk,
)
from qnu.domains.rag.answer.decomposition import decompose_query, needs_decomposition
from qnu.domains.rag.answer.drafting import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    parse_answer,
)
from qnu.domains.rag.answer.intent_router import classify_intent
from qnu.domains.rag.answer.reasoning import split_reasoning_and_answer
from qnu.domains.rag.answer.schemas import EvidenceSource
from qnu.platform.errors import AppException

# ============================================================================
# 1. split_reasoning_and_answer (IRAC Extraction)
# ============================================================================

def test_split_reasoning_and_answer_well_formed():
    raw = (
        "<phan_tich>\n"
        "- Bước 1: Quy định điểm sàn ngành 7480201 năm 2026 là 18.0.\n"
        "- Bước 2: Thí sinh có 17.5 điểm.\n"
        "- Bước 3: Đầy đủ chứng cứ E1.\n"
        "- Bước 4: Kết luận thí sinh không đạt ngưỡng.\n"
        "</phan_tich>\n"
        '{"status":"answered","statements":[{"text":"Thí sinh không đủ điểm.","evidence_ids":["E1"]}],"lookups":[],"assessment":[],"message":null}'
    )
    reasoning, clean = split_reasoning_and_answer(raw)
    assert "- Bước 1: Quy định điểm sàn" in reasoning
    assert "- Bước 4: Kết luận thí sinh" in reasoning
    assert "<phan_tich>" not in clean
    assert "</phan_tich>" not in clean
    assert json.loads(clean)["status"] == "answered"


def test_split_reasoning_and_answer_case_insensitive_and_multiline():
    raw = (
        "<PHAN_TICH>\n"
        "BƯỚC 1: QUY CHẾ 2025\n"
        "BƯỚC 2: SO SÁNH 2026\n"
        "</PHAN_TICH>\n"
        '{"status":"insufficient_evidence","statements":[],"lookups":[],"assessment":[],"message":"Chưa có thông tin."}'
    )
    reasoning, clean = split_reasoning_and_answer(raw)
    assert "BƯỚC 1: QUY CHẾ 2025" in reasoning
    assert json.loads(clean)["status"] == "insufficient_evidence"


def test_split_reasoning_and_answer_unclosed_tag():
    raw = (
        "<phan_tich>\n"
        "- Phân tích dở dang nhưng quên đóng thẻ\n"
        '{"status":"answered","statements":[{"text":"Kết quả.","evidence_ids":["E1"]}],"lookups":[],"assessment":[],"message":null}'
    )
    reasoning, clean = split_reasoning_and_answer(raw)
    assert "- Phân tích dở dang" in reasoning
    assert "<phan_tich>" not in clean


def test_split_reasoning_and_answer_absent_tags():
    raw = '{"status":"answered","statements":[{"text":"Không có thẻ phân tích.","evidence_ids":["E1"]}],"lookups":[],"assessment":[],"message":null}'
    reasoning, clean = split_reasoning_and_answer(raw)
    assert reasoning == ""
    assert clean == raw
    assert json.loads(clean)["status"] == "answered"


def test_split_reasoning_and_answer_empty_input():
    reasoning, clean = split_reasoning_and_answer("")
    assert reasoning == ""
    assert clean == ""


# ============================================================================
# 2. Query Decomposition & Needs Decomposition
# ============================================================================

def test_needs_decomposition_simple_queries():
    assert not needs_decomposition("Ngành Công nghệ thông tin học phí bao nhiêu?")
    assert not needs_decomposition("Mã ngành 7480201 là gì")
    assert not needs_decomposition("Chỉ tiêu tuyển sinh năm 2026")


def test_needs_decomposition_conditional_and_comparison():
    assert needs_decomposition("Tôi có 18 điểm thi tốt nghiệp nhưng muốn xét học bạ ngành Sư phạm Toán thì có được không?")
    assert needs_decomposition("Nếu rớt nguyện vọng 1 thì có được xét học bạ thay thế không?")
    assert needs_decomposition("Có được dùng điểm tổ hợp A01 thay cho A00 khi xét tuyển không?")
    assert needs_decomposition("Quy chế 2026 so với 2025 khác gì về điều kiện loại trừ?")
    assert needs_decomposition("Ngưỡng đầu vào ngành Sư phạm tiếng Anh là bao nhiêu? Ngành Ngôn ngữ Anh là bao nhiêu?")


def test_decompose_query_preserves_identifiers_and_combinations():
    query = "Thí sinh có mã hồ sơ 0012 có được dùng điểm môn Toán 8.0 thay cho môn Lý trong tổ hợp A01 không?"
    sub_queries = decompose_query(query)
    assert 1 <= len(sub_queries) <= 3
    # Check that key identifiers are preserved across sub-queries
    combined = " ".join(sub_queries)
    assert "0012" in combined
    assert "Toán" in combined


def test_decompose_query_replacement_generates_three_focused_queries():
    query = "Có được dùng điểm IELTS 6.5 thay cho môn tiếng Anh để xét tuyển học bạ ngành Sư phạm Anh không?"
    sub_queries = decompose_query(query)
    assert len(sub_queries) == 3
    assert any("Quy định xét tuyển" in q for q in sub_queries)
    assert any("Điều kiện ngưỡng đầu vào" in q for q in sub_queries)
    assert any("Trường hợp ngoại lệ" in q for q in sub_queries)


def test_decompose_query_multiple_clauses_bounded_to_three():
    query = "Học phí ngành CNTT bao nhiêu? Chỉ tiêu tuyển sinh là bao nhiêu? Điểm chuẩn năm trước là bao nhiêu? Điều kiện tuyển thẳng là gì?"
    sub_queries = decompose_query(query)
    assert len(sub_queries) <= 3


# ============================================================================
# 3. Intent Router
# ============================================================================

def test_classify_intent_tabular_aggregation():
    assert classify_intent("Liệt kê tất cả các ngành đào tạo đại học năm 2026") == "tabular_aggregation"
    assert classify_intent("Có bao nhiêu ngành xét tuyển tổ hợp A00?") == "tabular_aggregation"
    assert classify_intent("Tổng chỉ tiêu tuyển sinh năm 2026 là bao nhiêu?") == "tabular_aggregation"
    assert classify_intent("Ngành nào xét tổ hợp Văn Sử Địa?") == "tabular_aggregation"
    assert classify_intent("Điểm chuẩn cao nhất năm 2025 là ngành nào?") == "tabular_aggregation"


def test_classify_intent_rule_reasoning():
    assert classify_intent("Nếu học sinh đạt giải nhì học sinh giỏi tỉnh nhưng hạnh kiểm khá thì có được tuyển thẳng không?") == "rule_reasoning"
    assert classify_intent("Có được dùng chứng chỉ tin học quốc tế thay thế môn Tin khi xét học bạ không?") == "rule_reasoning"
    assert classify_intent("Điều kiện ngưỡng đầu vào ngành Y khoa so với Điều dưỡng có gì khác?") == "rule_reasoning"


def test_classify_intent_direct_lookup():
    assert classify_intent("Trường Đại học Quy Nhơn thành lập năm nào?") == "direct_lookup"
    assert classify_intent("Địa chỉ trường ở đâu?") == "direct_lookup"
    assert classify_intent("Hiệu trưởng hiện nay là ai?") == "direct_lookup"


# ============================================================================
# 4. RowCard to Chunk & Chunk Building
# ============================================================================

def test_row_card_to_chunk():
    card = RowCard(
        card_id="card_t1_r0",
        table_id="t1",
        source_table_citation="ocr_1:ev_p004_b001",
        fact_ids=["fact_1", "fact_2"],
        row_kind="data",
        data_years=[2026],
        detail_md_pointers={},
        cross_references=["t2:r0"],
        source_cell_refs=["c1:r0:k1", "c1:r0:k2"],
        text="Ngành: Sư phạm Toán | Mã ngành: 7140209 | Năm: 2026",
    )
    chunk = row_card_to_chunk(card)
    assert chunk.kind == "row_card"
    assert chunk.text == card.text
    assert chunk.citations == {"c1:r0:k1": "c1:r0:k1", "c1:r0:k2": "c1:r0:k2"}
    assert chunk.structure["card_id"] == "card_t1_r0"
    assert chunk.structure["table_id"] == "t1"
    assert chunk.structure["data_years"] == [2026]
    assert chunk.structure["table"] is True


def test_build_row_card_chunks_integration():
    tables = [
        {
            "citation": "ocr_1:ev_p004_b001",
            "title": "Danh mục ngành tuyển sinh",
            "table": {
                "status": "parsed",
                "row_count": 2,
                "column_count": 3,
                "rows": [
                    [
                        {"text": "Mã ngành", "header": True, "row_span": 1, "col_span": 1},
                        {"text": "Tên ngành", "header": True, "row_span": 1, "col_span": 1},
                        {"text": "Chỉ tiêu", "header": True, "row_span": 1, "col_span": 1},
                    ],
                    [
                        {"text": "7480201", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "ev1"},
                        {"text": "Công nghệ thông tin", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "ev2"},
                        {"text": "150", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "ev3"},
                    ],
                ],
            },
        }
    ]
    chunks = build_row_card_chunks(tables, doc_title="Đề án tuyển sinh 2026")
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.kind == "row_card"
    assert "7480201" in chunk.text
    assert "Công nghệ thông tin" in chunk.text
    assert "150" in chunk.text
    assert chunk.structure["table"] is True


# ============================================================================
# 5. Prompt Spec & IRAC System Instructions
# ============================================================================

def test_prompt_version_and_system_instructions():
    assert PROMPT_VERSION == "qnu.rag.answer/v42"
    assert "<phan_tich>" in SYSTEM_PROMPT
    assert "</phan_tich>" in SYSTEM_PROMPT
    assert "Bước 1" in SYSTEM_PROMPT
    assert "Bước 2" in SYSTEM_PROMPT
    assert "Bước 3" in SYSTEM_PROMPT
    assert "Bước 4" in SYSTEM_PROMPT
    # Invariant checks
    assert "KHÔNG BỊA ĐẶT" in SYSTEM_PROMPT
    assert "KHÔNG GIẤU XUNG ĐỘT" in SYSTEM_PROMPT
    assert "KỶ LUẬT PHỦ ĐỊNH & NGOẠI LỆ" in SYSTEM_PROMPT
    assert "BẢO TOÀN ĐỊNH DANH & KÝ HIỆU" in SYSTEM_PROMPT
    assert "Chỉ giải nghĩa hoặc mở rộng từ viết tắt" in SYSTEM_PROMPT
    assert "tuyệt đối không dùng kiến thức ngoài để tự suy diễn hay đoán nghĩa" in SYSTEM_PROMPT


# ============================================================================
# 6. parse_answer with <phan_tich> Stripping
# ============================================================================

def test_parse_answer_strips_phan_tich_and_validates():
    source = EvidenceSource(
        evidence_id="E1",
        chunk_id="ich_1",
        document_id="cdoc_1",
        version_id="cver_1",
        publication_decision_id="pdec_1",
        score=1.0,
        kind="paragraph",
        text="Thí sinh được xét tuyển.",
        citations={"c1": "c1"},
        structure={},
    )
    raw = (
        "<phan_tich>\n"
        "- Bước 1: Quy định E1 cho phép xét tuyển.\n"
        "- Bước 2: Thí sinh đủ điều kiện.\n"
        "- Bước 3: Không có điểm khuyết.\n"
        "- Bước 4: Đủ căn cứ khẳng định được xét tuyển.\n"
        "</phan_tich>\n"
        '{"status":"answered","statements":[{"text":"Thí sinh được xét tuyển.","evidence_ids":["E1"]}],"lookups":[],"assessment":[{"label":"Yêu cầu","status":"covered","evidence_ids":["E1"]}],"message":null}'
    )
    parsed = parse_answer(raw, [source])
    assert parsed.status == "answered"
    assert len(parsed.statements) == 1
    assert parsed.statements[0].text == "Thí sinh được xét tuyển."
    assert parsed.statements[0].evidence_ids == ["E1"]


def test_parse_answer_invalid_json_raises_app_exception():
    source = EvidenceSource(
        evidence_id="E1",
        chunk_id="ich_1",
        document_id="cdoc_1",
        version_id="cver_1",
        publication_decision_id="pdec_1",
        score=1.0,
        kind="paragraph",
        text="Sample text",
        citations={},
        structure={},
    )
    raw = "<phan_tich>Phân tích</phan_tich>Đây không phải JSON"
    with pytest.raises(AppException) as exc_info:
        parse_answer(raw, [source])
    assert exc_info.value.code == "answer_response_invalid"
