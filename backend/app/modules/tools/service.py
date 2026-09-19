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
        if tool.requires_approval and not request.parameters.get("is_approved"):
            raise AppException(
                f"Công cụ '{request.tool_name}' yêu cầu phê duyệt nhân sự (Human-in-the-loop) trước khi thực thi.",
                code="tool_requires_approval",
                status_code=403,
                details={"tool_name": request.tool_name},
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

