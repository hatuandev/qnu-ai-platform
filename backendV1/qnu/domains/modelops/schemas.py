"""DTOs for ModelOps providers, credentials, defaults and workspace allowlists."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from qnu.domains.modelops.capacity.schemas import ModelTokenLimits

ProviderType = Literal["openai_compatible", "gemini", "local", "nemotron", "paddleocr"]
Capability = Literal["chat", "embedding", "rerank", "ocr"]


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class ProviderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=2, max_length=255)
    provider_type: ProviderType
    base_url: str = Field(..., min_length=8, max_length=1024)
    model_name: str = Field(..., min_length=1, max_length=200)
    capabilities: list[Capability] = Field(..., min_length=1)
    priority: int = Field(5, ge=1, le=10)
    timeout_seconds: int = Field(30, ge=1, le=600)
    token_limits: ModelTokenLimits | None = None
    embedding_dimension: int | None = Field(None, strict=True, gt=0, le=65536)

    @field_validator("name", "base_url", "model_name", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _strip(value)

    @field_validator("capabilities")
    @classmethod
    def dedupe_capabilities(cls, value: list[str]) -> list[str]:
        unique = list(dict.fromkeys(value))
        if len(unique) != len(value):
            raise ValueError("Capabilities không được trùng.")
        return unique


class ProviderUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=2, max_length=255)
    base_url: str | None = Field(None, min_length=8, max_length=1024)
    model_name: str | None = Field(None, min_length=1, max_length=200)
    capabilities: list[Capability] | None = Field(None, min_length=1)
    is_active: bool | None = None
    priority: int | None = Field(None, ge=1, le=10)
    timeout_seconds: int | None = Field(None, ge=1, le=600)
    token_limits: ModelTokenLimits | None = None
    embedding_dimension: int | None = Field(None, strict=True, gt=0, le=65536)

    @field_validator("name", "base_url", "model_name", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _strip(value)

    @field_validator("capabilities")
    @classmethod
    def unique_capabilities(cls, value):
        if value is not None and len(value) != len(set(value)):
            raise ValueError("Capabilities không được trùng.")
        return value


class ProviderResponse(BaseModel):
    is_connection: bool = False
    parent_id: str | None = None
    id: str
    name: str
    provider_type: str
    base_url: str
    model_name: str
    capabilities: list[str]
    is_active: bool
    priority: int
    timeout_seconds: int
    token_limits: ModelTokenLimits | None = None
    capacity_status: Literal["unknown", "configured", "stale"] = "unknown"
    capacity_basis: Literal["operator_configured", "server_reported"] | None = None
    embedding_dimension: int | None = None
    embedding_dimension_status: Literal["unknown", "configured", "stale"] = "unknown"
    created_at: datetime
    updated_at: datetime


class KeyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=2, max_length=120)
    secret: str = Field(..., min_length=8, max_length=4096, repr=False)
    priority: int = Field(5, ge=1, le=10)

    @field_validator("name", "secret", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _strip(value)


class KeyRevokeRequest(BaseModel):
    reason: str | None = Field(None, max_length=512)


class KeyRotateRequest(KeyCreateRequest):
    reason: str | None = Field(None, max_length=512)


class KeyAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_ref: str | None
    key_id: str | None
    action: str
    reason: str | None
    created_at: datetime


class KeyResponse(BaseModel):
    model_ids: list[str] | None = None
    lease_until: datetime | None = None
    cooldown_until: datetime | None = None
    consecutive_failures: int = 0
    id: str
    provider_id: str
    name: str
    masked_hint: str
    status: str
    priority: int
    created_at: datetime
    updated_at: datetime


class DefaultsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chat_provider_id: str | None = Field(None, max_length=64)
    chat_model: str | None = Field(None, max_length=200)
    embedding_provider_id: str | None = Field(None, max_length=64)
    embedding_model: str | None = Field(None, max_length=200)
    rerank_provider_id: str | None = Field(None, max_length=64)
    rerank_model: str | None = Field(None, max_length=200)
    ocr_provider_id: str | None = Field(None, max_length=64)
    ocr_model: str | None = Field(None, max_length=200)


class DefaultsResponse(BaseModel):
    chat_provider_id: str | None = None
    chat_model: str | None = None
    embedding_provider_id: str | None = None
    embedding_model: str | None = None
    rerank_provider_id: str | None = None
    rerank_model: str | None = None
    ocr_provider_id: str | None = None
    ocr_model: str | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class AllowlistUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_ids: list[str] = Field(default_factory=list, max_length=50)
    default_provider_id: str | None = Field(None, max_length=64)
    defaults: dict[Capability, str] = Field(default_factory=dict)

    @field_validator("provider_ids")
    @classmethod
    def dedupe_ids(cls, value: list[str]) -> list[str]:
        unique = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if len(unique) != len(value):
            raise ValueError("provider_ids không được trùng.")
        return unique


class AllowedProviderItem(BaseModel):
    provider_id: str
    name: str
    capabilities: list[str]
    is_active: bool
    is_default: bool
    default_capabilities: list[Capability] = Field(default_factory=list)


class AllowlistResponse(BaseModel):
    workspace_id: str
    providers: list[AllowedProviderItem] = Field(default_factory=list)


class WorkspaceDefaultsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    defaults: dict[Capability, str] = Field(default_factory=dict)


class CatalogItem(BaseModel):
    id: str
    name: str
    model_name: str
    capabilities: list[str]
    default_capabilities: list[str] = Field(default_factory=list)


class QuotaUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    monthly_token_limit: int | None = Field(None, ge=0, le=10**15)
    is_blocked: bool = False


class QuotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workspace_id: str
    month_period: date
    monthly_token_limit: int | None
    tokens_used: int
    tokens_reserved: int
    is_blocked: bool
    configured: bool = True


class UsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    provider_id: str
    request_id: str
    capability: str
    model_name: str
    status: str
    reserved_tokens: int
    total_tokens: int | None
    cost_usd: Decimal | None
    created_at: datetime


class ModelOpsEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_ref: str
    action: str
    provider_id: str | None
    detail: dict[str, Any]
    created_at: datetime


class ProviderSummaryItem(ProviderResponse):
    id: str
    name: str
    provider_type: str
    base_url: str
    model_name: str
    capabilities: list[str]
    is_active: bool
    priority: int
    timeout_seconds: int
    active_keys_count: int = 0
    total_keys_count: int = 0
    last_probe_status: Literal["success", "failed", "unsupported", "untested", "stale"] = "untested"
    last_probe_at: datetime | None = None
    last_probe_latency_ms: int | None = None
