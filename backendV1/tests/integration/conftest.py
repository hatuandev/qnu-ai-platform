"""Integration fixtures: real database, real HTTP stack, no fake persistence."""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()

TABLES = (
    "app_request_logs",
    "app_api_keys",
    "app_clients",
    "ops_storage_cleanup_actions",
    "resource_lifecycle_actions",
    "resource_lifecycle_states",
    "ops_evidence_backups",
    "ops_actions",
    "kb_compilation_edit_previews",
    "kb_compilation_review_segment_artifacts",
    "kb_compilation_review_segments",
    "kb_compilation_review_jobs",
    "kb_compilation_review_artifacts",
    "kb_compilation_reviews",
    "kb_compilation_outputs",
    "kb_compilation_segment_artifacts",
    "kb_compilation_segments",
    "ocr_spelling_reviews",
    "ocr_spelling_defaults",
    "ocr_spelling_dispositions",
    "ocr_spelling_runs",
    "ocr_text_versions",
    "kb_answer_review_items",
    "kb_answer_reviews",
    "assistant_publication_questions",
    "assistant_publication_stats",
    "assistant_publications",
    "chat_turns",
    "chat_conversations",
    "chat_assistants",
    "kb_index_chunks",
    "kb_index_sync",
    "kb_index_inputs",
    "kb_index_runs",
    "kb_publication_decisions",
    "kb_review_submission_actions",
    "kb_review_submission_previews",
    "kb_review_submissions",
    "kb_publication_previews",
    "kb_compiled_versions",
    "kb_compiled_documents",
    "kb_compilation_artifacts",
    "kb_compilation_inputs",
    "kb_compilation_runs",
    "kb_preparation_intents",
    "ocr_run_artifacts",
    "ocr_run_pages",
    "ocr_processing_runs",
    "kb_upload_requests",
    "kb_source_revisions",
    "kb_sources",
    "kb_folders",
    "kb_collections",
    "modelops_events",
    "model_usage_records",
    "workspace_quotas",
    "workspace_events",
    "workspace_members",
    "provider_key_audits",
    "provider_keys",
    "providers",
    "model_defaults",
    "workspaces",
)


@pytest.fixture(scope="session")
def client():
    if not TEST_DATABASE_URL:
        pytest.skip("NOT RUN: TEST_DATABASE_URL chưa cấu hình (Postgres test riêng).")
    from qnu.main import app
    from qnu.platform.database import engine

    assert engine.url.database.startswith("qnu_v1_test_")
    options = {}
    # Opt-in host workaround for the reproduced Windows Proactor portal-close
    # deadlock. TCP/Redis groups can use Selector; subprocess recovery tests keep
    # the default loop. This never changes the application's production loop.
    if os.name == "nt" and os.environ.get("QNU_TEST_WINDOWS_SELECTOR_LOOP") == "true":
        options["loop_factory"] = asyncio.SelectorEventLoop
    with TestClient(app, backend_options=options) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_tables(client):
    from sqlalchemy import text

    from qnu.platform.database import engine

    async def _truncate() -> None:
        async with engine.begin() as connection:
            await connection.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY"))

    client.portal.call(_truncate)
    yield
    from qnu.api.dependencies import get_actor, get_job_queue
    from qnu.main import app

    app.dependency_overrides.pop(get_actor, None)
    app.dependency_overrides.pop(get_job_queue, None)
