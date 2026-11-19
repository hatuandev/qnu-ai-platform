"""Unit tests for Phase 2 Slice 5: Sandbox Deterministic Calculator."""

from __future__ import annotations

from qnu.domains.rag.answer.calculator import CalculationRequest, evaluate_expression


def test_basic_arithmetic_evaluation():
    req = CalculationRequest(formula="10 + 5 * 2 - (8 / 4)")
    res = evaluate_expression(req)
    assert res.status == "success"
    assert res.evaluated_value == 18.0
    assert res.formatted_result == "18"


def test_weighted_formula_evaluation():
    req = CalculationRequest(
        formula="0.45 * A + 0.35 * B + 0.20 * C",
        variables={"A": 24.0, "B": 26.0, "C": 28.0},
        rounding=2,
    )
    res = evaluate_expression(req)
    assert res.status == "success"
    # 0.45 * 24 = 10.8, 0.35 * 26 = 9.1, 0.20 * 28 = 5.6 -> 25.5
    assert res.evaluated_value == 25.5
    assert res.formatted_result == "25.5"


def test_subject_combination_with_coefficient():
    req = CalculationRequest(
        formula="2 * Toan + Van + Anh",
        variables={"Toan": 8.0, "Van": 7.5, "Anh": 9.0},
        rounding=2,
    )
    res = evaluate_expression(req)
    assert res.status == "success"
    assert res.evaluated_value == 32.5
    assert res.formatted_result == "32.5"


def test_precondition_check_passed():
    req = CalculationRequest(
        formula="0.45 * A + 0.35 * B + 0.20 * C",
        variables={"A": 24.0, "B": 26.0, "C": 28.0, "minh_chung": 0.85},
        preconditions=["minh_chung >= 0.8"],
    )
    res = evaluate_expression(req)
    assert res.status == "success"
    assert res.evaluated_value == 25.5


def test_precondition_check_failed():
    req = CalculationRequest(
        formula="0.45 * A + 0.35 * B + 0.20 * C",
        variables={"A": 24.0, "B": 26.0, "C": 28.0, "minh_chung": 0.75},
        preconditions=["minh_chung >= 0.8"],
    )
    res = evaluate_expression(req)
    assert res.status == "precondition_failed"
    assert res.failed_precondition == "minh_chung >= 0.8"
    assert "Không thỏa điều kiện tiên quyết" in (res.error or "")
    assert res.evaluated_value is None


def test_missing_variables_never_defaults_to_zero():
    # Only A and B provided; C is omitted
    req = CalculationRequest(
        formula="0.45 * A + 0.35 * B + 0.20 * C",
        variables={"A": 24.0, "B": 26.0},
    )
    res = evaluate_expression(req)
    assert res.status == "missing_variables"
    assert res.missing_variables == ["C"]
    assert "thiếu giá trị cho các biến: C" in (res.error or "")
    # Invariant: C must NOT be defaulted to 0
    assert res.evaluated_value is None

    # Variable explicitly provided as None
    req_none = CalculationRequest(
        formula="A + B",
        variables={"A": 10.0, "B": None},
    )
    res_none = evaluate_expression(req_none)
    assert res_none.status == "missing_variables"
    assert res_none.missing_variables == ["B"]


def test_division_by_zero_safe_handling():
    req = CalculationRequest(formula="100 / 0")
    res = evaluate_expression(req)
    assert res.status == "error"
    assert "Lỗi chia cho 0" in (res.error or "")
    assert res.evaluated_value is None


def test_security_ast_sandbox_rejects_unsafe_operations():
    # Reject __import__
    req_import = CalculationRequest(formula="__import__('os').system('ls')")
    res_import = evaluate_expression(req_import)
    assert res_import.status in {"error", "missing_variables"}

    # Reject attribute access
    req_attr = CalculationRequest(formula="A.__class__.__bases__", variables={"A": 10})
    res_attr = evaluate_expression(req_attr)
    assert res_attr.status == "error"

    # Reject huge power DoS
    req_dos = CalculationRequest(formula="9999 ** 9999")
    res_dos = evaluate_expression(req_dos)
    assert res_dos.status == "error"
    assert "giới hạn an toàn" in (res_dos.error or "")
