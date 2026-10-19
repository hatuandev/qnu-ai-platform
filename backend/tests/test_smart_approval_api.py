"""Source approval through real local Storage and an owned, rollback-isolated DB."""
import copy
import hashlib
import json
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest

import tests.test_semantic_lifecycle as lifecycle
from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.schemas import SmartApprovalRequest
from app.modules.knowledge.services.semantic_annotations import SemanticAnnotations
from app.modules.knowledge.services.semantic_context_review import proposal_summary
from app.modules.knowledge.services.semantic_store import STORE, identity, rebuild_projection
from app.modules.knowledge.services.smart_approval import _payload_hash
from app.modules.knowledge.services.smart_approval_service import smart_approve
from tests.test_semantic_scope_assertions import assertion

database = lifecycle.database


@pytest.fixture
def storage(tmp_path):
    with contextmanager(lifecycle.storage.__wrapped__)(tmp_path) as driver, patch(
            "app.modules.knowledge.services.smart_approval_service.storage_service", driver):
        yield driver


async def prepare_clear_revision(database, *, with_proposal=False):
    from app.modules.knowledge.services.qnu_docx_artifacts import save_qnu_document
    from app.modules.knowledge.services.qnu_serving import (
        prepare_standard_revision,
        verify_revision_pair,
    )

    async with database.factory() as db:
        revision = await db.get(KnowledgeSourceRevision, database.ids[2])
        doc = await verify_revision_pair(revision)
        from docx import Document
        binary_source = Document()
        binary_source.add_paragraph("Context558 independent synthetic approval fixture.")
        buffer = BytesIO()
        binary_source.save(buffer)
        source_bytes = buffer.getvalue()
        doc.source.sha256 = hashlib.sha256(source_bytes).hexdigest()
        revision.origin_file_hash = doc.source.sha256
        await database.storage.save(revision.snapshot_storage_path, source_bytes)
        for block in doc.blocks:
            if block.type == "table":
                for column in block.attributes["columns"]:
                    if column.get("temporal"):
                        column["temporal"]["basis_quote"] = " / ".join(column["header_path"])
            if block.type == "table_row":
                fields = block.attributes["fields"]
                for field in fields.values():
                    if field["state"] == "ambiguous":
                        field.update(raw="Recorded TEST status", state="present")
                columns = next(b for b in doc.blocks if b.id == block.parent_id).attributes["columns"]
                block.body = "\n\n".join(f"**{' / '.join(c['header_path'])}:** {fields[c['id']]['raw']}" for c in columns)
        reference = await save_qnu_document(doc, document_id=revision.binding_id, revision_id=revision.id,
            snapshot_path=revision.snapshot_storage_path)
        revision.snapshot_metadata, revision.parse_provenance = {"qnu_markdown": reference}, {}
        await prepare_standard_revision(revision)
        artifact = lifecycle.artifact_of(revision)
        if with_proposal:
            await lifecycle.stage(revision, SemanticAnnotations(notes=[
                assertion(artifact, "Only the 2026 column has this condition.", scope="column", columns=["c4"])]))
            artifact = lifecycle.artifact_of(revision)
        request = SmartApprovalRequest(expected_canonical_hash=revision.canonical_hash,
            expected_semantic_proposal_hash=(artifact.get("semantic_annotations") or {}).get("proposal_hash"),
            idempotency_key="TEST-idempotency-558")
        await db.commit()
        return request


async def allow_test_case(database, monkeypatch, tmp_path):
    from app.modules.knowledge.services import smart_approval

    async with database.factory() as db:
        revision = await db.get(KnowledgeSourceRevision, database.ids[2])
        proposal = lifecycle.artifact_of(revision)["semantic_annotations"]
        policy = {"policy_id": "synthetic-reviewed-acceptance-v1", "identity": identity(revision),
            "proposal_hash": proposal["proposal_hash"], "payload_sha256": _payload_hash(proposal), "cells": []}
    path = tmp_path / "synthetic-acceptance.json"
    path.write_text(json.dumps([policy]), encoding="utf-8")
    monkeypatch.setattr(smart_approval, "POLICY_FILE", path)


async def submit(database, request, actor=None):
    async with database.factory() as db:
        return await smart_approve(db, *database.ids, request, actor or lifecycle.actor())


