"""Store the ordered document model group and its scheduling mode."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0033_document_model_group"
down_revision = "0032_document_processing_defaults"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("model_defaults", sa.Column("document_mode", sa.String(16)))
    op.add_column("model_defaults", sa.Column("document_models", JSONB))


def downgrade() -> None:
    op.drop_column("model_defaults", "document_models")
    op.drop_column("model_defaults", "document_mode")
