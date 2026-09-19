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
    source_port: str | None = Field(None, description="Cổng nguồn (ví dụ: grounded, ungrounded, response)")
    target_port: str | None = Field(None, description="Cổng đích (ví dụ: message, question, reason)")
    condition: str | None = None
    label: str | None = None


class WorkflowDagSpec(BaseModel):
    execution_mode: str = "conversational"
    entry_node_id: str = Field(..., description="Node bắt đầu thực thi của DAG")
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    policies: dict[str, Any] = Field(default_factory=dict)
    nodes: list[WorkflowNodeSpec] = Field(default_factory=list)
    edges: list[WorkflowEdgeSpec] = Field(default_factory=list)


class WorkflowExecuteRequest(BaseModel):
    workflow_id: str = Field(..., description="Mã workflow hoặc tên tệp định nghĩa")
    workflow_version_id: str | None = Field(
        None, description="Mã phiên bản bất biến cụ thể cần thực thi"
    )
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
    paused_node_id: str | None = None


class WorkflowValidationIssue(BaseModel):
    """One actionable finding returned by the workflow compiler."""

    code: str
    message: str
    severity: str = "error"
    node_id: str | None = None
    edge_index: int | None = None


class WorkflowValidationReport(BaseModel):
    """Publication gate result for a normalized DAG specification."""

    is_valid: bool
    issues: list[WorkflowValidationIssue] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


class WorkflowDraftSaveRequest(BaseModel):
    """Optimistic-concurrency request for a mutable workflow working copy."""

    dag_spec: WorkflowDagSpec
    expected_revision: int | None = Field(default=None, ge=1)
    updated_by: str | None = Field(default=None, max_length=128)


class WorkflowDraftResponse(BaseModel):
    workflow_id: str
    dag_spec: WorkflowDagSpec
    revision: int
    updated_by: str | None = None
    created_at: str
    updated_at: str


class WorkflowPublishRequest(BaseModel):
    """Publishes the current draft after compiler validation succeeds."""

    expected_revision: int | None = Field(default=None, ge=1)
    published_by: str | None = Field(default=None, max_length=128)


class WorkflowVersionResponse(BaseModel):
    id: str
    workflow_id: str
    version_number: int
    content_hash: str
    dag_spec: WorkflowDagSpec
    validation_report: WorkflowValidationReport
    published_by: str | None = None
    published_at: str


class WorkflowRollbackRequest(BaseModel):
    """Creates a new published version from a prior immutable snapshot."""

    published_by: str | None = Field(default=None, max_length=128)


class WorkflowApprovalDecisionRequest(BaseModel):
    """Human approval decision used to resume or reject a paused run."""

    approved: bool
    decided_by: str = Field(..., min_length=1, max_length=128)
    decision_reason: str | None = Field(default=None, max_length=1000)


class WorkflowApprovalResponse(BaseModel):
    id: str
    execution_id: str
    checkpoint_id: str
    node_id: str
    tool_name: str | None = None
    payload_hash: str | None = None
    requested_by: str | None = None
    expires_at: str | None = None
    description: str | None = None
    status: str
    decided_by: str | None = None
    decision_reason: str | None = None
    created_at: str
    decided_at: str | None = None


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
    published_version_id: str | None = None
    ownership: str = "shared"
    assistant_id: str | None = None

    model_config = {"from_attributes": True}


class WorkflowAssistantItem(BaseModel):
    id: str
    code: str
    name: str
    is_active: bool
    workflow_ownership: str


class WorkflowAssistantsUsageResponse(BaseModel):
    workflow_id: str
    ownership: str
    total_assistants: int
    assistants: list[WorkflowAssistantItem] = Field(default_factory=list)
