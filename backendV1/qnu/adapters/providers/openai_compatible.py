"""One OpenAI-compatible chat request; no implicit retry, redirect or fallback."""

from __future__ import annotations

import time

import httpx

from qnu.adapters.providers.failures import tag_failure
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.platform.logging import get_logger
from qnu.platform.network_policy import assert_allowed_endpoint
from qnu.ports.chat_model import ChatMessage, ChatRequest, ChatResponseError, ChatResult

logger = get_logger(__name__)


def completions_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    return cleaned + ("/chat/completions" if cleaned.endswith(("/v1", "/openai")) else "/v1/chat/completions")


def build_payload(messages: list[ChatMessage], request: ChatRequest) -> dict:
    """Request body from the pinned contract; reasoning only when explicitly declared.

    The adapter never adds a provider-specific reasoning parameter on its own: a
    ``server_default`` target keeps exactly the previous body.
    """
    payload = {
        "model": request.model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "max_tokens": request.max_output_tokens,
        "stream": False,
    }
    if request.output_schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "qnu_output",
                "schema": request.output_schema,
                "strict": True,
            },
        }
    elif request.json_mode:
        payload["response_format"] = {"type": "json_object"}
    if request.reasoning is not None:
        request.reasoning.apply(payload)
    return payload


def _error(code: str, detail: str, status: int = 502) -> AppException:
    return AppException(detail, code=code, status_code=status, title="Provider chat lỗi")


def _tokens(usage: object, field: str) -> int | None:
    value = usage.get(field) if isinstance(usage, dict) else None
    return value if type(value) is int and value >= 0 else None


def _decode(response: httpx.Response, request: ChatRequest) -> ChatResult:
    status = response.status_code
    if status in (401, 403):
        raise _error("chat_provider_auth_failed", "Provider từ chối credential.")
    if status == 429:
        raise _error("chat_provider_rate_limited", "Provider giới hạn tần suất.", 503)
    if status >= 500:
        raise _error("chat_provider_unavailable", "Provider chat không sẵn sàng.", 503)
    if status != 200:
        raise _error("chat_provider_rejected", "Provider từ chối yêu cầu chat.")
    try:
        data = response.json()
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish = choice.get("finish_reason")
        usage = data.get("usage")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise _error("chat_response_invalid", "Phản hồi chat không đúng cấu trúc.") from exc
    if finish == "length":
        raise _error("chat_output_truncated", "Đầu ra chat bị cắt; chưa có bản nháp đầy đủ.", 422)
    if finish != "stop":
        raise _error("chat_response_incomplete", "Provider chưa kết thúc câu trả lời hợp lệ.")
    if not isinstance(content, str) or not content.strip():
        raise _error("chat_response_empty", "Provider trả về nội dung rỗng.")
    return ChatResult(
        content=content,
        provider="openai-compatible",
        model=request.model,
        prompt_tokens=_tokens(usage, "prompt_tokens"),
        completion_tokens=_tokens(usage, "completion_tokens"),
        total_tokens=_tokens(usage, "total_tokens"),
        finish_reason=finish,
        raw_body=response.content,
    )


class OpenAICompatibleChatModel:
    name = "openai-compatible"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def complete(self, messages: list[ChatMessage], request: ChatRequest) -> ChatResult:
        url = completions_url(request.endpoint)
        assert_allowed_endpoint(url, allow_private=not get_settings().is_production)
        if not request.api_key:
            raise _error("chat_credentials_missing", "Chưa có credential chat.", 503)
        if not messages or any(m.role not in {"system", "user", "assistant"} for m in messages):
            raise _error("chat_messages_invalid", "Messages không hợp lệ.", 422)
        payload = build_payload(messages, request)
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=(
                    httpx.Timeout(request.timeout_seconds, read=None)
                    if request.wait_for_completion else request.timeout_seconds
                ),
                follow_redirects=False,
                transport=self._transport,
                trust_env=False,
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json",
                    },
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
            raise _error("chat_provider_unreachable", "Không kết nối được provider chat.") from exc
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise _error(
                "chat_provider_uncertain",
                "Chưa xác định kết quả gọi provider; không tự gọi lại.",
                504,
            ) from exc
        try:
            result = _decode(response, request)
        except AppException as exc:
            try:
                usage = _tokens(response.json().get("usage"), "total_tokens")
            except (ValueError, AttributeError):
                usage = None
            raise ChatResponseError(tag_failure(exc, response), response.content, usage) from exc
        logger.info(
            "chat_request_finished",
            model=request.model,
            status=response.status_code,
            duration_ms=int((time.monotonic() - started) * 1000),
            total_tokens=result.total_tokens,
            reasoning_mode=request.reasoning.mode if request.reasoning is not None else "server_default",
        )
        return result
