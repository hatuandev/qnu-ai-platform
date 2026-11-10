"""Permanent deletion boundaries. Synthetic data only; no network or application DB."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qnu.api.dependencies import get_actor, get_blob_store, get_db
from qnu.api.handlers import register_exception_handlers
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.lifecycle import purge, service, targets
from qnu.domains.lifecycle.models import LifecycleAction
from qnu.domains.lifecycle.purge_graph import graph_plan
from qnu.domains.lifecycle.router import router
from qnu.domains.lifecycle.schemas import AcceptRequest, ActionResponse
from qnu.platform.errors import Conflict, DependencyUnavailable


def test_published_source_preview_lists_versions_without_destructive_call(monkeypatch):
    actor = AuthActor(username="synthetic-admin", actor_id="synthetic-admin")

    added = []

    def add(row):
        # Flush-time column defaults are not applied by the mocked session.
        row.progress, row.attempt_count = {}, 0
        if isinstance(row, LifecycleAction):
            added.append(row)

    db = SimpleNamespace(add=add, commit=AsyncMock())
    blob = SimpleNamespace(purge=AsyncMock(), target_hash="storage")
    source = SimpleNamespace(id="source", workspace_id="w", collection_id="c", title="Synthetic")
    monkeypatch.setattr(service, "authorize", AsyncMock())
    monkeypatch.setattr(targets, "target", AsyncMock(return_value=source))
    monkeypatch.setattr(purge, "require_not_pending", AsyncMock())
    monkeypatch.setattr(targets, "state", AsyncMock(return_value=None))
    monkeypatch.setattr(targets, "require_operation", Mock())
    monkeypatch.setattr(targets, "snapshot", AsyncMock(return_value=({}, {})))
    plan = {"graph_sha256": "graph", "objects": {}, "rows": {}}
    monkeypatch.setattr(
        purge,
        "inspect_source",
        AsyncMock(
            return_value=(
                plan,
                {
                    "permanent": True,
                    "published_versions_to_withdraw": 1,
                    "published_version_ids": ["version"],
                    "restore_available": False,
                },
            )
        ),
    )
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_actor] = lambda: actor
    app.dependency_overrides[get_blob_store] = lambda: blob
    with TestClient(app) as client:
        response = client.post(
            "/workspaces/w/lifecycle/previews",
            json={
                "kind": "source",
                "resource_id": "source",
                "action": "delete",
                "reason": "Synthetic deletion",
            },
        )
    assert response.status_code == 200, response.text
    assert response.json()["impact"]["published_versions_to_withdraw"] == 1
    assert response.json()["impact"]["published_version_ids"] == ["version"]
    assert len(added) == 1
    assert added[0].status == "preview"
    blob.purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_rechecks_publication_after_preview_before_preparing_purge(monkeypatch):
    row = SimpleNamespace(
        id="a",
        workspace_id="w",
        actor_ref="actor",
        kind="source",
        resource_id="source",
        action="delete",
        parameters={},
        reason="Synthetic",
        impact={},
        state_sha256="old",
        status="preview",
        expires_at=utcnow() + timedelta(minutes=5),
    )
    row.preview_sha256 = service.preview_hash(row)
    db = SimpleNamespace(scalar=AsyncMock(return_value=None))
    monkeypatch.setattr(service, "resolve_workspace_access", AsyncMock())
    monkeypatch.setattr(service, "detail", AsyncMock(return_value=row))
    monkeypatch.setattr(
        service,
        "inspect",
        AsyncMock(
            side_effect=Conflict(
                "Tài liệu đã phát hành sau preview.",
                code="source_publication_in_use",
            )
        ),
    )
    prepare = AsyncMock()
    monkeypatch.setattr(purge, "prepare", prepare)
    with pytest.raises(Conflict) as caught:
        await service.accept(
            db,
            None,
            None,
            None,
            AuthActor(username="actor", actor_id="actor"),
            "w",
            AcceptRequest(preview_id="a", preview_sha256=row.preview_sha256),
            "same-key",
        )
    assert caught.value.code == "source_publication_in_use"
    prepare.assert_not_awaited()


@pytest.mark.asyncio
async def test_partial_storage_failure_keeps_intent_and_same_receipt_can_resume(monkeypatch):
    plan = {**graph_plan({}), "blob_target_hash": "storage", "vector_target_hash": "vector"}
    row = SimpleNamespace(
        id="a",
        workspace_id="w",
        actor_ref="actor",
        kind="source",
        resource_id="source",
        action="delete",
        status="pending",
        error_code=None,
        phase=None,
        progress={},
        worker_id=None,
        lease_expires_at=None,
        attempt_count=0,
        last_error_at=None,
        result={
            "permanent": True,
            "_purge_plan": plan,
            "not_before": (utcnow() - timedelta(seconds=1)).isoformat(),
        },
    )

    async def scalar(statement):
        # Apply fenced UPDATE values like the database would; the row itself is state.
        for column, value in (getattr(statement, "_values", None) or {}).items():
            setattr(row, column.key, getattr(value, "value", value))
        return row

    db = SimpleNamespace(
        get=AsyncMock(return_value=row),
        scalar=scalar,
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    monkeypatch.setattr(purge, "resolve_workspace_access", AsyncMock())
    monkeypatch.setattr(purge, "graph_for_source", AsyncMock(return_value={}))
    monkeypatch.setattr(purge, "_assert_exclusive_blobs", AsyncMock())
    monkeypatch.setattr(purge, "_delete_vectors", AsyncMock())
    files = AsyncMock(side_effect=[DependencyUnavailable("Storage offline"), None])
    monkeypatch.setattr(purge, "_delete_objects", files)
    records = AsyncMock()
    monkeypatch.setattr(purge, "delete_rows", records)
    monkeypatch.setattr(purge, "record_workspace_event", AsyncMock())
    blob, vectors = SimpleNamespace(target_hash="storage"), SimpleNamespace(target_hash="vector")
    assert await purge.execute(db, blob, vectors, "a") == "pending"
    records.assert_not_awaited()
    assert row.result["_purge_plan"] == plan
    assert await purge.execute(db, blob, vectors, "a") == "completed"
    records.assert_awaited_once()
    assert row.result["restore_available"] is False
    assert "_purge_plan" not in row.result


@pytest.mark.asyncio
async def test_purge_plan_never_deletes_a_key_outside_authorized_workspace():
    blob = SimpleNamespace(purge=AsyncMock(), exists=AsyncMock())
    with pytest.raises(Conflict) as caught:
        await purge._delete_objects(blob, {"objects": {"v1/workspaces/other/source": None}}, "w")
    assert caught.value.code == "purge_scope_invalid"
    blob.purge.assert_not_awaited()


def test_private_storage_plan_is_not_exposed_in_receipt_response():
    receipt = ActionResponse.model_construct(
        result={"permanent": True, "_purge_plan": {"objects": "private"}}
    )
    assert receipt.model_dump(include={"result"}) == {"result": {"permanent": True}}


def test_cancelled_call_can_retain_raw_within_approved_run_but_not_add_versions():
    original = {"kb_compilation_reviews": {("review",): {"id": "review"}}}
    plan = graph_plan(original)
    settled = {
        **original,
        "kb_compilation_review_artifacts": {
            ("raw",): {
                "id": "raw",
                "review_id": "review",
                "blob_key": "v1/workspaces/w/raw",
                "sha256": "sha",
            }
        },
    }
    assert "v1/workspaces/w/raw" in purge._settled_plan(plan, settled)["objects"]
    unexpected = {**settled, "kb_compiled_versions": {("version",): {"id": "version"}}}
    with pytest.raises(Conflict) as caught:
        purge._settled_plan(plan, unexpected)
    assert caught.value.code == "purge_dependency_changed"


@pytest.mark.parametrize(
    ("artifact_table", "parent_table"),
    [
        ("kb_compilation_segment_artifacts", "kb_compilation_segments"),
        ("kb_compilation_review_segment_artifacts", "kb_compilation_review_segments"),
    ],
)
def test_cancelled_segment_artifacts_stay_within_approved_parts(artifact_table, parent_table):
    parent = {parent_table: {("part",): {"id": "part"}}}
    plan = graph_plan(parent)
    raw = {
        "id": "raw",
        "segment_id": "part",
        "blob_key": "v1/workspaces/w/segments/raw",
        "sha256": "hash",
    }
    graph = {**parent, artifact_table: {("raw",): raw}}
    settled = purge._settled_plan(plan, graph)
    assert settled["objects"][raw["blob_key"]] == "hash"
    with pytest.raises(Conflict) as caught:
        purge._settled_plan(
            plan, {**parent, artifact_table: {("raw",): {**raw, "segment_id": "other"}}}
        )
    assert caught.value.code == "purge_scope_invalid"
    with pytest.raises(Conflict) as caught:
        purge._settled_plan(plan, {parent_table: {("new-part",): {"id": "new-part"}}})
    assert caught.value.code == "purge_dependency_changed"


def test_partial_output_pairs_are_purged_with_their_approved_compiler_run():
    parent = {"kb_compilation_runs": {("run",): {"id": "run"}}}
    plan = graph_plan(parent)
    output = {
        "id": "out",
        "run_id": "run",
        "draft_blob_key": "v1/workspaces/w/outputs/out/draft.json",
        "draft_sha256": "draft-hash",
        "markdown_blob_key": "v1/workspaces/w/outputs/out/markdown.md",
        "markdown_sha256": "markdown-hash",
    }
    graph = {**parent, "kb_compilation_outputs": {("out",): output}}
    settled = purge._settled_plan(plan, graph)
    assert settled["objects"] == {
        output["draft_blob_key"]: "draft-hash",
        output["markdown_blob_key"]: "markdown-hash",
    }
    with pytest.raises(Conflict) as caught:
        purge._settled_plan(
            plan, {**parent, "kb_compilation_outputs": {("out",): {**output, "run_id": "other"}}}
        )
    assert caught.value.code == "purge_scope_invalid"


@pytest.mark.asyncio
async def test_s3_purge_removes_versions_and_markers_only_for_exact_key():
    from qnu.adapters.storage.s3 import S3BlobStore

    store = object.__new__(S3BlobStore)
    store._bucket = "synthetic"
    store._client = Mock()
    store._client.get_paginator.return_value.paginate.return_value = [
        {
            "Versions": [
                {"Key": "source", "VersionId": "v1"},
                {"Key": "source-extra", "VersionId": "keep"},
            ],
            "DeleteMarkers": [{"Key": "source", "VersionId": "marker"}],
        }
    ]
    store._client.delete_objects.return_value = {}
    await store.purge("source")
    deleted = store._client.delete_objects.call_args.kwargs["Delete"]["Objects"]
    assert deleted == [
        {"Key": "source", "VersionId": "v1"},
        {"Key": "source", "VersionId": "marker"},
    ]
    store._client.get_paginator.return_value.paginate.return_value = [{}]
    await store.purge("source")
    store._client.delete_object.assert_not_called()
    assert store._client.delete_objects.call_count == 1


@pytest.mark.asyncio
async def test_worker_rechecks_actor_authority_before_any_delete(monkeypatch):
    row = SimpleNamespace(
        kind="source",
        action="delete",
        status="pending",
        workspace_id="w",
        actor_ref="actor",
        phase=None,
        progress={},
        worker_id=None,
        lease_expires_at=None,
        attempt_count=0,
        last_error_at=None,
        result={},
        error_code=None,
    )
    db = SimpleNamespace(
        get=AsyncMock(return_value=row),
        scalar=AsyncMock(return_value=row),
        rollback=AsyncMock(),
        commit=AsyncMock(),
    )
    monkeypatch.setattr(
        purge,
        "resolve_workspace_access",
        AsyncMock(side_effect=Conflict("Revoked", code="workspace_forbidden")),
    )
    objects, vectors = AsyncMock(), AsyncMock()
    monkeypatch.setattr(purge, "_delete_objects", objects)
    monkeypatch.setattr(purge, "_delete_vectors", vectors)
    assert await purge.execute(db, None, None, "a") == "pending"
    objects.assert_not_awaited()
    vectors.assert_not_awaited()


@pytest.mark.asyncio
async def test_remaining_index_gets_derived_manifest_without_reembedding(monkeypatch):
    import json

    from qnu.domains.knowledge.index import search

    run = SimpleNamespace(id="i", workspace_id="w", manifest_key="old", manifest_sha256="old-sha")
    action = SimpleNamespace(id="a", workspace_id="w", result={})
    old = {
        "inputs": [{"version_id": "removed"}, {"version_id": "kept"}],
        "chunks": [{"id": "removed-chunk"}, {"id": "kept-chunk"}],
        "config": {"sealed": True},
    }
    monkeypatch.setattr(search, "manifest", AsyncMock(return_value=old))
    db, blob = (
        SimpleNamespace(
            get=AsyncMock(return_value=action),
            scalar=AsyncMock(return_value=run),
            commit=AsyncMock(),
        ),
        SimpleNamespace(put_bytes=AsyncMock()),
    )
    graph = {
        "kb_index_inputs": {("input",): {"run_id": "i", "version_id": "removed"}},
        "kb_index_chunks": {("chunk",): {"run_id": "i", "id": "removed-chunk"}},
    }
    await purge._reseal_indexes(db, blob, graph, "a", "purge:test")
    written = json.loads(blob.put_bytes.call_args.args[1])
    assert written["inputs"] == [{"version_id": "kept"}]
    assert written["chunks"] == [{"id": "kept-chunk"}]
    assert written["purge"]["previous_manifest_sha256"] == "old-sha"
    assert run.chunks_total == 1
    assert old["chunks"] == [{"id": "removed-chunk"}, {"id": "kept-chunk"}]
