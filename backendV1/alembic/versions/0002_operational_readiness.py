"""Human review acknowledgements and approved storage cleanup receipts."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_operational_readiness"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kb_publication_previews", sa.Column("review_ack", postgresql.JSONB(), nullable=True)
    )
    op.create_table(
        "ops_storage_cleanup_actions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(64),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("actor_ref", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("target_hash", sa.String(64), nullable=False),
        sa.Column("candidates", postgresql.JSONB(), nullable=False),
        sa.Column("preview_sha256", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("request_hash", sa.String(64)),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "actor_ref", "idempotency_key", name="uq_storage_cleanup_request"
        ),
        sa.CheckConstraint(
            "status IN ('preview','pending','completed')", name="ck_storage_cleanup_status"
        ),
    )
    op.create_index(
        "ix_ops_storage_cleanup_actions_workspace_id",
        "ops_storage_cleanup_actions",
        ["workspace_id"],
    )


def downgrade() -> None:
    raise RuntimeError("Source evidence must be preserved; downgrade is disabled.")
