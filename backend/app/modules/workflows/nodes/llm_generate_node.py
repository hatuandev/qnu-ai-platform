"""LLM Generation Node Handler — Executes LLM Completion with Fallbacks."""

from __future__ import annotations

import logging

from app.core.exceptions import AppException
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.nodes.routed_inputs import routed_text
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)


class LLMGenerateNodeHandler(BaseNodeHandler):
    """Invokes ModelOps Multi-LLM provider adapter with dynamic fallback."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        profile = context.assistant_profile
        system_prompt = (
            config.get("system_prompt")
            or config.get("instruction")
            or (profile.system_prompt if profile else None)
            or "Bạn là Trợ lý AI chính thức của Trường Đại học Quy Nhơn."
        )
        user_message = routed_text(
            context,
            node_spec.id,
            ("message", "question", "text", "content", "response", "answer"),
            (context.node_data.get("user_message") or context.inputs.get("message", "")),
        )
        if context.db is None:
            raise AppException("Node LLM cần kết nối dữ liệu.", code="WORKFLOW_DATABASE_REQUIRED", status_code=503)

        messages = [ChatMessage(role="system", content=system_prompt)]
        conv_history = context.inputs.get("conversation_history")
        if conv_history and isinstance(conv_history, list):
            for h_msg in conv_history[-6:]:
                h_role = h_msg.get("role", "user")
                h_text = h_msg.get("content", "")
                if h_role in ("user", "assistant") and h_text:
                    messages.append(ChatMessage(role=h_role, content=h_text))
        messages.append(ChatMessage(role="user", content=user_message))

        model_policy = getattr(profile, "model_policy", None) if profile else None
        preferred_model = (
            config.get("preferred_model_name")
            or config.get("primary_model")
            or config.get("model_name")
            or (getattr(model_policy, "primary_model", None) if model_policy else None)
        )
        fallback_model = (
            config.get("fallback_model_name")
            or config.get("fallback_model")
            or (getattr(model_policy, "fallback_model", None) if model_policy else None)
        )
        preferred_provider_id = (config.get("preferred_provider_id") or config.get("provider_id")
                                 or getattr(model_policy, "preferred_provider_id", None))

        gen_req = LLMGenerateRequest(
            messages=messages,
            tenant_id=context.tenant_id,
            assistant_code=profile.assistant_code if profile else None,
            conversation_id=context.conversation_id,
            preferred_model_name=preferred_model,
            fallback_model_name=fallback_model,
            preferred_provider_id=preferred_provider_id,
            temperature=getattr(model_policy, "temperature", config.get("temperature", 0.2)),
            max_tokens=getattr(model_policy, "max_tokens", config.get("max_tokens", 2000)),
        )

        resp = await modelops_service.generate(context.db, gen_req)
        content, provider, tokens = resp.content, resp.provider, resp.total_tokens
        if not content.strip():
            raise AppException("Mô hình trả nội dung rỗng.", code="LLM_EMPTY_RESPONSE", status_code=502)

        context.node_data["llm_content"] = content
        context.node_data["provider"] = provider

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "content": content,
                "response": content,
                "provider": provider,
                "total_tokens": tokens,
            },
        )
