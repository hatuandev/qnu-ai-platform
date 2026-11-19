"""Sandbox Deterministic Calculator and Python Expression Evaluator (Slice 5).

Provides a secure, read-only, AST-based mathematical and conditional evaluator
without I/O or unsafe code execution (no eval/exec).
Strictly adheres to AGENTS.md and RULE_REASONING_PROMPTS_SPEC.md:
- Precondition validation (e.g. evidence ratio >= 80%).
- Strict missing variables handling (keeps None, strictly FORBIDS defaulting to 0).
- Pure arithmetic evaluation with division-by-zero and DoS protection.
"""

from __future__ import annotations

import ast
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_ALLOWED_FUNCTIONS: dict[str, Any] = {
    "min": min,
    "max": max,
    "round": round,
    "abs": abs,
    "sum": sum,
}

_MAX_POWER_EXPONENT = 10
_MAX_POWER_BASE = 10000


class CalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula: str = Field(..., min_length=1, max_length=500)
    variables: dict[str, float | int | None] = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    rounding: int | None = Field(default=2, ge=0, le=10)


class CalculationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "missing_variables", "precondition_failed", "error"]
    formula: str
    evaluated_value: float | int | bool | None = None
    formatted_result: str | None = None
    missing_variables: list[str] = Field(default_factory=list)
    failed_precondition: str | None = None
    error: str | None = None
    trace: dict[str, Any] = Field(default_factory=dict)


