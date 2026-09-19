"""API Caller Node Handler — Connects and queries tools via Tool Gateway."""

from __future__ import annotations

import logging
from typing import Any

from app.modules.tools.registry import tool_registry
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)


class APICallerNodeHandler(BaseNodeHandler):
    """Executes a registered tool or external API within workflow execution."""

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

        # Collect parameters from context.inputs or node config
        params: dict[str, Any] = {}
        for key, value in context.inputs.items():
            if key not in ("message", "query", "is_approved", "approved_by"):
                params[key] = value

        if "params" in config and isinstance(config["params"], dict):
            params.update(config["params"])

        try:
            tool_result = await tool.execute(params)
            output_data: dict[str, Any] = {
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
