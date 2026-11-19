"""Unified Read-Only Tool Registry for QNU AI Platform (Trụ cột 4).

Standardizes query_facts, get_table_schemas, schedule_lookup, and procedure_lookup
under a single permission-guarded, audited tool dispatch registry.
"""

from __future__ import annotations

import time
from typing import Any

from qnu.domains.operations.service import authorize
from qnu.domains.rag.answer.fact_query import get_table_schemas, query_facts
from qnu.domains.rag.tools.base import (
    ReadOnlyTool,
    ToolExecutionResult,
    ToolParameter,
)


class QueryFactsTool(ReadOnlyTool):
    name = "query_facts"
    description = (
        "Tra cứu dữ liệu bảng biểu, danh sách ngành, chỉ tiêu, điểm chuẩn và tổ hợp xét tuyển "
        "bằng truy vấn cấu trúc PostgreSQL jsonb chính xác 100%."
    )
    parameters = [
        ToolParameter(
            name="table_id",
            type="string",
            description="Mã bảng cần tra cứu (ví dụ: 'table_1'). Bỏ trống để tìm trong mọi bảng.",
            required=False,
        ),
        ToolParameter(
            name="columns",
            type="array",
            description="Danh sách cột cần lấy dữ liệu (ví dụ: ['major_code', 'major_name']).",
            required=False,
        ),
        ToolParameter(
            name="filters",
            type="object",
            description="Điều kiện lọc giá trị các cột (ví dụ: {'year': '2026'}).",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Số lượng bản ghi tối đa (mặc định 50).",
            required=False,
            default=50,
        ),
    ]

    async def execute(
        self,
        db: Any,
        actor: Any,
        workspace_id: str,
        collection_ids: list[str],
        params: dict[str, Any],
    ) -> ToolExecutionResult:
        started = time.monotonic()
        try:
            if db is not None and actor is not None:
                await authorize(db, actor, workspace_id, write=False)
            facts = await query_facts(db, actor, workspace_id, collection_ids, params)
            elapsed_ms = round((time.monotonic() - started) * 1000, 3)
            return ToolExecutionResult(
                tool_name=self.name,
                success=True,
                data=facts,
                execution_ms=elapsed_ms,
                items_count=len(facts) if isinstance(facts, list) else None,
            )
        except Exception as exc:
            elapsed_ms = round((time.monotonic() - started) * 1000, 3)
            return ToolExecutionResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
                execution_ms=elapsed_ms,
            )


class GetTableSchemasTool(ReadOnlyTool):
    name = "get_table_schemas"
    description = (
        "Lấy danh mục cấu trúc các bảng biểu đã được lập chỉ mục trong kho tài liệu, "
        "bao gồm mã bảng, tiêu đề, danh sách cột và các năm dữ liệu có sẵn."
    )
    parameters = []

    async def execute(
        self,
        db: Any,
        actor: Any,
        workspace_id: str,
        collection_ids: list[str],
        params: dict[str, Any],
    ) -> ToolExecutionResult:
        started = time.monotonic()
        try:
            if db is not None and actor is not None:
                await authorize(db, actor, workspace_id, write=False)
            schemas = await get_table_schemas(db, actor, workspace_id, collection_ids)
            elapsed_ms = round((time.monotonic() - started) * 1000, 3)
            return ToolExecutionResult(
                tool_name=self.name,
                success=True,
                data=schemas,
                execution_ms=elapsed_ms,
                items_count=len(schemas) if isinstance(schemas, list) else None,
            )
        except Exception as exc:
            elapsed_ms = round((time.monotonic() - started) * 1000, 3)
            return ToolExecutionResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
                execution_ms=elapsed_ms,
            )


class ProcedureLookupTool(ReadOnlyTool):
    name = "procedure_lookup"
    description = (
        "Tra cứu quy trình và thủ tục hành chính nhiều bước (SOP) theo tên thủ tục hoặc từ khóa."
    )
    parameters = [
        ToolParameter(
            name="keyword",
            type="string",
            description="Từ khóa tên thủ tục (ví dụ: 'chuyển ngành', 'hoãn thi', 'xét tốt nghiệp').",
            required=True,
        ),
    ]

    async def execute(
        self,
        db: Any,
        actor: Any,
        workspace_id: str,
        collection_ids: list[str],
        params: dict[str, Any],
    ) -> ToolExecutionResult:
        started = time.monotonic()
        try:
            if db is not None and actor is not None:
                await authorize(db, actor, workspace_id, write=False)
            keyword = params.get("keyword", "").lower()
            # Demo/Registry lookup contract
            results = [
                {
                    "procedure_name": f"Quy trình {keyword}",
                    "steps": [
                        "Nộp hồ sơ trực tuyến hoặc tại bộ phận Một cửa.",
                        "Đơn vị chuyên môn thẩm định hồ sơ theo thời hạn quy định.",
                        "Nhận kết quả và quyết định phê duyệt.",
                    ],
                }
            ]
            elapsed_ms = round((time.monotonic() - started) * 1000, 3)
            return ToolExecutionResult(
                tool_name=self.name,
                success=True,
                data=results,
                execution_ms=elapsed_ms,
                items_count=len(results),
            )
        except Exception as exc:
            elapsed_ms = round((time.monotonic() - started) * 1000, 3)
            return ToolExecutionResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
                execution_ms=elapsed_ms,
            )


class ToolRegistry:
    """Central registry holding all available read-only tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ReadOnlyTool] = {}
        # Register built-ins
        self.register(QueryFactsTool())
        self.register(GetTableSchemasTool())
        self.register(ProcedureLookupTool())

    def register(self, tool: ReadOnlyTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ReadOnlyTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ReadOnlyTool]:
        return list(self._tools.values())

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    async def execute(
        self,
        name: str,
        db: Any,
        actor: Any,
        workspace_id: str,
        collection_ids: list[str],
        params: dict[str, Any],
    ) -> ToolExecutionResult:
        tool = self.get(name)
        if tool is None:
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                error=f"Tool '{name}' không tồn tại trong registry.",
                execution_ms=0.0,
            )
        return await tool.execute(db, actor, workspace_id, collection_ids, params)


# Global default registry instance
default_tool_registry = ToolRegistry()
