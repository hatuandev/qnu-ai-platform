"""Additive glossary tables for collection-scoped search aliases."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20261015_glossary_terms"
down_revision = "20261012_sync_struct_review"
branch_labels = None
depends_on = None


def _table_names(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    names = _table_names(op.get_bind())
    if "knowledge_glossary_terms" not in names:
        op.create_table(
            "knowledge_glossary_terms",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("collection_id", sa.String(64),
                      sa.ForeignKey("knowledge_collections.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_phrase", sa.Text(), nullable=False),
            sa.Column("phrase_normalized", sa.String(512), nullable=False),
            sa.Column("target_term", sa.String(512), nullable=False),
            sa.Column("note", sa.Text(), nullable=False, server_default=""),
            sa.Column("scope", JSONB(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("created_by", sa.String(64), nullable=True),
            sa.Column("updated_by", sa.String(64), nullable=True),
            sa.Column("reviewed_by", sa.String(64), nullable=True),
            sa.Column("review_reason", sa.String(512), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
        )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("knowledge_glossary_terms")} \
        if "knowledge_glossary_terms" in _table_names(op.get_bind()) else set()
    for name, columns in (
        ("ix_glossary_terms_collection", ["collection_id"]),
        ("ix_glossary_terms_phrase", ["phrase_normalized"]),
        ("ix_glossary_terms_status", ["status"]),
        ("ix_glossary_terms_col_status", ["collection_id", "status"]),
    ):
        if name not in indexes:
            op.create_index(name, "knowledge_glossary_terms", columns)

    if "knowledge_glossary_audits" not in names:
        op.create_table(
            "knowledge_glossary_audits",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("entry_id", sa.String(64),
                      sa.ForeignKey("knowledge_glossary_terms.id", ondelete="CASCADE"), nullable=True),
            sa.Column("collection_id", sa.String(64),
                      sa.ForeignKey("knowledge_collections.id", ondelete="CASCADE"), nullable=False),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("actor_id", sa.String(64), nullable=True),
            sa.Column("reason", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
        )
        op.create_index("ix_glossary_audits_entry", "knowledge_glossary_audits", ["entry_id"])
        op.create_index("ix_glossary_audits_collection", "knowledge_glossary_audits", ["collection_id"])

    if "knowledge_glossary_settings" not in names:
        op.create_table(
            "knowledge_glossary_settings",
            sa.Column("collection_id", sa.String(64),
                      sa.ForeignKey("knowledge_collections.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("updated_by", sa.String(64), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
        )


def downgrade() -> None:
    # Retain glossary tables on downgrade to preserve approval provenance.
    pass
