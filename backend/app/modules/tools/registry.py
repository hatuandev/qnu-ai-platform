"""Tool Registry implementing the Registry Pattern for Function Calling Tools."""

from __future__ import annotations

from typing import Any

from app.modules.tools.builtin.admission_score_tool import AdmissionScoreLookupTool
from app.modules.tools.builtin.base import BaseTool
from app.modules.tools.builtin.document_exporter import DocumentExporterTool
from app.modules.tools.builtin.exam_matrix_tool import ExamMatrixExporterTool


class ToolRegistry:
    """Central registry of executable tools and OpenAPI function schemas."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register the 3 essential QNU built-in tools."""
        self.register(AdmissionScoreLookupTool())
        self.register(DocumentExporterTool())
        self.register(ExamMatrixExporterTool())

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get tool by unique name."""
        return self._tools.get(name)

    def list_all(self, category: str | None = None) -> list[BaseTool]:
        """List all registered tools, optionally filtered by category."""
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def list_schemas(self, category: str | None = None) -> list[dict[str, Any]]:
        """List OpenAPI 3.0 schemas of registered tools for LLM binding."""
        tools = self.list_all(category)
        return [t.get_openapi_schema() for t in tools]


# Global tool registry singleton
tool_registry = ToolRegistry()
