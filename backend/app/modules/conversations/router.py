"""HTTP router for QNU Conversations & Staff Handoff."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.conversations.schemas import (
    ConversationCreateMessageRequest,
    ConversationMessageResponse,
    ConversationReplyRequest,
    ConversationStatusUpdateRequest,
    ConversationThreadDetailResponse,
    ConversationThreadItemResponse,
)
from app.modules.conversations.service import conversation_service

router = APIRouter(prefix="/conversations", tags=["Quản Lý Hội Thoại & Bàn Giao Nhân Sự"])


@router.get("", response_model=list[ConversationThreadItemResponse])
async def list_conversations(
    assistant_code: str | None = Query(None, description="Lọc theo mã trợ lý"),
    status: str | None = Query(None, description="Lọc theo trạng thái: ai_active, handoff_requested, staff_claimed, resolved"),
    search: str | None = Query(None, description="Tìm kiếm theo tên người dùng, email, tin nhắn"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationThreadItemResponse]:
    """Danh sách các phiên hội thoại với Trợ lý AI và yêu cầu hỗ trợ từ thí sinh/sinh viên."""
    return await conversation_service.list_threads(
        db,
        assistant_code=assistant_code,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/{thread_id}", response_model=ConversationThreadDetailResponse)
async def get_conversation_detail(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConversationThreadDetailResponse:
    """Lấy chi tiết phiên hội thoại kèm toàn bộ lịch sử tin nhắn."""
    return await conversation_service.get_thread_detail(db, thread_id)


@router.post("/{thread_id}/reply", response_model=ConversationMessageResponse)
async def reply_conversation(
    thread_id: str,
    body: ConversationReplyRequest,
    db: AsyncSession = Depends(get_db),
) -> ConversationMessageResponse:
    """Cán bộ tư vấn trả lời trực tiếp cho thí sinh/sinh viên và tiếp quản phiên chat."""
    return await conversation_service.reply_from_staff(
        db,
        thread_id=thread_id,
        text=body.text,
        staff_name=body.staff_name,
    )


@router.patch("/{thread_id}/status", response_model=ConversationThreadItemResponse)
async def update_conversation_status(
    thread_id: str,
    body: ConversationStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ConversationThreadItemResponse:
    """Cập nhật trạng thái phiên hội thoại (tiếp quản, hoàn thành, chuyển giao)."""
    return await conversation_service.update_thread_status(
        db,
        thread_id=thread_id,
        status=body.status,
        assigned_to=body.assigned_to,
    )


@router.post(
    "/messages",
    response_model=ConversationMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_conversation_message(
    body: ConversationCreateMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> ConversationMessageResponse:
    """Ghi nhận tin nhắn mới từ client/widget/chat studio vào lịch sử hội thoại."""
    return await conversation_service.record_message(db, body)
