"""Pipeline unit & integration tests for Phase 2 Slice 4: IRAC 4-step reasoning, query decomposition, and deterministic fact query routing."""

from __future__ import annotations

from qnu.domains.rag.answer.cells import catalog
from qnu.domains.rag.answer.decomposition import decompose_query, needs_decomposition
from qnu.domains.rag.answer.drafting import (
    PROMPT_VERSION,
    parse_answer,
)
from qnu.domains.rag.answer.fact_query import (
    FactFilter,
    FactQueryRequest,
    execute_fact_query,
    materialize_fact_query_answer,
)
from qnu.domains.rag.answer.intent_router import classify_intent
from qnu.domains.rag.answer.reasoning import split_reasoning_and_answer
from qnu.domains.rag.answer.schemas import AnswerTrace, EvidenceSource


def _table_source(table_citation: str = "ocr_1:ev_p004_b001") -> tuple[EvidenceSource, dict]:
    rows = [
        [
            {"text": "Mã ngành", "header": True, "row_span": 1, "col_span": 1, "evidence_id": "h0"},
            {"text": "Tên ngành", "header": True, "row_span": 1, "col_span": 1, "evidence_id": "h1"},
            {"text": "Tổ hợp xét tuyển", "header": True, "row_span": 1, "col_span": 1, "evidence_id": "h2"},
            {"text": "Chỉ tiêu", "header": True, "row_span": 1, "col_span": 1, "evidence_id": "h3"},
        ],
        [
            {"text": "7140201", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c1_0"},
            {"text": "Sư phạm Văn", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c1_1"},
            {"text": "C00; D01", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c1_2"},
            {"text": "60", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c1_3"},
        ],
        [
            {"text": "7140209", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c2_0"},
            {"text": "Sư phạm Toán", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c2_1"},
            {"text": "A00; A01", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c2_2"},
            {"text": "80", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c2_3"},
        ],
    ]
    citations = {
        f"ocr_1:{cell['evidence_id']}": {"page_number": 4}
        for row in rows
        for cell in row
        if cell.get("evidence_id")
    }
    structure = {
        "source_table_citation": table_citation,
        "original_row_count": 3,
        "original_column_count": 4,
        "row_indices": [0, 1, 2],
        "rows": rows,
    }
    source = EvidenceSource(
        evidence_id="E1",
        chunk_id="ich_tbl_1",
        document_id="cdoc_1",
        version_id="cver_1",
        publication_decision_id="pdec_1",
        score=1.0,
        kind="table",
        text="Bảng danh mục ngành và chỉ tiêu 2026",
        citations=citations,
        structure=structure,
    )
    cell_catalog = catalog([source], include_names=True)
    return source, cell_catalog


# ============================================================================
# 1. End-to-End IRAC Multi-Clause Pipeline
# ============================================================================

def test_irac_multi_clause_pipeline_flow():
    question = (
        "Thí sinh mã 0012 có 18 điểm tốt nghiệp nhưng muốn xét học bạ ngành Sư phạm Toán "
        "thì có được dùng điểm tổ hợp A01 thay cho A00 không?"
    )
    # Step 1: Intent router classifies complex question as rule_reasoning
    intent = classify_intent(question)
    assert intent == "rule_reasoning"

    # Step 2: Query decomposition splits question into <= 3 sub-queries preserving 0012
    assert needs_decomposition(question)
    sub_queries = decompose_query(question)
    assert 1 <= len(sub_queries) <= 3
    combined = " ".join(sub_queries)
    assert "0012" in combined
    assert "Sư phạm Toán" in combined

    # Step 3: Raw model response with IRAC 4-step analysis in <phan_tich>
    raw_response = (
        "<phan_tich>\n"
        "- Bước 1 (Quy định gốc & Ngoại lệ): E1 quy định ngành Sư phạm Toán xét cả tổ hợp A00 và A01. "
        "Phương thức học bạ yêu cầu tổng điểm 3 môn từ 24.0 trở lên, không cho phép dùng điểm tốt nghiệp thay thế điểm học bạ.\n"
        "- Bước 2 (Đối chiếu dữ kiện): Thí sinh có 18 điểm thi tốt nghiệp và muốn dùng thay điểm học bạ.\n"
        "- Bước 3 (Kiểm tra điểm khuyết): Evidence E1 chưa có quy định về quy đổi điểm thi tốt nghiệp sang học bạ.\n"
        "- Bước 4 (Chốt phạm vi kết luận): ĐÃ ĐỦ CĂN CỨ khẳng định ngành có xét tổ hợp A01; CHƯA ĐỦ CĂN CỨ việc dùng điểm tốt nghiệp thay cho học bạ.\n"
        "</phan_tich>\n"
        '{"status":"answered","statements":['
        '{"text":"Ngành Sư phạm Toán có xét tuyển tổ hợp A01 bên cạnh A00.","evidence_ids":["E1"]},'
        '{"text":"Hiện chưa có quy định cho phép dùng điểm thi tốt nghiệp thay thế điểm học bạ.","evidence_ids":["E1"]}'
        '],"lookups":[],"assessment":['
        '{"label":"Tổ hợp xét tuyển A01","status":"covered","evidence_ids":["E1"]},'
        '{"label":"Dùng điểm tốt nghiệp thay học bạ","status":"missing","evidence_ids":[]}'
        '],"message":null}'
    )

    # Step 4: Reasoning separation
    internal_reasoning, clean_content = split_reasoning_and_answer(raw_response)
    assert "Bước 1 (Quy định gốc & Ngoại lệ)" in internal_reasoning
    assert "Bước 4 (Chốt phạm vi kết luận)" in internal_reasoning
    assert "<phan_tich>" not in clean_content
    assert "</phan_tich>" not in clean_content

    # Step 5: Answer parsing and trace recording
    source, _ = _table_source()
    parsed = parse_answer(clean_content, [source])
    assert parsed.status == "answered"
    assert len(parsed.statements) == 2
    assert parsed.statements[0].evidence_ids == ["E1"]

    trace = AnswerTrace(prompt_version=PROMPT_VERSION)
    trace.reasoning["irac_analysis"] = internal_reasoning
    trace.context["intent"] = intent
    assert trace.reasoning["irac_analysis"] == internal_reasoning
    assert trace.context["intent"] == "rule_reasoning"


# ============================================================================
# 2. Year Conflict Retention (2025 vs 2026)
# ============================================================================

def test_year_conflict_preservation():
    raw_response = (
        "<phan_tich>\n"
        "- Bước 1: Quyết định 2025 quy định điểm sàn 18.0 (E1). Đề án 2026 quy định điểm sàn 19.0 (E2).\n"
        "- Bước 2: Hai năm có quy định khác nhau.\n"
        "- Bước 3: Đầy đủ chứng cứ cả 2 văn bản.\n"
        "- Bước 4: Chốt cả 2 mức điểm theo từng năm, không giấu mốc nào.\n"
        "</phan_tich>\n"
        '{"status":"answered","statements":['
        '{"text":"Năm 2025: Điểm sàn xét tuyển là 18.0 theo Quyết định tuyển sinh 2025.","evidence_ids":["E1"]},'
        '{"text":"Năm 2026: Điểm sàn xét tuyển tăng lên 19.0 theo Đề án tuyển sinh 2026.","evidence_ids":["E2"]}'
        '],"lookups":[],"assessment":['
        '{"label":"Điểm sàn 2025","status":"covered","evidence_ids":["E1"]},'
        '{"label":"Điểm sàn 2026","status":"covered","evidence_ids":["E2"]}'
        '],"message":null}'
    )
    s1 = EvidenceSource(
        evidence_id="E1",
        chunk_id="ich_2025",
        document_id="doc_2025",
        version_id="ver_2025",
        publication_decision_id="pdec_2025",
        score=1.0,
        kind="paragraph",
        text="Điểm sàn 2025 là 18.0",
        citations={},
        structure={},
    )
    s2 = EvidenceSource(
        evidence_id="E2",
        chunk_id="ich_2026",
        document_id="doc_2026",
        version_id="ver_2026",
        publication_decision_id="pdec_2026",
        score=1.0,
        kind="paragraph",
        text="Điểm sàn 2026 là 19.0",
        citations={},
        structure={},
    )
    _, clean = split_reasoning_and_answer(raw_response)
    parsed = parse_answer(clean, [s1, s2])
    assert parsed.status == "answered"
    assert len(parsed.statements) == 2
    # Verify both years are preserved
    all_text = " ".join(s.text for s in parsed.statements)
    assert "2025" in all_text and "18.0" in all_text
    assert "2026" in all_text and "19.0" in all_text


# ============================================================================
# 3. Deterministic Fact Query Fast Path Integration
# ============================================================================

def test_deterministic_fact_query_routing_through_cells_materialize():
    source, cell_catalog = _table_source()

    from qnu.domains.knowledge.index.facts import project_table
    from qnu.domains.rag.answer.fact_query import ScopedTableSchema

    table_dict = {
        "status": "parsed",
        "row_count": 3,
        "column_count": 4,
        "rows": [
            [
                {"text": "Mã ngành", "header": True, "row_span": 1, "col_span": 1},
                {"text": "Tên ngành", "header": True, "row_span": 1, "col_span": 1},
                {"text": "Tổ hợp xét tuyển", "header": True, "row_span": 1, "col_span": 1},
                {"text": "Chỉ tiêu", "header": True, "row_span": 1, "col_span": 1},
            ],
            [
                {"text": "7140201", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c1_0"},
                {"text": "Sư phạm Văn", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c1_1"},
                {"text": "C00; D01", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c1_2"},
                {"text": "60", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c1_3"},
            ],
            [
                {"text": "7140209", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c2_0"},
                {"text": "Sư phạm Toán", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c2_1"},
                {"text": "A00; A01", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c2_2"},
                {"text": "80", "header": False, "row_span": 1, "col_span": 1, "evidence_id": "c2_3"},
            ],
        ],
    }
    projected = project_table(
        table_dict,
        table_id="ocr_1:ev_p004_b001",
        source_table_citation="ocr_1:ev_p004_b001",
        title="Danh mục ngành 2026",
    )

    schema = ScopedTableSchema(
        table_id=projected.table_id,
        source_table_citation=projected.source_table_citation,
        table_title=projected.title,
        index_run_id="run1",
        collection_id="col1",
        document_id="cdoc_1",
        version_id="cver_1",
        publication_decision_id="pdec_1",
        has_header=projected.has_header,
        keep_whole_in_chunk=projected.keep_whole_in_chunk,
        column_keys=list(projected.column_keys),
        data_years=list(projected.data_years),
        data_row_count=projected.table_schema().data_row_count,
        scoped_notes=list(projected.scoped_notes),
    )

    # SUM query: Tổng chỉ tiêu
    sum_req = FactQueryRequest(
        table_id="ocr_1:ev_p004_b001",
        aggregation="sum",
        target_column="Chỉ tiêu",
    )
    sum_result = execute_fact_query(projected.facts, schema, sum_req)
    assert sum_result.numeric_result == "140"
    assert sum_result.included_numeric_count == 2

    # Route through materialize_fact_query_answer
    report = {}
    materialized = materialize_fact_query_answer(sum_result, [source], cell_catalog, report=report)
    assert materialized.status == "answered"
    assert len(materialized.lookups) == 2 or len(materialized.statements) >= 1

    # LIST query with set_contains filter
    list_req = FactQueryRequest(
        table_id="ocr_1:ev_p004_b001",
        aggregation="list",
        filters=[
            FactFilter(
                column="Tổ hợp xét tuyển",
                op="set_contains",
                value=["A00"],
            )
        ],
    )
    list_result = execute_fact_query(projected.facts, schema, list_req)
    assert [r.subject_name for r in list_result.matched_rows] == ["Sư phạm Toán"]

    materialized_list = materialize_fact_query_answer(list_result, [source], cell_catalog)
    assert materialized_list.status == "answered"


# ============================================================================
# 4. Missing Evidence / External Reference Gaps
# ============================================================================

def test_missing_evidence_safe_abstention():
    raw_response = (
        "<phan_tich>\n"
        "- Bước 1: Evidence E1 không có thông tin về ngành Kỹ thuật ô tô.\n"
        "- Bước 2: Không thể đối chiếu.\n"
        "- Bước 3: Thiếu hoàn toàn dữ kiện về ngành này trong tài liệu đã cấp.\n"
        "- Bước 4: CHƯA ĐỦ CĂN CỨ trả lời.\n"
        "</phan_tich>\n"
        '{"status":"insufficient_evidence","statements":[],"lookups":[],'
        '"assessment":[{"label":"Chỉ tiêu ngành Kỹ thuật ô tô","status":"missing","evidence_ids":[]}],'
        '"message":"Chưa tìm thấy thông tin phù hợp trong nguồn hiện có. Vui lòng nêu rõ tên văn bản hoặc bổ sung tài liệu."}'
    )
    source, _ = _table_source()
    _, clean = split_reasoning_and_answer(raw_response)
    parsed = parse_answer(clean, [source])
    assert parsed.status == "insufficient_evidence"
    assert parsed.statements == []
    assert parsed.message is not None
    assert "Chưa tìm thấy thông tin" in parsed.message
