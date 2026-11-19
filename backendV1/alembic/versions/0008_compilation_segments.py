"""Add segmented compiler/review checkpoints and verified output generations."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008_compilation_segments"
down_revision = "0007_native_extraction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("kb_compilation_runs", sa.Column("output_id", sa.String(64)))

    op.create_table(
        "kb_compilation_segments",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("kb_compilation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("scope", postgresql.JSONB(), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(120), nullable=False),
        sa.Column("schema_sha256", sa.String(64)),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("request_started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "usage_id",
            sa.String(64),
            sa.ForeignKey("model_usage_records.id", ondelete="RESTRICT"),
        ),
        sa.Column("usage_tokens", sa.Integer()),
        sa.Column("error_code", sa.String(64)),
        sa.UniqueConstraint("run_id", "segment_index", name="uq_compilation_segment_index"),
        sa.CheckConstraint(
            "status IN ('pending','running','received','completed','failed','uncertain')",
            name="ck_compilation_segment_status",
        ),
        sa.CheckConstraint(
            "segment_index >= 1 AND attempt_count >= 0",
            name="ck_compilation_segment_counters",
        ),
    )
    op.create_index(
        "ix_kb_compilation_segments_run_id", "kb_compilation_segments", ["run_id"]
    )
    op.create_index(
        "ix_kb_compilation_segments_status", "kb_compilation_segments", ["status"]
    )

    op.create_table(
        "kb_compilation_segment_artifacts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "segment_id",
            sa.String(64),
            sa.ForeignKey("kb_compilation_segments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("blob_key", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("segment_id", "kind", name="uq_compilation_segment_artifact"),
        sa.CheckConstraint(
            "kind IN ('raw_response','draft_json')",
            name="ck_compilation_segment_artifact_kind",
        ),
        sa.CheckConstraint(
            "size_bytes >= 0 AND char_length(sha256) = 64",
            name="ck_compilation_segment_artifact_integrity",
        ),
    )
    op.create_index(
        "ix_kb_compilation_segment_artifacts_segment_id",
        "kb_compilation_segment_artifacts",
        ["segment_id"],
    )

    op.create_table(
        "kb_compilation_outputs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("kb_compilation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("partial", sa.Boolean(), nullable=False),
        sa.Column("draft_blob_key", sa.String(512), nullable=False),
        sa.Column("draft_sha256", sa.String(64), nullable=False),
        sa.Column("markdown_blob_key", sa.String(512), nullable=False),
        sa.Column("markdown_sha256", sa.String(64), nullable=False),
        sa.Column("coverage", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "generation", name="uq_compilation_output_generation"),
        sa.CheckConstraint("generation >= 1", name="ck_compilation_output_generation"),
        sa.CheckConstraint(
            "char_length(draft_sha256) = 64 AND char_length(markdown_sha256) = 64",
            name="ck_compilation_output_hash",
        ),
    )
    op.create_index(
        "ix_kb_compilation_outputs_run_id", "kb_compilation_outputs", ["run_id"]
    )

    op.create_table(
        "kb_compilation_review_segments",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "review_id",
            sa.String(64),
            sa.ForeignKey("kb_compilation_reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("scope", postgresql.JSONB(), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(120), nullable=False),
        sa.Column("schema_sha256", sa.String(64)),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("request_started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "usage_id",
            sa.String(64),
            sa.ForeignKey("model_usage_records.id", ondelete="RESTRICT"),
        ),
        sa.Column("usage_tokens", sa.Integer()),
        sa.Column("error_code", sa.String(64)),
        sa.UniqueConstraint(
            "review_id", "segment_index", name="uq_compilation_review_segment_index"
        ),
        sa.CheckConstraint(
            "status IN ('pending','running','received','completed','failed','uncertain')",
            name="ck_compilation_review_segment_status",
        ),
        sa.CheckConstraint(
            "segment_index >= 1 AND attempt_count >= 0",
            name="ck_compilation_review_segment_counters",
        ),
    )
    op.create_index(
        "ix_kb_compilation_review_segments_review_id",
        "kb_compilation_review_segments",
        ["review_id"],
    )
    op.create_index(
        "ix_kb_compilation_review_segments_status",
        "kb_compilation_review_segments",
        ["status"],
    )

    op.create_table(
        "kb_compilation_review_segment_artifacts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "segment_id",
            sa.String(64),
            sa.ForeignKey("kb_compilation_review_segments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("blob_key", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "segment_id", "kind", name="uq_compilation_review_segment_artifact"
        ),
        sa.CheckConstraint(
            "kind IN ('raw_response','assessment_json')",
            name="ck_compilation_review_segment_artifact_kind",
        ),
        sa.CheckConstraint(
            "size_bytes >= 0 AND char_length(sha256) = 64",
            name="ck_compilation_review_segment_artifact_hash",
        ),
    )
    op.create_index(
        "ix_kb_compilation_review_segment_artifacts_segment_id",
        "kb_compilation_review_segment_artifacts",
        ["segment_id"],
    )

    op.drop_constraint(
        "ck_compilation_artifact_kind", "kb_compilation_artifacts", type_="check"
    )
    op.create_check_constraint(
        "ck_compilation_artifact_kind",
        "kb_compilation_artifacts",
        "kind IN ('input_snapshot','raw_response','draft_json','markdown','segment_manifest')",
    )
    op.drop_constraint(
        "ck_compilation_review_artifact_kind",
        "kb_compilation_review_artifacts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_compilation_review_artifact_kind",
        "kb_compilation_review_artifacts",
        "kind IN ('input_snapshot','raw_response','report_json','markdown','segment_manifest')",
    )


def downgrade() -> None:
    raise RuntimeError("evidence must be preserved; segmented compilation downgrade is not supported")
