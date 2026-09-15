"""Pydantic Schemas for Workflow DAG Engine — Specifications, Executions & Auditing."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowNodeSpec(BaseModel):
    id: str = Field(..., description="Mã định danh duy nhất của Node")
    type: str = Field(..., description="Loại node: input.chat, core.knowledge.answer, output.chat...")
    version: str = "1.0.0"
    display_name: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdgeSpec(BaseModel):
    source: str = Field(..., description="Node ID nguồn")
    target: str = Field(..., description="Node ID đích")
    condition: str | None = None
    label: str | None = None


class WorkflowDagSpec(BaseModel):
    execution_mode: str = "conversational"
    entry_node_id: str = Field(..., description="Node bắt đầu thực thi của DAG")
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    nodes: list[WorkflowNodeSpec] = Field(default_factory=list)
    edges: list[WorkflowEdgeSpec] = Field(default_factory=list)


class WorkflowExecuteRequest(BaseModel):
    workflow_id: str = Field(..., description="Mã workflow hoặc tên tệp định nghĩa")
    inputs: dict[str, Any] = Field(..., description="Dữ liệu đầu vào (ví dụ: {'message': '...'})")
    tenant_id: str = Field("tenant_qnu", description="Mã người thuê")
    conversation_id: str | None = Field(None, description="Mã phiên hội thoại")


class WorkflowExecuteResponse(BaseModel):
    execution_id: str
    workflow_id: str
    status: str = Field(..., description="Trạng thái: completed, failed, paused_for_approval")
    outputs: dict[str, Any] = Field(default_factory=dict)
    executed_nodes: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    error_message: str | None = None


class WorkflowDefinitionResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str | None = None
    module_code: str
    version: str
    is_active: bool
    nodes_count: int = 0
    edges_count: int = 0

    model_config = {"from_attributes": True}
