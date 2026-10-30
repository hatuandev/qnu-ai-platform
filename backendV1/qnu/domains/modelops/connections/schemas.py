"""Provider-first admin contracts. A connection has zero or more runnable models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qnu.domains.modelops.capacity.schemas import ModelTokenLimits
from qnu.ports.provider_diagnostics import DiscoveredModel

Family = Literal["openai", "gemini", "qnu", "custom", "anthropic"]


class ConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    family: Family = "custom"
    base_url: str = Field(min_length=8, max_length=1024)
    timeout_seconds: int = Field(30, ge=1, le=300)
    prefix: str | None = Field(None, max_length=64)
    api_type: str | None = Field(None, max_length=64)


class ConnectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str | None = Field(None, min_length=2, max_length=120)
    family: Family | None = None
    base_url: str | None = Field(None, min_length=8, max_length=1024)
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    prefix: str | None = Field(None, max_length=64)
    api_type: str | None = Field(None, max_length=64)
    is_active: bool | None = None


class ConnectionResponse(BaseModel):
    id: str
    name: str
    family: Family
    base_url: str
    timeout_seconds: int
    is_active: bool
    is_connection: bool = True
    prefix: str | None = None
    api_type: str | None = None
    model_count: int
    active_model_count: int
    active_keys_count: int
    total_keys_count: int
    last_probe_status: Literal["success", "failed", "unsupported", "untested", "stale"]
    last_probe_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ConnectionModelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    model_name: str = Field(min_length=1, max_length=128)
    capabilities: list[Literal["chat", "embedding", "rerank", "ocr"]] = Field(
        min_length=1, max_length=4
    )
    token_limits: ModelTokenLimits | None = None
    embedding_dimension: int | None = Field(None, ge=1, le=65536)
    discovery_check_id: str | None = Field(None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def one_capacity_source(self):
        if self.discovery_check_id and (
            self.token_limits is not None or self.embedding_dimension is not None
        ):
            raise ValueError("Chọn thông số server hoặc khai báo tay, không dùng đồng thời.")
        return self


class ConnectionTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    key_id: str | None = Field(None, min_length=1, max_length=64)
    api_key: str | None = Field(None, min_length=1, max_length=4096, repr=False)
    model_name: str | None = Field(None, max_length=200)

    @model_validator(mode="after")
    def one_credential(self):
        if self.key_id and self.api_key:
            raise ValueError("Chọn khóa đã lưu hoặc nhập khóa thử, không dùng đồng thời.")
        return self


class ConnectionTestResponse(BaseModel):
    ok: bool
    key_id: str | None = None
    check_id: str | None = None
    tested_at: datetime | None = None
    code: str = "diagnostic_ok"
    http_status: int | None = None
    retry_after: datetime | None = None
    latency_ms: int | None = None
    detail: str
    models: list[str] = Field(default_factory=list)
    model_metadata: list[DiscoveredModel] = Field(default_factory=list)


class CapacitySyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_id: str = Field(min_length=1, max_length=64)
    model_names: list[str] = Field(min_length=1, max_length=500)
