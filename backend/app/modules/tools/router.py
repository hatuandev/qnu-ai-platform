"""API Router for Tool Gateway & Action Execution."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.tools.schemas import (
    ToolDefinitionResponse,
    ToolExecuteRequest,
    ToolExecuteResponse,
)
from app.modules.tools.service import ToolService

router = APIRouter(prefix="/tools", tags=["Tool Gateway & Function Calling"])
service = ToolService()


@router.get("", response_model=list[ToolDefinitionResponse])
async def list_tools(
    category: str | None = Query(None, description="Lọc theo danh mục: admissions, drafting, question_bank"),
) -> list[ToolDefinitionResponse]:
    """Danh sách tất cả các công cụ (Tools) đã đăng ký trong hệ thống."""
    return service.list_tools(category=category)


@router.get("/schemas", response_model=list[dict[str, Any]])
async def get_tool_schemas(
    category: str | None = Query(None, description="Lọc schema theo danh mục"),
) -> list[dict[str, Any]]:
    """Lấy danh sách lược đồ OpenAPI 3.0 của các tool phục vụ Function Calling của LLM."""
    return service.get_openapi_schemas(category=category)


@router.get("/{tool_name}", response_model=ToolDefinitionResponse)
async def get_tool_detail(tool_name: str) -> ToolDefinitionResponse:
    """Xem chi tiết một công cụ theo mã định danh."""
    return service.get_tool(tool_name)


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    request: ToolExecuteRequest,
    session: AsyncSession = Depends(get_db),
) -> ToolExecuteResponse:
    """Thực thi một công cụ trong môi trường Sandboxed có ghi vết kiểm toán (Audit Logging)."""
    return await service.execute_tool(session=session, request=request)
