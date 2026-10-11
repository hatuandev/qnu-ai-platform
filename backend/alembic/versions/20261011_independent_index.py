"""Remove the legacy source FK from independent Knowledge index artifacts."""

import sqlalchemy as sa

from alembic import op

revision = "20261011_independent_index"
down_revision = "20261011_finalize_adr012_provenance_and_bindings"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys("knowledge_index_revisions"):
        if fk.get("referred_table") == "document_revisions" and fk.get("name"):
            op.drop_constraint(fk["name"], "knowledge_index_revisions", type_="foreignkey")
    op.alter_column("knowledge_index_revisions", "source_revision_id",
                    existing_type=sa.String(64), nullable=True)


def downgrade():
    # Independent artifacts have no legacy revision: do not invent provenance.
    pass
