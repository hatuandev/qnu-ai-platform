"""API Caller Node Handler — Connects and queries tools via Tool Gateway."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.tools.registry import tool_registry
from app.modules.tools.schemas import ToolExecuteRequest
from app.modules.tools.service import tool_service
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)


class APICallerNodeHandler(BaseNodeHandler):
    """Executes a registered tool or external API within workflow execution via Tool Gateway."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        tool_id = config.get("tool_id") or config.get("tool_name", "")
        on_error_behavior = config.get("on_error_behavior", "return_empty")
        fallback_message = config.get(
            "fallback_message",
            "Không thể kết nối hoặc truy vấn dữ liệu từ công cụ ngoại vi.",
        )

        if not tool_id:
            return NodeExecutionResult(
                node_id=node_spec.id,
                status="completed",
                output={"status": "skipped", "reason": "No tool_id specified in node config"},
            )

        clean_tool_name = tool_id.replace("tool_", "") if tool_id.startswith("tool_") else tool_id

        tool = tool_registry.get(clean_tool_name) or tool_registry.get(tool_id)
        if not tool:
            if on_error_behavior == "fail_workflow":
                return NodeExecutionResult(
                    node_id=node_spec.id,
                    status="failed",
                    error=f"Công cụ '{tool_id}' không tồn tại trong hệ thống.",
                )
            return NodeExecutionResult(
                node_id=node_spec.id,
                status="completed",
                output={
                    "status": "error",
                    "error": f"Tool '{tool_id}' not found",
                    "data": (
                        {}
                        if on_error_behavior == "return_empty"
                        else {"message": fallback_message}
                    ),
                },
            )

        # Collect parameters from context.inputs and node config
        params: dict[str, Any] = {}
        for key, value in context.inputs.items():
            if key not in ("message", "query"):
                params[key] = value

        if "params" in config and isinstance(config["params"], dict):
            params.update(config["params"])

        assistant_code = None
        if context.assistant_profile:
            assistant_code = (
                getattr(context.assistant_profile, "assistant_code", None)
                or getattr(context.assistant_profile, "code", None)
            )


        # Route through ToolService to enforce assistant allowlist, HITL approval, and audit logging
        if context.db is not None:
            tool_req = ToolExecuteRequest(
                tool_name=clean_tool_name,
                parameters=params,
                tenant_id=context.tenant_id or "tenant_qnu",
                assistant_code=assistant_code,
                conversation_id=context.conversation_id,
            )
            try:
                tool_resp = await tool_service.execute_tool(context.db, tool_req)
                output_data: dict[str, Any] = {
                    "tool_id": tool_id,
                    "status": tool_resp.status,
                    "result": tool_resp.result,
                }
                if isinstance(tool_resp.result, dict):
                    output_data.update(tool_resp.result)

                return NodeExecutionResult(
                    node_id=node_spec.id,
                    status="completed",
                    output=output_data,
                )
            except AppException as exc:
                if exc.code == "tool_requires_approval":
                    logger.info(
                        "APICallerNodeHandler pausing for approval on node %s (tool: %s)",
                        node_spec.id,
                        clean_tool_name,
                    )
                    return NodeExecutionResult(
                        node_id=node_spec.id,
                        status="paused_for_approval",
                        output={
                            "checkpoint": node_spec.id,
                            "action_required": exc.message,
                            "pending_approval": True,
                            "tool_name": clean_tool_name,
                            "parameters": params,
                        },
                    )
                if exc.code == "tool_not_allowed_for_assistant":
                    logger.warning(
                        "Tool %s not allowed for assistant %s: %s",
                        clean_tool_name,
                        assistant_code,
                        exc.message,
                    )
                    if on_error_behavior == "fail_workflow":
                        return NodeExecutionResult(
                            node_id=node_spec.id,
                            status="failed",
                            error=exc.message,
                        )
                    return NodeExecutionResult(
                        node_id=node_spec.id,
                        status="completed",
                        output={
                            "tool_id": tool_id,
                            "status": "error",
                            "error": exc.message,
                            "data": (
                                {}
                                if on_error_behavior == "return_empty"
                                else {"message": fallback_message}
                            ),
                        },
                    )
                logger.warning("APICallerNodeHandler failed executing %s: %s", tool_id, exc)
                if on_error_behavior == "fail_workflow":
                    return NodeExecutionResult(
                        node_id=node_spec.id,
                        status="failed",
                        error=f"Lỗi thực thi công cụ '{tool_id}': {exc}",
                    )
                return NodeExecutionResult(
                    node_id=node_spec.id,
                    status="completed",
                    output={
                        "tool_id": tool_id,
                        "status": "error",
                        "error": str(exc),
                        "data": (
                            {}
                            if on_error_behavior == "return_empty"
                            else {"message": fallback_message}
                        ),
                    },
                )
            except Exception as exc:
                logger.warning("APICallerNodeHandler unexpected error on %s: %s", tool_id, exc)
                if on_error_behavior == "fail_workflow":
                    return NodeExecutionResult(
                        node_id=node_spec.id,
                        status="failed",
                        error=f"Lỗi thực thi công cụ '{tool_id}': {exc}",
                    )
                return NodeExecutionResult(
                    node_id=node_spec.id,
                    status="completed",
                    output={
                        "tool_id": tool_id,
                        "status": "error",
                        "error": str(exc),
                        "data": (
                            {}
                            if on_error_behavior == "return_empty"
                            else {"message": fallback_message}
                        ),
                    },
                )

        # Fallback when context has no DB session (e.g., isolated in-memory unit tests)
        if context.db is None and settings.ENVIRONMENT not in ("test", "testing"):
            raise AppException(
                "Không thể thực thi Tool Gateway: Thiếu phiên kết nối cơ sở dữ liệu bảo mật (Database Session Missing).",
                code="database_session_required",
                status_code=500,
            )

        if tool.requires_approval:
            is_approved = bool(params.get("is_approved"))
            approved_by = params.get("approved_by")
            if not is_approved or not approved_by:
                logger.info(
                    "APICallerNodeHandler pausing for approval on node %s (tool: %s)",
                    node_spec.id,
                    clean_tool_name,
                )
                return NodeExecutionResult(
                    node_id=node_spec.id,
                    status="paused_for_approval",
                    output={
                        "checkpoint": node_spec.id,
                        "action_required": f"Công cụ '{clean_tool_name}' yêu cầu phê duyệt nhân sự (Human-in-the-loop) với danh tính người phê duyệt hợp lệ trước khi thực thi.",
                        "pending_approval": True,
                        "tool_name": clean_tool_name,
                        "parameters": params,
                    },
                )

        try:
            tool_result = await tool.execute(
                params,
                context={
                    "tenant_id": context.tenant_id,
                    "conversation_id": context.conversation_id,
                    "assistant_code": assistant_code,
                },
            )
            output_data = {
                "tool_id": tool_id,
                "status": "success",
                "result": tool_result,
            }
            if isinstance(tool_result, dict):
                output_data.update(tool_result)

            return NodeExecutionResult(
                node_id=node_spec.id,
                status="completed",
                output=output_data,
            )
        except Exception as exc:
            logger.warning("APICallerNodeHandler failed executing %s: %s", tool_id, exc)
            if on_error_behavior == "fail_workflow":
                return NodeExecutionResult(
                    node_id=node_spec.id,
                    status="failed",
                    error=f"Lỗi thực thi công cụ '{tool_id}': {exc}",
                )

            return NodeExecutionResult(
                node_id=node_spec.id,
                status="completed",
                output={
                    "tool_id": tool_id,
                    "status": "error",
                    "error": str(exc),
                    "data": (
                        {}
                        if on_error_behavior == "return_empty"
                        else {"message": fallback_message}
                    ),
                },
            )

