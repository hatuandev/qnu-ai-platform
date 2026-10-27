"""OCR engine port: one page image in, one structured provider answer out.

The request carries everything the transport needs (endpoint, credential, model,
timeout) so an adapter holds no per-provider state and the domain stays free of HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from qnu.platform.errors import AppException


@dataclass(frozen=True, slots=True)
class OcrRequest:
    endpoint: str
    model: str
    prompt: str
    max_tokens: int
    timeout_seconds: float
    api_key: str | None = field(default=None, repr=False)
    auth_optional: bool = False


@dataclass(frozen=True, slots=True)
class OcrPageResponse:
    text: str
    raw: dict[str, Any]
    usage_tokens: int | None
    duration_ms: int
    raw_body: bytes | None = field(default=None, repr=False)


class OcrResponseError(AppException):
    """A provider replied, but the answer failed validation; retain original bytes."""

    def __init__(self, error: AppException, raw_body: bytes, usage_tokens: int | None):
        super().__init__(
            error.detail, code=error.code, status_code=error.status_code, title=error.title
        )
        self.raw_body = raw_body
        self.usage_tokens = usage_tokens


@runtime_checkable
class OcrEngine(Protocol):
    name: str

    async def extract_page(self, image_png: bytes, request: OcrRequest) -> OcrPageResponse: ...


__all__ = ["OcrEngine", "OcrPageResponse", "OcrRequest", "OcrResponseError"]
