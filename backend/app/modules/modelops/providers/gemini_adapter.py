"""Google Gemini Provider Adapter for Gemini 1.5 Flash / Pro."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import httpx

from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.schemas import ChatMessage


class GeminiAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini API."""

    @property
    def provider_type(self) -> str:
        return "gemini"

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        start_time = time.perf_counter()

        # Safe offline mock mode when API key is not configured or dummy
        if not self.api_key or self.api_key in ("mock", "test", "demo"):
            user_msg = messages[-1].content if messages else ""
            mock_text = (
                f"[Gemini {self.model_name}] Thông tin phản hồi từ ĐH Quy Nhơn (Dự phòng):\n"
                f"Đã tiếp nhận yêu cầu: '{user_msg[:100]}'."
            )
            elapsed = (time.perf_counter() - start_time) * 1000
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

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
            f"?key={self.api_key}"
        )

        contents = []
        for m in messages:
            role = "user" if m.role in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)
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
