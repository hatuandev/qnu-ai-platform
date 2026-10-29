"""Retain native extraction and images without changing old artifacts."""

from alembic import op

revision = "0007_native_extraction"
down_revision = "0006_kb_folders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_ocr_artifact_kind", "ocr_run_artifacts", type_="check")
    op.create_check_constraint(
        "ck_ocr_artifact_kind",
        "ocr_run_artifacts",
        "kind IN ('render_pdf','page_image','raw_response','canonical_json','markdown','manifest','native_page','embedded_image')",
    )


def downgrade() -> None:
    raise RuntimeError("evidence must be preserved; native extraction downgrade is not supported")
