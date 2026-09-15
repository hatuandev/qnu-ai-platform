"""LLM Provider Adapters Factory."""

from __future__ import annotations

from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.providers.gemini_adapter import GeminiAdapter
from app.modules.modelops.providers.local_vllm_adapter import LocalVLLMAdapter
from app.modules.modelops.providers.openai_adapter import OpenAIAdapter

__all__ = [
    "BaseLLMAdapter",
    "GeminiAdapter",
    "LLMResponse",
    "LocalVLLMAdapter",
    "OpenAIAdapter",
    "get_llm_adapter",
]


def get_llm_adapter(
    provider_type: str,
    model_name: str,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_seconds: int = 15,
) -> BaseLLMAdapter:
    """Factory method for creating LLM provider adapters."""
    pt = provider_type.lower().strip()
    if pt == "openai":
        return OpenAIAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    if pt == "gemini":
        return GeminiAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    if pt in ("local_vllm", "local", "ollama", "vllm"):
        return LocalVLLMAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

    # Default to Local / vLLM
    return LocalVLLMAdapter(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )
