"""OpenAI-compatible chat transport with explicit JSON/SSE contracts."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.providers.chat_contract import (
    MAX_NEGOTIATIONS,
    adapt_rejected_payload,
    build_chat_payload,
    decode_completion,
    decode_stream_event,
    post_chat,
)
from app.modules.modelops.providers.context_budget import fit_rejected_context
from app.modules.modelops.schemas import ChatMessage


class OpenAIAdapter(BaseLLMAdapter):
    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 15,
        provider_type: str = "openai",
        request_capabilities: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(model_name, api_key, base_url, timeout_seconds)
        self._provider_type_override = provider_type
        self.request_capabilities = dict(request_capabilities or {})
        self.served_model = model_name
        self.stream_usage: dict[str, int] = {}

    @property
    def provider_type(self) -> str:
        return self._provider_type_override

    def _headers(self) -> dict[str, str]:
        effective_key = self.api_key
        if not effective_key and self.provider_type in ("ollama", "local", "vllm", "tei"):
            effective_key = self.provider_type
        if not effective_key:
            raise AppException(
                f"Chưa cấu hình API Key cho provider '{self.provider_type}'.",
                code="provider_key_missing",
                status_code=401,
            )
        headers = {"Authorization": f"Bearer {effective_key}", "Content-Type": "application/json"}
        if self.provider_type == "openrouter":
            headers.update({"HTTP-Referer": "https://qnu.edu.vn", "X-Title": "QNU AI Platform"})
        return headers

    def _payload(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        stream: bool,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = build_chat_payload(
            self.model_name,
            [m.model_dump() for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            capabilities=self.request_capabilities,
        )
        if kwargs.get("enable_thinking") or kwargs.get("thinking_budget"):
            payload["chat_template_kwargs"] = {"enable_thinking": True}
        return payload

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        started = time.perf_counter()
        if settings.ENVIRONMENT in ("test", "testing") and self.api_key in ("mock", "test") and not kwargs.get("probe"):
            return LLMResponse(
                f"[Test Mock {self.provider_type}] Phản hồi thử nghiệm cho {self.model_name}.",
                self.provider_type,
                self.model_name,
                1,
                1,
                2,
            )
        payload = self._payload(messages, temperature, max_tokens, False, **kwargs)
        endpoint = f"{(self.base_url or 'https://api.openai.com/v1').rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=self.timeout_seconds, trust_env=False) as client:
            response = await post_chat(
                client,
                endpoint,
                self._headers(),
                payload,
                self.request_capabilities,
                probe=kwargs.get("probe", False),
            )
            content, usage, served_model = decode_completion(response)
        self.served_model = served_model or self.model_name
        return LLMResponse(
            content=content,
            provider=self.provider_type,
            model=self.served_model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if settings.ENVIRONMENT in ("test", "testing") and self.api_key in ("mock", "test"):
            yield (await self.generate(messages, temperature, max_tokens, **kwargs)).content
            return
        payload = self._payload(messages, temperature, max_tokens, True, **kwargs)
        endpoint = f"{(self.base_url or 'https://api.openai.com/v1').rstrip('/')}/chat/completions"
        self.stream_usage = {}
        context_retried = False
        async with httpx.AsyncClient(timeout=self.timeout_seconds, trust_env=False) as client:
            for attempt in range(MAX_NEGOTIATIONS + 1):
                async with client.stream(
                    "POST", endpoint, headers=self._headers(), json=payload
                ) as response:
                    if response.status_code >= 400:
                        await response.aread()
                        if attempt < MAX_NEGOTIATIONS and adapt_rejected_payload(
                            response, payload, self.request_capabilities
                        ):
                            continue
                        if (attempt < MAX_NEGOTIATIONS and not context_retried
                                and await fit_rejected_context(client, endpoint, self._headers(), payload, response,
                                                               int(self.request_capabilities.get("minimum_output_tokens", 1)))):
                            context_retried = True
                            continue
                        response.raise_for_status()
                    if "text/event-stream" not in response.headers.get("content-type", ""):
                        raise AppException(
                            "Provider không trả SSE cho stream=true.",
                            code="MODEL_RESPONSE_PROTOCOL_ERROR",
                            status_code=502,
                        )
                    has_content = False
                    has_finish = False
                    async for line in response.aiter_lines():
                        event = decode_stream_event(line)
                        if event is None:
                            continue
                        if event.get("done"):
                            has_finish = True
                            break
                        self.served_model = event.get("model") or self.served_model
                        if event.get("usage"):
                            self.stream_usage = event["usage"]
                        choices = event.get("choices", [])
                        if choices:
                            choice = choices[0]
                            if choice.get("finish_reason") == "length":
                                raise AppException(
                                    "Model đã hết ngân sách đầu ra; câu trả lời chưa hoàn tất.",
                                    code="MODEL_OUTPUT_BUDGET_EXHAUSTED", status_code=502,
                                )
                            has_finish = has_finish or choice.get("finish_reason") is not None
                            content = choice.get("delta", {}).get("content")
                            if content:
                                has_content = True
                                yield content
                    if not has_content or not has_finish:
                        raise AppException(
                            "Provider trả SSE rỗng hoặc bị ngắt.",
                            code="MODEL_RESPONSE_PROTOCOL_ERROR",
                            status_code=502,
                        )
                    return
