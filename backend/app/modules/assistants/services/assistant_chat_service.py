"""Assistant Chat Service — Real-time chat, SSE streaming, and multi-turn conversation context."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.assistants.runtime import build_runtime_profile, prepare_user_message
from app.modules.assistants.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
)
from app.modules.assistants.services.assistant_lifecycle_service import assistant_lifecycle_service
from app.modules.workflows.schemas import WorkflowExecuteRequest
from app.modules.workflows.service import workflow_service

logger = logging.getLogger(__name__)


def _get_workflow_service():
    import sys

    mod = sys.modules.get("app.modules.assistants.service")
    if mod and hasattr(mod, "workflow_service"):
        return mod.workflow_service
    return workflow_service


def _get_assistant_service():
    import sys

    mod = sys.modules.get("app.modules.assistants.service")
    if mod and hasattr(mod, "assistant_service"):
        return mod.assistant_service
    return assistant_lifecycle_service


def _extract_primary_model(assistant: Any) -> str:
    fallback_default = settings.DEFAULT_LLM_MODEL
    config = getattr(assistant, "config", None)
    if not config:
        return fallback_default
    if hasattr(config, "model_policy"):
        mp = config.model_policy
        if hasattr(mp, "primary_model") and mp.primary_model:
            return mp.primary_model
        if isinstance(mp, dict) and mp.get("primary_model"):
            return mp["primary_model"]
    elif isinstance(config, dict):
        mp = config.get("model_policy", {})
        if isinstance(mp, dict) and mp.get("primary_model"):
            return mp["primary_model"]
        if hasattr(mp, "primary_model") and mp.primary_model:
            return mp.primary_model
    return fallback_default


def _format_message_with_attachments(message: str, attachments: list[dict[str, Any]]) -> str:
    if not attachments:
        return message
    snippets: list[str] = []
    for att in attachments:
        t_name = att.get("name") or "tài liệu"
        t_text = (att.get("text_content") or att.get("raw_text") or "").strip()
        if t_text:
            snippets.append(f"--- Tệp '{t_name}' ---\n{t_text[:4000]}")
    if snippets:
        return (
            "[NỘI DUNG TÀI LIỆU ĐÍNH KÈM TỪ NGƯỜI DÙNG]:\n"
            + "\n\n".join(snippets)
            + f"\n\n[CÂU HỎI CỦA NGƯỜI DÙNG]:\n{message}"
        )
    return message


class AssistantChatService:
    """Service handling real-time chat invocations and streaming execution."""

    @staticmethod
    async def _get_recent_conversation_history(
        db: AsyncSession, conversation_id: str, limit: int = 6
    ) -> list[dict[str, str]]:
        if not conversation_id:
            return []
        try:
            from sqlalchemy import select

            from app.modules.conversations.models import ConversationMessageModel

            stmt = (
                select(ConversationMessageModel)
                .where(ConversationMessageModel.thread_id == conversation_id)
                .order_by(ConversationMessageModel.created_at.desc())
                .limit(limit)
            )
            res = await db.execute(stmt)
            records = list(reversed(res.scalars().all()))
            history: list[dict[str, str]] = []
            for r in records:
                h_role = "user" if r.sender == "user" else "assistant"
                if r.text:
                    history.append({"role": h_role, "content": r.text})
            return history
        except Exception as exc:
            logger.warning("failed_to_fetch_recent_conversation_history: %s", exc)
            return []

    async def chat(
        self,
        db: AsyncSession,
        reference: str,
        request: AssistantChatRequest,
        *,
        correlation_id: str | None = None,
    ) -> AssistantChatResponse:
        assistant = await _get_assistant_service().get_assistant(db, reference)
        if not assistant.is_active:
            raise AppException(
                f"Trợ lý '{assistant.code}' đang bị vô hiệu hóa.",
                code="assistant_inactive",
                status_code=409,
                details={"assistant_code": assistant.code},
            )

        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        recent_history = await self._get_recent_conversation_history(db, conversation_id, limit=6)

        # Record user question in persistent conversation thread
        try:
            from app.modules.conversations.schemas import ConversationCreateMessageRequest
            from app.modules.conversations.service import conversation_service

            await conversation_service.record_message(
                db,
                ConversationCreateMessageRequest(
                    thread_id=conversation_id,
                    assistant_code=assistant.code,
                    assistant_name=assistant.name,
                    sender="user",
                    text=request.message,
                    user_name="Thí sinh / Sinh viên",
                ),
            )
        except Exception as conv_user_err:
            logger.warning("failed_to_record_user_message_in_chat: %s", conv_user_err)

        runtime_profile = build_runtime_profile(assistant)
        prepared_message = _format_message_with_attachments(request.message, request.attachments)
        sanitized_message = prepare_user_message(prepared_message, runtime_profile)
        workflow_request = WorkflowExecuteRequest(
            workflow_id=assistant.workflow_id,
            workflow_version_id=getattr(assistant, "published_workflow_version_id", None),
            inputs={
                "message": sanitized_message,
                "is_approved": False,
                "format": "docx,pdf",
                "conversation_history": recent_history,
            },
            tenant_id=request.tenant_id,
            conversation_id=conversation_id,
        )
        workflow_response = await _get_workflow_service().execute(
            db,
            workflow_request,
            assistant_profile=runtime_profile,
            correlation_id=correlation_id,
        )

        if workflow_response.status == "paused_for_approval":
            output_status = "paused_for_approval"
            action_req = (
                workflow_response.outputs.get("action_required")
                or "Yêu cầu thực thi tác vụ cần phê duyệt của nhân sự."
            )
            approval_id = (
                workflow_response.outputs.get("approval_id")
                or workflow_response.outputs.get("checkpoint")
                or "pending"
            )
            answer = (
                f"Yêu cầu thực thi tác vụ '{action_req}' đang chờ cán bộ có thẩm quyền phê duyệt.\n\n"
                f"- **Mã yêu cầu:** `{approval_id}`\n"
                f"- **Trạng thái:** Chờ phê duyệt (Human-in-the-loop)\n\n"
                f"Quản trị viên có thể xem xét và phê duyệt tại mục [Hộp Thư Phê Duyệt](/runs)."
            )
        else:
            answer = workflow_response.outputs.get("answer")
            if not isinstance(answer, str) or not answer.strip():
                guardrails = getattr(getattr(assistant, "config", None), "guardrails", None)
                answer = getattr(guardrails, "no_answer_message", "Xin lỗi, hiện tại tôi chưa có dữ liệu chính thức để trả lời câu hỏi này.")
            output_status = str(workflow_response.outputs.get("status") or workflow_response.status)

        citations = workflow_response.outputs.get("citations", [])
        artifacts = workflow_response.outputs.get("artifacts", [])

        # Record assistant answer in persistent conversation thread
        try:
            from app.modules.conversations.schemas import ConversationCreateMessageRequest
            from app.modules.conversations.service import conversation_service

            await conversation_service.record_message(
                db,
                ConversationCreateMessageRequest(
                    thread_id=conversation_id,
                    assistant_code=assistant.code,
                    assistant_name=assistant.name,
                    sender="assistant",
                    text=answer,
                ),
            )
        except Exception as conv_asst_err:
            logger.warning("failed_to_record_assistant_message_in_chat: %s", conv_asst_err)

        sample_questions = getattr(assistant, "sample_questions", None)
        if not sample_questions:
            config = getattr(assistant, "config", None)
            if hasattr(config, "persona_scope"):
                sample_questions = getattr(config.persona_scope, "sample_questions", [])
            elif isinstance(config, dict):
                sample_questions = config.get("persona_scope", {}).get("sample_questions", [])
            else:
                sample_questions = []
        if output_status == "insufficient_context":
            try:
                from app.modules.evaluation.service import evaluation_service

                await evaluation_service.record_gap(
                    db,
                    assistant_code=assistant.code,
                    collection_id=assistant.collection_id,
                    question=request.message,
                )
            except Exception as gap_err:
                logger.warning("failed_to_record_knowledge_gap_in_chat: %s", gap_err)

        # Record LLM Usage
        try:
            from app.modules.modelops.service import modelops_service

            model_name = _extract_primary_model(assistant)
            prompt_toks = max(1, len(request.message) // 4 + 80)
            comp_toks = max(1, len(answer) // 4)
            await modelops_service.record_usage_log(
                db,
                tenant_id=getattr(assistant, "tenant_id", "tenant_qnu"),
                assistant_id=assistant.code,
                conversation_id=conversation_id,
                provider="qnu_workflow",
                model_name=model_name,
                prompt_tokens=prompt_toks,
                completion_tokens=comp_toks,
                latency_ms=workflow_response.latency_ms,
                status="success" if output_status != "error" else "error",
            )
        except Exception as u_err:
            logger.warning("failed_to_record_usage_in_chat: %s", u_err)

        dynamic_suggestions = workflow_response.outputs.get("suggested_questions")
        final_suggested_questions = (
            dynamic_suggestions
            if (dynamic_suggestions and isinstance(dynamic_suggestions, list))
            else (sample_questions or [])[:3]
        )

        return AssistantChatResponse(
            assistant_code=assistant.code,
            assistant_name=assistant.name,
            answer=answer,
            status=output_status,
            citations=citations if isinstance(citations, list) else [],
            suggested_questions=final_suggested_questions,
            latency_ms=workflow_response.latency_ms,
            execution_id=workflow_response.execution_id,
            artifacts=artifacts if isinstance(artifacts, list) else [],
            conversation_id=conversation_id,
        )

    async def chat_stream(
        self,
        db: AsyncSession,
        reference: str,
        request: AssistantChatRequest,
        *,
        correlation_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream assistant response token-by-token via Server-Sent Events (SSE)."""
        assistant = await _get_assistant_service().get_assistant(db, reference)
        if not assistant.is_active:
            err_data = json.dumps({"error": f"Trợ lý '{assistant.code}' đang bị vô hiệu hóa."}, ensure_ascii=False)
            yield f"event: error\ndata: {err_data}\n\n"
            return

        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        recent_history = await self._get_recent_conversation_history(db, conversation_id, limit=6)

        # Record user question in persistent conversation thread
        try:
            from app.modules.conversations.schemas import ConversationCreateMessageRequest
            from app.modules.conversations.service import conversation_service

            await conversation_service.record_message(
                db,
                ConversationCreateMessageRequest(
                    thread_id=conversation_id,
                    assistant_code=assistant.code,
                    assistant_name=assistant.name,
                    sender="user",
                    text=request.message,
                    user_name="Thí sinh / Sinh viên",
                ),
            )
        except Exception as conv_user_err:
            logger.warning("failed_to_record_user_message_in_chat_stream: %s", conv_user_err)

        yield f"event: status\ndata: {json.dumps({'stage': 'retrieving', 'message': 'Đang tìm kiếm tài liệu đối soát...', 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"

        runtime_profile = build_runtime_profile(assistant)
        prepared_message = _format_message_with_attachments(request.message, request.attachments)
        sanitized_message = prepare_user_message(prepared_message, runtime_profile)
        workflow_request = WorkflowExecuteRequest(
            workflow_id=assistant.workflow_id,
            workflow_version_id=getattr(assistant, "published_workflow_version_id", None),
            inputs={
                "message": sanitized_message,
                "is_approved": False,
                "format": "docx,pdf",
                "conversation_history": recent_history,
            },
            tenant_id=request.tenant_id,
            conversation_id=conversation_id,
        )

        try:
            workflow_response = await _get_workflow_service().execute(
                db,
                workflow_request,
                assistant_profile=runtime_profile,
                correlation_id=correlation_id,
            )
        except Exception as e:
            logger.error("Workflow execution failed during chat_stream: %s", e)
            err_data = json.dumps({"error": f"Lỗi thực thi quy trình: {e}"}, ensure_ascii=False)
            yield f"event: error\ndata: {err_data}\n\n"
            return

        citations = workflow_response.outputs.get("citations", [])
        if isinstance(citations, list):
            for cite in citations:
                yield f"event: citation\ndata: {json.dumps(cite, ensure_ascii=False)}\n\n"

        artifacts = workflow_response.outputs.get("artifacts", [])
        if isinstance(artifacts, list):
            for art in artifacts:
                yield f"event: artifact\ndata: {json.dumps(art, ensure_ascii=False)}\n\n"

        approval_id = None
        if workflow_response.status == "paused_for_approval":
            output_status = "paused_for_approval"
            action_req = (
                workflow_response.outputs.get("action_required")
                or "Yêu cầu thực thi tác vụ cần phê duyệt của nhân sự."
            )
            approval_id = (
                workflow_response.outputs.get("approval_id")
                or workflow_response.outputs.get("checkpoint")
                or "pending"
            )
            approval_payload = {
                "approval_id": approval_id,
                "paused_node_id": workflow_response.paused_node_id or workflow_response.outputs.get("checkpoint"),
                "action_required": action_req,
                "tool_name": workflow_response.outputs.get("tool_name"),
            }
            yield f"event: approval_required\ndata: {json.dumps(approval_payload, ensure_ascii=False)}\n\n"
            answer = (
                f"Yêu cầu thực thi tác vụ '{action_req}' đang chờ cán bộ có thẩm quyền phê duyệt.\n\n"
                f"- **Mã yêu cầu:** `{approval_id}`\n"
                f"- **Trạng thái:** Chờ phê duyệt (Human-in-the-loop)\n\n"
                f"Quản trị viên có thể xem xét và phê duyệt tại mục [Hộp Thư Phê Duyệt](/runs)."
            )
        else:
            answer = workflow_response.outputs.get("answer")
            if not isinstance(answer, str) or not answer.strip():
                guardrails = getattr(getattr(assistant, "config", None), "guardrails", None)
                answer = getattr(guardrails, "no_answer_message", "Xin lỗi, hiện tại tôi chưa có dữ liệu chính thức để trả lời câu hỏi này.")
            output_status = str(workflow_response.outputs.get("status") or workflow_response.status)

        words = answer.split(" ")
        for idx, word in enumerate(words):
            suffix = " " if idx < len(words) - 1 else ""
            delta = word + suffix
            yield f"event: token\ndata: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.012)

        # Record assistant answer in persistent conversation thread
        try:
            from app.modules.conversations.schemas import ConversationCreateMessageRequest
            from app.modules.conversations.service import conversation_service

            await conversation_service.record_message(
                db,
                ConversationCreateMessageRequest(
                    thread_id=conversation_id,
                    assistant_code=assistant.code,
                    assistant_name=assistant.name,
                    sender="assistant",
                    text=answer,
                ),
            )
        except Exception as conv_asst_err:
            logger.warning("failed_to_record_assistant_message_in_chat_stream: %s", conv_asst_err)

        sample_questions = getattr(assistant, "sample_questions", None)
        if not sample_questions:
            config = getattr(assistant, "config", None)
            if hasattr(config, "persona_scope"):
                sample_questions = getattr(config.persona_scope, "sample_questions", [])
            elif isinstance(config, dict):
                sample_questions = config.get("persona_scope", {}).get("sample_questions", [])
            else:
                sample_questions = []

        output_status = str(workflow_response.outputs.get("status") or workflow_response.status)
        if output_status == "insufficient_context":
            try:
                from app.modules.evaluation.service import evaluation_service

                await evaluation_service.record_gap(
                    db,
                    assistant_code=assistant.code,
                    collection_id=assistant.collection_id,
                    question=request.message,
                )
            except Exception as gap_err:
                logger.warning("failed_to_record_knowledge_gap_in_chat_stream: %s", gap_err)

        # Record LLM Usage
        try:
            from app.modules.modelops.service import modelops_service

            model_name = _extract_primary_model(assistant)
            prompt_toks = max(1, len(request.message) // 4 + 80)
            comp_toks = max(1, len(answer) // 4)
            await modelops_service.record_usage_log(
                db,
                tenant_id=getattr(assistant, "tenant_id", "tenant_qnu"),
                assistant_id=assistant.code,
                conversation_id=conversation_id,
                provider="qnu_workflow",
                model_name=model_name,
                prompt_tokens=prompt_toks,
                completion_tokens=comp_toks,
                latency_ms=workflow_response.latency_ms,
                status="success" if output_status != "error" else "error",
            )
        except Exception as u_err:
            logger.warning("failed_to_record_usage_in_chat_stream: %s", u_err)

        dynamic_suggestions = workflow_response.outputs.get("suggested_questions")
        final_suggested_questions = (
            dynamic_suggestions
            if (dynamic_suggestions and isinstance(dynamic_suggestions, list))
            else (sample_questions or [])[:3]
        )

        done_payload = {
            "conversation_id": conversation_id,
            "latency_ms": workflow_response.latency_ms,
            "suggested_questions": final_suggested_questions,
            "execution_id": workflow_response.execution_id,
            "status": output_status,
            "approval_id": approval_id,
        }
        yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


assistant_chat_service = AssistantChatService()
