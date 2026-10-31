"""Durable compiler refinement hierarchy and per-node Markdown."""

import sqlalchemy as sa

from alembic import op

revision = "0009_compiler_refinement"
down_revision = "0008_compilation_segments"
branch_labels = depends_on = None


def upgrade():
    op.add_column("kb_compilation_segments", sa.Column("parent_segment_id", sa.String(64)))
    op.create_index(
        "ix_kb_compilation_segments_parent_segment_id",
        "kb_compilation_segments",
        ["parent_segment_id"],
    )
    op.create_foreign_key(
        "fk_compiler_parent",
        "kb_compilation_segments",
        "kb_compilation_segments",
        ["parent_segment_id"],
        ["id"],
    )
    op.drop_constraint("ck_compilation_segment_artifact_kind", "kb_compilation_segment_artifacts")
    op.create_check_constraint(
        "ck_compilation_segment_artifact_kind",
        "kb_compilation_segment_artifacts",
        "kind IN ('raw_response','draft_json','markdown')",
    )


def downgrade():
    # Refuse downgrade until callers explicitly archive Markdown node artifacts.
    op.drop_constraint("ck_compilation_segment_artifact_kind", "kb_compilation_segment_artifacts")
    op.create_check_constraint(
        "ck_compilation_segment_artifact_kind",
        "kb_compilation_segment_artifacts",
        "kind IN ('raw_response','draft_json')",
    )
    op.drop_index(
        "ix_kb_compilation_segments_parent_segment_id", table_name="kb_compilation_segments"
    )
    op.drop_constraint("fk_compiler_parent", "kb_compilation_segments", type_="foreignkey")
    op.drop_column("kb_compilation_segments", "parent_segment_id")
