"""Schemas for external application API keys and OpenAI compatible endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- Application & Key Management Schemas ---


class AppClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=1000)


class AppClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    name: str
    description: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class AppApiKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_id: str | None = None
    app_name: str | None = Field(
        default=None, max_length=160, description="Create new app if app_id not given"
    )
    name: str = Field(min_length=2, max_length=160)
    allowed_assistant_ids: list[str] = Field(default_factory=list)
    allow_all_assistants: bool = False
    rate_limit_rpm: int | None = Field(default=60, ge=1, le=10000)
    rate_limit_rpd: int | None = Field(default=10000, ge=1, le=1000000)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)
    idempotency_key: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def explicit_scope(self):
        if self.allow_all_assistants == bool(self.allowed_assistant_ids):
            raise ValueError("Chọn rõ tất cả trợ lý hoặc ít nhất một trợ lý cụ thể.")
        return self


class AppApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    app_id: str
    app_name: str
    workspace_id: str
    name: str
    key_prefix: str
    status: str
    allowed_assistant_ids: list[str]
    rate_limit_rpm: int | None
    rate_limit_rpd: int | None
    expires_at: datetime | None
    last_used_at: datetime | None
    rotated_from_key_id: str | None
    revoked_at: datetime | None
    revoked_reason: str | None
    created_by: str
    created_at: datetime


class AppApiKeySecretResponse(AppApiKeyResponse):
    """Returned ONLY ONCE upon creation or rotation. Plaintext secret is never stored."""

    secret_key: str = Field(repr=False)


class AppApiKeyStatusUpdate(BaseModel):
    status: Literal["active", "suspended"]
    reason: str | None = Field(default=None, max_length=255)


class AppApiKeyRotateRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=128)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


class AppApiKeyRevokeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


class AppRequestLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    app_id: str
    key_id: str
    workspace_id: str
    assistant_id: str
    endpoint: str
    status_code: int
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    error_code: str | None
    created_at: datetime


class IntegrationConfigResponse(BaseModel):
    base_url: str
    openai_endpoint: str
    supported_protocols: list[str]
    capabilities: list[str]
    version: str = "v1alpha1"


# --- OpenAI Compatible Schemas ---


class OpenAIModelItem(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "qnu-ai"
    permission: list[dict[str, Any]] = Field(default_factory=list)
    root: str | None = None
    parent: str | None = None
    name: str
    description: str


class OpenAIModelsResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[OpenAIModelItem]


class OpenAIChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class OpenAIChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(min_length=1, max_length=64)
    messages: list[OpenAIChatMessage] = Field(min_length=1, max_length=21)
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    tools: list[Any] | None = None
    functions: list[Any] | None = None


class OpenAIChoiceMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class OpenAIChoice(BaseModel):
    index: int = 0
    message: OpenAIChoiceMessage
    finish_reason: Literal["stop", "length"] = "stop"


class OpenAIUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class OpenAIChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChoice]
    usage: OpenAIUsage
    qnu_extensions: dict[str, Any] = Field(default_factory=dict)
