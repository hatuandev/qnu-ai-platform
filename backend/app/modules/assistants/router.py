"""FastAPI Router for QNU AI Assistants — Catalog Browsing & Conversational Chat."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.assistants.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantResponse,
)
from app.modules.assistants.service import assistant_service

router = APIRouter(prefix="/assistants", tags=["05 Trợ lý Chuyên trách Chuẩn QNU"])


@router.get(
    "",
    response_model=list[AssistantResponse],
    summary="Liệt kê danh mục 05 Trợ lý Chuyên trách Chuẩn của Trường Đại học Quy Nhơn",
)
async def list_assistants(
    db: AsyncSession = Depends(get_db),
) -> list[AssistantResponse]:
    return await assistant_service.list_assistants(db)


@router.get(
    "/{code}",
    response_model=AssistantResponse,
    summary="Xem thông tin chi tiết, phạm vi và câu hỏi mẫu của một Trợ lý AI",
)
async def get_assistant(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> AssistantResponse:
    return await assistant_service.get_assistant(db, code)


@router.post(
    "/{code}/chat",
    response_model=AssistantChatResponse,
    summary="Hội thoại trực tiếp với Trợ lý AI qua luồng Workflow DAG chuyên biệt",
)
async def chat_with_assistant(
    code: str,
    body: AssistantChatRequest,
    db: AsyncSession = Depends(get_db),
) -> AssistantChatResponse:
    return await assistant_service.chat(db, code, body)
