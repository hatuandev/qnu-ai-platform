"""Harden publishing V2 invariants, jobs outbox and vector generation metadata.

Revision ID: 20261008_publishing_v2_hardening
Revises: 20261007_knowledge_publishing_v2
Create Date: 2026-10-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261008_publishing_v2_hardening"
down_revision: str | Sequence[str] | None = "20261007_knowledge_publishing_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "knowledge_vector_generations",
        sa.Column("provider_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "knowledge_vector_generations",
        sa.Column("qdrant_collection_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "knowledge_vector_generations",
        sa.Column("config_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "knowledge_vector_generations",
        sa.Column(
            "payload_schema_version",
            sa.Integer(),
            nullable=False,
            server_default="2",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE knowledge_vector_generations "
            "SET provider_id = 'legacy_unresolved', "
            "qdrant_collection_name = CASE WHEN lower(collection_id) LIKE 'col_%' "
            "THEN lower(replace(collection_id, '-', '_')) "
            "ELSE 'col_' || lower(replace(collection_id, '-', '_')) END, "
            "config_hash = md5(collection_id || ':' || embedding_model || ':' || embedding_dimension::text) "
            "WHERE provider_id IS NULL"
        )
    )
    op.alter_column("knowledge_vector_generations", "provider_id", nullable=False)
    op.alter_column("knowledge_vector_generations", "qdrant_collection_name", nullable=False)
    op.alter_column("knowledge_vector_generations", "config_hash", nullable=False)
    op.create_index(
        "uq_knowledge_vector_generation_active",
        "knowledge_vector_generations",
        ["collection_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_foreign_key(
        "fk_index_activation_from_revision",
        "knowledge_index_activations",
        "knowledge_index_revisions",
        ["from_index_revision_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_index_activation_to_revision",
        "knowledge_index_activations",
        "knowledge_index_revisions",
        ["to_index_revision_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_knowledge_activation_binding_epoch",
        "knowledge_index_activations",
        ["binding_id", "epoch"],
        unique=True,
    )

    op.create_index(
        "uq_document_revision_idempotency",
        "document_revisions",
        ["document_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.add_column(
        "job_records",
        sa.Column("phase", sa.String(length=64), nullable=False, server_default="queued"),
    )
    op.add_column(
        "job_records",
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("job_records", sa.Column("idempotency_key", sa.String(length=128)))
    op.add_column("job_records", sa.Column("request_hash", sa.String(length=64)))
    op.add_column("job_records", sa.Column("correlation_id", sa.String(length=128)))
    op.add_column("job_records", sa.Column("heartbeat_at", sa.DateTime(timezone=True)))
    op.add_column(
        "job_records",
        sa.Column(
            "cancel_requested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "job_records",
        sa.Column(
            "dispatch_status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "job_records",
        sa.Column(
            "workspace_id",
            sa.String(length=64),
            nullable=False,
            server_default="workspace_qnu",
        ),
    )
    op.create_index("ix_job_records_dispatch_status", "job_records", ["dispatch_status"])
    op.create_index("ix_job_records_correlation_id", "job_records", ["correlation_id"])
    op.create_index("ix_job_records_idempotency_key", "job_records", ["idempotency_key"])
    op.create_index(
        "uq_job_records_tenant_workspace_idempotency",
        "job_records",
        ["tenant_id", "workspace_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_job_records_tenant_workspace_idempotency", table_name="job_records")
    op.drop_index("ix_job_records_idempotency_key", table_name="job_records")
    op.drop_index("ix_job_records_correlation_id", table_name="job_records")
    op.drop_index("ix_job_records_dispatch_status", table_name="job_records")
    op.drop_column("job_records", "workspace_id")
    op.drop_column("job_records", "dispatch_status")
    op.drop_column("job_records", "cancel_requested")
    op.drop_column("job_records", "heartbeat_at")
    op.drop_column("job_records", "correlation_id")
    op.drop_column("job_records", "request_hash")
    op.drop_column("job_records", "idempotency_key")
    op.drop_column("job_records", "attempt")
    op.drop_column("job_records", "phase")

    op.drop_index("uq_document_revision_idempotency", table_name="document_revisions")
    op.drop_index(
        "uq_knowledge_activation_binding_epoch",
        table_name="knowledge_index_activations",
    )
    op.drop_constraint(
        "fk_index_activation_to_revision",
        "knowledge_index_activations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_index_activation_from_revision",
        "knowledge_index_activations",
        type_="foreignkey",
    )
    op.drop_index(
        "uq_knowledge_vector_generation_active",
        table_name="knowledge_vector_generations",
    )
    op.drop_column("knowledge_vector_generations", "payload_schema_version")
    op.drop_column("knowledge_vector_generations", "config_hash")
    op.drop_column("knowledge_vector_generations", "qdrant_collection_name")
    op.drop_column("knowledge_vector_generations", "provider_id")
