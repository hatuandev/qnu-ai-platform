"""Cloudflare Workers AI Provider Adapter for Edge-accelerated LLMs (@cf/meta/llama-3.3-70b-instruct, @cf/deepseek-ai/deepseek-r1-distill-qwen-32b)."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.exceptions import AppException
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

        # Missing credentials must reach ModelOps fallback, never fabricate success.
        if not self.api_key or not self.account_id:
            raise AppException(
                "Cloudflare chưa có khóa API và Account ID hợp lệ.",
                code="provider_key_missing",
                status_code=401,
            )

        # Build endpoint with account_id
        raw_base = (
            self.base_url or "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run"
        )
        formatted_base = raw_base.replace("{account_id}", self.account_id)

        # Decide whether using REST AI Run (/ai/run/{model}) or OpenAI compat (/ai/v1/chat/completions)
        if "/ai/v1" in formatted_base:
            endpoint = f"{formatted_base.rstrip('/')}/chat/completions"
            payload = {
                "model": self.model_name,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
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

        async with httpx.AsyncClient(timeout=self.timeout_seconds, trust_env=False) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        if data.get("success") is False or data.get("errors") or data.get("error"):
            raise AppException(
                "Cloudflare trả lỗi trong phản hồi.",
                code="MODEL_RESPONSE_PROTOCOL_ERROR",
                status_code=502,
            )

        # Parse response flexibly: REST format or OpenAI format
        content = ""
        prompt_tokens = 0
        completion_tokens = 0

        if "result" in data and isinstance(data["result"], dict):
            # Cloudflare REST format: {"result": {"response": "..."}} or {"result": {"response": {"text": "..."}}}
            raw_resp = data["result"].get("response", "")
            if isinstance(raw_resp, dict):
                content = str(raw_resp.get("text") or raw_resp.get("content") or "")
            else:
                content = str(raw_resp or "")
            usage = data["result"].get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
        elif "choices" in data and isinstance(data["choices"], list):
            # OpenAI compatible format: {"choices": [{"message": {"content": "..."}}]}
            content = str(data["choices"][0].get("message", {}).get("content", ""))
            if "usage" in data:
                prompt_tokens = data["usage"].get("prompt_tokens", prompt_tokens)
                completion_tokens = data["usage"].get("completion_tokens", 0)

        if not content.strip():
            raise AppException(
                "Cloudflare không trả nội dung trả lời hợp lệ.",
                code="MODEL_RESPONSE_PROTOCOL_ERROR",
                status_code=502,
            )
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
