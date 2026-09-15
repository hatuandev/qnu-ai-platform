"""Pydantic Schemas for ModelOps — LLM Requests, Responses, and Quota Management."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ..., description="Vai trò: system, user, hoặc assistant"
    )
    content: str = Field(..., min_length=1, description="Nội dung tin nhắn")


class LLMGenerateRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, description="Danh sách ngữ cảnh tin nhắn")
    tenant_id: str = Field("qnu-default", description="Mã định danh đơn vị / khoa phòng")
    assistant_code: str | None = Field(
        None, description="Mã trợ lý: admissions, regulations, library..."
    )
    conversation_id: str | None = Field(None, description="Mã phiên hội thoại")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="Độ sáng tạo")
    max_tokens: int = Field(2000, ge=50, le=8192, description="Giới hạn số token đầu ra")
    stream: bool = Field(False, description="Bật chế độ Streaming SSE")


class LLMGenerateResponse(BaseModel):
    content: str = Field(..., description="Văn bản sinh ra từ mô hình")
    provider: str = Field(..., description="Nhà cung cấp đã phục vụ: openai, gemini, local_vllm")
    model: str = Field(..., description="Tên mô hình cụ thể")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    is_fallback: bool = Field(
        False, description="True nếu phải chuyển sang nhà cung cấp dự phòng"
    )


class ProviderConfigCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    provider_type: Literal["openai", "gemini", "local_vllm"]
    model_name: str = Field(..., min_length=2, max_length=100)
    api_base_url: str | None = None
    api_key: str | None = None
    priority: int = Field(1, ge=1, le=10, description="1 là ưu tiên cao nhất")
    timeout_seconds: int = Field(15, ge=5, le=120)
    extra_config: dict[str, Any] = Field(default_factory=dict)


class ProviderConfigResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    model_name: str
    api_base_url: str | None = None
    priority: int
    is_active: bool
    timeout_seconds: int

    model_config = {"from_attributes": True}


class TenantQuotaResponse(BaseModel):
    tenant_id: str
    month_period: str
    monthly_token_limit: int
    monthly_cost_limit_usd: float
    tokens_used: int
    cost_used_usd: float
    is_blocked: bool
    usage_percent: float = Field(..., description="Phần trăm hạn ngạch token đã sử dụng")

    model_config = {"from_attributes": True}
