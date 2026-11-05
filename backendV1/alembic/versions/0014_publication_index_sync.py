"""Durable publication-driven indexing and safe vector retirement."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0014_publication_index_sync"
down_revision = "0013_queued_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("kb_index_runs", sa.Column("vectors_retired_at", sa.DateTime(timezone=True)))
    op.add_column("kb_index_runs", sa.Column("deactivated_at", sa.DateTime(timezone=True)))
    op.create_table(
        "kb_index_sync",
        sa.Column("collection_id", sa.String(64), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("run_revision", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("kb_index_runs.id", ondelete="SET NULL")),
        sa.Column("error_code", sa.String(64)),
        sa.Column("retry_receipts", JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("revision >= 1 AND run_revision >= 0", name="ck_index_sync_revision"),
        sa.CheckConstraint(
            "status IN ('pending','building','ready','failed','uncertain')",
            name="ck_index_sync_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("kb_index_sync")
    op.drop_column("kb_index_runs", "vectors_retired_at")
    op.drop_column("kb_index_runs", "deactivated_at")
