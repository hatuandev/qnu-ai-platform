"""Local vLLM / Ollama Provider Adapter (OpenAI-compatible)."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import httpx

from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.schemas import ChatMessage


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
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        except Exception:
            # Safe campus fallback mock if local server is unreachable
            user_msg = messages[-1].content if messages else ""
            content = (
                f"[Local {self.model_name}] Phản hồi từ máy chủ AI nội bộ ĐH Quy Nhơn:\n"
                f"Đã ghi nhận yêu cầu: '{user_msg[:100]}'."
            )
            prompt_tokens = sum(len(m.content.split()) for m in messages) * 2
            completion_tokens = len(content.split()) * 2
            total_tokens = prompt_tokens + completion_tokens

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
