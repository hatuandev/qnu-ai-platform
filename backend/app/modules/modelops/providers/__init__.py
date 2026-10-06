"""LLM Provider Adapters Factory."""

from __future__ import annotations

from typing import Any

from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.providers.cloudflare_adapter import CloudflareAdapter
from app.modules.modelops.providers.gemini_adapter import GeminiAdapter
from app.modules.modelops.providers.mistral_adapter import MistralAdapter
from app.modules.modelops.providers.openai_adapter import OpenAIAdapter

__all__ = [
    "BaseLLMAdapter",
    "CloudflareAdapter",
    "GeminiAdapter",
    "LLMResponse",
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

    if pt in ("deepseek", "groq", "openrouter", "nvidia", "claude", "ollama_cloud", "ollama", "custom"):
        # OpenAI compatible endpoints
        from app.core.config import resolve_ollama_network_url, settings

        raw_ollama_url = getattr(settings, "OLLAMA_BASE_URL", "") or "http://tormemrtxproto.tail0924dd.ts.net:11434"
        ollama_default = resolve_ollama_network_url(raw_ollama_url).rstrip("/")
        if not ollama_default.endswith("/v1"):
            ollama_default = f"{ollama_default}/v1"

        default_urls = {
            "deepseek": "https://api.deepseek.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "nvidia": "https://integrate.api.nvidia.com/v1",
            "ollama_cloud": "https://ollama.com/v1",
            "ollama": ollama_default,
        }
        effective_base = base_url or default_urls.get(pt)
        if pt in ("ollama", "custom") and effective_base:
            effective_base = resolve_ollama_network_url(effective_base)
        if effective_base and not effective_base.endswith("/v1") and not effective_base.endswith("/v1/"):
            effective_base = f"{effective_base.rstrip('/')}/v1"

        return OpenAIAdapter(
            model_name=model_name,
            api_key=api_key or ("ollama" if pt in ("ollama", "custom") else None),
            base_url=effective_base,
            timeout_seconds=timeout_seconds,
            provider_type=pt,
        )

    raise ValueError(f"Unsupported LLM provider type: '{provider_type}'")
