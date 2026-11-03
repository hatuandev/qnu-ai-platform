"""Resolve page budgets from ModelOps without inventing multimodal token counts."""

import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.public_api import OcrRuntime, plan_model_request, resolve_ocr_runtime
from qnu.platform.errors import AppException


async def page_request_budget(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    expected: OcrRuntime,
    *,
    width: int,
    height: int,
    prompt: str,
    output_tokens: int | None,
):
    current = await resolve_ocr_runtime(db, workspace_id, expected.provider_id)
    if current.configuration_hash != expected.configuration_hash:
        raise AppException(
            "Cấu hình provider đã thay đổi.", code="provider_changed", status_code=409
        )
    limits = current.token_limits
    if current.capacity_status == "stale":
        raise AppException(
            "Capacity đã hết hiệu lực.", code="model_token_limits_stale", status_code=409
        )
    if limits is None:
        raise AppException(
            "Chưa cấu hình capacity.", code="model_capacity_required", status_code=422
        )
    accounting = limits.ocr_page_input if limits else None
    if accounting is None:
        raise AppException(
            "Chưa có căn cứ ngân sách token ảnh/prompt cho model OCR.",
            code="model_input_budget_unknown",
            status_code=422,
        )
    if (
        width > accounting.max_image_width
        or height > accounting.max_image_height
        or hashlib.sha256(prompt.encode()).hexdigest() != accounting.prompt_sha256
    ):
        raise AppException(
            "Ảnh/prompt nằm ngoài phạm vi ngân sách OCR đã cấu hình.",
            code="model_input_budget_unverified",
            status_code=422,
        )
    _, budget = await plan_model_request(
        db,
        actor,
        workspace_id,
        "ocr",
        provider_id=current.provider_id,
        input_tokens=accounting.input_tokens_upper_bound,
        requested_output_tokens=output_tokens,
    )
    return current, budget
