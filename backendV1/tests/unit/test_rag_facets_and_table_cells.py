"""Unit tests for multi-clause facets, decomposition and table cell grounding."""


from qnu.domains.rag.answer.cells import _row_facts, _statement_numbers, _table_support
from qnu.domains.rag.answer.decomposition import decompose_query, needs_decomposition
from qnu.domains.rag.answer.retrieval import question_facets
from qnu.domains.rag.answer.schemas import EvidenceSource


def test_question_facets_preserves_proper_noun_with_va():
    query = (
        "Trong Kế hoạch 130, thông tin liên hệ đầu mối của Phòng Khảo thí và BĐCL là ai, số điện thoại nào; "
        "việc đặt phòng khách sạn và ăn uống cho đoàn chuyên gia được phân công cho đơn vị nào phụ trách?"
    )
    facets = question_facets(query)
    assert len(facets) == 2
    assert "Phòng Khảo thí và BĐCL" in facets[0]
    assert "đầu mối" in facets[0]
    assert "đặt phòng khách sạn và ăn uống" in facets[1]


def test_question_facets_bare_conjunction_with_proper_noun():
    # Câu hỏi không có dấu chấm phẩy, chỉ nối bằng "và" giữa 2 mệnh đề hỏi:
    query = (
        "Công tác đặt phòng khách sạn/ăn uống cho Đoàn đánh giá ngoài do đơn vị nào chủ trì "
        "và thông tin liên hệ đầu mối của Phòng Khảo thí và BĐCL là ai?"
    )
    facets = question_facets(query)
    assert len(facets) == 2
    assert "đơn vị nào chủ trì" in facets[0]
    assert "Phòng Khảo thí và BĐCL" in facets[1]
    assert "đầu mối" in facets[1]


def test_question_facets_interrogatives_vietnamese():
    # Clause with "ai" and clause with "ở đâu"
    query = "Ai là trưởng đoàn đánh giá ngoài; địa điểm làm việc chính thức diễn ra ở đâu?"
    facets = question_facets(query)
    assert len(facets) == 2
    assert "Ai là trưởng đoàn" in facets[0]
    assert "ở đâu" in facets[1]


def test_multi_criteria_decomposition():
    query = "Mức điểm tối đa và các mức điểm đánh giá của tiêu chí 2.4 và 2.5 quy định như thế nào?"
    assert needs_decomposition(query) is True
    sub_queries = decompose_query(query)
    assert len(sub_queries) == 2
    assert "tiêu chí 2.4" in sub_queries[0]
    assert "tiêu chí 2.5" in sub_queries[1]
    assert "2.5" not in sub_queries[0]
    assert "2.4" not in sub_queries[1]


def test_cells_structural_ref_criteria():
    text = "Theo quy định, tiêu chí 2.4 có mức điểm là 50."
    numbers = _statement_numbers(text)
    # "2.4" is structural ref (tiêu chí 2.4), so it should not be treated as a data fact number
    assert "2.4" not in numbers
    assert "50" in numbers


def test_cells_row_facts_dot_code_and_long_label():
    cells = [
        {"row_span": 1, "col_span": 1, "text": "2.4."},
        {
            "row_span": 1,
            "col_span": 1,
            "text": "Có triển khai phần mềm quản trị cơ sở giáo dục đại học (cung cấp thông tin: tên giải pháp, nhà cung cấp, ngày triển khai)",
        },
        {"row_span": 1, "col_span": 1, "text": "50"},
        {"row_span": 1, "col_span": 1, "text": "15; 30; 50"},
    ]
    source = EvidenceSource(
        evidence_id="ev_test_1",
        chunk_id="chk_test_1",
        kind="table",
        document_id="doc_1",
        version_id="ver_1",
        publication_decision_id="pub_1",
        score=1.0,
        text="2.4. Có triển khai phần mềm quản trị... 50 15; 30; 50",
        citations={},
        structure={
            "rows": [cells],
            "row_indices": [0],
            "original_row_count": 1,
            "original_column_count": 4,
            "source_table_citation": "table_1",
        },
    )
    facts = _row_facts(source)
    assert len(facts) == 1
    labels = [label for _, label in facts[0]["labels"]]
    # Should include "2.4" and head of long text
    assert "2.4" in labels
    assert "có triển khai phần mềm quản trị cơ sở giáo dục đại học" in labels

    # Test statement verification
    statement = (
        "Tiêu chí 2.4 (Có triển khai phần mềm quản trị cơ sở giáo dục đại học) "
        "có mức điểm tối đa là 50 điểm, các mức đánh giá là 15, 30 hoặc 50 điểm."
    )
    supported = _table_support(source, statement)
    assert "50" in supported
    assert "15" in supported
    assert "30" in supported
