"""MinerU transport, original ZIP evidence and tokenless document reservations."""

from sqlalchemy import text

from alembic import op

revision = "0011_mineru_ocr"
down_revision = "0010_review_refinement"
branch_labels = depends_on = None

TYPES = "'openai_compatible','gemini','local','nemotron','paddleocr'"
KINDS = "'render_pdf','page_image','raw_response','canonical_json','markdown','manifest','native_page','embedded_image'"


def constraints(mineru):
    for table, name, clause in (
        (
            "providers",
            "ck_provider_type",
            f"provider_type IN ({TYPES}{",'mineru'" if mineru else ''})",
        ),
        (
            "ocr_run_artifacts",
            "ck_ocr_artifact_kind",
            f"kind IN ({KINDS}{",'provider_document'" if mineru else ''})",
        ),
        (
            "model_usage_records",
            "ck_model_usage_tokens",
            f"reserved_tokens {'>=' if mineru else '>'} 0 AND (total_tokens IS NULL OR total_tokens >= 0)",
        ),
    ):
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, clause)


def upgrade():
    constraints(True)


def downgrade():
    connection = op.get_bind()
    for query in (
        "SELECT 1 FROM providers WHERE provider_type='mineru' LIMIT 1",
        "SELECT 1 FROM ocr_run_artifacts WHERE kind='provider_document' LIMIT 1",
        "SELECT 1 FROM model_usage_records WHERE reserved_tokens=0 LIMIT 1",
    ):
        if connection.execute(text(query)).first():
            raise RuntimeError("MinerU evidence exists; downgrade would invalidate stored records.")
    constraints(False)
