"""Provider-first admin contracts. A connection has zero or more runnable models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from qnu.domains.modelops.capacity.schemas import ModelTokenLimits

Family = Literal["openai", "gemini", "qnu", "custom"]


class ConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    family: Family = "custom"
    base_url: str = Field(min_length=8, max_length=1024)
    timeout_seconds: int = Field(30, ge=1, le=300)


class ConnectionUpdate(ConnectionCreate):
    is_active: bool | None = None


class ConnectionResponse(BaseModel):
    id: str
    name: str
    family: Family
    base_url: str
    timeout_seconds: int
    is_active: bool
    is_connection: bool = True
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
