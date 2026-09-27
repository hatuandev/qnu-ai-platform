"""API Router for Tool Gateway & Action Execution."""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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


def _content_disposition(filename: str) -> str:
    """Build an RFC 5987 download header that preserves Vietnamese filenames."""
    normalized = unicodedata.normalize("NFC", filename)
    ascii_name = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode()
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_name).strip("._")
    if not ascii_name:
        ascii_name = "qnu-document"
    encoded_name = quote(normalized, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded_name}"


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


@router.get("/artifacts/{filename}")
async def download_artifact(filename: str) -> Response:
    """Download an exported document artifact (DOCX, PDF, XLSX, etc.)."""
    from app.core.storage import storage_service

    rel_path = f"artifacts/{filename}"
    file_bytes = await storage_service.get(rel_path)
    if not file_bytes:
        raise HTTPException(status_code=404, detail=f"Tệp '{filename}' không tồn tại hoặc đã hết hạn.")

    media_type = "application/octet-stream"
    if filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": _content_disposition(filename),
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/export/document")
async def export_document(payload: dict[str, Any]) -> dict[str, Any]:
    """Export administrative document to DOCX and/or PDF using docxtpl and Gotenberg."""
    from app.modules.tools.document_generator import export_document_package

    template_code = str(payload.get("template_code") or "to_trinh")
    context = payload.get("context") or {}
    formats = payload.get("formats") or ["docx", "pdf"]
    base_name = payload.get("base_name")

    artifacts = await export_document_package(
        template_code=template_code,
        context=context,
        formats=formats,
        base_name=base_name,
    )
    return {
        "status": "success",
        "artifacts": artifacts,
    }

