"""Prepare chat calls from authorized ModelOps state, without sending HTTP or retrying."""

from __future__ import annotations

import json
import math
from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.capacity.automatic import capacity_identity
from qnu.domains.modelops.capacity.schemas import RequestTokenBudget
from qnu.domains.modelops.public_api import ChatRuntime, plan_model_request, resolve_chat_runtime
from qnu.domains.modelops.resilience.routing import choose_target
from qnu.domains.modelops.resilience.schemas import Task
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import Conflict
from qnu.ports.chat_model import ChatMessage, ChatRequest

DOCUMENT_CHAT_TASKS: frozenset[Task] = frozenset({"compiler", "compiler_review", "ocr_review"})


def input_token_upper_bound(messages: list[ChatMessage]) -> int:
    """Conservative UTF-8 byte estimate (~2 bytes/token) plus message/request framing.

    Vietnamese UTF-8 averages ~3-4 bytes per BPE token, so ceil(bytes / 2) remains
    a conservative operational bound without 3-4x false context rejections.
    Nothing is cropped to fit; actual tokens are only taken from provider usage.
    """
    encoded = json.dumps(
        [{"role": m.role, "content": m.content} for m in messages], ensure_ascii=False
    ).encode("utf-8")
    return math.ceil(len(encoded) / 2) + 64 * len(messages) + 128


def request_input_tokens(messages: list[ChatMessage], schema: dict | None) -> int:
    """Same conservative bound used by ``prepare_chat_request``; never a tokenizer claim."""
    schema_bytes = len(json.dumps(schema, ensure_ascii=False).encode("utf-8")) if schema is not None else 0
    return input_token_upper_bound(messages) + math.ceil(schema_bytes / 2)


def available_input_tokens(limits, output_tokens: int) -> int | None:
    """Input upper-bound units available after reserving declared output tokens."""
    if limits is None:
        return None
    values = []
    if limits.max_input_tokens is not None:
        values.append(limits.max_input_tokens)
    if limits.context_window_tokens is not None:
        values.append(limits.context_window_tokens - output_tokens)
    if not values:
        return None
    return max(0, min(values))


async def prepare_chat_limits(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    *,
    provider_id: str | None,
    max_output_tokens: int | None,
    task: Task = "chat",
) -> tuple[ChatRuntime, RequestTokenBudget]:
    """Resolve the pinned target and output budget without checking a message body.

    Callers that must first plan parts use this to learn the declared input envelope;
    every actual send still goes through ``prepare_chat_request``.
    """
    await resolve_workspace_access(db, actor, workspace_id)
    provider_id, routing = await choose_target(db, workspace_id, task, provider_id)
    snapshot, budget = await plan_model_request(
        db,
        actor,
        workspace_id,
        "chat",
        input_tokens=1,
        provider_id=provider_id,
        requested_output_tokens=max_output_tokens,
    )
    runtime = await resolve_chat_runtime(db, workspace_id, provider_id)
    runtime = replace(runtime, routing_trace=routing)
    current = capacity_identity(
        runtime.provider_id,
        runtime.base_url,
        runtime.model_name,
        runtime.token_limits,
        runtime.operational_budget,
    )
    if current != snapshot.configuration_hash:
        raise Conflict("Model thay đổi trong lúc lập ngân sách.", code="chat_provider_changed")
    return runtime, budget


async def prepare_chat_request(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    messages: list[ChatMessage],
    *,
    provider_id: str | None,
    max_output_tokens: int | None,
    output_schema: dict | None = None,
    task: Task = "chat",
    reasoning=None,
    admission_limit: int | None = None,
    temperature: float | None = None,
    json_mode: bool | None = None,
) -> tuple[ChatRuntime, ChatRequest, RequestTokenBudget]:
    await resolve_workspace_access(db, actor, workspace_id)
    provider_id, routing = await choose_target(db, workspace_id, task, provider_id)
    snapshot, budget = await plan_model_request(
        db,
        actor,
        workspace_id,
        "chat",
        input_tokens=request_input_tokens(messages, output_schema),
        provider_id=provider_id,
        requested_output_tokens=max_output_tokens,
    )
    runtime = await resolve_chat_runtime(db, workspace_id, provider_id)
    runtime = replace(runtime, routing_trace=routing)
    if reasoning is None:
        reasoning = runtime.reasoning_directive()
    current = capacity_identity(
        runtime.provider_id,
        runtime.base_url,
        runtime.model_name,
        runtime.token_limits,
        runtime.operational_budget,
    )
    if current != snapshot.configuration_hash:
        raise Conflict("Model thay đổi trong lúc lập ngân sách.", code="chat_provider_changed")
    effective_json_mode = (
        json_mode
        if json_mode is not None
        else (output_schema is not None or task != "chat")
    )
    return (
        runtime,
        ChatRequest(
            endpoint=runtime.base_url,
            model=runtime.model_name,
            max_output_tokens=budget.max_output_tokens,
            automatic_output_budget=max_output_tokens is None,
            budget_identity=current,
            timeout_seconds=runtime.timeout_seconds,
            wait_for_completion=runtime.wait_for_completion and task in DOCUMENT_CHAT_TASKS,
            api_key=runtime.api_key,
            output_schema=output_schema,
            json_mode=effective_json_mode,
            execution=runtime.execution_scope,
            reasoning=reasoning,
            admission_limit=admission_limit,
            temperature=temperature,
        ),
        budget,
    )
