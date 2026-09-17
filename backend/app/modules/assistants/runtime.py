"""Runtime profile and input-safety helpers for assistant executions."""

from __future__ import annotations

import re
import unicodedata

from app.core.exceptions import AppException
from app.modules.assistants.schemas import AssistantResponse, AssistantRuntimeProfile

_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?84|0)(?:[ .-]?\d){8,10}(?!\d)")
_IDENTITY_PATTERN = re.compile(r"(?<!\d)\d{9,12}(?!\d)")
_PROMPT_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous",
    "system prompt",
    "reveal your instructions",
    "jailbreak",
    "dan mode",
    "bỏ qua hướng dẫn trước",
    "tiết lộ hướng dẫn hệ thống",
)


def build_runtime_profile(assistant: AssistantResponse) -> AssistantRuntimeProfile:
    """Create a stable policy snapshot so active runs cannot observe later edits."""
    return AssistantRuntimeProfile(
        assistant_id=assistant.id,
        assistant_code=assistant.code,
        assistant_revision=assistant.updated_at.isoformat(),
        tenant_id=assistant.tenant_id,
        system_prompt=assistant.system_prompt,
        collection_id=assistant.collection_id,
        persona_scope=assistant.config.persona_scope,
        knowledge_policy=assistant.config.knowledge_policy,
        model_policy=assistant.config.model_policy,
        guardrails=assistant.config.guardrails,
        tools=assistant.config.tools,
        output_policy=assistant.config.output_policy,
        evaluation_policy=assistant.config.evaluation_policy,
    )


def prepare_user_message(message: str, profile: AssistantRuntimeProfile) -> str:
    """Normalize user input, reject injection attempts and mask PII before model access."""
    normalized_message = unicodedata.normalize("NFC", message).strip()
    if not normalized_message:
        raise AppException("Nội dung câu hỏi không được để trống.", code="assistant_message_empty")

    normalized_casefold = normalized_message.casefold()
    if profile.guardrails.block_prompt_injection and any(
        pattern in normalized_casefold for pattern in _PROMPT_INJECTION_PATTERNS
    ):
        raise AppException(
            "Yêu cầu chứa mẫu hướng dẫn không an toàn và đã bị từ chối.",
            code="assistant_input_rejected",
            status_code=400,
            details={"assistant_code": profile.assistant_code, "reason": "prompt_injection"},
        )

    if not profile.guardrails.mask_pii:
        return normalized_message

    masked_message = _EMAIL_PATTERN.sub("[EMAIL_ĐÃ_CHE]", normalized_message)
    masked_message = _PHONE_PATTERN.sub("[SĐT_ĐÃ_CHE]", masked_message)
    return _IDENTITY_PATTERN.sub("[ĐỊNH_DANH_ĐÃ_CHE]", masked_message)
