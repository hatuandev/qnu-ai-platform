"""LLM Provider Adapters Factory."""

from __future__ import annotations

from typing import Any

from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.providers.cloudflare_adapter import CloudflareAdapter
from app.modules.modelops.providers.gemini_adapter import GeminiAdapter
from app.modules.modelops.providers.local_vllm_adapter import LocalVLLMAdapter
from app.modules.modelops.providers.mistral_adapter import MistralAdapter
from app.modules.modelops.providers.openai_adapter import OpenAIAdapter

__all__ = [
    "BaseLLMAdapter",
    "CloudflareAdapter",
    "GeminiAdapter",
    "LLMResponse",
    "LocalVLLMAdapter",
    "MistralAdapter",
    "OpenAIAdapter",
    "get_llm_adapter",
]


def get_llm_adapter(
    provider_type: str,
    model_name: str,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_seconds: int = 15,
    account_id: str | None = None,
    **kwargs: Any,
) -> BaseLLMAdapter:
    """Factory method for creating LLM provider adapters."""
    pt = provider_type.lower().strip()

    if pt == "openai":
        return OpenAIAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1",
            timeout_seconds=timeout_seconds,
        )

    if pt == "gemini":
        return GeminiAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://generativelanguage.googleapis.com/v1beta",
            timeout_seconds=timeout_seconds,
        )

    if pt == "mistral":
        return MistralAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.mistral.ai/v1",
            timeout_seconds=timeout_seconds,
        )

    if pt == "cloudflare":
        return CloudflareAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run",
            timeout_seconds=timeout_seconds,
            account_id=account_id,
        )

    if pt in ("deepseek", "groq", "openrouter", "nvidia", "claude", "custom"):
        # OpenAI compatible endpoints
        default_urls = {
            "deepseek": "https://api.deepseek.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "nvidia": "https://integrate.api.nvidia.com/v1",
        }
        return OpenAIAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or default_urls.get(pt),
            timeout_seconds=timeout_seconds,
        )

    if pt in ("local_vllm", "local", "ollama", "vllm"):
        return LocalVLLMAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "http://localhost:8000/v1",
            timeout_seconds=timeout_seconds,
        )

    # Default fallback to Local / vLLM
    return LocalVLLMAdapter(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )
