"""Automated Answer Evaluation Engine for QNU EvalOps.

Measures answer correctness, factual groundedness, IRAC reasoning presence,
cross-year conflict transparency (AGENTS.md Invariant #4), missing variables
enforcement (no defaulting to 0), and entity code preservation (zero prefixes
and confusable siblings) against golden benchmarks.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AnswerExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_status: Literal["answered", "insufficient_evidence"] | None = None
    must_contain: list[str] = Field(default_factory=list)
    must_not_contain: list[str] = Field(default_factory=list)
    expected_citations: list[str] = Field(default_factory=list)
    expected_year_conflict: bool | None = None
    require_irac_reasoning: bool | None = None
    require_calculator: bool | None = None
    expected_missing_vars: list[str] = Field(default_factory=list)
    exact_code_anchors: list[str] = Field(default_factory=list)


class AnswerEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passed: bool
    correctness_score: float = Field(ge=0.0, le=1.0)
    groundedness_score: float = Field(ge=0.0, le=1.0)
    breakdown: dict[str, str] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)


def evaluate_answer(
    response: Any,
    expectation: AnswerExpectation | None,
) -> AnswerEvaluationResult:
    """Evaluate an AnswerResponse (or equivalent dict) against golden expectation."""
    if expectation is None:
        return AnswerEvaluationResult(
            passed=True,
            correctness_score=1.0,
            groundedness_score=1.0,
            breakdown={"status": "no_expectation"},
            failures=[],
        )

    # Normalize response to dictionary
    if isinstance(response, BaseModel):
        data = response.model_dump()
    elif isinstance(response, dict):
        data = response
    else:
        data = {
            "status": getattr(response, "status", "insufficient_evidence"),
            "answer": getattr(response, "answer", None),
            "message": getattr(response, "message", None),
            "trace": getattr(response, "trace", {}),
            "statements": getattr(response, "statements", []),
            "sources": getattr(response, "sources", []),
        }

    status = data.get("status")
    answer_text = data.get("answer") or ""
    message_text = data.get("message") or ""
    combined_text = f"{answer_text}\n{message_text}".strip()
    trace = data.get("trace") or {}
    if isinstance(trace, BaseModel):
        trace = trace.model_dump()
    statements = data.get("statements") or []
    sources = data.get("sources") or []

    failures: list[str] = []
    breakdown: dict[str, str] = {}
    total_checks = 0
    passed_checks = 0

    # 1. Status check
    if expectation.expected_status is not None:
        total_checks += 1
        if status == expectation.expected_status:
            passed_checks += 1
            breakdown["status"] = "pass"
        else:
            breakdown["status"] = "fail"
            failures.append(
                f"Trạng thái không khớp: kỳ vọng '{expectation.expected_status}', thực tế '{status}'"
            )

    # 2. Must contain phrases
    for term in expectation.must_contain:
        total_checks += 1
        if term.lower() in combined_text.lower():
            passed_checks += 1
            breakdown[f"contain:{term}"] = "pass"
        else:
            breakdown[f"contain:{term}"] = "fail"
            failures.append(f"Câu trả lời thiếu cụm từ bắt buộc: '{term}'")

    # 3. Must not contain phrases (hallucination & improper default defense)
    for forbidden in expectation.must_not_contain:
        total_checks += 1
        if forbidden.lower() in combined_text.lower():
            breakdown[f"forbid:{forbidden}"] = "fail"
            failures.append(f"Câu trả lời chứa cụm từ bị cấm (sai lệch dữ kiện): '{forbidden}'")
        else:
            passed_checks += 1
            breakdown[f"forbid:{forbidden}"] = "pass"

    # 4. Year conflict disclosure (Invariant #4) - general detection of distinct years
    if expectation.expected_year_conflict is True:
        total_checks += 1
        years_found = set(re.findall(r"\b(20\d{2})\b", combined_text))
        if len(years_found) >= 2:
            passed_checks += 1
            breakdown["year_conflict"] = "pass"
        else:
            breakdown["year_conflict"] = "fail"
            failures.append(
                f"Vi phạm xung đột niên độ: phải nêu rõ ít nhất 2 mốc niên độ khác nhau, thực tế tìm thấy: {sorted(years_found)}"
            )

    # 5. IRAC reasoning presence (Slice 4)
    if expectation.require_irac_reasoning is True:
        total_checks += 1
        reasoning = trace.get("reasoning") or {}
        analysis = reasoning.get("analysis") or ""
        steps = reasoning.get("steps") or []
        if analysis or steps:
            passed_checks += 1
            breakdown["irac_reasoning"] = "pass"
        else:
            breakdown["irac_reasoning"] = "fail"
            failures.append("Thiếu phân tích suy luận IRAC: trace log không có khối <phan_tich>/steps")

    # 6. Deterministic calculator & Missing variables (Slice 5)
    if expectation.require_calculator is True:
        total_checks += 1
        calc = trace.get("calculator") or {}
        calc_status = calc.get("status")
        if expectation.expected_missing_vars:
            if calc_status == "missing_variables":
                passed_checks += 1
                breakdown["calculator_status"] = "pass"
            else:
                breakdown["calculator_status"] = "fail"
                failures.append(
                    f"Calculator kỳ vọng trạng thái 'missing_variables', thực tế: '{calc_status}'"
                )
        else:
            if calc_status == "success":
                passed_checks += 1
                breakdown["calculator_status"] = "pass"
            else:
                breakdown["calculator_status"] = "fail"
                failures.append(f"Calculator kỳ vọng trạng thái 'success', thực tế: '{calc_status}'")

    for var_name in expectation.expected_missing_vars:
        total_checks += 1
        calc = trace.get("calculator") or {}
        missing_in_calc = set(calc.get("missing_variables") or [])
        var_detected = (var_name in missing_in_calc) or (var_name in combined_text)
        if var_detected:
            passed_checks += 1
            breakdown[f"missing_var:{var_name}"] = "pass"
        else:
            breakdown[f"missing_var:{var_name}"] = "fail"
            failures.append(
                f"Biến thiếu '{var_name}' không được ghi nhận trong calculator hoặc câu trả lời"
            )

    # 7. Exact code anchors preservation (Slice 5 / Section 2.6)
    for anchor in expectation.exact_code_anchors:
        total_checks += 1
        if anchor.isdigit():
            pattern = rf"(?<!\d){re.escape(anchor)}(?!\d)"
        else:
            pattern = re.escape(anchor)

        if re.search(pattern, combined_text):
            passed_checks += 1
            breakdown[f"anchor:{anchor}"] = "pass"
        else:
            breakdown[f"anchor:{anchor}"] = "fail"
            failures.append(
                f"Mã định danh bảo toàn '{anchor}' không xuất hiện nguyên vẹn (lỗi mất số 0 đầu)"
            )

    # 8. Expected citations coverage
    if expectation.expected_citations:
        total_checks += 1
        cited_ids = set()
        for stmt in statements:
            evidence_ids = stmt.get("evidence_ids") if isinstance(stmt, dict) else getattr(stmt, "evidence_ids", [])
            cited_ids.update(evidence_ids)
        for src in sources:
            eid = src.get("evidence_id") if isinstance(src, dict) else getattr(src, "evidence_id", None)
            if eid:
                cited_ids.add(eid)

        expected_set = set(expectation.expected_citations)
        if expected_set.issubset(cited_ids) or not expected_set:
            passed_checks += 1
            breakdown["citations"] = "pass"
        else:
            breakdown["citations"] = "fail"
            failures.append(
                f"Trích dẫn thiếu dẫn chứng kỳ vọng: thiếu {sorted(expected_set - cited_ids)}"
            )

    # 9. Groundedness assessment
    if status == "answered":
        has_citations = bool(statements or sources)
        groundedness_score = 1.0 if has_citations else 0.0
        if not has_citations:
            failures.append("Groundedness vi phạm: trạng thái answered nhưng không dẫn chiếu căn cứ")
    else:
        # Refusal / insufficient evidence without making unfounded claims is fully grounded
        groundedness_score = 1.0

    correctness_score = round(passed_checks / total_checks, 4) if total_checks > 0 else 1.0
    passed = len(failures) == 0 and groundedness_score == 1.0

    return AnswerEvaluationResult(
        passed=passed,
        correctness_score=correctness_score,
        groundedness_score=groundedness_score,
        breakdown=breakdown,
        failures=failures,
    )
