"""Durable review refinement hierarchy and per-node Markdown."""

import sqlalchemy as sa

from alembic import op

revision = "0010_review_refinement"
down_revision = "0009_compiler_refinement"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "kb_compilation_review_segments",
        sa.Column("parent_segment_id", sa.String(64)),
    )
    op.create_index(
        "ix_kb_compilation_review_segments_parent_segment_id",
        "kb_compilation_review_segments",
        ["parent_segment_id"],
    )
    op.create_foreign_key(
        "fk_review_segment_parent",
        "kb_compilation_review_segments",
        "kb_compilation_review_segments",
        ["parent_segment_id"],
        ["id"],
    )
    op.drop_constraint(
        "ck_compilation_review_segment_artifact_kind",
        "kb_compilation_review_segment_artifacts",
    )
    op.create_check_constraint(
        "ck_compilation_review_segment_artifact_kind",
        "kb_compilation_review_segment_artifacts",
        "kind IN ('raw_response','assessment_json','markdown')",
    )


def downgrade():
    op.drop_constraint(
        "ck_compilation_review_segment_artifact_kind",
        "kb_compilation_review_segment_artifacts",
    )
    op.create_check_constraint(
        "ck_compilation_review_segment_artifact_kind",
        "kb_compilation_review_segment_artifacts",
        "kind IN ('raw_response','assessment_json')",
    )
    op.drop_index(
        "ix_kb_compilation_review_segments_parent_segment_id",
        table_name="kb_compilation_review_segments",
    )
    op.drop_constraint(
        "fk_review_segment_parent",
        "kb_compilation_review_segments",
        type_="foreignkey",
    )
    op.drop_column("kb_compilation_review_segments", "parent_segment_id")