async def test_one_click_approves_atomically_and_duplicate_is_idempotent(database):
    request = await prepare_clear_revision(database)
    result = await submit(database, request)
    assert result["approved"], result["blockers"]
    assert not result["idempotent"]
    again = await submit(database, request.model_copy(update={"idempotency_key": "second-click-same-intent"}))
    assert again["approved"] and again["idempotent"]
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        assert rev.status == "ready"
        assert (await db.get(KnowledgeBinding, database.ids[1])).active_source_revision_id == rev.id
        assert rev.parse_provenance["smart_approval"]["actor_id"] == lifecycle.actor().actor_id
        assert rev.parse_provenance["smart_approval"]["action"] == "bulk_acceptance_v1"
        assert STORE not in rev.parse_provenance


async def test_dry_run_and_unproven_scope_make_no_writes(database):
    request = await prepare_clear_revision(database, with_proposal=True)
    result = await submit(database, request)
    assert not result["approved"]
    assert any(b["reason_code"] == "SEMANTIC_SCOPE_NOT_PROVEN" for b in result["blockers"])
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        assert rev.status == "review_required" and STORE not in rev.parse_provenance
        assert "smart_approval" not in rev.parse_provenance
    request = await prepare_clear_revision(database)
    result = await submit(database, request.model_copy(update={"dry_run": True}))
    assert not result["approved"] and not result["blockers"]
    async with database.factory() as db:
        assert (await db.get(KnowledgeSourceRevision, database.ids[2])).status == "review_required"


async def test_fixture_bulk_certificate_rebuild_has_no_fabricated_human_issue_decisions(database, monkeypatch, tmp_path):
    request = await prepare_clear_revision(database, with_proposal=True)
    await allow_test_case(database, monkeypatch, tmp_path)
    result = await submit(database, request)
    assert result["approved"] and result["validation"]["auto_verified_count"] == 1
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        ref = rev.parse_provenance[STORE]["active"]
        snapshot = json.loads(await database.storage.get(ref["path"]))
        assert snapshot["semantic_hash_version"] == 3
        assert snapshot["review"]["action"] == "bulk_acceptance_v1"
        assert "context_decisions" not in snapshot["review"]
        _, restored = await rebuild_projection(rev)
        assert not proposal_summary(restored["semantic_annotations"])["publication_blocked"]
        assert restored["semantic_annotations"]["review"]["actor_id"] == lifecycle.actor().actor_id


@pytest.mark.parametrize("failure", ["storage", "commit"])
async def test_failure_rolls_back_source_and_semantic_pointer(database, monkeypatch, tmp_path, failure):
    request = await prepare_clear_revision(database, with_proposal=True)
    await allow_test_case(database, monkeypatch, tmp_path)
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        before = copy.deepcopy(rev.parse_provenance)
        target = patch("app.modules.knowledge.services.semantic_store.storage_service.save", AsyncMock(side_effect=OSError("TEST Storage failure"))) if failure == "storage" else patch.object(db, "commit", AsyncMock(side_effect=RuntimeError("TEST commit failure")))
        with target, pytest.raises((AppException, RuntimeError)):
            await smart_approve(db, *database.ids, request, lifecycle.actor())
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        assert rev.status == "review_required" and rev.parse_provenance == before
        assert (await db.get(KnowledgeBinding, database.ids[1])).active_source_revision_id is None


@pytest.mark.parametrize("change", ["canonical", "proposal", "actor", "collection", "binding", "revision"])
async def test_stale_wrong_identity_and_permission_do_not_approve(database, change):
    request = await prepare_clear_revision(database)
    args = list(database.ids)
    actor = lifecycle.actor()
    if change == "canonical": request = request.model_copy(update={"expected_canonical_hash": "0" * 64})
    if change == "proposal": request = request.model_copy(update={"expected_semantic_proposal_hash": "0" * 64})
    if change == "actor": actor = actor.model_copy(update={"permissions": [], "authenticated": False})
    if change in {"collection", "binding", "revision"}: args[["collection", "binding", "revision"].index(change)] = "wrong-TEST-identity"
    async with database.factory() as db:
        with pytest.raises(AppException):
            await smart_approve(db, *args, request, actor)
    async with database.factory() as db:
        assert (await db.get(KnowledgeSourceRevision, database.ids[2])).status == "review_required"


