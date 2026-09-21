"""Local vLLM / Ollama Provider Adapter (OpenAI-compatible)."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator

import httpx

from app.core.exceptions import AppException
from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.schemas import ChatMessage

logger = logging.getLogger(__name__)


class LocalVLLMAdapter(BaseLLMAdapter):
    """Adapter for self-hosted vLLM or Ollama instances on campus."""

    @property
    def provider_type(self) -> str:
        return "local_vllm"

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        start_time = time.perf_counter()
        base_url = self.base_url or "http://localhost:8000/v1"
        endpoint = f"{base_url.rstrip('/')}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, trust_env=False) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        except Exception as exc:
            logger.warning(
                "Local vLLM server at %s unreachable or returned error: %s",
                endpoint,
                exc,
            )
            raise AppException(
                message=f"Máy chủ AI nội bộ ({self.model_name}) hiện không phản hồi: {exc}",
                code="local_llm_unavailable",
                status_code=502,
                details={"model": self.model_name, "endpoint": endpoint},
            ) from exc

        elapsed = (time.perf_counter() - start_time) * 1000
        return LLMResponse(
            content=content,
            provider=self.provider_type,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(elapsed, 2),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncIterator[str]:
        response = await self.generate(messages, temperature=temperature, max_tokens=max_tokens)
        words = response.content.split(" ")
        for word in words:
            yield word + " "
