"""Unit tests for EvalOps Golden Suite and Answer Evaluator (Slice 6A).

Verifies benchmark runner, answer correctness, groundedness, IRAC reasoning check,
year conflict disclosure (AGENTS.md Invariant #4), calculator missing variable refusal,
and code preservation (leading zeros).
"""

import pytest

from qnu.domains.evaluation.answer_eval import (
    AnswerExpectation,
    evaluate_answer,
)
from qnu.domains.evaluation.golden_suite import (
    GoldenTestCase,
    get_golden_suite,
    run_golden_suite,
)
from qnu.domains.evaluation.metrics import aggregate, retrieval_metrics


def test_answer_eval_passes_on_compliant_answer():
    response = {
        "status": "answered",
        "answer": "Điểm chuẩn năm 2025 cao nhất là ngành Sư phạm Toán với 27.5 điểm. [E1]",
        "statements": [{"text": "Ngành Sư phạm Toán có điểm 27.5.", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
        "trace": {},
    }
    expectation = AnswerExpectation(
        expected_status="answered",
        must_contain=["Sư phạm Toán", "27.5"],
        must_not_contain=["ngoại lệ"],
    )
    result = evaluate_answer(response, expectation)
    assert result.passed is True
    assert result.correctness_score == 1.0
    assert result.groundedness_score == 1.0
    assert len(result.failures) == 0


def test_answer_eval_flags_status_mismatch():
    response = {
        "status": "answered",
        "answer": "Thông tư 08 quy định cụ thể như sau...",
        "statements": [{"text": "Thông tư 08", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    }
    expectation = AnswerExpectation(
        expected_status="insufficient_evidence",
        must_contain=["Thông tư 08", "chưa có"],
    )
    result = evaluate_answer(response, expectation)
    assert result.passed is False
    assert any("Trạng thái không khớp" in f for f in result.failures)
    assert any("thiếu cụm từ bắt buộc" in f for f in result.failures)


def test_answer_eval_flags_forbidden_hallucinated_phrase():
    response = {
        "status": "answered",
        "answer": "Thí sinh được tự do thay thế bất kỳ môn nào của tổ hợp A sang B.",
        "statements": [{"text": "Thay thế môn", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    }
    expectation = AnswerExpectation(
        expected_status="answered",
        must_not_contain=["được tự do thay thế bất kỳ"],
    )
    result = evaluate_answer(response, expectation)
    assert result.passed is False
    assert any("chứa cụm từ bị cấm" in f for f in result.failures)


def test_answer_eval_enforces_year_conflict_invariant_4():
    # Suppression: only reports 2025, hides 2026
    suppressed_response = {
        "status": "answered",
        "answer": "Mức quy đổi điểm IELTS 5.5 là 9.0 điểm theo quy định năm 2025.",
        "statements": [{"text": "IELTS 5.5 = 9.0", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    }
    expectation = AnswerExpectation(
        expected_status="answered",
        expected_year_conflict=True,
        must_contain=["2025", "2026", "9.0", "8.5"],
    )
    res1 = evaluate_answer(suppressed_response, expectation)
    assert res1.passed is False
    assert any("xung đột niên độ" in f for f in res1.failures)

    # Compliant: discloses both 2025 and 2026
    compliant_response = {
        "status": "answered",
        "answer": "Theo Đề án 2025, IELTS 5.5 quy đổi thành 9.0 điểm; tuy nhiên theo Đề án 2026, mức quy đổi là 8.5 điểm.",
        "statements": [{"text": "2025: 9.0; 2026: 8.5", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    }
    res2 = evaluate_answer(compliant_response, expectation)
    assert res2.passed is True
    assert res2.correctness_score == 1.0


def test_answer_eval_enforces_irac_reasoning_trace():
    no_trace_response = {
        "status": "answered",
        "answer": "Không được dùng tổ hợp A00 thay cho D01 vào Sư phạm.",
        "statements": [{"text": "Quy chế tổ hợp", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
        "trace": {"reasoning": {}},
    }
    expectation = AnswerExpectation(
        expected_status="answered",
        require_irac_reasoning=True,
        must_contain=["tổ hợp"],
    )
    res_no_trace = evaluate_answer(no_trace_response, expectation)
    assert res_no_trace.passed is False
    assert any("Thiếu phân tích suy luận IRAC" in f for f in res_no_trace.failures)

    trace_response = {
        "status": "answered",
        "answer": "Không được dùng tổ hợp A00 thay cho D01 vào Sư phạm.",
        "statements": [{"text": "Quy chế tổ hợp", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
        "trace": {
            "reasoning": {
                "analysis": "1. Vấn đề: thay thế tổ hợp. 2. Quy tắc: loại trừ sư phạm. 3. Áp dụng: không đủ điều kiện. 4. Kết luận: từ chối.",
                "steps": ["Vấn đề", "Quy tắc", "Áp dụng", "Kết luận"],
            }
        },
    }
    res_trace = evaluate_answer(trace_response, expectation)
    assert res_trace.passed is True


def test_answer_eval_enforces_calculator_missing_variables_discipline():
    # Hallucinating 0 instead of refusing
    bad_calc_response = {
        "status": "answered",
        "answer": "Kết quả tính điểm là 5.4 (thay B = 0 điểm).",
        "statements": [{"text": "5.4 điểm", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
        "trace": {"calculator": {"status": "success", "result": 5.4}},
    }
    expectation = AnswerExpectation(
        expected_status="insufficient_evidence",
        require_calculator=True,
        expected_missing_vars=["B"],
        must_contain=["Chưa đủ điều kiện tính", "B"],
        must_not_contain=["0 điểm", "thay B = 0"],
    )
    bad_res = evaluate_answer(bad_calc_response, expectation)
    assert bad_res.passed is False
    assert any("Trạng thái không khớp" in f for f in bad_res.failures)
    assert any("cụm từ bị cấm" in f for f in bad_res.failures)

    # Disciplined refusal
    good_calc_response = {
        "status": "insufficient_evidence",
        "message": "Chưa đủ điều kiện tính điểm vì thiếu biến B trong công thức.",
        "trace": {"calculator": {"status": "missing_variables", "missing_variables": ["B"]}},
    }
    good_res = evaluate_answer(good_calc_response, expectation)
    assert good_res.passed is True


def test_answer_eval_enforces_code_preservation_leading_zeros():
    dropped_zero_response = {
        "status": "answered",
        "answer": "Thông tin mã ngành 12 và mã ngành 120 là...",
        "statements": [{"text": "Mã ngành 12", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    }
    expectation = AnswerExpectation(
        expected_status="answered",
        exact_code_anchors=["0012", "0120"],
        must_contain=["0012", "0120"],
    )
    res_dropped = evaluate_answer(dropped_zero_response, expectation)
    assert res_dropped.passed is False
    assert any("0012" in f for f in res_dropped.failures)

    preserved_response = {
        "status": "answered",
        "answer": "Thông tin mã ngành 0012 và mã ngành 0120 khác nhau về đối tượng tuyển sinh.",
        "statements": [{"text": "Mã 0012 và 0120", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    }
    res_preserved = evaluate_answer(preserved_response, expectation)
    assert res_preserved.passed is True


def test_answer_eval_enforces_groundedness():
    # Answered status with no statements or sources is ungrounded
    ungrounded_response = {
        "status": "answered",
        "answer": "Ngành CNTT có điểm chuẩn 25.0.",
        "statements": [],
        "sources": [],
    }
    expectation = AnswerExpectation(expected_status="answered")
    res = evaluate_answer(ungrounded_response, expectation)
    assert res.passed is False
    assert res.groundedness_score == 0.0
    assert any("Groundedness vi phạm" in f for f in res.failures)


def test_golden_suite_structure_and_counts():
    cases = get_golden_suite()
    assert len(cases) == 18

    groups = {c.group for c in cases}
    assert groups == {
        "tabular_aggregation",
        "rule_reasoning",
        "multi_turn",
        "year_conflict",
        "calculator_and_negations",
        "code_preservation",
    }

    for grp in groups:
        grp_cases = [c for c in cases if c.group == grp]
        assert len(grp_cases) == 3, f"Group {grp} should have 3 representative cases"


@pytest.mark.asyncio
async def test_run_golden_suite_end_to_end_mock_runner():
    cases = get_golden_suite()

    async def mock_runner(case: GoldenTestCase):
        # Generate fully compliant mock responses for all 18 cases
        if case.id == "g1_list_majors_cs":
            return {
                "status": "answered",
                "answer": "Các ngành xét môn Tin học năm 2026: Công nghệ thông tin (mã ngành 7480201).",
                "statements": [{"text": "Ngành 7480201 xét môn Tin học.", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g1_max_cutoff_score":
            return {
                "status": "answered",
                "answer": "Ngành có điểm chuẩn năm 2025 cao nhất là Sư phạm Toán với 27.5 điểm.",
                "statements": [{"text": "Sư phạm Toán 27.5", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g1_count_quota":
            return {
                "status": "answered",
                "answer": "Tổng chỉ tiêu tuyển sinh khối ngành Kỹ thuật năm 2026 là 450 chỉ tiêu.",
                "statements": [{"text": "Chỉ tiêu Kỹ thuật", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g2_combo_score_substitution":
            return {
                "status": "answered",
                "answer": "Nguyên tắc tính theo tổ hợp xét tuyển quy định không được tự do chuyển đổi điểm môn. Ngành Sư phạm thuộc diện loại trừ và có ngưỡng đầu vào riêng.",
                "statements": [{"text": "Quy định tổ hợp", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
                "trace": {"reasoning": {"analysis": "IRAC analysis", "steps": ["I", "R", "A", "C"]}},
            }
        elif case.id == "g2_early_graduation":
            return {
                "status": "answered",
                "answer": "Sinh viên không được tốt nghiệp sớm khi thiếu chứng chỉ ngoại ngữ. Chứng chỉ ngoại ngữ là điều kiện tốt nghiệp bắt buộc.",
                "statements": [{"text": "Điều kiện ngoại ngữ", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
                "trace": {"reasoning": {"analysis": "IRAC analysis", "steps": ["I", "R", "A", "C"]}},
            }
        elif case.id == "g2_external_circular_unknown":
            return {
                "status": "insufficient_evidence",
                "message": "Hệ thống chưa có văn bản Thông tư 08 đầy đủ trong cơ sở dữ liệu hiện tại.",
            }
        elif case.id == "g3_major_year_followup":
            return {
                "status": "answered",
                "answer": "Thông tin tuyển sinh năm 2026 ngành Công nghệ thông tin (mã ngành 7480201)...",
                "statements": [{"text": "Ngành CNTT 2026", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g3_anaphora_tuition":
            return {
                "status": "answered",
                "answer": "Học phí của ngành Kỹ thuật phần mềm là 450.000đ/tín chỉ.",
                "statements": [{"text": "Học phí Kỹ thuật phần mềm", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g3_clarification_choice":
            return {
                "status": "answered",
                "answer": "Theo phương thức 2 xét tuyển ngành Ngôn ngữ Anh...",
                "statements": [{"text": "PT2 Ngôn ngữ Anh", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g4_ielts_conversion_conflict":
            return {
                "status": "answered",
                "answer": "Theo quy chế năm 2025, IELTS 5.5 quy đổi thành 9.0; sang năm 2026 mức quy đổi điều chỉnh thành 8.5.",
                "statements": [{"text": "2025: 9.0; 2026: 8.5", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g4_quota_conflict":
            return {
                "status": "answered",
                "answer": "Chỉ tiêu ngành Quản trị kinh doanh năm 2025 là 120, năm 2026 là 150.",
                "statements": [{"text": "2025 và 2026", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g4_english_exit_req":
            return {
                "status": "answered",
                "answer": "Theo quy chế 2024 chuẩn đầu ra là B1, nhưng quy chế 2026 yêu cầu chuẩn B2.",
                "statements": [{"text": "2024 và 2026", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g5_calc_full_variables":
            return {
                "status": "answered",
                "answer": "Điểm đánh giá rèn luyện Q = 8.025.",
                "statements": [{"text": "Q = 8.025", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
                "trace": {"calculator": {"status": "success", "result": 8.025}},
            }
        elif case.id == "g5_calc_missing_vars_refusal":
            return {
                "status": "insufficient_evidence",
                "message": "Chưa đủ điều kiện tính điểm vì thiếu biến B trong công thức.",
                "trace": {"calculator": {"status": "missing_variables", "missing_variables": ["B"]}},
            }
        elif case.id == "g5_negation_exclusion":
            return {
                "status": "answered",
                "answer": "Không được áp dụng ưu tiên thiết bị của nhóm A cho nhóm B.",
                "statements": [{"text": "Chỉ áp dụng nhóm A", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g6_leading_zero_major_code":
            return {
                "status": "answered",
                "answer": "Mã ngành 0012 và mã ngành 0120 là hai mã riêng biệt.",
                "statements": [{"text": "0012 và 0120", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g6_course_code_anchors":
            return {
                "status": "answered",
                "answer": "Học phần AM-0007 là học phần tiên quyết của AM-0070.",
                "statements": [{"text": "AM-0007 và AM-0070", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        elif case.id == "g6_zero_vs_slash_priority":
            return {
                "status": "answered",
                "answer": "Số 0 thể hiện không có điểm cộng ưu tiên, khác biệt hoàn toàn với ô trống hoặc dấu gạch chéo '/'.",
                "statements": [{"text": "0 khác /", "evidence_ids": ["E1"]}],
                "sources": [{"evidence_id": "E1"}],
            }
        raise ValueError(f"Unknown case {case.id}")

    report = await run_golden_suite(cases, mock_runner)
    assert report.total_cases == 18
    assert report.passed_cases == 18
    assert report.failed_cases == 0
    assert report.pass_rate == 1.0
    assert report.overall_passed is True

    for summary in report.group_summaries.values():
        assert summary["total"] == 3
        assert summary["passed"] == 3
        assert summary["pass_rate"] == 1.0
        assert summary["mean_correctness"] == 1.0
        assert summary["mean_groundedness"] == 1.0


def test_metrics_aggregation_with_answer_eval():
    records = [
        {
            "query_id": "q1",
            "group": "group_a",
            "strategy": "hybrid",
            "status": "completed",
            "metrics": retrieval_metrics(
                ["c1", "c2"],
                ["c1"],
                2,
                answer_correctness=1.0,
                answer_groundedness=1.0,
                answer_passed=True,
            ),
        },
        {
            "query_id": "q2",
            "group": "group_a",
            "strategy": "hybrid",
            "status": "completed",
            "metrics": retrieval_metrics(
                ["c2", "c3"],
                ["c1"],
                2,
                answer_correctness=0.8,
                answer_groundedness=1.0,
                answer_passed=False,
                answer_failures=["Missing term"],
            ),
        },
    ]
    summary = aggregate(records)
    hybrid_metrics = summary["hybrid"]["completed_only_metrics"]
    assert hybrid_metrics["answer_correctness"] == 0.9
    assert hybrid_metrics["answer_groundedness"] == 1.0
    assert summary["hybrid"]["answer_pass_rate"] == 0.5
