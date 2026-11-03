"""A frozen baseline and additive revisions initialize only the owned v1 schema."""

from io import StringIO
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command
from qnu.platform.schema import SCHEMA_HEAD


def test_single_initial_revision_has_no_dependencies():
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    revisions = list(scripts.walk_revisions())
    assert len(revisions) == 12
    assert scripts.get_revision("0012_assistant_auto_output").down_revision == "0011_mineru_ocr"
    assert scripts.get_heads() == [SCHEMA_HEAD]
    assert (
        scripts.get_revision("0011_mineru_ocr").down_revision
        == "0010_review_refinement"
    )
    assert (
        scripts.get_revision("0010_review_refinement").down_revision
        == "0009_compiler_refinement"
    )
    assert (
        scripts.get_revision("0009_compiler_refinement").down_revision
        == "0008_compilation_segments"
    )
    assert (
        scripts.get_revision("0008_compilation_segments").down_revision == "0007_native_extraction"
    )
    assert SCHEMA_HEAD == scripts.get_current_head()
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
    assert "DROP TABLE" not in sql
    assert "0001_initial_schema" in sql
    assert len(list(Path("alembic/versions").glob("[0-9]*.py"))) == 12
    assert "'mineru'" in sql and "'provider_document'" in sql
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
