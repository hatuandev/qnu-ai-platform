"""Reverse-flow receipts: purge checkpoints, admin takeover and empty-store status.

Revision ID: 0020_reverse_flow
Revises: 0019_source_only_compilation
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0020_reverse_flow"
down_revision = "0019_source_only_compilation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("resource_lifecycle_actions") as actions:
        actions.add_column(sa.Column("phase", sa.String(32)))
        actions.add_column(
            sa.Column("progress", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"))
        )
        actions.add_column(sa.Column("worker_id", sa.String(120)))
        actions.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
        actions.add_column(
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0")
        )
        actions.add_column(sa.Column("last_error_at", sa.DateTime(timezone=True)))
        actions.add_column(sa.Column("confirmed_by", sa.String(200)))
        actions.add_column(sa.Column("takeover_by", sa.String(200)))
        actions.add_column(sa.Column("takeover_at", sa.DateTime(timezone=True)))
    op.drop_constraint("ck_index_sync_status", "kb_index_sync", type_="check")
    op.create_check_constraint(
        "ck_index_sync_status",
        "kb_index_sync",
        "status IN ('pending','building','ready','empty','failed','uncertain')",
    )


def downgrade() -> None:
    # The old worker needs not_before to resume a pending deletion safely.
    op.execute("LOCK TABLE resource_lifecycle_actions IN ACCESS EXCLUSIVE MODE")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM resource_lifecycle_actions
                WHERE kind = 'source' AND action = 'delete' AND status = 'pending'
                  AND (result ->> 'not_before') IS NULL
            ) THEN
                RAISE EXCEPTION 'Finish pending V1 source deletions before downgrading';
            END IF;
        END;
        $$;
        """
    )
    op.drop_constraint("ck_index_sync_status", "kb_index_sync", type_="check")
    # 0019 used ready with no generation for empty collections.
    op.execute("UPDATE kb_index_sync SET status = 'ready' WHERE status = 'empty'")
    op.create_check_constraint(
        "ck_index_sync_status",
        "kb_index_sync",
        "status IN ('pending','building','ready','failed','uncertain')",
    )
    with op.batch_alter_table("resource_lifecycle_actions") as actions:
        for column in (
            "takeover_at",
            "takeover_by",
            "confirmed_by",
            "last_error_at",
            "attempt_count",
            "lease_expires_at",
            "worker_id",
            "progress",
            "phase",
        ):
            actions.drop_column(column)
