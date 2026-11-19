"""Base abstractions for Read-Only Tools in QNU AI Platform (Trụ cột 4).

All tools must be strictly read-only, scope-locked by (workspace_id, collection_ids),
and audited with runtime execution traces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    type: str  # "string", "integer", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any | None = None


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_name: str
    success: bool
    data: Any | None = None
    execution_ms: float = Field(ge=0.0)
    error: str | None = None
    items_count: int | None = None


class ReadOnlyTool(ABC):
    """Abstract base class for all read-only tools."""

    name: str
    description: str
    parameters: list[ToolParameter]

    @abstractmethod
    async def execute(
        self,
        db: Any,
        actor: Any,
        workspace_id: str,
        collection_ids: list[str],
        params: dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute the read-only tool within authorized workspace and collections."""
        raise NotImplementedError

    def schema(self) -> dict[str, Any]:
        """Return the JSON schema representation of the tool for LLM function calling."""
        properties = {}
        required = []
        for p in self.parameters:
            properties[p.name] = {
                "type": p.type,
                "description": p.description,
            }
            if p.default is not None:
                properties[p.name]["default"] = p.default
            if p.required:
                required.append(p.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
