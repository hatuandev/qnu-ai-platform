"""Knowledge directory hierarchy (folders) and source folder association."""

import sqlalchemy as sa

from alembic import op

revision = "0006_kb_folders"
down_revision = "0005_provider_connections"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "kb_folders",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("parent_id", sa.String(64), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="CASCADE",
            name="fk_kb_folder_collection",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["kb_folders.id"],
            ondelete="CASCADE",
            name="fk_kb_folder_parent",
        ),
        sa.UniqueConstraint("id", "collection_id", "workspace_id", name="uq_kb_folder_scope"),
        sa.CheckConstraint("char_length(name) >= 1", name="ck_kb_folder_name_len"),
    )
    op.create_index("ix_kb_folders_workspace_id", "kb_folders", ["workspace_id"])
    op.create_index("ix_kb_folders_collection_id", "kb_folders", ["collection_id"])
    op.create_index("ix_kb_folders_parent_id", "kb_folders", ["parent_id"])

    op.add_column("kb_sources", sa.Column("folder_id", sa.String(64), nullable=True))
    op.create_foreign_key(
        "fk_kb_source_folder",
        "kb_sources",
        "kb_folders",
        ["folder_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_kb_sources_folder_id", "kb_sources", ["folder_id"])


def downgrade():
    op.drop_index("ix_kb_sources_folder_id", table_name="kb_sources")
    op.drop_constraint("fk_kb_source_folder", "kb_sources", type_="foreignkey")
    op.drop_column("kb_sources", "folder_id")
    op.drop_table("kb_folders")
