"""Abstract Base Class for LLM Provider Adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.modules.modelops.schemas import ChatMessage


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float = 0.0


class BaseLLMAdapter(ABC):
    """Strategy interface for LLM providers (OpenAI, Gemini, Local vLLM/Ollama)."""

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 15,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Identifier for the provider: openai, gemini, local_vllm."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        """Generate full completion response from LLM."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream token chunks asynchronously."""
        ...
