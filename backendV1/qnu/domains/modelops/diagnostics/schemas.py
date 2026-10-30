from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from qnu.ports.provider_diagnostics import DiagnosticKind, DiscoveredModel


class ProbeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capability: Literal["chat", "embedding", "rerank", "ocr"]


class DiagnosticCheck(BaseModel):
    id: str
    key_id: str | None = None
    kind: DiagnosticKind
    outcome: Literal["ok", "failed", "unsupported"]
    configuration_status: Literal["current", "stale"] = "current"
    tested_at: datetime
    latency_ms: int | None = None
    code: str
    detail: str
    http_status: int | None = None
    retry_after: datetime | None = None
    requested_model: str
    observed_model: str | None = None
    observed_dimension: int | None = None
    total_tokens: int | None = None
    models: list[str] = Field(default_factory=list)
    model_metadata: list[DiscoveredModel] = Field(default_factory=list)


class ProviderDiagnostics(BaseModel):
    provider_id: str
    configured_active: bool
    checks: list[DiagnosticCheck] = Field(default_factory=list)
