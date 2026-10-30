"""Chat completion port."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from qnu.platform.errors import AppException
from qnu.ports.provider_execution import ProviderExecution


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


@runtime_checkable
class ReasoningParameter(Protocol):
    """One declared reasoning parameter; the adapter applies it verbatim."""

    mode: str
    parameter: str

    def apply(self, payload: dict[str, Any]) -> None: ...

    def public_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ChatRequest:
    endpoint: str
    model: str
    max_output_tokens: int
    timeout_seconds: float
    api_key: str = field(repr=False)
    json_mode: bool = True
    output_schema: dict | None = field(default=None, repr=False)
    execution: ProviderExecution | None = field(default=None, repr=False)
    # Declared reasoning parameter only; None keeps the provider/server default.
    reasoning: ReasoningParameter | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class ChatResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    finish_reason: str | None = None
    total_tokens: int | None = None
    raw_body: bytes = field(default=b"", repr=False)


class ChatResponseError(AppException):
    """Keep exact provider bytes even when its response cannot become a draft."""

    def __init__(self, error: AppException, raw_body: bytes, usage_tokens: int | None):
        super().__init__(
            error.detail, code=error.code, status_code=error.status_code, title=error.title
        )
        self.provider_failure = getattr(error, "provider_failure", None)
        self.raw_body = raw_body
        self.usage_tokens = usage_tokens


@runtime_checkable
class ChatModel(Protocol):
    async def complete(self, messages: list[ChatMessage], request: ChatRequest) -> ChatResult: ...
