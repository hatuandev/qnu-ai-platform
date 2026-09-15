"""Pydantic Schemas for QNU AI Assistants — Catalogs, Chat Requests & Responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AssistantResponse(BaseModel):
    id: str
    code: str = Field(..., description="Mã duy nhất: admissions, regulations, library...")
    name: str = Field(..., description="Tên hiển thị của Trợ lý")
    description: str
    avatar_url: str | None = None
    category: str
    workflow_id: str
    collection_id: str
    is_active: bool
    sample_questions: list[str] = Field(
        default_factory=list, description="Các câu hỏi mẫu gợi ý"
    )

    model_config = {"from_attributes": True}


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="Nội dung câu hỏi người dùng")
    conversation_id: str | None = Field(None, description="Mã phiên trao đổi")
    tenant_id: str = Field("tenant_qnu", description="Mã người thuê")
    stream: bool = Field(False, description="Chế độ Streaming")


class AssistantChatResponse(BaseModel):
    assistant_code: str
    assistant_name: str
    answer: str
    status: str = Field(..., description="answered, insufficient_context, paused_for_approval")
    citations: list[dict[str, Any]] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    execution_id: str | None = None
