"""Add nullable fact query projections; never infer legacy years from filenames."""

import sqlalchemy as sa

from alembic import op

revision = "20261012_fact_temporal_context"
down_revision = "20261011_independent_index"
branch_labels = None
depends_on = None


def upgrade():
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("knowledge_facts")}
    columns = {"entity_code": sa.String(128), "attribute_code": sa.String(64), "applicability_year": sa.Integer(),
               "temporal_type": sa.String(32), "admission_method": sa.String(255), "unit": sa.String(128)}
    for name, data_type in columns.items():
        if name not in existing:
            op.add_column("knowledge_facts", sa.Column(name, data_type, nullable=True))
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("knowledge_facts")}
    if "ix_fact_snapshot_context" not in indexes:
        op.create_index("ix_fact_snapshot_context", "knowledge_facts",
                        ["collection_id", "index_revision_id", "entity_code", "attribute_code", "applicability_year"])


def downgrade():
    # Retain provenance-bearing columns; no destructive downgrade of fact context.
    pass
