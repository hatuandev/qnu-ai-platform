"""Replace unused provider types with the Ollama and llama.cpp chat runtimes."""

from sqlalchemy import text

from alembic import op

revision = "0026_ollama_llamacpp"
down_revision = "0025_index_fts_gin"
branch_labels = depends_on = None

RETAINED_TYPES = "'openai_compatible','gemini','local','mineru'"
REPLACED_TYPES = "'nemotron','paddleocr'"


def replace_types(allowed: str) -> None:
    op.drop_constraint("ck_provider_type", "providers", type_="check")
    op.create_check_constraint("ck_provider_type", "providers", f"provider_type IN ({allowed})")


def guard(statement: str, message: str) -> None:
    # Offline SQL generation has no database to inspect; the guard applies when the migration runs.
    if op.get_context().as_sql:
        return
    if op.get_bind().execute(text(statement)).first():
        raise RuntimeError(message)


def upgrade() -> None:
    guard(
        f"SELECT 1 FROM providers WHERE provider_type IN ({REPLACED_TYPES}) LIMIT 1",
        "Nemotron/PaddleOCR provider rows exist; reassign them before removing the types.",
    )
    replace_types(f"{RETAINED_TYPES},'ollama','llamacpp'")


def downgrade() -> None:
    guard(
        "SELECT 1 FROM providers WHERE provider_type IN ('ollama','llamacpp') LIMIT 1",
        "Ollama/llama.cpp provider rows exist; downgrade would invalidate them.",
    )
    replace_types(f"{RETAINED_TYPES},{REPLACED_TYPES}")
