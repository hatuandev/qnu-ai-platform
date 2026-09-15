"""Base Tool Strategy Interface for Function Calling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract Strategy interface for an executable tool/action in QNU AI Platform."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for function calling: e.g. lookup_admission_score."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human readable title."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Description supplied to LLM for function calling selection."""
        ...

    @property
    def category(self) -> str:
        return "general"

    @property
    def requires_approval(self) -> bool:
        """If True, triggers Human-in-the-loop approval before running."""
        return False

    @abstractmethod
    def get_openapi_schema(self) -> dict[str, Any]:
        """Return OpenAPI 3.0 function declaration schema."""
        ...

    @abstractmethod
    async def execute(
        self, parameters: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute the tool logic and return structured result."""
        ...
