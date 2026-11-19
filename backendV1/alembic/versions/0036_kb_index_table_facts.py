"""Add kb_index_table_facts for scoped deterministic query_facts (Slice 3).

Facts are bound to an active kb_index_runs / kb_index_inputs generation with
ON DELETE CASCADE so lifecycle withdraw/delete cleans them up automatically.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0036_kb_index_table_facts"
down_revision = "0035_assistant_without_collections"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "kb_index_table_facts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("input_id", sa.String(length=64), nullable=False),
        sa.Column("index_run_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("version_id", sa.String(length=64), nullable=False),
        sa.Column("publication_decision_id", sa.String(length=64), nullable=False),
        sa.Column("table_id", sa.String(length=128), nullable=False),
        sa.Column("source_table_citation", sa.String(length=256), nullable=False),
        sa.Column("table_title", sa.Text(), nullable=False, server_default=""),
        sa.Column("has_header", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "keep_whole_in_chunk", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "column_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "scoped_notes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("fact_id", sa.String(length=192), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("row_kind", sa.String(length=24), nullable=False, server_default="data"),
        sa.Column("row_pointer", sa.String(length=256), nullable=False),
        sa.Column("group_name", sa.Text(), nullable=True),
        sa.Column("subject_code", sa.String(length=128), nullable=True),
        sa.Column("subject_name", sa.Text(), nullable=True),
        sa.Column("data_year", sa.Integer(), nullable=True),
        sa.Column("data_status", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "detail_md_pointers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "applicable_note_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "source_cell_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "cross_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["input_id", "index_run_id", "workspace_id", "collection_id"],
            [
                "kb_index_inputs.id",
                "kb_index_inputs.run_id",
                "kb_index_inputs.workspace_id",
                "kb_index_inputs.collection_id",
            ],
            ondelete="CASCADE",
            name="fk_index_table_fact_input",
        ),
        sa.ForeignKeyConstraint(
            ["index_run_id", "workspace_id", "collection_id"],
            ["kb_index_runs.id", "kb_index_runs.workspace_id", "kb_index_runs.collection_id"],
            ondelete="CASCADE",
            name="fk_index_table_fact_run",
        ),
        sa.UniqueConstraint("index_run_id", "fact_id", name="uq_index_table_fact_id"),
        sa.CheckConstraint(
            "row_kind IN ('data','summary','group_header','inline_note')",
            name="ck_index_table_fact_row_kind",
        ),
        sa.CheckConstraint(
            "data_status IN ('locked','interim','planned','unknown')",
            name="ck_index_table_fact_data_status",
        ),
        sa.CheckConstraint("row_index >= 0", name="ck_index_table_fact_row_index"),
    )
    op.create_index(
        "ix_kb_index_table_facts_index_run_id",
        "kb_index_table_facts",
        ["index_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_kb_index_table_facts_scope",
        "kb_index_table_facts",
        ["workspace_id", "index_run_id", "table_id", "data_year", "row_kind"],
        unique=False,
    )
    op.create_index(
        "ix_kb_index_table_facts_attributes_gin",
        "kb_index_table_facts",
        ["attributes"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_kb_index_table_facts_attributes_gin", table_name="kb_index_table_facts")
    op.drop_index("ix_kb_index_table_facts_scope", table_name="kb_index_table_facts")
    op.drop_index("ix_kb_index_table_facts_index_run_id", table_name="kb_index_table_facts")
    op.drop_table("kb_index_table_facts")
