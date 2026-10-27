"""Nemotron Parse over an OpenAI-compatible chat-completions endpoint.

This adapter is the only place that knows HTTP. It normalises the endpoint, applies
the egress policy, attaches the decrypted credential and maps every transport outcome
to one stable domain code, so callers never guess what happened.

One page, one request. There is no fallback engine, no automatic resend and no retry
here: a retry decision belongs to the run, which knows whether the page already
completed.
"""

from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.platform.logging import get_logger
from qnu.platform.network_policy import assert_allowed_endpoint
from qnu.ports.ocr_engine import OcrPageResponse, OcrRequest, OcrResponseError

logger = get_logger(__name__)

CHAT_COMPLETIONS_SUFFIX = "/v1/chat/completions"


def _error(detail: str, code: str, status: int) -> AppException:
    return AppException(detail, code=code, status_code=status, title="Provider OCR lỗi")


def completions_url(base_url: str) -> str:
    """Normalise a configured base URL to the chat-completions endpoint."""
    cleaned = (base_url or "").strip().rstrip("/")
    if cleaned.endswith(CHAT_COMPLETIONS_SUFFIX):
        return cleaned
    if cleaned.endswith("/v1"):
        return cleaned + "/chat/completions"
    return cleaned + CHAT_COMPLETIONS_SUFFIX


def build_payload(request: OcrRequest, image_png: bytes) -> dict[str, Any]:
    encoded = base64.b64encode(image_png).decode("ascii")
    return {
        "model": request.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": request.prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    },
                ],
            }
        ],
        "max_tokens": request.max_tokens,
        "temperature": 0,
        "repetition_penalty": 1.1,
        "top_k": 1,
        "skip_special_tokens": False,
    }


def _extract_text(data: Any) -> tuple[str, str]:
    """Return (text, finish_reason); a malformed body is never treated as empty output."""
    if not isinstance(data, dict):
        raise _error("Phản hồi OCR không phải JSON object.", "ocr_response_invalid", 502)
    try:
        choice = data["choices"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise _error("Phản hồi OCR thiếu choices.", "ocr_response_invalid", 502) from exc
    if not isinstance(choice, dict):
        raise _error("Phần tử choices không hợp lệ.", "ocr_response_invalid", 502)
    message = choice.get("message")
    if not isinstance(message, dict):
        raise _error("Phản hồi OCR thiếu message.", "ocr_response_invalid", 502)
    text = message.get("content")
    if not isinstance(text, str):
        raise _error("Phản hồi OCR thiếu nội dung văn bản.", "ocr_response_invalid", 502)
    return text, str(choice.get("finish_reason") or "")


def _usage_tokens(data: dict[str, Any]) -> int | None:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    total = usage.get("total_tokens")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        return None
    return total


def _decode_response(response: httpx.Response) -> tuple[str, dict[str, Any]]:
    status = response.status_code
    if status in (401, 403):
        raise _error("Provider OCR từ chối credential.", "ocr_provider_auth_failed", 502)
    if status == 429:
        raise _error("Provider OCR giới hạn tần suất.", "ocr_provider_rate_limited", 503)
    if status >= 500:
        raise _error(f"Provider OCR lỗi HTTP {status}.", "ocr_provider_unavailable", 503)
    if status != 200:
        raise _error(f"Provider OCR từ chối yêu cầu (HTTP {status}).", "ocr_provider_rejected", 502)

    try:
        data = response.json()
    except ValueError as exc:
        raise _error("Phản hồi OCR không phải JSON.", "ocr_response_invalid", 502) from exc

    text, finish_reason = _extract_text(data)
    if finish_reason == "length":
        raise _error(
            "Đầu ra OCR bị cắt; chưa đủ bằng chứng cho toàn trang.",
            "ocr_output_truncated",
            422,
        )
    if finish_reason not in ("stop", ""):
        raise _error(
            f"Provider OCR kết thúc bất thường ({finish_reason}).",
            "ocr_response_incomplete",
            502,
        )
    if not text.strip():
        raise _error("Provider OCR trả về trang không có nội dung.", "ocr_response_empty", 502)

    return text, data


class NemotronOcrEngine:
    """Single-provider engine; ``name`` is recorded in the canonical document."""

    name = "nemotron"

    async def extract_page(self, image_png: bytes, request: OcrRequest) -> OcrPageResponse:
        if not image_png:
            raise _error("Ảnh trang rỗng.", "ocr_input_empty", 422)
        try:
            url = completions_url(request.endpoint)
            assert_allowed_endpoint(url, allow_private=not get_settings().is_production)
        except AppException as exc:
            raise _error(
                "Endpoint OCR bị chặn bởi chính sách mạng.",
                "ocr_provider_endpoint_blocked",
                503,
            ) from exc

        headers = {"Content-Type": "application/json"}
        if request.api_key:
            headers["Authorization"] = f"Bearer {request.api_key}"
        elif not request.auth_optional:
            raise _error("Thiếu credential OCR.", "ocr_credentials_missing", 503)

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(request.timeout_seconds), follow_redirects=False
            ) as client:
                response = await client.post(
                    url, json=build_payload(request, image_png), headers=headers
                )
        except httpx.TimeoutException as exc:
            raise _error(
                "Provider OCR không phản hồi trong thời gian cho phép.",
                "ocr_provider_timeout",
                504,
            ) from exc
        except httpx.RequestError as exc:
            raise _error(
                "Không kết nối được provider OCR.", "ocr_provider_unreachable", 502
            ) from exc

        duration_ms = int((time.monotonic() - started) * 1000)
        status = response.status_code
        try:
            text, data = _decode_response(response)
        except AppException as exc:
            try:
                usage = _usage_tokens(response.json())
            except (ValueError, AttributeError):
                usage = None
            raise OcrResponseError(exc, response.content, usage) from exc

        logger.info(
            "ocr_page_called",
            model=request.model,
            status=status,
            duration_ms=duration_ms,
            image_bytes=len(image_png),
        )
        return OcrPageResponse(
            text=text,
            raw=data if isinstance(data, dict) else {},
            usage_tokens=_usage_tokens(data),
            duration_ms=duration_ms,
            raw_body=response.content,
        )
