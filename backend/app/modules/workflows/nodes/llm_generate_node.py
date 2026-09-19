"""LLM Generation Node Handler — Executes LLM Completion with Fallbacks."""

from __future__ import annotations

from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


class LLMGenerateNodeHandler(BaseNodeHandler):
    """Invokes ModelOps Multi-LLM provider adapter with dynamic fallback."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        profile = context.assistant_profile
        system_prompt = (
            profile.system_prompt
            if profile
            else config.get("system_prompt")
            or "Bạn là Trợ lý AI chính thức của Trường Đại học Quy Nhơn."
        )
        user_message = (
            context.node_data.get("user_message")
            or context.inputs.get("message", "")
        )

        messages = [ChatMessage(role="system", content=system_prompt)]
        conv_history = context.inputs.get("conversation_history")
        if conv_history and isinstance(conv_history, list):
            for h_msg in conv_history[-6:]:
                h_role = h_msg.get("role", "user")
                h_text = h_msg.get("content", "")
                if h_role in ("user", "assistant") and h_text:
                    messages.append(ChatMessage(role=h_role, content=h_text))
        messages.append(ChatMessage(role="user", content=user_message))

        gen_req = LLMGenerateRequest(
            messages=messages,
            tenant_id=context.tenant_id,
            assistant_code=profile.assistant_code if profile else None,
            conversation_id=context.conversation_id,
            temperature=profile.model_policy.temperature if profile else config.get("temperature", 0.2),
            max_tokens=profile.model_policy.max_tokens if profile else config.get("max_tokens", 2000),
        )

        if context.db:
            resp = await modelops_service.generate(context.db, gen_req)
            content = resp.content
            provider = resp.provider
            tokens = resp.total_tokens
        else:
            content = f"Văn bản sinh ra từ trợ lý QNU: '{user_message[:100]}'."
            provider = "openai"
            tokens = 100

        context.node_data["llm_content"] = content
        context.node_data["provider"] = provider

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "content": content,
                "provider": provider,
                "total_tokens": tokens,
            },
        )
