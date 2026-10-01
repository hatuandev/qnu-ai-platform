"""OpenAI Provider Adapter for GPT-4o, GPT-4o-mini."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.schemas import ChatMessage


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI API."""

    @property
    def provider_type(self) -> str:
        return "openai"

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        start_time = time.perf_counter()
        base_url = self.base_url or "https://api.openai.com/v1"
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
            mock_text = f"[Test Mock {self.provider_type}] Phản hồi thử nghiệm cho {self.model_name}."
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
        if "openrouter" in (self.base_url or "").lower():
            headers["HTTP-Referer"] = "https://qnu.edu.vn"
            headers["X-Title"] = "QNU AI Platform"
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        lower_m = self.model_name.lower()
        if (
            "nemotron" in lower_m
            or "r1" in lower_m
            or "thinking" in lower_m
            or "qwq" in lower_m
            or kwargs.get("enable_thinking")
            or kwargs.get("thinking_budget")
        ):
            payload["chat_template_kwargs"] = {"enable_thinking": True}

        async with httpx.AsyncClient(timeout=self.timeout_seconds, trust_env=False) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        reasoning_content = msg.get("reasoning_content") or ""
        if not content and reasoning_content:
            content = reasoning_content

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
        # Check API key configuration: Fail loud if not configured
        if not self.api_key:
            raise AppException(
                f"Chưa cấu hình API Key cho nhà cung cấp '{self.provider_type}' (mô hình: {self.model_name}).",
                code="provider_key_missing",
                status_code=401,
            )

        # Isolated test mock mode strictly for unit test environments
        if settings.ENVIRONMENT in ("test", "testing") and self.api_key in ("mock", "test"):
            response = await self.generate(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
            for word in response.content.split(" "):
                yield word + " "
            return

        base_url = self.base_url or "https://api.openai.com/v1"
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if "openrouter" in (self.base_url or "").lower():
            headers["HTTP-Referer"] = "https://qnu.edu.vn"
            headers["X-Title"] = "QNU AI Platform"
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        lower_m = self.model_name.lower()
        if (
            "nemotron" in lower_m
            or "r1" in lower_m
            or "thinking" in lower_m
            or "qwq" in lower_m
            or kwargs.get("enable_thinking")
            or kwargs.get("thinking_budget")
        ):
            payload["chat_template_kwargs"] = {"enable_thinking": True}

        try:
            import json
            async with (
                httpx.AsyncClient(timeout=self.timeout_seconds, trust_env=False) as client,
                client.stream("POST", endpoint, json=payload, headers=headers) as resp,
            ):
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk_str = line[5:].strip()
                    if chunk_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(chunk_str)
                        choices = chunk_data.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        token = delta.get("content")
                        if token:
                            yield token
                        else:
                            reasoning = delta.get("reasoning_content")
                            if reasoning:
                                yield reasoning
                    except json.JSONDecodeError:
                        continue
        except Exception:
            # Fallback to standard generate if streaming fails
            response = await self.generate(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
            words = response.content.split(" ")
            for word in words:
                yield word + " "
