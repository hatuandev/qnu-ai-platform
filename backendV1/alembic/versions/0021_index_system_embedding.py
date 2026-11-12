"""Pin authorization granted by the system embedding default to each index run."""

import sqlalchemy as sa

from alembic import op

revision = "0021_index_system_embedding"
down_revision = "0020_reverse_flow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kb_index_runs",
        sa.Column(
            "system_default_authorized", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    # Preserve active and in-flight runs with a demonstrable current system grant.
    op.execute(
        """
        UPDATE kb_index_runs AS run
        SET system_default_authorized = true
        FROM model_defaults AS defaults
        WHERE defaults.id = 'system'
          AND defaults.embedding_provider_id = run.provider_id
          AND (run.is_active OR run.status IN ('queued', 'running'))
        """
    )


def downgrade() -> None:
    op.drop_column("kb_index_runs", "system_default_authorized")
