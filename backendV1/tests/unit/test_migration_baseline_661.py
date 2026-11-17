"""A frozen baseline and additive revisions initialize only the owned v1 schema."""

import re
from io import StringIO

from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command
from qnu.platform.schema import SCHEMA_HEAD


def test_single_initial_revision_has_no_dependencies():
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert scripts.get_bases() == ["0001_initial_schema"]
    assert scripts.get_heads() == [SCHEMA_HEAD]
    assert scripts.get_revision("0020_reverse_flow").down_revision == (
        "0019_source_only_compilation"
    )
    assert scripts.get_revision("0019_source_only_compilation").down_revision == (
        "0018_preparation_auto"
    )
    assert scripts.get_revision("0018_preparation_auto").down_revision == "0017_answer_review"
    assert scripts.get_revision("0014_publication_index_sync").down_revision == "0013_queued_review"
    assert scripts.get_revision("0017_answer_review").down_revision == "0016_review_submission"
    assert scripts.get_revision("0016_review_submission").down_revision == "0015_preparation_intent"
    assert scripts.get_revision("0015_preparation_intent").down_revision == (
        "0014_publication_index_sync"
    )
    assert scripts.get_revision("0013_queued_review").down_revision == "0012_assistant_auto_output"
    assert scripts.get_revision("0012_assistant_auto_output").down_revision == "0011_mineru_ocr"
    assert scripts.get_revision("0011_mineru_ocr").down_revision == "0010_review_refinement"
    assert (
        scripts.get_revision("0010_review_refinement").down_revision == "0009_compiler_refinement"
    )
    assert (
        scripts.get_revision("0009_compiler_refinement").down_revision
        == "0008_compilation_segments"
    )
    assert (
        scripts.get_revision("0008_compilation_segments").down_revision == "0007_native_extraction"
    )
    assert scripts.get_revision("0007_native_extraction").down_revision == "0006_kb_folders"
    baseline = scripts.get_revision("0001_initial_schema")
    assert baseline.down_revision is None
    assert scripts.get_revision("0002_operational_readiness").down_revision == baseline.revision
    assert (
        scripts.get_revision("0003_rag_policy_metadata").down_revision
        == "0002_operational_readiness"
    )
    assert (
        scripts.get_revision("0004_application_api_keys").down_revision
        == "0003_rag_policy_metadata"
    )

    assert (
        scripts.get_revision("0005_provider_connections").down_revision
        == "0004_application_api_keys"
    )
    assert scripts.get_revision("0006_kb_folders").down_revision == "0005_provider_connections"


def test_initial_schema_offline_sql_creates_v1_without_touching_legacy():
    buffer = StringIO()
    config = Config("alembic.ini", output_buffer=buffer)
    command.upgrade(config, "head", sql=True)
    sql = buffer.getvalue()
    assert "CREATE TABLE resource_lifecycle_actions" in sql
    assert "CREATE TABLE kb_sources" in sql and "serving_revision_no" in sql
    assert "CREATE TABLE alembic_version_backendv1" in sql
    assert "CREATE TABLE alembic_version (" not in sql
    assert set(re.findall(r"^DROP TABLE (\w+);$", sql, re.MULTILINE)) == {
        "workspace_allowed_providers",
        "workspace_model_defaults",
    }
    assert "0001_initial_schema" in sql
    assert "ADD COLUMN progress JSONB" in sql and "ADD COLUMN attempt_count INTEGER" in sql
    assert "status IN ('pending','building','ready','empty','failed','uncertain')" in sql
    assert "CREATE INDEX ix_compilation_reuse_key" in sql
    assert "mode IN ('source','ai','auto')" in sql
    assert "CREATE TABLE kb_index_sync" in sql
    assert "ADD COLUMN vectors_retired_at" in sql
    assert "'mineru'" in sql and "'provider_document'" in sql
    assert (
        "provider_type IN ('openai_compatible','gemini','local','mineru','ollama','llamacpp')"
        in sql
    )
    assert "reserved_tokens >= 0" in sql
    assert "ADD COLUMN parent_segment_id" in sql
    assert "fk_compiler_parent" in sql
    assert "fk_review_segment_parent" in sql
    assert "CREATE TABLE app_api_keys" in sql
    assert "CREATE UNIQUE INDEX ix_app_api_keys_idempotency_key" in sql
    assert "ADD COLUMN rag_policy JSONB" in sql
    assert "ADD COLUMN retrieval_metadata JSONB" in sql
    assert "CREATE TABLE ops_storage_cleanup_actions" in sql
    assert "CREATE TABLE kb_folders" in sql
