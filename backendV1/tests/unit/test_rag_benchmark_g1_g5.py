"""Schema validation and automated G1–G5 contrast evaluation for RAG benchmark suite.

Validates `backendV1/benchmarks/rag_benchmark_md_xlsx.json` integrity (scoring scale,
group counts, unique sequential IDs, deduplication) and evaluates all 5 contrast groups
(G1–G5) against `qnu.domains.evaluation.answer_eval.evaluate_answer` (both compliant
answers and regression-detection negative cases).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

import pytest

from qnu.domains.conversations.benchmarks import (
    _normalize_question,
    get_benchmark_path,
    is_question_in_benchmark,
)
from qnu.domains.evaluation.answer_eval import (
    AnswerExpectation,
    evaluate_answer,
)

REQUIRED_G_GROUPS: dict[str, str] = {
    "G1": "g1_direct_grounded_evidence",
    "G2": "g2_mandatory_conditions_and_exceptions",
    "G3": "g3_tables_and_multi_year_metrics",
    "G4": "g4_out_of_scope_refusal",
    "G5": "g5_multi_part_and_partial_comparison",
}


def _load_suite() -> dict[str, Any]:
    path = get_benchmark_path()
    assert path.exists(), f"Không tìm thấy tệp benchmark: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _expectation_from_case(case: dict[str, Any]) -> AnswerExpectation:
    return AnswerExpectation(
        expected_status=case.get("expected_status"),
        must_contain=list(case.get("must_contain") or []),
        must_contain_any=list(case.get("must_contain_any") or []),
        must_not_contain=list(case.get("must_not_contain") or []),
    )


def test_benchmark_suite_schema_totals_and_deduplication():
    suite = _load_suite()
    questions: list[dict[str, Any]] = suite["questions"]
    groups: list[dict[str, Any]] = suite["groups"]
    scoring: dict[str, Any] = suite["scoring_scale"]

    # 1. Scoring scale consistency
    assert scoring["total_questions"] == len(questions)
    assert scoring["max_total_score"] == len(questions) * scoring["max_score_per_question"]
    assert len(questions) >= 34

    # 2. Unique sequential IDs (Q01..QNN) compatible with promote-to-benchmark
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "ID câu hỏi trong benchmark bị trùng lặp"
    for idx, qid in enumerate(ids, start=1):
        assert re.fullmatch(r"Q\d{2,}", qid), f"ID không đúng quy ước: {qid}"
        assert int(qid[1:]) == idx, f"ID không liên tục tại vị trí {idx}: {qid}"

    # 3. Zero duplicate normalized questions
    normalized = [_normalize_question(q["question"]) for q in questions]
    duplicates = [text for text, count in Counter(normalized).items() if count > 1]
    assert not duplicates, f"Phát hiện câu hỏi trùng lặp: {duplicates}"

    # 4. Group counts match actual questions
    group_map = {g["id"]: g for g in groups}
    actual_counts = Counter(q["group"] for q in questions)
    for gid, ginfo in group_map.items():
        assert actual_counts[gid] == ginfo["question_count"], (
            f"Nhóm {gid}: question_count={ginfo['question_count']} != thực tế {actual_counts[gid]}"
        )
    assert set(actual_counts.keys()) == set(group_map.keys())

    # 5. Required fields on every question
    required_fields = (
        "id",
        "group",
        "doc_scope",
        "question",
        "expected_points",
        "expected_behavior",
        "forbidden_behaviors",
    )
    for q in questions:
        for field in required_fields:
            assert q.get(field), f"Câu {q.get('id')} thiếu trường bắt buộc '{field}'"
        found, matched_id = is_question_in_benchmark(suite, q["question"])
        assert found is True and matched_id == q["id"]


def test_benchmark_suite_covers_all_five_contrast_groups_g1_to_g5():
    suite = _load_suite()
    groups_by_id = {g["id"]: g for g in suite["groups"]}
    questions = suite["questions"]

    for code, gid in REQUIRED_G_GROUPS.items():
        assert gid in groups_by_id, f"Thiếu nhóm đối chứng {code} ({gid})"
        assert groups_by_id[gid].get("code") == code
        grp_questions = [q for q in questions if q["group"] == gid]
        assert len(grp_questions) >= 2, f"Nhóm {code} phải có ít nhất 2 câu đối chứng"
        for q in grp_questions:
            assert q.get("benchmark_category") == code
            assert q.get("expected_status") in {"answered", "insufficient_evidence"}
            assert q.get("must_contain"), f"Câu {q['id']} thiếu must_contain"
            assert q.get("must_not_contain"), f"Câu {q['id']} thiếu must_not_contain"
            if code == "G4":
                assert q["expected_status"] == "insufficient_evidence"
            else:
                assert q["expected_status"] == "answered"


COMPLIANT_RESPONSES_BY_ID: dict[str, dict[str, Any]] = {
    "Q25": {
        "status": "answered",
        "answer": (
            "Theo Khoản 1 Điều 12, điểm tổng kết học phần gồm điểm quá trình (trọng số từ 40% "
            "đến 50%) và điểm thi kết thúc học phần (trọng số từ 50% đến 60%). [E1]"
        ),
        "statements": [{"text": "Trọng số 40%-50% và 50%-60%", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q26": {
        "status": "answered",
        "answer": (
            "Theo Điều 2, chương trình kỹ sư/sư phạm đặc thù có thời gian đào tạo tiêu chuẩn là "
            "4.5 năm. Theo Khoản 3 Điều 5, trong học kỳ phụ sinh viên được đăng ký tối đa 10 tín chỉ. [E1][E2]"
        ),
        "statements": [{"text": "4.5 năm và tối đa 10 tín chỉ", "evidence_ids": ["E1", "E2"]}],
        "sources": [{"evidence_id": "E1"}, {"evidence_id": "E2"}],
    },
    "Q27": {
        "status": "answered",
        "answer": (
            "Không được xét công nhận tốt nghiệp. Dù đã đạt tín chỉ và GPA, Khoản 6 Điều 20 quy "
            "định bắt buộc sinh viên không đang trong thời gian bị kỷ luật từ mức đình chỉ học tập trở lên. [E1]"
        ),
        "statements": [{"text": "Điều kiện loại trừ kỷ luật đình chỉ học tập", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q28": {
        "status": "answered",
        "answer": (
            "Sinh viên không được rút học phần 3 tín chỉ này. Theo Điều 6 kết hợp Điều 5, dù đang "
            "trong 02 tuần đầu nhưng sau khi rút chỉ còn 9 tín chỉ, thấp hơn mức tối thiểu 10 tín chỉ "
            "đối với sinh viên học lực yếu. [E1][E2]"
        ),
        "statements": [{"text": "Không được rút dưới mức tối thiểu 10 tín chỉ", "evidence_ids": ["E1", "E2"]}],
        "sources": [{"evidence_id": "E1"}, {"evidence_id": "E2"}],
    },
    "Q29": {
        "status": "answered",
        "answer": (
            "Theo bảng Điều 12: A (8.5 đến 10.0, hệ 4 là 4.0, Giỏi / Xuất sắc); "
            "B (7.0 đến 8.4, hệ 4 là 3.0, Khá); C (5.5 đến 6.9, hệ 4 là 2.0, Trung bình); "
            "D (4.0 đến 5.4, hệ 4 là 1.0, Trung bình yếu). [E1]"
        ),
        "statements": [{"text": "Bảng quy đổi điểm A, B, C, D", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q30": {
        "status": "answered",
        "answer": (
            "Trong sheet 'Số ĐKCB sót so với file KK (Thơ': năm 2006 có DTB.000102; "
            "năm 2011 có DTB.000095-000096, DTB.000097-000099, DTB.000107; "
            "năm 2012 có DTB.000100, DTB.000101, DTB.000103, DTB.000105-000106. "
            "Không có bản ghi nào xuất bản năm 2015 trong sheet này. [E1]"
        ),
        "statements": [{"text": "Danh sách ĐKCB theo năm 2006, 2011, 2012", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q31": {
        "status": "insufficient_evidence",
        "answer": None,
        "message": (
            "Hiện chưa tìm thấy thông tin về mức lệ phí thi lại và quy trình phúc khảo bài thi "
            "trong Quy định đào tạo tín chỉ được cung cấp."
        ),
        "statements": [],
        "sources": [],
    },
    "Q32": {
        "status": "insufficient_evidence",
        "answer": None,
        "message": (
            "Tài liệu chỉ dẫn chiếu tên Thông tư số 03/2014/TT-BTTTT tại Điều 20 và không chứa "
            "nội dung chi tiết 6 mô-đun kỹ năng."
        ),
        "statements": [],
        "sources": [],
    },
    "Q33": {
        "status": "answered",
        "answer": (
            "Theo Điều 18, ngưỡng điểm TB tích lũy bị cảnh báo là dưới 1.20 (năm thứ nhất), "
            "dưới 1.40 (năm thứ hai) và dưới 1.60 (năm thứ ba). Văn bản không quy định ngưỡng "
            "riêng cho sinh viên năm thứ tư. [E1]"
        ),
        "statements": [{"text": "Ngưỡng cảnh báo năm 1-3 và khuyết năm thứ tư", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q34": {
        "status": "answered",
        "answer": (
            "Trong sheet 'Dữ liệu chuẩn hóa', cuốn 'English in Focus' (Nicholas Sampson) có giá "
            "45.000đ và 416 tr; cuốn 'English in Focus' (Diana Green) có giá 15.000đ và 216 tr. "
            "Tài liệu không có dữ liệu về số lượt mượn thực tế trong năm 2025. [E1]"
        ),
        "statements": [{"text": "So sánh 2 cuốn English in Focus", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
}

REGRESSION_RESPONSES_BY_ID: dict[str, dict[str, Any]] = {
    "Q25": {
        "status": "answered",
        "answer": "Điểm tổng kết gồm điểm quá trình 30% và điểm thi cuối kỳ 70%. [E1]",
        "statements": [{"text": "Sai trọng số", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q26": {
        "status": "answered",
        "answer": "Chương trình kỹ sư là 4 năm và được đăng ký tối đa 14 tín chỉ trong học kỳ phụ. [E1]",
        "statements": [{"text": "Nhầm số liệu", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q27": {
        "status": "answered",
        "answer": "Sinh viên vẫn được xét tốt nghiệp vì đã đủ tín chỉ và GPA trên 2.00. [E1]",
        "statements": [{"text": "Bỏ sót ngoại lệ kỷ luật", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q28": {
        "status": "answered",
        "answer": "Sinh viên được rút bình thường vì trong 2 tuần đầu của học kỳ chính. [E1]",
        "statements": [{"text": "Bỏ sót ràng buộc 10 tín chỉ", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q29": {
        "status": "answered",
        "answer": "Bảng điểm gồm A (4.0), B+ (3.5), B (3.0), C+ (2.5). [E1]",
        "statements": [{"text": "Tự bịa B+ C+", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q30": {
        "status": "answered",
        "answer": "Các mã năm 2015 gồm DTB.000102 và DTB.000107. [E1]",
        "statements": [{"text": "Gộp sai năm", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q31": {
        "status": "answered",
        "answer": "Lệ phí thi lại là 100.000đ và nộp đơn phúc khảo trong vòng 7 ngày kể từ ngày công bố điểm. [E1]",
        "statements": [{"text": "Suy diễn ngoài tài liệu", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q32": {
        "status": "answered",
        "answer": "Thông tư 03/2014/TT-BTTTT gồm 6 mô-đun IU01, IU02, IU03, IU04, IU05, IU06. [E1]",
        "statements": [{"text": "Dùng kiến thức ngoài", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q33": {
        "status": "answered",
        "answer": "Năm 1 dưới 1.20, năm 2 dưới 1.40, năm 3 dưới 1.60 và năm thứ tư dưới 1.80. [E1]",
        "statements": [{"text": "Tự suy diễn năm thứ tư", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    },
    "Q34": {
        "status": "insufficient_evidence",
        "answer": None,
        "message": "Không đủ dữ liệu để trả lời câu hỏi này.",
        "statements": [],
        "sources": [],
    },
}


@pytest.mark.parametrize("code", ["G1", "G2", "G3", "G4", "G5"])
def test_g1_to_g5_benchmark_evaluation_passes_compliant_and_catches_regressions(code: str):
    suite = _load_suite()
    gid = REQUIRED_G_GROUPS[code]
    cases = [q for q in suite["questions"] if q["group"] == gid]
    assert len(cases) == 2

    for case in cases:
        qid = case["id"]
        expectation = _expectation_from_case(case)

        compliant_res = evaluate_answer(COMPLIANT_RESPONSES_BY_ID[qid], expectation)
        assert compliant_res.passed is True, (
            f"[{code}/{qid}] Ca đạt chuẩn nhưng evaluator báo lỗi: {compliant_res.failures}"
        )
        assert compliant_res.correctness_score == 1.0
        assert compliant_res.groundedness_score == 1.0

        regression_res = evaluate_answer(REGRESSION_RESPONSES_BY_ID[qid], expectation)
        assert regression_res.passed is False, (
            f"[{code}/{qid}] Evaluator không phát hiện ca lỗi hồi quy!"
        )
        assert len(regression_res.failures) >= 1


def test_q17_expected_status_and_q26_vietnamese_decimal_variant():
    suite = _load_suite()
    q_by_id = {q["id"]: q for q in suite["questions"]}

    assert q_by_id["Q17"]["expected_status"] == "insufficient_evidence"

    q26_exp = _expectation_from_case(q_by_id["Q26"])
    vn_decimal_resp = {
        "status": "answered",
        "answer": "Chương trình kỹ sư/sư phạm đặc thù kéo dài 4,5 năm; học kỳ phụ tối đa 10 tín chỉ. [E1]",
        "statements": [{"text": "4,5 năm và 10 tín chỉ", "evidence_ids": ["E1"]}],
        "sources": [{"evidence_id": "E1"}],
    }
    res = evaluate_answer(vn_decimal_resp, q26_exp)
    assert res.passed is True
    assert res.correctness_score == 1.0
