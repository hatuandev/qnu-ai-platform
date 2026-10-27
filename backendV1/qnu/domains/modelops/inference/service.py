"""Prepare chat calls from authorized ModelOps state, without sending HTTP or retrying."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.capacity.schemas import RequestTokenBudget
from qnu.domains.modelops.public_api import ChatRuntime, plan_model_request, resolve_chat_runtime
from qnu.platform.errors import Conflict
from qnu.ports.chat_model import ChatMessage, ChatRequest


def input_token_upper_bound(messages: list[ChatMessage]) -> int:
    """UTF-8 bytes plus 64 framing tokens/message and 128 request framing tokens.

    This is a conservative operational bound for text, not measured tokenizer usage.
    Nothing is cropped to fit; actual tokens are only taken from provider usage.
    """
    encoded = json.dumps(
        [{"role": m.role, "content": m.content} for m in messages], ensure_ascii=False
    ).encode("utf-8")
    return len(encoded) + 64 * len(messages) + 128


async def prepare_chat_request(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    messages: list[ChatMessage],
    *,
    provider_id: str | None,
    max_output_tokens: int,
    output_schema: dict | None = None,
) -> tuple[ChatRuntime, ChatRequest, RequestTokenBudget]:
    snapshot, budget = await plan_model_request(
        db,
        actor,
        workspace_id,
        "chat",
        input_tokens=input_token_upper_bound(messages)
        + (
            len(json.dumps(output_schema, ensure_ascii=False).encode())
            if output_schema is not None
            else 0
        ),
        provider_id=provider_id,
        requested_output_tokens=max_output_tokens,
    )
    runtime = await resolve_chat_runtime(db, workspace_id, provider_id)
    material = {
        "provider_id": runtime.provider_id,
        "endpoint": runtime.base_url.rstrip("/"),
        "model_name": runtime.model_name,
        "limits": runtime.token_limits.model_dump() if runtime.token_limits else None,
    }
    current = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if current != snapshot.configuration_hash:
        raise Conflict("Model thay đổi trong lúc lập ngân sách.", code="chat_provider_changed")
    return (
        runtime,
        ChatRequest(
            endpoint=runtime.base_url,
            model=runtime.model_name,
            max_output_tokens=budget.max_output_tokens,
            timeout_seconds=runtime.timeout_seconds,
            api_key=runtime.api_key,
            output_schema=output_schema,
        ),
        budget,
    )
