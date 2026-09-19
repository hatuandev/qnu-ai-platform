"""Tool Service handling Tool Gateway operations, execution, and auditing."""

from __future__ import annotations

import time
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.modules.tools.models import ToolExecutionLog
from app.modules.tools.registry import tool_registry
from app.modules.tools.schemas import (
    ToolDefinitionResponse,
    ToolExecuteRequest,
    ToolExecuteResponse,
)

logger = structlog.get_logger(__name__)


class ToolService:
    """Service encapsulating tool discovery, safe execution, and audit logging."""

    def __init__(self) -> None:
        self.registry = tool_registry

    def list_tools(self, category: str | None = None) -> list[ToolDefinitionResponse]:
        """List registered tools formatted for API response."""
        return [
            ToolDefinitionResponse(
                id=f"tool_{t.name}",
                name=t.name,
                display_name=t.display_name,
                description=t.description,
                category=t.category,
                openapi_schema=t.get_openapi_schema(),
                is_builtin=True,
                is_active=True,
                requires_approval=t.requires_approval,
            )
            for t in self.registry.list_all(category)
        ]

    def get_tool(self, name: str) -> ToolDefinitionResponse:
        """Get a single tool definition by name."""
        tool = self.registry.get(name)
        if not tool:
            raise NotFoundException(f"Công cụ (Tool) '{name}' không tồn tại trong hệ thống")
        return ToolDefinitionResponse(
            id=f"tool_{tool.name}",
            name=tool.name,
            display_name=tool.display_name,
            description=tool.description,
            category=tool.category,
            openapi_schema=tool.get_openapi_schema(),
            is_builtin=True,
            is_active=True,
            requires_approval=tool.requires_approval,
        )

    def get_openapi_schemas(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get OpenAPI 3.0 function declaration schemas for LLM injection."""
        return self.registry.list_schemas(category)

    async def execute_tool(
        self,
        session: AsyncSession,
        request: ToolExecuteRequest,
    ) -> ToolExecuteResponse:
        """Execute tool logic safely, track latency and persist audit log."""
        tool = self.registry.get(request.tool_name)
        if not tool:
            raise NotFoundException(f"Công cụ (Tool) '{request.tool_name}' không tồn tại trong hệ thống")

        # 1. Check Assistant enabled_tools allowlist if executed in assistant context
        if request.assistant_code:
            import asyncio

            from sqlalchemy import select

            from app.modules.assistants.models import AssistantModel

            stmt = select(AssistantModel).where(AssistantModel.code == request.assistant_code)
            exec_res = await session.execute(stmt)
            assistant_rec = (
                exec_res.scalar_one_or_none()
                if hasattr(exec_res, "scalar_one_or_none")
                else None
            )
            if asyncio.iscoroutine(assistant_rec):
                assistant_rec = await assistant_rec

            if assistant_rec is not None and (
                isinstance(assistant_rec, AssistantModel) or hasattr(assistant_rec, "config")
            ):
                config_data = assistant_rec.config or {}
                tools_config = (
                    config_data.get("tools")
                    if isinstance(config_data, dict)
                    else getattr(config_data, "tools", None)
                )
                enabled_tools = (
                    tools_config.get("enabled_tools")
                    if isinstance(tools_config, dict)
                    else getattr(tools_config, "enabled_tools", None)
                )
                if (
                    enabled_tools is not None
                    and len(enabled_tools) > 0
                    and request.tool_name not in enabled_tools
                ):
                    raise AppException(
                        f"Công cụ '{request.tool_name}' không được kích hoạt cho trợ lý '{request.assistant_code}'.",
                        code="tool_not_allowed_for_assistant",
                        status_code=403,
                        details={
                            "assistant_code": request.assistant_code,
                            "tool_name": request.tool_name,
                        },
                    )

        # 2. Check approval requirement if tool has side-effects
        approval_rec = None
        if tool.requires_approval:
            approval_id = getattr(request, "approval_id", None) or request.parameters.get("approval_id")
            if not approval_id:
                raise AppException(
                    f"Công cụ '{request.tool_name}' yêu cầu phê duyệt nhân sự (Human-in-the-loop) với mã approval_id hợp lệ trước khi thực thi.",
                    code="tool_requires_approval",
                    status_code=403,
                    details={"tool_name": request.tool_name},
                )

            import hashlib
            import json
            from datetime import UTC, datetime

            from sqlalchemy import select

            from app.modules.workflows.models import WorkflowApprovalRequest

            stmt = select(WorkflowApprovalRequest).where(WorkflowApprovalRequest.id == str(approval_id).strip())
            exec_res = await session.execute(stmt)
            approval_rec = (
                exec_res.scalar_one_or_none()
                if hasattr(exec_res, "scalar_one_or_none")
                else None
            )
            if hasattr(approval_rec, "__await__"):
                approval_rec = await approval_rec

            if not approval_rec:
                raise AppException(
                    f"Không tìm thấy bản ghi phê duyệt với mã '{approval_id}'.",
                    code="approval_not_found",
                    status_code=404,
                    details={"approval_id": approval_id},
                )

            if approval_rec.status == "consumed":
                raise AppException(
                    "Yêu cầu phê duyệt này đã được thực thi trước đó (chống lặp tác vụ).",
                    code="approval_already_consumed",
                    status_code=409,
                    details={"approval_id": approval_id},
                )

            if approval_rec.status != "approved":
                approval_code = "approval_pending" if approval_rec.status == "pending" else "approval_not_approved"
                raise AppException(
                    f"Yêu cầu phê duyệt '{approval_id}' chưa được chấp thuận (trạng thái hiện tại: '{approval_rec.status}').",
                    code=approval_code,
                    status_code=403,
                    details={"approval_id": approval_id, "status": approval_rec.status},
                )

            now_utc = datetime.now(UTC).replace(tzinfo=None)
            if approval_rec.expires_at:
                exp = approval_rec.expires_at
                if exp.tzinfo is not None:
                    exp = exp.astimezone(UTC).replace(tzinfo=None)
                if exp < now_utc:
                    approval_rec.status = "expired"
                    await session.commit()
                    raise AppException(
                        "Yêu cầu phê duyệt đã hết hạn.",
                        code="approval_expired",
                        status_code=403,
                        details={"approval_id": approval_id, "expires_at": approval_rec.expires_at.isoformat()},
                    )

            # Check payload_hash if present
            if approval_rec.payload_hash:
                clean_params = {
                    k: v
                    for k, v in request.parameters.items()
                    if k not in ("approval_id", "is_approved", "approved_by")
                }
                computed_hash = hashlib.sha256(
                    json.dumps(clean_params, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                if approval_rec.payload_hash != computed_hash:
                    raise AppException(
                        "Tham số gọi công cụ không khớp với nội dung đã được cán bộ phê duyệt.",
                        code="approval_payload_mismatch",
                        status_code=403,
                        details={"approval_id": approval_id, "expected_hash": approval_rec.payload_hash},
                    )

        start_time = time.perf_counter()
        status = "success"
        error_message = None
        result: dict[str, Any] = {}

        try:
            result = await tool.execute(
                parameters=request.parameters,
                context={
                    "tenant_id": request.tenant_id,
                    "assistant_code": request.assistant_code,
                    "conversation_id": request.conversation_id,
                },
            )
            # Atomic Consumption upon successful execution
            if approval_rec is not None:
                from datetime import UTC, datetime
                approval_rec.status = "consumed"
                approval_rec.decided_at = datetime.now(UTC).replace(tzinfo=None)
        except Exception as exc:
            logger.error("tool_execution_failed", tool_name=request.tool_name, error=str(exc))
            status = "failed"
            error_message = str(exc)
            result = {"error": str(exc)}

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Audit log into PostgreSQL
        log_record = ToolExecutionLog(
            tool_name=request.tool_name,
            tenant_id=request.tenant_id,
            assistant_code=request.assistant_code,
            conversation_id=request.conversation_id,
            parameters=request.parameters,
            result=result,
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        try:
            session.add(log_record)
            await session.commit()
        except Exception as db_exc:
            logger.warning("failed_to_save_tool_log", error=str(db_exc))
            await session.rollback()

        return ToolExecuteResponse(
            tool_name=request.tool_name,
            status=status,
            result=result,
            latency_ms=latency_ms,
            error_message=error_message,
        )


tool_service = ToolService()

