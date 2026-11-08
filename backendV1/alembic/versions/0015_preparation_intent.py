"""Durable preparation intents for the source → preparation handoff."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0015_preparation_intent"
down_revision = "0014_publication_index_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kb_preparation_intents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("revision_sha256", sa.String(64), nullable=False),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("topic", sa.String(2000), nullable=False),
        sa.Column("text_version", sa.Integer(), nullable=False),
        sa.Column("text_version_id", sa.String(64)),
        sa.Column("text_canonical_sha256", sa.String(64)),
        sa.Column("provider_id", sa.String(64)),
        sa.Column("max_output_tokens", sa.Integer()),
        sa.Column("config", JSONB(), nullable=False),
        sa.Column(
            "ocr_run_id",
            sa.String(64),
            sa.ForeignKey("ocr_processing_runs.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "compilation_run_id",
            sa.String(64),
            sa.ForeignKey("kb_compilation_runs.id", ondelete="RESTRICT"),
        ),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_detail", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("worker_id", sa.String(120)),
        sa.ForeignKeyConstraint(
            ["source_id", "collection_id", "workspace_id"],
            ["kb_sources.id", "kb_sources.collection_id", "kb_sources.workspace_id"],
            name="fk_preparation_source",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "source_id", "collection_id", "workspace_id"],
            [
                "kb_source_revisions.id",
                "kb_source_revisions.source_id",
                "kb_source_revisions.collection_id",
                "kb_source_revisions.workspace_id",
            ],
            name="fk_preparation_revision",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "workspace_id", "requested_by", "idempotency_key", name="uq_preparation_idempotency"
        ),
        sa.UniqueConstraint("id", "workspace_id", "collection_id", name="uq_preparation_scope"),
        sa.CheckConstraint(
            "status IN ('queued','waiting_ocr','compiling','ready','failed','uncertain','cancelled')",
            name="ck_preparation_status",
        ),
        sa.CheckConstraint("mode IN ('source','ai')", name="ck_preparation_mode"),
        sa.CheckConstraint("revision_no >= 1", name="ck_preparation_revision"),
        sa.CheckConstraint("text_version >= 0", name="ck_preparation_text_version"),
        sa.CheckConstraint("char_length(revision_sha256) = 64", name="ck_preparation_sha256"),
    )
    op.create_index(
        "ix_kb_preparation_intents_workspace_id",
        "kb_preparation_intents",
        ["workspace_id"],
    )
    op.create_index(
        "ix_kb_preparation_intents_ocr_run_id",
        "kb_preparation_intents",
        ["ocr_run_id"],
    )
    op.create_index(
        "ix_kb_preparation_intents_compilation_run_id",
        "kb_preparation_intents",
        ["compilation_run_id"],
    )
    op.create_index(
        "ix_preparation_source_created",
        "kb_preparation_intents",
        ["source_id", "created_at"],
    )
    op.create_index(
        "ix_preparation_status_lease",
        "kb_preparation_intents",
        ["status", "lease_expires_at"],
    )


def downgrade() -> None:
    op.drop_table("kb_preparation_intents")
