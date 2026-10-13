"""Synchronize source revision state with structured review requirements."""

import sqlalchemy as sa

from alembic import op

revision = "20261012_sync_struct_review"
down_revision = "20261012_fact_long_text_identity"
branch_labels = None
depends_on = None


def upgrade():
    """Expose legacy structured-review requirements through the source state machine."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE knowledge_source_revisions
            SET status = 'review_required',
                quality_report = jsonb_set(
                    jsonb_set(
                        coalesce(quality_report, '{}'::jsonb),
                        '{overall_status}',
                        '"warning"'::jsonb,
                        true
                    ),
                    '{structured_issues}',
                    CASE
                        WHEN jsonb_typeof(parse_provenance #> '{structured_artifact,issues}') = 'array'
                        THEN parse_provenance #> '{structured_artifact,issues}'
                        ELSE '[]'::jsonb
                    END,
                    true
                ) || '{"structured_review_required": true}'::jsonb
            WHERE status = 'ready'
              AND coalesce(parse_provenance #>> '{structured_artifact,review,status}', '') <> 'approved'
              AND (
                    parse_provenance #>> '{structured_artifact,review,status}' = 'required'
                    OR CASE
                        WHEN jsonb_typeof(parse_provenance #> '{structured_artifact,issues}') = 'array'
                        THEN jsonb_array_length(parse_provenance #> '{structured_artifact,issues}') > 0
                        ELSE false
                    END
              )
            """
        )
    )


def downgrade():
    """A previous ready state cannot be inferred safely after human review may have occurred."""
