"""Store the system document model and concurrency per registered model."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0032_document_processing_defaults"
down_revision = "0031_spelling_defaults"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("model_defaults", sa.Column("document_provider_id", sa.String(64)))
    op.add_column("model_defaults", sa.Column("document_concurrency", JSONB))


def downgrade() -> None:
    op.drop_column("model_defaults", "document_concurrency")
    op.drop_column("model_defaults", "document_provider_id")
