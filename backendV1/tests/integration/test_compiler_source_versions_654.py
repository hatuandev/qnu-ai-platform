"""Exact saved OCR selection is carried through snapshot and downstream provenance."""

import json

import pytest

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.test_ocr_text_review_651 import edit_body, review_url, save


def test_exact_saved_text_is_pinned_despite_newer_saved_text(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.compilation import artifacts
    from qnu.domains.knowledge.compilation.models import CompilationInput, CompilationRun
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client, code="selected-text")
    url = review_url(data)
    original = client.get(url).json()
    raw = client.get(url.removesuffix("/text-review") + "/document").content
    first = save(client, url, edit_body(original, original["units"][0], "PHỤ LỤC ĐÃ SỬA"))
    assert first.status_code == 200, first.text
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        result = request_compile(client, data, text_versions={data["ocr_run_id"]: 1})
        assert result.status_code == 201, result.text
        saved = first.json()
        newer = save(client, url, edit_body(saved, saved["units"][0], "BẢN MỚI KHÁC"), "save-two")
        assert newer.status_code == 200, newer.text
        run = result.json()["run"]["id"]
        assert execute_compile(client, run) == "completed"
        incoming = json.loads(chat.requests[0]["body"]["messages"][-1]["content"])["documents"][0]
        assert incoming["pages"][0]["blocks"][0]["text"] == "PHỤ LỤC ĐÃ SỬA"

        async def pinned_source():
            async with AsyncSessionFactory() as db:
                row = await db.get(CompilationRun, run)
                _, payload = await artifacts.read(
                    db, app.state.container.blob_store, row, "input_snapshot"
                )
                binding = await db.scalar(
                    select(CompilationInput).where(
                        CompilationInput.run_id == run,
                        CompilationInput.ocr_run_id == data["ocr_run_id"],
                    )
                )
                return json.loads(payload)["documents"][0], binding.text_version_id

        snapshot, pinned_id = client.portal.call(pinned_source)
        assert pinned_id == snapshot["text_version"]["id"] == saved["version_id"]
        assert pinned_id != newer.json()["version_id"]
        assert snapshot["text_version"]["canonical_sha256"] == saved["canonical_sha256"]
        assert snapshot["pages"][0]["blocks"][0]["text"] == "PHỤ LỤC ĐÃ SỬA"
        draft = client.get(data["url"] + "/" + run + "/draft").json()
        citation = next(iter(draft["citations"].values()))
        assert citation["text_version"]["id"] == saved["version_id"]
        assert citation["artifact"] == "text_review_document"
        assert citation["original_canonical_sha256"] == original["canonical_sha256"]
        ctx = client.get(data["url"] + "/" + run + "/edit-context")
        assert ctx.status_code == 200, ctx.text
    assert client.get(url.removesuffix("/text-review") + "/document").content == raw


@pytest.mark.parametrize(
    "selection,status", [("foreign", 422), ("negative", 422), ("bool", 422), ("missing", 404)]
)
def test_selection_rejects_invalid_or_missing_versions(client, selection, status):
    data = processed_input(client)
    values = {
        "foreign": {"ocr_other": 1},
        "negative": {data["ocr_run_id"]: -1},
        "bool": {data["ocr_run_id"]: True},
        "missing": {data["ocr_run_id"]: 99},
    }
    result = request_compile(client, data, text_versions=values[selection])
    assert result.status_code == status, result.text


def test_default_uses_raw_even_after_text_save_and_can_disable_auto_review(client):
    data = processed_input(client)
    url = review_url(data)
    original = client.get(url).json()
    assert (
        save(client, url, edit_body(original, original["units"][0], "BẢN SỬA RIÊNG")).status_code
        == 200
    )
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        response = request_compile(client, data, auto_review=False)
        assert response.status_code == 201, response.text
        run_id = response.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        doc = json.loads(chat.requests[0]["body"]["messages"][-1]["content"])["documents"][0]
        assert "text_version" not in doc and doc["pages"][0]["blocks"][0]["text"] == "PHỤ LỤC 01"
        assert client.get(data["url"] + "/" + run_id + "/auto-review").status_code == 404


def test_legacy_idempotency_replays_without_changing_old_workflow(client):
    from qnu.domains.knowledge.compilation.models import CompilationRun
    from qnu.domains.knowledge.publication.evidence import digest
    from qnu.platform.database import AsyncSessionFactory
    from tests.integration.workflow_support import prepared

    with prepared(client) as (data, chat):
        run = client.get(data["url"] + "/" + data["run_id"]).json()
        old_request = {
            "topic": run["topic"],
            "ocr_run_ids": [data["ocr_run_id"]],
            "provider_id": None,
            "max_output_tokens": None,
            "collection_id": data["collection"]["id"],
        }

        async def legacy():
            async with AsyncSessionFactory() as db:
                row = await db.get(CompilationRun, data["run_id"])
                row.request_hash = digest(old_request)
                row.config = {
                    k: v
                    for k, v in row.config.items()
                    if k not in {"workflow_version", "review", "auto_review"}
                }
                await db.commit()

        client.portal.call(legacy)
        repeated = request_compile(client, data)
        assert repeated.status_code == 200, repeated.text
        assert repeated.json()["run"]["id"] == data["run_id"] and len(chat.requests) == 1


def test_corrupt_selected_markdown_blocks_compile_before_model(client):
    from qnu.domains.ocr.review.models import TextVersion
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client)
    url = review_url(data)
    original = client.get(url).json()
    result = save(client, url, edit_body(original, original["units"][0], "Bản sửa"))
    assert result.status_code == 200, result.text
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        requested = request_compile(client, data, text_versions={data["ocr_run_id"]: 1})
        assert requested.status_code == 201, requested.text

        async def corrupt():
            async with AsyncSessionFactory() as db:
                row = await db.get(TextVersion, result.json()["version_id"])
                await app.state.container.blob_store.put_bytes(
                    row.markdown_key, b"damaged", "text/markdown"
                )

        client.portal.call(corrupt)
        assert execute_compile(client, requested.json()["run"]["id"]) == "failed"
        assert not chat.requests
