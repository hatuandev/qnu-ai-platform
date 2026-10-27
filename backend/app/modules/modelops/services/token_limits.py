"""Endpoint-bound model capacity; names and catalog presence do not prove limits."""
from app.core.exceptions import AppException
from app.modules.modelops.schemas import ModelTokenLimits


def configured_token_limits(extra: dict | None, model: str, endpoint: str | None) -> dict | None:
    if not isinstance(extra, dict):
        return None  # No declared capacity; never label this as a verified model limit.
    raw = (((extra or {}).get('model_capabilities') or {}).get(model) or {}).get('token_limits')
    if raw is None:
        return None
    try:
        limits = ModelTokenLimits.model_validate(raw)
    except ValueError as exc:
        raise AppException('Giới hạn token của model chưa hợp lệ.',
            code='MODEL_TOKEN_LIMITS_INVALID', status_code=422) from exc
    if limits.endpoint.rstrip('/') != (endpoint or '').rstrip('/'):
        raise AppException('Giới hạn token thuộc endpoint cũ; cần xác nhận lại.',
            code='MODEL_TOKEN_LIMITS_STALE', status_code=409)
    return limits.model_dump(exclude={'endpoint'})


def validate_output_budget(extra: dict | None, model: str, endpoint: str | None, output: int) -> None:
    limits = configured_token_limits(extra, model, endpoint)
    if limits and limits['max_output_tokens'] is not None and output > limits['max_output_tokens']:
        raise AppException('Ngân sách đầu ra vượt giới hạn model đã cấu hình.',
            code='MODEL_OUTPUT_LIMIT_EXCEEDED', status_code=422,
            details={'requested_output': output, 'model_output_limit': limits['max_output_tokens']})


def merge_model_capabilities(existing: dict, updates: dict, models: list[str]) -> dict:
    """An older admin form must not silently delete an unseen capacity profile."""
    result = {name: dict(value) for name, value in existing.items() if name in models}
    for name, capability in updates.items():
        if name not in models:
            continue
        changed = capability.model_dump(exclude_unset=True)
        if 'token_limits' in capability.model_fields_set and capability.token_limits is None:
            changed['token_limits'] = None  # Explicit clearing remains an authorized admin action.
        result[name] = {**result.get(name, {}), **changed}
    return result
