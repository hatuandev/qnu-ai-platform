"""Review handoff receipts and previews beside the publication status enum."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0016_review_submission"
down_revision = "0015_preparation_intent"
branch_labels = None
depends_on = None

_VERSION_FK = (
    ["version_id", "document_id", "workspace_id", "collection_id"],
    [
        "kb_compiled_versions.id",
        "kb_compiled_versions.document_id",
        "kb_compiled_versions.workspace_id",
        "kb_compiled_versions.collection_id",
    ],
)


def upgrade() -> None:
    op.create_table(
        "kb_review_submissions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("version_id", sa.String(64), nullable=False),
        sa.Column("bundle_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(1000), nullable=False),
        sa.Column("submitted_by", sa.String(200), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("document_sequence", sa.Integer(), nullable=False),
        sa.Column("closed_by", sa.String(200)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("close_reason", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            *_VERSION_FK,
            name="fk_review_submission_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            name="fk_review_submission_collection",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id", "workspace_id", "collection_id", name="uq_review_submission_scope"
        ),
        sa.CheckConstraint(
            "status IN ('pending','changes_requested','resolved','cancelled')",
            name="ck_review_submission_status",
        ),
        sa.CheckConstraint(
            "state_version >= 1 AND document_sequence >= 1", name="ck_review_sequence"
        ),
        sa.CheckConstraint("char_length(bundle_sha256) = 64", name="ck_review_bundle_sha256"),
    )
    op.create_index(
        "uq_review_submission_pending",
        "kb_review_submissions",
        ["version_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_review_submission_document",
        "kb_review_submissions",
        ["document_id", "version_id", "submitted_at"],
    )
    op.create_index(
        "ix_review_submission_worklist",
        "kb_review_submissions",
        ["workspace_id", "collection_id", "status", "submitted_at"],
    )
    op.create_index(
        "ix_kb_review_submissions_workspace_id",
        "kb_review_submissions",
        ["workspace_id"],
    )

    op.create_table(
        "kb_review_submission_previews",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("version_id", sa.String(64), nullable=False),
        sa.Column("submission_id", sa.String(64)),
        sa.Column("actor_ref", sa.String(200), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("expected_document_sequence", sa.Integer(), nullable=False),
        sa.Column("expected_version_sequence", sa.Integer(), nullable=False),
        sa.Column("expected_submission_status", sa.String(20)),
        sa.Column("expected_submission_sequence", sa.Integer()),
        sa.Column("bundle_sha256", sa.String(64), nullable=False),
        sa.Column("preview_sha256", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["submission_id", "workspace_id", "collection_id"],
            [
                "kb_review_submissions.id",
                "kb_review_submissions.workspace_id",
                "kb_review_submissions.collection_id",
            ],
            name="fk_review_preview_submission",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            *_VERSION_FK,
            name="fk_review_preview_version",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("id", "workspace_id", "collection_id", name="uq_review_preview_scope"),
        sa.CheckConstraint(
            "action IN ('submit','request_changes','cancel')", name="ck_review_preview_action"
        ),
    )
    op.create_index(
        "ix_review_preview_created",
        "kb_review_submission_previews",
        ["workspace_id", "collection_id", "created_at"],
    )

    op.create_table(
        "kb_review_submission_actions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("version_id", sa.String(64), nullable=False),
        sa.Column("submission_id", sa.String(64), nullable=False),
        sa.Column("preview_id", sa.String(64)),
        sa.Column("publication_decision_id", sa.String(64)),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("actor_ref", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("request_hash", sa.String(64)),
        sa.Column("document_sequence", sa.Integer(), nullable=False),
        sa.Column("bundle_sha256", sa.String(64), nullable=False),
        sa.Column("before", JSONB(), nullable=False),
        sa.Column("after", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["submission_id", "workspace_id", "collection_id"],
            [
                "kb_review_submissions.id",
                "kb_review_submissions.workspace_id",
                "kb_review_submissions.collection_id",
            ],
            name="fk_review_action_submission",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["preview_id", "workspace_id", "collection_id"],
            [
                "kb_review_submission_previews.id",
                "kb_review_submission_previews.workspace_id",
                "kb_review_submission_previews.collection_id",
            ],
            name="fk_review_action_preview",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["publication_decision_id"],
            ["kb_publication_decisions.id"],
            name="kb_review_submission_actions_publication_decision_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "workspace_id", "actor_ref", "idempotency_key", name="uq_review_action_idempotency"
        ),
        sa.UniqueConstraint("preview_id", name="uq_review_action_preview"),
        sa.UniqueConstraint("publication_decision_id", name="uq_review_action_decision"),
        sa.CheckConstraint(
            "action IN ('submit','request_changes','cancel','approved','superseded')",
            name="ck_review_action_action",
        ),
    )
    op.create_index(
        "ix_review_action_submission",
        "kb_review_submission_actions",
        ["submission_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("kb_review_submission_actions")
    op.drop_table("kb_review_submission_previews")
    op.drop_table("kb_review_submissions")