class _SafeEvaluator:
    def __init__(self, variables: dict[str, float | int | None]) -> None:
        self.variables = variables

    def extract_names(self, node: ast.AST) -> set[str]:
        names: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id not in _ALLOWED_FUNCTIONS:
                names.add(child.id)
        return names

    def eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return self.eval_node(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, bool)):
                return node.value
            raise ValueError(f"Kiểu dữ liệu hằng số không được hỗ trợ: {type(node.value).__name__}")

        if isinstance(node, ast.Name):
            if node.id in _ALLOWED_FUNCTIONS:
                return _ALLOWED_FUNCTIONS[node.id]
            if node.id in self.variables:
                val = self.variables[node.id]
                if val is None:
                    raise KeyError(node.id)
                return val
            raise KeyError(node.id)

        if isinstance(node, ast.UnaryOp):
            operand = self.eval_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.Not):
                return not operand
            raise ValueError(f"Toán tử một ngôi không được hỗ trợ: {type(node.op).__name__}")

        if isinstance(node, ast.BinOp):
            left = self.eval_node(node.left)
            right = self.eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError("Lỗi chia cho 0.")
                return left / right
            if isinstance(node.op, ast.FloorDiv):
                if right == 0:
                    raise ZeroDivisionError("Lỗi chia cho 0.")
                return left // right
            if isinstance(node.op, ast.Mod):
                if right == 0:
                    raise ZeroDivisionError("Lỗi chia cho 0.")
                return left % right
            if isinstance(node.op, ast.Pow):
                if abs(right) > _MAX_POWER_EXPONENT or abs(left) > _MAX_POWER_BASE:
                    raise ValueError("Số mũ hoặc cơ số vượt quá giới hạn an toàn.")
                return left**right
            raise ValueError(f"Toán tử hai ngôi không được hỗ trợ: {type(node.op).__name__}")

        if isinstance(node, ast.Compare):
            left = self.eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self.eval_node(comparator)
                if isinstance(op, ast.Lt) and not (left < right):
                    return False
                if isinstance(op, ast.LtE) and not (left <= right):
                    return False
                if isinstance(op, ast.Gt) and not (left > right):
                    return False
                if isinstance(op, ast.GtE) and not (left >= right):
                    return False
                if isinstance(op, ast.Eq) and left != right:
                    return False
                if isinstance(op, ast.NotEq) and left == right:
                    return False
                left = right
            return True

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(bool(self.eval_node(v)) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(bool(self.eval_node(v)) for v in node.values)
            raise ValueError(f"Toán tử logic không được hỗ trợ: {type(node.op).__name__}")

        if isinstance(node, ast.Call):
            func = self.eval_node(node.func)
            if func not in _ALLOWED_FUNCTIONS.values():
                raise ValueError("Chỉ được gọi các hàm toán học an toàn (min, max, round, abs, sum).")
            args = [self.eval_node(arg) for arg in node.args]
            return func(*args)

        raise ValueError(f"Thành phần cú pháp không được phép: {type(node).__name__}")


def evaluate_expression(request: CalculationRequest) -> CalculationResult:
    """Safely and deterministically evaluates an expression with variables and preconditions.

    Invariants:
    1. If any variable is missing or None, NEVER default to 0; return status="missing_variables".
    2. Check all preconditions first; if any fails, return status="precondition_failed".
    3. Return exact rounded/formatted float string.
    """
    clean_formula = request.formula.strip()
    evaluator = _SafeEvaluator(request.variables)

    # 1. Parse formula
    try:
        parsed_formula = ast.parse(clean_formula, mode="eval")
    except SyntaxError as exc:
        return CalculationResult(
            status="error",
            formula=clean_formula,
            error=f"Cú pháp công thức không hợp lệ: {exc.msg}",
        )

    # 2. Check missing variables across formula and preconditions
    required_names = evaluator.extract_names(parsed_formula)
    parsed_preconditions: list[tuple[str, ast.Expression]] = []

    for precond in request.preconditions:
        clean_precond = precond.strip()
        if not clean_precond:
            continue
        try:
            parsed_pre = ast.parse(clean_precond, mode="eval")
            parsed_preconditions.append((clean_precond, parsed_pre))
            required_names.update(evaluator.extract_names(parsed_pre))
        except SyntaxError as exc:
            return CalculationResult(
                status="error",
                formula=clean_formula,
                error=f"Cú pháp điều kiện tiên quyết không hợp lệ '{clean_precond}': {exc.msg}",
            )

    missing = sorted(
        name for name in required_names if name not in request.variables or request.variables[name] is None
    )
    if missing:
        return CalculationResult(
            status="missing_variables",
            formula=clean_formula,
            missing_variables=missing,
            error=f"Chưa đủ điều kiện tính toán: thiếu giá trị cho các biến: {', '.join(missing)}.",
            trace={"required_variables": sorted(required_names), "missing": missing},
        )

    # 3. Evaluate preconditions
    for precond_str, parsed_pre in parsed_preconditions:
        try:
            pre_res = evaluator.eval_node(parsed_pre)
            if not bool(pre_res):
                return CalculationResult(
                    status="precondition_failed",
                    formula=clean_formula,
                    failed_precondition=precond_str,
                    error=f"Không thỏa điều kiện tiên quyết: {precond_str}.",
                    trace={"failed_precondition": precond_str},
                )
        except Exception as exc:
            return CalculationResult(
                status="error",
                formula=clean_formula,
                error=f"Lỗi kiểm tra điều kiện tiên quyết '{precond_str}': {exc}",
            )

    # 4. Evaluate main formula
    try:
        raw_val = evaluator.eval_node(parsed_formula)
    except ZeroDivisionError:
        return CalculationResult(
            status="error",
            formula=clean_formula,
            error="Lỗi chia cho 0 trong công thức tính.",
        )
    except Exception as exc:
        return CalculationResult(
            status="error",
            formula=clean_formula,
            error=f"Lỗi thực thi công thức: {exc}",
        )

    # 5. Format result
    if isinstance(raw_val, float):
        if request.rounding is not None:
            val = round(raw_val, request.rounding)
            formatted = f"{val:.{request.rounding}f}".rstrip("0").rstrip(".") if "." in f"{val:.{request.rounding}f}" else str(val)
        else:
            val = raw_val
            formatted = str(val)
    elif isinstance(raw_val, (int, bool)):
        val = raw_val
        formatted = str(val)
    else:
        val = raw_val
        formatted = str(raw_val)

    return CalculationResult(
        status="success",
        formula=clean_formula,
        evaluated_value=val,
        formatted_result=formatted,
        trace={
            "variables_used": {k: request.variables.get(k) for k in sorted(required_names)},
            "preconditions_checked": len(parsed_preconditions),
        },
    )