async def test_authenticated_endpoint_one_request_and_viewer_denied(database):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.core.exceptions import register_exception_handlers
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.knowledge.router import router

    request = await prepare_clear_revision(database)
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    actor = lifecycle.actor().model_copy(update={"permissions": ["ai.knowledge.view"]})
    app.dependency_overrides[get_current_actor] = lambda: actor
    async def get_test_db():
        async with database.factory() as db:
            yield db
    app.dependency_overrides[get_db] = get_test_db
    path = next(p for p in app.openapi()["paths"] if p.endswith("/smart-approval"))
    for key, value in zip(["collection_id", "source_id", "revision_id"], database.ids, strict=True):
        path = path.replace("{" + key + "}", value)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post(path, json=request.model_dump())).status_code == 403
        actor = lifecycle.actor()
        response = await client.post(path, json=request.model_dump())
        assert response.status_code == 200, response.text
        assert response.json()["approved"] is True
        assert (await client.post(path, json={**request.model_dump(), "actor_id": "forged"})).status_code == 422


@pytest.mark.parametrize("failure", ["missing-table", "integrity", "cached-cell", "pair-checksum"])
async def test_important_content_failures_are_never_downgraded(database, failure):
    request = await prepare_clear_revision(database)
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        if failure == "missing-table":
            rev.quality_report = {"overall_status": "passed", "warning_flags": ["tables_detected_but_missing_in_markdown"]}
        elif failure == "integrity":
            rev.parse_provenance = {**rev.parse_provenance, "structured_artifact": {
                **lifecycle.artifact_of(rev), "content_integrity": {"status": "failed"}}}
        elif failure == "cached-cell":
            artifact = copy.deepcopy(lifecycle.artifact_of(rev))
            artifact["tables"][0]["row_fields"][0][0]["raw"] = "forged"
            rev.parse_provenance = {**rev.parse_provenance, "structured_artifact": artifact}
        else:
            rev.snapshot_metadata = {**rev.snapshot_metadata, "qnu_markdown": {**rev.snapshot_metadata["qnu_markdown"], "structured_sha256": "0" * 64}}
        await db.commit()
    if failure in {"cached-cell", "pair-checksum"}:
        with pytest.raises(AppException):
            await submit(database, request)
    else:
        result = await submit(database, request)
        assert not result["approved"] and result["blockers"]


async def test_real_two_connection_concurrent_duplicate_has_one_committed_decision(storage):
    import asyncio
    from types import SimpleNamespace
    from uuid import uuid4

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.config import settings
    from app.modules.knowledge.models import KnowledgeCollection

    assert "qnu_test_context548_" in settings.DATABASE_URL
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = None
    try:
        async with factory() as db:
            collection = KnowledgeCollection(name="Context558 concurrent TEST", module_code="test558_" + uuid4().hex)
            db.add(collection)
            await db.flush()
            binding = KnowledgeBinding(collection_id=collection.id, status="pending")
            db.add(binding)
            await db.flush()
            revision = await lifecycle.make_pair(binding.id, collection.id)
            db.add(revision)
            await db.commit()
            ids = collection.id, binding.id, revision.id
        owned = SimpleNamespace(factory=factory, ids=ids, storage=storage)
        request = await prepare_clear_revision(owned)
        results = await asyncio.gather(submit(owned, request), submit(owned, request))
        assert all(r["approved"] for r in results)
        assert sum(r["idempotent"] for r in results) == 1
        async with factory() as db:
            revision = await db.get(KnowledgeSourceRevision, ids[2])
            binding = await db.get(KnowledgeBinding, ids[1])
            assert revision.parse_provenance["smart_approval"]["transaction_result"] == "committed"
            assert binding.active_source_revision_id == ids[2] and binding.active_index_revision_id is None
            assert STORE not in revision.parse_provenance
    finally:
        if ids:
            async with factory() as db:
                binding = await db.get(KnowledgeBinding, ids[1])
                binding.active_source_revision_id = None
                await db.flush()
                await db.execute(delete(KnowledgeSourceRevision).where(KnowledgeSourceRevision.id == ids[2]))
                await db.execute(delete(KnowledgeBinding).where(KnowledgeBinding.id == ids[1]))
                await db.execute(delete(KnowledgeCollection).where(KnowledgeCollection.id == ids[0]))
                await db.commit()
        await engine.dispose()
