"""Reconcile a partially migrated database with the core platform schema.

Revision ID: 20260926_reconcile_core_schema
Revises: 20260922_conversation_feedback
Create Date: 2026-09-26

This revision is intentionally forward-only.  It creates missing core tables,
adds missing indexes, and validates existing tables before accepting them.  It
never drops or rewrites existing production data.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op as alembic_op

# revision identifiers, used by Alembic.
revision: str = "20260926_reconcile_core_schema"
down_revision: str | Sequence[str] | None = "20260922_conversation_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REQUIRED_PLATFORM_TABLES = frozenset(
    {
        "assistant_versions",
        "assistants",
        "conversation_feedbacks",
        "conversation_messages",
        "conversation_threads",
        "evaluation_datasets",
        "evaluation_result_items",
        "evaluation_runs",
        "evaluation_test_cases",
        "job_records",
        "knowledge_chunks",
        "knowledge_collections",
        "knowledge_documents",
        "knowledge_facts",
        "knowledge_gaps",
        "llm_usage_logs",
        "model_provider_configs",
        "ocr_engines",
        "ocr_job_logs",
        "platform_document_types",
        "tenant_quotas",
        "tool_definitions",
        "tool_execution_logs",
        "workflow_approval_requests",
        "workflow_checkpoints",
        "workflow_definitions",
        "workflow_drafts",
        "workflow_executions",
        "workflow_node_executions",
        "workflow_versions",
    }
)


def _type_signature(column_type: sa.types.TypeEngine[Any]) -> tuple[str, int | None, bool | None]:
    """Return the stable parts of a reflected/declared SQL type."""
    affinity = column_type._type_affinity.__name__
    length = getattr(column_type, "length", None)
    timezone = getattr(column_type, "timezone", None)
    return affinity, length, timezone


class _SchemaReconciler:
    """Guard explicit Alembic operations with schema inspection.

    Tables absent from a partially migrated database are created normally.
    Existing tables are preserved, but their columns and indexes must match
    this frozen revision.  Unsafe drift fails loudly instead of being guessed.
    """

    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate

    def f(self, name: str) -> Any:
        return self._delegate.f(name)

    def create_table(self, table_name: str, *schema_items: Any, **kwargs: Any) -> Any:
        bind = self._delegate.get_bind()
        inspector = sa.inspect(bind)
        if not inspector.has_table(table_name):
            return self._delegate.create_table(table_name, *schema_items, **kwargs)

        reflected = {column["name"]: column for column in inspector.get_columns(table_name)}
        expected = {item.name: item for item in schema_items if isinstance(item, sa.Column)}
        missing_columns = sorted(set(expected) - set(reflected))
        if missing_columns:
            raise RuntimeError(
                f"Existing table '{table_name}' is missing required columns: "
                f"{', '.join(missing_columns)}"
            )

        incompatible: list[str] = []
        for column_name, declared in expected.items():
            actual = reflected[column_name]
            if _type_signature(actual["type"]) != _type_signature(declared.type):
                incompatible.append(f"{column_name} type={actual['type']} expected={declared.type}")
            if bool(actual["nullable"]) != bool(declared.nullable):
                incompatible.append(
                    f"{column_name} nullable={actual['nullable']} expected={declared.nullable}"
                )
        if incompatible:
            raise RuntimeError(
                f"Existing table '{table_name}' has incompatible schema: " + "; ".join(incompatible)
            )

        expected_pk: tuple[str, ...] = ()
        for item in schema_items:
            if isinstance(item, sa.PrimaryKeyConstraint):
                expected_pk = tuple(str(name) for name in item._pending_colargs)
                break
        actual_pk = tuple(inspector.get_pk_constraint(table_name).get("constrained_columns") or ())
        if expected_pk and actual_pk != expected_pk:
            raise RuntimeError(
                f"Existing table '{table_name}' has primary key {actual_pk}, expected {expected_pk}"
            )

        actual_foreign_keys = {
            (
                tuple(foreign_key.get("constrained_columns") or ()),
                str(foreign_key.get("referred_table") or ""),
                tuple(foreign_key.get("referred_columns") or ()),
                str((foreign_key.get("options") or {}).get("ondelete") or "").upper(),
            )
            for foreign_key in inspector.get_foreign_keys(table_name)
        }
        for item in schema_items:
            if not isinstance(item, sa.ForeignKeyConstraint):
                continue
            local_columns = tuple(str(name) for name in item._pending_colargs)
            target_specs = [str(element._colspec) for element in item.elements]
            referred_tables = {target.rsplit(".", 1)[0] for target in target_specs}
            if len(referred_tables) != 1:
                raise RuntimeError(
                    f"Foreign key on '{table_name}' references multiple tables: {target_specs}"
                )
            referred_table = referred_tables.pop()
            referred_columns = tuple(target.rsplit(".", 1)[1] for target in target_specs)
            ondelete = str(item.ondelete or "").upper()
            signature = (local_columns, referred_table, referred_columns, ondelete)
            if signature in actual_foreign_keys:
                continue
            constraint_name = f"fk_{table_name}_{'_'.join(local_columns)}_{referred_table}"
            self._delegate.create_foreign_key(
                constraint_name,
                table_name,
                referred_table,
                list(local_columns),
                list(referred_columns),
                ondelete=item.ondelete,
            )
        return None

    def create_index(
        self,
        index_name: str,
        table_name: str,
        columns: Sequence[str],
        *,
        unique: bool = False,
        **kwargs: Any,
    ) -> Any:
        inspector = sa.inspect(self._delegate.get_bind())
        indexes = {
            index["name"]: index for index in inspector.get_indexes(table_name) if index.get("name")
        }
        existing = indexes.get(index_name)
        if existing is None:
            return self._delegate.create_index(
                index_name,
                table_name,
                list(columns),
                unique=unique,
                **kwargs,
            )

        actual_columns = tuple(existing.get("column_names") or ())
        expected_columns = tuple(columns)
        if actual_columns != expected_columns or bool(existing.get("unique")) != unique:
            raise RuntimeError(
                f"Existing index '{index_name}' on '{table_name}' is incompatible: "
                f"columns={actual_columns}, unique={bool(existing.get('unique'))}; "
                f"expected columns={expected_columns}, unique={unique}"
            )
        return None


op = _SchemaReconciler(alembic_op)


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "assistant_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("assistant_id", sa.String(length=36), nullable=False),
        sa.Column("assistant_code", sa.String(length=50), nullable=False),
        sa.Column("version_number", sa.String(length=20), nullable=False),
        sa.Column("change_summary", sa.String(length=255), nullable=False),
        sa.Column("snapshot_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistant_versions_assistant_code"),
        "assistant_versions",
        ["assistant_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assistant_versions_assistant_id"),
        "assistant_versions",
        ["assistant_id"],
        unique=False,
    )
    op.create_table(
        "assistants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("avatar_url", sa.String(length=300), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("workflow_id", sa.String(length=100), nullable=False),
        sa.Column("published_workflow_version_id", sa.String(length=36), nullable=True),
        sa.Column("workflow_ownership", sa.String(length=20), nullable=False),
        sa.Column("collection_id", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assistants_category"), "assistants", ["category"], unique=False)
    op.create_index(op.f("ix_assistants_code"), "assistants", ["code"], unique=True)
    op.create_index(op.f("ix_assistants_is_active"), "assistants", ["is_active"], unique=False)
    op.create_index(op.f("ix_assistants_tenant_id"), "assistants", ["tenant_id"], unique=False)
    op.create_index(
        op.f("ix_assistants_workflow_ownership"), "assistants", ["workflow_ownership"], unique=False
    )
    op.create_table(
        "evaluation_datasets",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("assistant_code", sa.String(length=50), nullable=False),
        sa.Column("total_test_cases", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_datasets_assistant_code"),
        "evaluation_datasets",
        ["assistant_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_datasets_name"), "evaluation_datasets", ["name"], unique=True
    )
    op.create_table(
        "evaluation_result_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("test_case_id", sa.String(length=36), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("generated_answer", sa.Text(), nullable=False),
        sa.Column("contexts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("faithfulness_score", sa.Float(), nullable=False),
        sa.Column("answer_relevance_score", sa.Float(), nullable=False),
        sa.Column("context_precision_score", sa.Float(), nullable=False),
        sa.Column("is_hallucinated", sa.Boolean(), nullable=False),
        sa.Column("is_refusal", sa.Boolean(), nullable=False),
        sa.Column("passed_all_criteria", sa.Boolean(), nullable=False),
        sa.Column("execution_path", sa.String(length=50), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_result_items_run_id"),
        "evaluation_result_items",
        ["run_id"],
        unique=False,
    )
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("assistant_code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("total_cases", sa.Integer(), nullable=False),
        sa.Column("passed_cases", sa.Integer(), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column("faithfulness_avg", sa.Float(), nullable=False),
        sa.Column("answer_relevance_avg", sa.Float(), nullable=False),
        sa.Column("context_precision_avg", sa.Float(), nullable=False),
        sa.Column("meets_tm08_standard", sa.Boolean(), nullable=False),
        sa.Column("evaluation_method", sa.String(length=30), nullable=False),
        sa.Column("metadata_info", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eval_run_assistant_created",
        "evaluation_runs",
        ["assistant_code", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_assistant_code"),
        "evaluation_runs",
        ["assistant_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_created_at"), "evaluation_runs", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_evaluation_runs_dataset_id"), "evaluation_runs", ["dataset_id"], unique=False
    )
    op.create_table(
        "evaluation_test_cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("ground_truth", sa.Text(), nullable=False),
        sa.Column("expected_source", sa.String(length=255), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_test_cases_dataset_id"),
        "evaluation_test_cases",
        ["dataset_id"],
        unique=False,
    )
    op.create_table(
        "job_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=True),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("arq_job_id", sa.String(length=128), nullable=True),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_records_collection_id"), "job_records", ["collection_id"], unique=False
    )
    op.create_index(
        op.f("ix_job_records_document_id"), "job_records", ["document_id"], unique=False
    )
    op.create_index(op.f("ix_job_records_job_type"), "job_records", ["job_type"], unique=False)
    op.create_index(op.f("ix_job_records_status"), "job_records", ["status"], unique=False)
    op.create_table(
        "knowledge_collections",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module_code", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("collection_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_collections_module_code"),
        "knowledge_collections",
        ["module_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_collections_tenant_id"),
        "knowledge_collections",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_collections_workspace_id"),
        "knowledge_collections",
        ["workspace_id"],
        unique=False,
    )
    op.create_table(
        "knowledge_gaps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("assistant_code", sa.String(length=50), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_gap_assistant_status", "knowledge_gaps", ["assistant_code", "status"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_gaps_assistant_code"), "knowledge_gaps", ["assistant_code"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_gaps_collection_id"), "knowledge_gaps", ["collection_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_gaps_created_at"), "knowledge_gaps", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_knowledge_gaps_status"), "knowledge_gaps", ["status"], unique=False)
    op.create_table(
        "llm_usage_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("assistant_id", sa.String(length=100), nullable=True),
        sa.Column("conversation_id", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_llm_usage_logs_assistant_id"), "llm_usage_logs", ["assistant_id"], unique=False
    )
    op.create_index(
        op.f("ix_llm_usage_logs_created_at"), "llm_usage_logs", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_llm_usage_logs_tenant_id"), "llm_usage_logs", ["tenant_id"], unique=False
    )
    op.create_table(
        "model_provider_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("api_base_url", sa.String(length=500), nullable=True),
        sa.Column("api_key_encrypted", sa.String(length=500), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("extra_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_provider_configs_is_active"),
        "model_provider_configs",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_provider_configs_priority"),
        "model_provider_configs",
        ["priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_provider_configs_provider_type"),
        "model_provider_configs",
        ["provider_type"],
        unique=False,
    )
    op.create_table(
        "ocr_engines",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("engine_type", sa.String(length=50), nullable=False),
        sa.Column("provider_category", sa.String(length=30), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("avg_confidence", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ocr_engines_is_active"), "ocr_engines", ["is_active"], unique=False)
    op.create_index(op.f("ix_ocr_engines_name"), "ocr_engines", ["name"], unique=True)
    op.create_table(
        "ocr_job_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("engine_used", sa.String(length=100), nullable=False),
        sa.Column("total_pages", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ocr_job_logs_created_at"), "ocr_job_logs", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_ocr_job_logs_tenant_id"), "ocr_job_logs", ["tenant_id"], unique=False)
    op.create_index(
        "ix_ocr_job_tenant_engine", "ocr_job_logs", ["tenant_id", "engine_used"], unique=False
    )
    op.create_table(
        "tenant_quotas",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("month_period", sa.String(length=7), nullable=False),
        sa.Column("monthly_token_limit", sa.Integer(), nullable=False),
        sa.Column("monthly_cost_limit_usd", sa.Float(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("cost_used_usd", sa.Float(), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_month_period", "tenant_quotas", ["tenant_id", "month_period"], unique=True
    )
    op.create_index(
        op.f("ix_tenant_quotas_month_period"), "tenant_quotas", ["month_period"], unique=False
    )
    op.create_index(
        op.f("ix_tenant_quotas_tenant_id"), "tenant_quotas", ["tenant_id"], unique=False
    )
    op.create_table(
        "tool_definitions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("openapi_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tool_definitions_category"), "tool_definitions", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_tool_definitions_is_active"), "tool_definitions", ["is_active"], unique=False
    )
    op.create_index(op.f("ix_tool_definitions_name"), "tool_definitions", ["name"], unique=True)
    op.create_table(
        "tool_execution_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("assistant_code", sa.String(length=50), nullable=True),
        sa.Column("conversation_id", sa.String(length=128), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tool_exec_tenant_tool", "tool_execution_logs", ["tenant_id", "tool_name"], unique=False
    )
    op.create_index(
        op.f("ix_tool_execution_logs_created_at"),
        "tool_execution_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tool_execution_logs_tenant_id"), "tool_execution_logs", ["tenant_id"], unique=False
    )
    op.create_index(
        op.f("ix_tool_execution_logs_tool_name"), "tool_execution_logs", ["tool_name"], unique=False
    )
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("module_code", sa.String(length=50), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("workspace_id", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("published_version_id", sa.String(length=36), nullable=True),
        sa.Column("ownership", sa.String(length=20), nullable=False),
        sa.Column("assistant_id", sa.String(length=36), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("dag_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_definitions_assistant_id"),
        "workflow_definitions",
        ["assistant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_definitions_is_active"),
        "workflow_definitions",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_definitions_module_code"),
        "workflow_definitions",
        ["module_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_definitions_ownership"),
        "workflow_definitions",
        ["ownership"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_definitions_tenant_id"),
        "workflow_definitions",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("conversation_id", sa.String(length=128), nullable=True),
        sa.Column("workflow_version_id", sa.String(length=36), nullable=True),
        sa.Column("assistant_id", sa.String(length=36), nullable=True),
        sa.Column("assistant_revision", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("runtime_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("node_execution_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wf_exec_tenant_status", "workflow_executions", ["tenant_id", "status"], unique=False
    )
    op.create_index(
        op.f("ix_workflow_executions_assistant_id"),
        "workflow_executions",
        ["assistant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_executions_conversation_id"),
        "workflow_executions",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_executions_correlation_id"),
        "workflow_executions",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_executions_created_at"),
        "workflow_executions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_executions_status"), "workflow_executions", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_workflow_executions_tenant_id"), "workflow_executions", ["tenant_id"], unique=False
    )
    op.create_index(
        op.f("ix_workflow_executions_workflow_id"),
        "workflow_executions",
        ["workflow_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_executions_workflow_version_id"),
        "workflow_executions",
        ["workflow_version_id"],
        unique=False,
    )
    op.create_table(
        "workflow_node_executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("execution_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=100), nullable=False),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_node_executions_execution_id"),
        "workflow_node_executions",
        ["execution_id"],
        unique=False,
    )
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("document_type_code", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("index_status", sa.String(length=32), nullable=False),
        sa.Column("index_error", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("doc_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["knowledge_collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_type_code"], ["platform_document_types.code"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_documents_collection_id"),
        "knowledge_documents",
        ["collection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_document_type_code"),
        "knowledge_documents",
        ["document_type_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_file_hash"), "knowledge_documents", ["file_hash"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_documents_index_status"),
        "knowledge_documents",
        ["index_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_is_active"), "knowledge_documents", ["is_active"], unique=False
    )
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_hash", sa.String(length=64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("chunk_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chunks_col_doc", "knowledge_chunks", ["collection_id", "document_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_chunks_collection_id"),
        "knowledge_chunks",
        ["collection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_chunks_document_id"), "knowledge_chunks", ["document_id"], unique=False
    )
    op.create_table(
        "knowledge_facts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("entity_name", sa.String(length=512), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("attribute_name", sa.String(length=255), nullable=False),
        sa.Column("attribute_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["knowledge_collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_facts_collection_id"), "knowledge_facts", ["collection_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_facts_document_id"), "knowledge_facts", ["document_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_facts_entity_name"), "knowledge_facts", ["entity_name"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_facts_entity_type"), "knowledge_facts", ["entity_type"], unique=False
    )
    # ### end Alembic commands ###

    actual_tables = set(sa.inspect(alembic_op.get_bind()).get_table_names())
    missing_tables = sorted(REQUIRED_PLATFORM_TABLES - actual_tables)
    if missing_tables:
        raise RuntimeError(
            "Core schema reconciliation did not create required tables: "
            + ", ".join(missing_tables)
        )


def downgrade() -> None:
    """Refuse destructive rollback of a reconciliation revision."""
    raise RuntimeError(
        "20260926_reconcile_core_schema is forward-only; restoring a backup is required."
    )
