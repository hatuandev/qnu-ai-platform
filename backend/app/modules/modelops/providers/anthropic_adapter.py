"""Native Anthropic Messages protocol; gateways use the custom OpenAI adapter."""

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.exceptions import AppException
from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.schemas import ChatMessage


class AnthropicAdapter(BaseLLMAdapter):
    @property
    def provider_type(self) -> str:
        return "claude"

    def headers(self) -> dict[str, str]:
        if not self.api_key:
            raise AppException(
                "Thiếu khóa Anthropic.", code="provider_key_missing", status_code=401
            )
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        start = time.perf_counter()
        payload = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages if m.role != "system"
            ],
        }
        system = "\n".join(m.content for m in messages if m.role == "system")
        if system:
            payload["system"] = system
        endpoint = f"{(self.base_url or 'https://api.anthropic.com/v1').rstrip('/')}/messages"
        async with httpx.AsyncClient(timeout=self.timeout_seconds, trust_env=False) as client:
            response = await client.post(endpoint, json=payload, headers=self.headers())
            response.raise_for_status()
            data = response.json()
            if kwargs.get("probe") and data.get("stop_reason") == "max_tokens" and max_tokens < 256:
                payload["max_tokens"] = 256
                response = await client.post(endpoint, json=payload, headers=self.headers())
                response.raise_for_status()
                data = response.json()
        content = "".join(
            part.get("text", "") for part in data.get("content", []) if part.get("type") == "text"
        )
        if not content.strip() or data.get("error"):
            raise AppException(
                "Anthropic không trả nội dung trả lời hợp lệ.",
                code="MODEL_RESPONSE_PROTOCOL_ERROR",
                status_code=502,
            )
        usage = data.get("usage", {})
        prompt = (
            usage.get("input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
        )
        completion = usage.get("output_tokens", 0)
        return LLMResponse(
            content,
            self.provider_type,
            data.get("model") or self.model_name,
            prompt,
            completion,
            prompt + completion,
            round((time.perf_counter() - start) * 1000, 2),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        # Buffered transport, like Gemini/Mistral; no claim of native token streaming.
        response = await self.generate(messages, temperature, max_tokens, **kwargs)
        yield response.content
