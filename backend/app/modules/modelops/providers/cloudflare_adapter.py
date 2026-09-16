"""Cloudflare Workers AI Provider Adapter for Edge-accelerated LLMs (@cf/meta/llama-3.3-70b-instruct, @cf/deepseek-ai/deepseek-r1-distill-qwen-32b)."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.schemas import ChatMessage


class CloudflareAdapter(BaseLLMAdapter):
    """Adapter for Cloudflare Workers AI Edge Inference Engine."""

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 20,
        account_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
        self.account_id = account_id or ""

    @property
    def provider_type(self) -> str:
        return "cloudflare"

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.perf_counter()

        # Safe offline mock mode when token or account_id is not set or mock
        if (
            not self.api_key
            or self.api_key in ("mock", "test", "demo", "placeholder")
            or not self.account_id
            or self.account_id in ("mock", "test", "demo", "placeholder")
        ):
            user_msg = messages[-1].content if messages else ""
            mock_text = (
                f"[Cloudflare Workers AI ({self.model_name})] Phản hồi từ mạng lưới Edge toàn cầu của Cloudflare:\n"
                f"Yêu cầu về Trường ĐH Quy Nhơn đã được giải quyết: '{user_msg[:100]}'."
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

        # Build endpoint with account_id
        raw_base = self.base_url or "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run"
        formatted_base = raw_base.replace("{account_id}", self.account_id)

        # Decide whether using REST AI Run (/ai/run/{model}) or OpenAI compat (/ai/v1/chat/completions)
        if "/ai/v1" in formatted_base:
            endpoint = f"{formatted_base.rstrip('/')}/chat/completions"
            payload = {
                "model": self.model_name,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        else:
            # REST run format: /accounts/{account_id}/ai/run/{model_name}
            endpoint = f"{formatted_base.rstrip('/')}/{self.model_name.lstrip('/')}"
            payload = {
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "max_tokens": max_tokens,
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # Parse response flexibly: REST format or OpenAI format
        content = ""
        prompt_tokens = sum(len(m.content.split()) for m in messages) * 2
        completion_tokens = 0

        if "result" in data and isinstance(data["result"], dict):
            # Cloudflare REST format: {"result": {"response": "..."}}
            content = data["result"].get("response", "")
        elif "choices" in data and isinstance(data["choices"], list):
            # OpenAI compatible format: {"choices": [{"message": {"content": "..."}}]}
            content = data["choices"][0].get("message", {}).get("content", "")
            if "usage" in data:
                prompt_tokens = data["usage"].get("prompt_tokens", prompt_tokens)
                completion_tokens = data["usage"].get("completion_tokens", 0)

        if not completion_tokens:
            completion_tokens = len(content.split()) * 2

        elapsed = (time.perf_counter() - start_time) * 1000

        return LLMResponse(
            content=content,
            provider=self.provider_type,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=round(elapsed, 2),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        response = await self.generate(messages, temperature=temperature, max_tokens=max_tokens)
        words = response.content.split(" ")
        for word in words:
            yield word + " "
