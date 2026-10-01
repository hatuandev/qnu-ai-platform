"""Mistral AI Provider Adapter for Mistral Large, Mistral Small, Codestral, Pixtral."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.schemas import ChatMessage


class MistralAdapter(BaseLLMAdapter):
    """Adapter for Mistral AI Platform."""

    @property
    def provider_type(self) -> str:
        return "mistral"

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        start_time = time.perf_counter()
        base_url = self.base_url or "https://api.mistral.ai/v1"
        endpoint = f"{base_url.rstrip('/')}/chat/completions"

        # Check API key configuration: Fail loud if not configured so Failover Cascade takes over
        if not self.api_key:
            raise AppException(
                f"Chưa cấu hình API Key cho nhà cung cấp '{self.provider_type}' (mô hình: {self.model_name}).",
                code="provider_key_missing",
                status_code=401,
            )

        # Isolated test mock mode strictly for unit test environments
        if settings.ENVIRONMENT in ("test", "testing") and self.api_key in ("mock", "test"):
            elapsed = (time.perf_counter() - start_time) * 1000
            mock_text = f"[Mistral AI {self.model_name}] Phản hồi thử nghiệm."
            prompt_toks = sum(len(m.content.split()) for m in messages) * 2
            comp_toks = len(mock_text.split()) * 2
            return LLMResponse(
                content=mock_text,
                provider=self.provider_type,
                model=self.model_name,
                prompt_tokens=prompt_toks,
                completion_tokens=comp_toks,
                total_tokens=prompt_toks + comp_toks,
                latency_ms=round(elapsed, 2),
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

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
