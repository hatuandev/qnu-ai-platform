"""Small synthetic diagnostic calls; credentials and response bodies stay private."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DiscoveredModel(BaseModel):
    """Allowlisted server declarations; discovery is not inference verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    context_window_tokens: int | None = Field(None, strict=True, gt=0, le=2147483647)
    max_output_tokens: int | None = Field(None, strict=True, gt=0, le=2147483647)
    embedding_dimension: int | None = Field(None, strict=True, gt=0, le=65536)

    @model_validator(mode="after")
    def consistent_limits(self):
        if (
            self.context_window_tokens is not None
            and self.max_output_tokens is not None
            and self.max_output_tokens > self.context_window_tokens
        ):
            raise ValueError("Output exceeds context")
        return self


DiagnosticKind = Literal["discovery", "chat", "embedding", "rerank", "ocr"]


@dataclass(frozen=True)
class DiagnosticTarget:
    endpoint: str
    model: str
    provider_type: str
    timeout_seconds: float
    api_key: str | None = field(default=None, repr=False)
    expected_dimension: int | None = None
    max_output_tokens: int = 1024
    auth_optional: bool = False
    auth_scheme: Literal["bearer", "anthropic"] = "bearer"


@dataclass
class DiagnosticResult:
    outcome: Literal["ok", "failed", "unsupported"]
    code: str
    detail: str
    latency_ms: int | None = None
    http_status: int | None = None
    retry_after: datetime | None = None
    observed_model: str | None = None
    observed_dimension: int | None = None
    total_tokens: int | None = None
    models: list[str] = field(default_factory=list)
    model_metadata: list[DiscoveredModel] = field(default_factory=list)


class ProviderDiagnosticClient(Protocol):
    async def check(self, kind: DiagnosticKind, target: DiagnosticTarget) -> DiagnosticResult: ...
