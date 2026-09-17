"""SQLAlchemy Models for Workflow DAG Engine & Executions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class WorkflowDefinition(Base):
    """Declarative DAG Workflow Definition matching qnu.ai/v1alpha1 schema."""

    __tablename__ = "workflow_definitions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    module_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="tenant_qnu", index=True)
    workspace_id: Mapped[str] = mapped_column(String(100), default="workspace_default")
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    published_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    dag_spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WorkflowExecution(Base):
    """Tracks a single execution of a Workflow DAG."""

    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="tenant_qnu", index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    workflow_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    assistant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    assistant_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default="running", index=True
    )  # running, completed, failed, paused_for_approval
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    runtime_profile: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    node_execution_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_wf_exec_tenant_status", "tenant_id", "status"),
    )


class WorkflowNodeExecution(Base):
    """Audit log for each individual node run inside a DAG execution."""

    __tablename__ = "workflow_node_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="completed")
    input_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    output_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkflowDraft(Base):
    """Mutable working copy of a workflow, kept separate from published definitions."""

    __tablename__ = "workflow_drafts"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dag_spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WorkflowVersion(Base):
    """Immutable snapshot created only after a DAG passes publication validation."""

    __tablename__ = "workflow_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dag_spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    validation_report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    published_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workflow_id", "version_number", name="uq_workflow_version_number"),
    )


class WorkflowCheckpoint(Base):
    """Recoverable pause state for approval-gated workflow executions."""

    __tablename__ = "workflow_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resume_node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    completed_node_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    node_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WorkflowApprovalRequest(Base):
    """Human decision bound to a checkpoint; no external action resumes automatically."""

    __tablename__ = "workflow_approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    checkpoint_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
