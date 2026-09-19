"""Pydantic Schemas for Tool Gateway — Function Calling Schemas & Executions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OpenAPIFunctionSchema(BaseModel):
    name: str = Field(..., description="Tên hàm Function Calling")
    description: str = Field(..., description="Mô tả chức năng của tool cho LLM")
    parameters: dict[str, Any] = Field(..., description="JSON Schema định nghĩa các tham số đầu vào")


class ToolDefinitionResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    category: str
    openapi_schema: OpenAPIFunctionSchema | dict[str, Any]
    is_builtin: bool
    is_active: bool
    requires_approval: bool

    model_config = {"from_attributes": True}


class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., description="Tên tool cần thực thi")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tham số truyền vào tool")
    approval_id: str | None = Field(None, description="Mã phê duyệt HITL hợp lệ từ CSDL khi gọi tool có tác dụng phụ")
    tenant_id: str = Field("tenant_qnu", description="Mã người thuê")
    assistant_code: str | None = Field(None, description="Mã trợ lý gọi tool")
    conversation_id: str | None = Field(None, description="Mã phiên trao đổi")


class ToolExecuteResponse(BaseModel):
    tool_name: str
    status: str = Field(..., description="Trạng thái: success, failed, requires_approval")
    result: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    error_message: str | None = None
