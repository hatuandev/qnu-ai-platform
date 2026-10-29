"""Small synthetic diagnostic calls; credentials and response bodies stay private."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

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


class ProviderDiagnosticClient(Protocol):
    async def check(self, kind: DiagnosticKind, target: DiagnosticTarget) -> DiagnosticResult: ...
