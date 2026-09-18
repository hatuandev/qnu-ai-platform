"""Pydantic schemas and DTOs for QNU Conversations & Staff Handoff."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConversationMessageResponse(BaseModel):
    id: str
    thread_id: str
    sender: Literal["user", "assistant", "agent"]
    text: str
    created_at: datetime


class ConversationThreadItemResponse(BaseModel):
    id: str
    assistant_code: str
    assistant_name: str
    user_name: str
    user_email: str | None = None
    last_message: str
    status: Literal["ai_active", "handoff_requested", "staff_claimed", "resolved"]
    assigned_to: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationThreadDetailResponse(ConversationThreadItemResponse):
    messages: list[ConversationMessageResponse] = Field(default_factory=list)


class ConversationReplyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Nội dung phản hồi từ cán bộ")
    staff_name: str | None = Field(None, max_length=100, description="Tên cán bộ tư vấn")


class ConversationStatusUpdateRequest(BaseModel):
    status: Literal["ai_active", "handoff_requested", "staff_claimed", "resolved"]
    assigned_to: str | None = Field(None, max_length=100)


class ConversationCreateMessageRequest(BaseModel):
    thread_id: str | None = Field(None, description="ID phiên hội thoại (nếu đã có)")
    assistant_code: str = Field(..., min_length=2, max_length=50)
    assistant_name: str | None = Field(None, max_length=150)
    sender: Literal["user", "assistant", "agent"]
    text: str = Field(..., min_length=1)
    user_name: str | None = Field(None, max_length=150)
    user_email: str | None = Field(None, max_length=150)
    request_handoff: bool = Field(False, description="Kích hoạt yêu cầu gặp cán bộ tư vấn")
