"""Index the published chunk full-text expression used by hybrid retrieval."""

import sqlalchemy as sa

from alembic import op

revision = "0025_index_fts_gin"
down_revision = "0024_spelling_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_kb_index_chunks_fts",
        "kb_index_chunks",
        [sa.text("to_tsvector('simple'::regconfig, text)")],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_kb_index_chunks_fts", table_name="kb_index_chunks")
