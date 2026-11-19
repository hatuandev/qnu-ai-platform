"""Unit tests for compound tasks, comparison, aggregation, and advisory query decomposition."""

from qnu.domains.rag.answer.decomposition import (
    decompose_query,
    needs_decomposition,
)
from qnu.domains.rag.answer.drafting import (
    APPEAL_INSTRUCTION,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
)
from qnu.domains.rag.answer.retrieval import question_facets


def test_compound_task_decomposition():
    """Verify that compound task questions conjoined by 'và' with a shared predicate split cleanly."""
    query = (
        "Việc thẩm định SAR (Tiếng Anh) và chuẩn bị hồ sơ, minh chứng bản giấy trong phòng phỏng vấn "
        "do đơn vị nào chủ trì, phối hợp và thời hạn thực hiện là khi nào?"
    )
    assert needs_decomposition(query) is True
    sub_queries = decompose_query(query)
    assert len(sub_queries) == 2
    assert "thẩm định SAR (Tiếng Anh)" in sub_queries[0]
    assert "chuẩn bị hồ sơ, minh chứng bản giấy" in sub_queries[1]
    assert "do đơn vị nào chủ trì, phối hợp và thời hạn thực hiện là khi nào?" in sub_queries[0]
    assert "do đơn vị nào chủ trì, phối hợp và thời hạn thực hiện là khi nào?" in sub_queries[1]


def test_multi_criteria_with_descriptions():
    """Verify criteria with parenthesized descriptions or codes decompose into focused sub-queries."""
    q1 = (
        "So sánh tiêu chí 1.4 (LMS/LCMS) và tiêu chí 1.5 (Thư viện số) về mức điểm tối đa "
        "và yêu cầu triển khai theo QĐ 4740."
    )
    assert needs_decomposition(q1) is True
    subs1 = decompose_query(q1)
    assert len(subs1) == 2
    assert "tiêu chí 1.4 (LMS/LCMS)" in subs1[0]
    assert "tiêu chí 1.5 (Thư viện số)" in subs1[1]

    q2 = (
        "So sánh thời gian thực hiện và đơn vị chủ trì giữa nhiệm vụ 1 (thẩm định SAR) "
        "và nhiệm vụ 6 (chuẩn bị minh chứng bản giấy) theo Kế hoạch 130."
    )
    assert needs_decomposition(q2) is True
    subs2 = decompose_query(q2)
    assert len(subs2) == 2
    assert "nhiệm vụ 1 (thẩm định SAR)" in subs2[0]
    assert "nhiệm vụ 6 (chuẩn bị minh chứng bản giấy)" in subs2[1]


def test_comparison_decomposition():
    """Verify general comparison questions between two organizational entities decompose."""
    query = "So sánh trách nhiệm giữa cơ sở giáo dục đại học và Cục Công nghệ thông tin theo QĐ 4740"
    assert needs_decomposition(query) is True
    subs = decompose_query(query)
    assert len(subs) == 2
    assert "cơ sở giáo dục đại học" in subs[0].lower()
    assert "cục công nghệ thông tin" in subs[1].lower()


def test_lead_condition_advisory_decomposition():
    """Verify advisory questions with lead conditions split into points and deadline sub-queries."""
    query = (
        "Để đạt mức đáp ứng cơ bản hoặc đáp ứng tốt theo Bộ chỉ số chuyển đổi số QĐ 4740, "
        "cơ sở giáo dục đại học cần đạt bao nhiêu điểm ở mỗi nhóm tiêu chí và cần lưu ý mốc báo cáo nào?"
    )
    assert needs_decomposition(query) is True
    subs = decompose_query(query)
    assert len(subs) == 2
    assert "Để đạt mức đáp ứng cơ bản hoặc đáp ứng tốt" in subs[0]
    assert "cần đạt bao nhiêu điểm ở mỗi nhóm tiêu chí" in subs[0]
    assert "Để đạt mức đáp ứng cơ bản hoặc đáp ứng tốt" in subs[1]
    assert "cần lưu ý mốc báo cáo nào" in subs[1]


def test_aggregation_multi_criteria_decomposition():
    """Verify aggregation queries over multiple criteria split into focused sub-queries."""
    query = "Tổng hợp các phân hệ của tiêu chí 2.4 và các dịch vụ trực tuyến của tiêu chí 2.5 theo QĐ 4740."
    assert needs_decomposition(query) is True
    subs = decompose_query(query)
    assert len(subs) == 2
    assert "tiêu chí 2.4" in subs[0]
    assert "tiêu chí 2.5" in subs[1]


def test_retrieval_facets_context_enrichment():
    """Verify that elliptical follow-up clauses inherit antecedent context in question_facets."""
    query = (
        "Cơ sở giáo dục đại học phải cập nhật kết quả tự đánh giá lên hệ thống cơ sở dữ liệu "
        "ngành Giáo dục trước thời điểm nào hằng năm và đơn vị nào chủ trì đánh giá ngoài?"
    )
    facets = question_facets(query)
    assert len(facets) == 2
    assert "cập nhật kết quả tự đánh giá" in facets[0]
    assert "đơn vị nào chủ trì đánh giá ngoài" in facets[1]
    assert "Context:" in facets[1]


def test_drafting_guidelines_and_version():
    """Verify prompt version v41 and guidelines for comparison, aggregation, and advisory."""
    assert PROMPT_VERSION == "qnu.rag.answer/v41"
    assert "SO SÁNH, THỐNG KÊ, TƯ VẤN VÀ CÂU HỎI GHÉP NHIỀU MỤC" in SYSTEM_PROMPT
    assert "SO SÁNH:" in SYSTEM_PROMPT
    assert "THỐNG KÊ & TỔNG HỢP:" in SYSTEM_PROMPT
    assert "TƯ VẤN & ĐỊNH HƯỚNG:" in SYSTEM_PROMPT
    assert "CÂU HỎI GHÉP NHIỀU MỤC / ĐẦU VIỆC:" in SYSTEM_PROMPT
    assert "so sánh/thống kê/tư vấn" in APPEAL_INSTRUCTION
