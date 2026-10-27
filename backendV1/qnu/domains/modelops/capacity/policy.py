"""Pure per-model budgeting; never count Base64 length as image tokens or crop input."""

from __future__ import annotations

from qnu.domains.modelops.capacity.schemas import ModelTokenLimits, RequestTokenBudget
from qnu.platform.errors import AppException


def _invalid(detail: str, code: str) -> AppException:
    return AppException(detail, code=code, status_code=422)


def plan_token_budget(
    limits: ModelTokenLimits,
    *,
    input_tokens: int | None,
    requested_output_tokens: int | None = None,
    reserve_tokens: int = 0,
    minimum_output_tokens: int = 1,
) -> RequestTokenBudget:
    """Input includes images/framing; output includes reasoning per provider protocol.

    Trusted runtime supplies a measured count or a documented conservative bound.
    Without a valid multimodal count, fail instead of inventing image capacity.
    """
    if input_tokens is None:
        raise _invalid("Chưa xác định ngân sách đầu vào.", "model_input_budget_unknown")
    values = [(input_tokens, 0), (reserve_tokens, 0), (minimum_output_tokens, 1)]
    if requested_output_tokens is not None:
        values.append((requested_output_tokens, 1))
    if any(type(value) is not int or value < minimum for value, minimum in values):
        raise _invalid("Ngân sách token không hợp lệ.", "model_token_budget_invalid")
    incoming = input_tokens + reserve_tokens
    if limits.max_input_tokens is None and limits.context_window_tokens is None:
        raise _invalid("Chưa có giới hạn đầu vào/context.", "model_capacity_required")
    if limits.max_input_tokens is not None and incoming > limits.max_input_tokens:
        raise _invalid("Đầu vào vượt giới hạn model.", "model_input_limit_exceeded")
    available = []
    if limits.max_output_tokens is not None:
        available.append(limits.max_output_tokens)
    if limits.context_window_tokens is not None:
        available.append(limits.context_window_tokens - incoming)
    if not available:
        raise _invalid("Chưa có giới hạn đầu ra.", "model_output_capacity_required")
    ceiling = min(available)
    if ceiling < minimum_output_tokens:
        raise _invalid("Không đủ context cho đầu ra.", "model_context_limit_exceeded")
    output = requested_output_tokens if requested_output_tokens is not None else ceiling
    if output > ceiling or output < minimum_output_tokens:
        raise _invalid("Ngân sách đầu ra vượt giới hạn.", "model_output_limit_exceeded")
    return RequestTokenBudget(
        input_tokens=input_tokens,
        reserve_tokens=reserve_tokens,
        max_output_tokens=output,
        total_reserved_tokens=incoming + output,
    )
