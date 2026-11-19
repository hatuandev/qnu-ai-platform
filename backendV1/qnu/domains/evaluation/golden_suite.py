"""Official EvalOps Golden Suite for QNU AI Platform.

Benchmark regression suite implementing the 6 Stress-Test Checklist groups
from RULE_REASONING_PROMPTS_SPEC.md Section 6.2:
1. Bảng biểu & Liệt kê (Tabular Aggregation: SUM, COUNT, schema listing)
2. Suy luận quy chế đa vế & Dẫn chiếu ngoài (IRAC, multi-clause exclusions)
3. Hội thoại đa lượt (Multi-turn Contextual Rewriting, anaphora resolution)
4. Xung đột niên độ (Cross-year conflicts, Invariant #4: 2025 vs 2026)
5. Phủ định & Công thức tất định (Deterministic Calculator, missing variables refusal)
6. Bảo toàn mã & Ký hiệu gốc (Entity code preservation, leading zeros, 0 vs '/' vs blank)
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from qnu.domains.evaluation.answer_eval import (
    AnswerEvaluationResult,
    AnswerExpectation,
    evaluate_answer,
)


class GoldenTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    group: Literal[
        "tabular_aggregation",
        "rule_reasoning",
        "multi_turn",
        "year_conflict",
        "calculator_and_negations",
        "code_preservation",
    ]
    name: str
    question: str
    history: list[dict] | None = None
    fact_query: dict | None = None
    calculation: dict | None = None
    document_ids: list[str] | None = None
    expectation: AnswerExpectation


class GoldenSuiteReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    overall_passed: bool
    group_summaries: dict[str, dict[str, Any]]
    failures: list[dict[str, Any]]


def get_golden_suite() -> list[GoldenTestCase]:
    """Return the 18 official benchmark cases covering the 6 stress-test groups."""
    return [
        # =========================================================================
        # Group 1: Bảng biểu & Liệt kê (Tabular Aggregation)
        # =========================================================================
        GoldenTestCase(
            id="g1_list_majors_cs",
            group="tabular_aggregation",
            name="Liệt kê ngành có môn Tin học năm 2026",
            question="Liệt kê tất cả các ngành xét tuyển có môn Tin học năm 2026",
            fact_query={
                "columns": ["major_code", "major_name"],
                "filters": {"subject": "Tin học", "year": "2026"},
            },
            expectation=AnswerExpectation(
                expected_status="answered",
                must_contain=["7480201", "Công nghệ thông tin"],
                must_not_contain=[],
            ),
        ),
        GoldenTestCase(
            id="g1_max_cutoff_score",
            group="tabular_aggregation",
            name="Tìm ngành có điểm chuẩn năm 2025 cao nhất",
            question="Ngành nào có điểm chuẩn năm 2025 cao nhất?",
            expectation=AnswerExpectation(
                expected_status="answered",
                must_contain=["Sư phạm Toán", "27.5"],
                must_not_contain=[],
            ),
        ),
        GoldenTestCase(
            id="g1_count_quota",
            group="tabular_aggregation",
            name="Thống kê chỉ tiêu khối ngành Kỹ thuật",
            question="Tổng chỉ tiêu tuyển sinh khối ngành Kỹ thuật năm 2026 là bao nhiêu?",
            expectation=AnswerExpectation(
                expected_status="answered",
                must_contain=["chỉ tiêu", "Kỹ thuật"],
                must_not_contain=[],
            ),
        ),
        # =========================================================================
        # Group 2: Suy luận quy chế đa vế & Dẫn chiếu ngoài (IRAC)
        # =========================================================================
        GoldenTestCase(
            id="g2_combo_score_substitution",
            group="rule_reasoning",
            name="Dùng điểm tổ hợp A thay cho tổ hợp B vào ngành Sư phạm",
            question="Thí sinh có được dùng 15 điểm của tổ hợp A00 thay cho 13 điểm của tổ hợp D01 để xét học bạ vào ngành Sư phạm không?",
            expectation=AnswerExpectation(
                expected_status="answered",
                require_irac_reasoning=True,
                must_contain=["tổ hợp", "loại trừ", "Sư phạm", "ngưỡng đầu vào"],
                must_not_contain=["được tự do thay thế bất kỳ"],
            ),
        ),
        GoldenTestCase(
            id="g2_early_graduation",
            group="rule_reasoning",
            name="Đăng ký tốt nghiệp sớm khi thiếu chứng chỉ ngoại ngữ",
            question="Sinh viên có được đăng ký tốt nghiệp sớm khi chưa hoàn thành chứng chỉ ngoại ngữ nhưng đã đủ tín chỉ chuyên môn không?",
            expectation=AnswerExpectation(
                expected_status="answered",
                require_irac_reasoning=True,
                must_contain=["chứng chỉ ngoại ngữ", "tốt nghiệp", "bắt buộc"],
                must_not_contain=["được miễn chứng chỉ ngoại ngữ khi đủ tín chỉ"],
            ),
        ),
        GoldenTestCase(
            id="g2_external_circular_unknown",
            group="rule_reasoning",
            name="Quy định Thông tư ngoài chưa có văn bản dẫn chiếu",
            question="Theo Thông tư 08 của Bộ GD&ĐT quy định chi tiết về điểm ưu tiên như thế nào?",
            expectation=AnswerExpectation(
                expected_status="insufficient_evidence",
                must_contain=["Thông tư 08", "chưa có", "văn bản"],
                must_not_contain=["toàn văn Thông tư 08 quy định cụ thể rằng"],
            ),
        ),
        # =========================================================================
        # Group 3: Hội thoại đa lượt (Multi-turn Contextual Rewriting)
        # =========================================================================
        GoldenTestCase(
            id="g3_major_year_followup",
            group="multi_turn",
            name="Hội thoại lượt 2: bổ sung ngành và năm",
            question="Ngành CNTT năm 2026 ạ",
            history=[
                {
                    "role": "user",
                    "content": "Quy định xét tuyển năm 2026 của trường như thế nào?",
                },
                {
                    "role": "assistant",
                    "content": "Trường áp dụng các phương thức xét tuyển điểm thi THPT, học bạ và ĐGNL.",
                },
            ],
            expectation=AnswerExpectation(
                expected_status="answered",
                must_contain=["7480201", "Công nghệ thông tin", "2026"],
                must_not_contain=[],
            ),
        ),
        GoldenTestCase(
            id="g3_anaphora_tuition",
            group="multi_turn",
            name="Hội thoại lượt 2: giải quyết đại từ thay thế (nó)",
            question="Học phí của nó bao nhiêu một tín chỉ?",
            history=[
                {
                    "role": "user",
                    "content": "Ngành Kỹ thuật phần mềm đào tạo những gì?",
                },
                {
                    "role": "assistant",
                    "content": "Ngành Kỹ thuật phần mềm đào tạo phát triển ứng dụng và kiến trúc hệ thống.",
                },
            ],
            expectation=AnswerExpectation(
                expected_status="answered",
                must_contain=["Kỹ thuật phần mềm", "học phí"],
                must_not_contain=[],
            ),
        ),
        GoldenTestCase(
            id="g3_clarification_choice",
            group="multi_turn",
            name="Hội thoại lượt 2: trả lời câu hỏi làm rõ của bot",
            question="Phương thức 2 ạ",
            history=[
                {
                    "role": "user",
                    "content": "Điều kiện xét học bạ ngành Ngôn ngữ Anh?",
                },
                {
                    "role": "assistant",
                    "content": "Bạn muốn hỏi phương thức 1 (kết quả cả năm lớp 12) hay phương thức 2 (kết quả 3 học kỳ)?",
                },
            ],
            expectation=AnswerExpectation(
                expected_status="answered",
                must_contain=["phương thức 2", "Ngôn ngữ Anh"],
                must_not_contain=[],
            ),
        ),
        # =========================================================================
        # Group 4: Xung đột niên độ (Cross-year conflicts - Invariant #4)
        # =========================================================================
        GoldenTestCase(
            id="g4_ielts_conversion_conflict",
            group="year_conflict",
            name="Quy đổi IELTS 5.5 khi không nêu năm (2025: 9.0 vs 2026: 8.5)",
            question="Mức quy đổi điểm IELTS 5.5 sang thang điểm 10 là bao nhiêu?",
            expectation=AnswerExpectation(
                expected_status="answered",
                expected_year_conflict=True,
                must_contain=["2025", "2026", "9.0", "8.5"],
                must_not_contain=["chỉ áp dụng điểm 9.0", "chỉ áp dụng điểm 8.5"],
            ),
        ),
        GoldenTestCase(
            id="g4_quota_conflict",
            group="year_conflict",
            name="Chỉ tiêu ngành Quản trị kinh doanh qua các năm",
            question="Chỉ tiêu tuyển sinh ngành Quản trị kinh doanh là bao nhiêu?",
            expectation=AnswerExpectation(
                expected_status="answered",
                expected_year_conflict=True,
                must_contain=["2025", "2026"],
                must_not_contain=[],
            ),
        ),
        GoldenTestCase(
            id="g4_english_exit_req",
            group="year_conflict",
            name="Chuẩn đầu ra ngoại ngữ theo quy chế cũ và mới",
            question="Chuẩn đầu ra tiếng Anh đối với sinh viên không chuyên là B1 hay B2?",
            expectation=AnswerExpectation(
                expected_status="answered",
                expected_year_conflict=True,
                must_contain=["2024", "2026"],
                must_not_contain=[],
            ),
        ),
        # =========================================================================
        # Group 5: Phủ định & Công thức tất định (Deterministic Calculator)
        # =========================================================================
        GoldenTestCase(
            id="g5_calc_full_variables",
            group="calculator_and_negations",
            name="Tính điểm rèn luyện đủ biến và đạt điều kiện tiên quyết",
            question="Tính điểm đánh giá rèn luyện Q = 0.45*A + 0.35*B + 0.20*C với A=8.0, B=7.5, C=9.0, minh chứng 0.9",
            calculation={
                "formula": "0.45*A + 0.35*B + 0.20*C",
                "variables": {"A": 8.0, "B": 7.5, "C": 9.0},
                "preconditions": {"minh_chung": 0.9},
            },
            expectation=AnswerExpectation(
                expected_status="answered",
                require_calculator=True,
                must_contain=["8.025"],
                must_not_contain=[],
            ),
        ),
        GoldenTestCase(
            id="g5_calc_missing_vars_refusal",
            group="calculator_and_negations",
            name="Từ chối tính khi thiếu biến B (cấm thay B = 0)",
            question="Tính điểm đánh giá rèn luyện Q = 0.45*A + 0.35*B + 0.20*C khi có A=8.0, C=9.0",
            calculation={
                "formula": "0.45*A + 0.35*B + 0.20*C",
                "variables": {"A": 8.0, "C": 9.0},
            },
            expectation=AnswerExpectation(
                expected_status="insufficient_evidence",
                require_calculator=True,
                expected_missing_vars=["B"],
                must_contain=["Chưa đủ điều kiện tính", "B"],
                must_not_contain=["0 điểm", "thay B = 0", "5.4"],
            ),
        ),
        GoldenTestCase(
            id="g5_negation_exclusion",
            group="calculator_and_negations",
            name="Từ chối áp dụng chéo ngoại lệ nhóm A cho nhóm B",
            question="Có được áp dụng chính sách ưu tiên thiết bị của nhóm A năm 2027 cho thí sinh nhóm B không?",
            expectation=AnswerExpectation(
                expected_status="answered",
                must_contain=["không được", "nhóm A"],
                must_not_contain=["được phép áp dụng cho nhóm B"],
            ),
        ),
        # =========================================================================
        # Group 6: Bảo toàn mã & Ký hiệu gốc (Code Preservation)
        # =========================================================================
        GoldenTestCase(
            id="g6_leading_zero_major_code",
            group="code_preservation",
            name="Phân biệt mã ngành 0012 và 0120 (giữ số 0 đầu)",
            question="Thông tin tuyển sinh mã ngành 0012 và mã ngành 0120 khác nhau như thế nào?",
            expectation=AnswerExpectation(
                expected_status="answered",
                exact_code_anchors=["0012", "0120"],
                must_contain=["0012", "0120"],
                must_not_contain=["mã ngành 12", "mã ngành 120"],
            ),
        ),
        GoldenTestCase(
            id="g6_course_code_anchors",
            group="code_preservation",
            name="Bảo toàn mã học phần anh em AM-0007 và AM-0070",
            question="Học phần AM-0007 và AM-0070 học phần nào là tiên quyết?",
            expectation=AnswerExpectation(
                expected_status="answered",
                exact_code_anchors=["AM-0007", "AM-0070"],
                must_contain=["AM-0007", "AM-0070"],
                must_not_contain=[],
            ),
        ),
        GoldenTestCase(
            id="g6_zero_vs_slash_priority",
            group="code_preservation",
            name="Phân biệt số 0 điểm ưu tiên, ô trống và ký hiệu '/'",
            question="Điểm cộng ưu tiên của đối tượng 04 ghi số 0 nghĩa là gì, có giống dấu gạch chéo '/' không?",
            expectation=AnswerExpectation(
                expected_status="answered",
                must_contain=["0", "không có", "khác"],
                must_not_contain=["đều là ô trống"],
            ),
        ),
    ]


async def run_golden_suite(
    cases: list[GoldenTestCase] | None = None,
    runner_fn: Callable[[GoldenTestCase], Any] | None = None,
) -> GoldenSuiteReport:
    """Execute the golden suite against a test runner function and evaluate results."""
    if cases is None:
        cases = get_golden_suite()

    if runner_fn is None:
        raise ValueError("runner_fn must be provided to run the golden suite.")

    failures: list[dict[str, Any]] = []
    passed_cases = 0
    group_results: dict[str, list[AnswerEvaluationResult]] = {}

    for case in cases:
        group_results.setdefault(case.group, [])
        if inspect.iscoroutinefunction(runner_fn):
            response = await runner_fn(case)
        else:
            response = runner_fn(case)

        eval_result = evaluate_answer(response, case.expectation)
        group_results[case.group].append(eval_result)

        if eval_result.passed:
            passed_cases += 1
        else:
            failures.append(
                {
                    "case_id": case.id,
                    "group": case.group,
                    "name": case.name,
                    "question": case.question,
                    "failures": eval_result.failures,
                    "breakdown": eval_result.breakdown,
                    "correctness_score": eval_result.correctness_score,
                    "groundedness_score": eval_result.groundedness_score,
                }
            )

    total_cases = len(cases)
    pass_rate = round(passed_cases / total_cases, 4) if total_cases > 0 else 0.0

    group_summaries: dict[str, dict[str, Any]] = {}
    for grp, results in group_results.items():
        grp_passed = sum(1 for r in results if r.passed)
        grp_total = len(results)
        grp_correctness = sum(r.correctness_score for r in results) / grp_total if grp_total else 0.0
        grp_groundedness = sum(r.groundedness_score for r in results) / grp_total if grp_total else 0.0
        group_summaries[grp] = {
            "total": grp_total,
            "passed": grp_passed,
            "pass_rate": round(grp_passed / grp_total, 4) if grp_total else 0.0,
            "mean_correctness": round(grp_correctness, 4),
            "mean_groundedness": round(grp_groundedness, 4),
        }

    return GoldenSuiteReport(
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=total_cases - passed_cases,
        pass_rate=pass_rate,
        overall_passed=(pass_rate == 1.0),
        group_summaries=group_summaries,
        failures=failures,
    )
