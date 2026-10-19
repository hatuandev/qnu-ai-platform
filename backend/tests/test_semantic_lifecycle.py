"""Real pair/Storage lifecycle and transaction-isolated DB; proposals are TEST DATA."""

import copy
import hashlib
import io
import json
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import tests.test_semantic_proposals as f
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.storage import LocalStorageDriver
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
from app.modules.knowledge.normalization.structure_chunks import structure_chunks
from app.modules.knowledge.schemas import SemanticProposalReviewRequest
from app.modules.knowledge.services.qnu_docx_artifacts import save_qnu_document
from app.modules.knowledge.services.qnu_serving import prepare_standard_revision
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    apply_reviewed_semantics,
    review_semantic_proposals,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_bundle import (
    download_revision_bundle,
    export_revision_bundle,
    read_external_bundle,
    restore_internal_bundle,
)
from app.modules.knowledge.services.semantic_store import (
    STORE,
    backfill_verified_semantics,
    proposal_base,
    rebuild_projection,
    record_decision,
    semantic_fingerprint,
    verify_effective_projection,
)
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
from app.modules.knowledge.services.source_links import unit_context_ids


async def make_pair(binding="binding545", collection="collection545"):
    document = f.fixture.fixture_document()
    document.blocks[-1].body = "Only the 2026 column has this condition."
    next(b for b in document.blocks if b.id == "r1").attributes["fields"]["c7"].update(raw="Not published yet", state="present")
    next(b for b in document.blocks if b.id == "r2").attributes["fields"]["c7"].update(raw="/", state="ambiguous")
    columns = next(b for b in document.blocks if b.id == "t").attributes["columns"]
    for block in document.blocks:
        if block.type == "table_row":
            block.attributes.pop("field_origins", None)  # Older unit fixture used an intentionally nonstandard origin.
            block.body = "\n\n".join(f"**{' / '.join(column['header_path'])}:** "
                + (block.attributes["fields"][column["id"]]["raw"] or "[Ô trống trong nguồn]") for column in columns)
    rev = KnowledgeSourceRevision(id=f"ks_rev_{uuid4().hex[:12]}", binding_id=binding, revision_no=1,
        origin_document_id="fixture545", origin_file_hash=document.source.sha256,
        snapshot_storage_path=f"snapshots/{collection}/{binding}/source.docx", snapshot_metadata={},
        parse_provenance={}, citation_metadata={}, page_manifest=[], quality_report={}, status="review_required")
    reference = await save_qnu_document(document, document_id=binding, revision_id=rev.id, snapshot_path=rev.snapshot_storage_path)
    assert reference["status"] == "ready"
    rev.snapshot_metadata = {"qnu_markdown": reference}
    await prepare_standard_revision(rev)
    return rev


@pytest.fixture
def storage(tmp_path):
    driver = LocalStorageDriver(str(tmp_path / "objects"))
    with ExitStack() as stack:
        for module in ("qnu_docx_artifacts", "qnu_serving", "semantic_store", "semantic_bundle"):
            stack.enter_context(patch(f"app.modules.knowledge.services.{module}.storage_service", driver))
        yield driver


@pytest.fixture
async def pair(storage):
    return await make_pair()


def artifact_of(rev):
    return rev.parse_provenance["structured_artifact"]


def payload(artifact, column="c4"):
    table = artifact["tables"][0]
    row = table["row_unit_ids"][0]
    return SemanticAnnotations(notes=[{"note_unit_id": "qnu:g", "table_id": table["id"], "scope": "column",
        "column_ids": [column], "evidence_quote": "Only the 2026 column has this condition."}],
        cells=[{"row_unit_id": row, "column_id": "c7", "raw": "Not published yet", "state": "not_stated",
                "evidence_unit_id": row, "evidence_quote": "Not published yet"}])


async def stage(rev, proposal=None):
    artifact = copy.deepcopy(artifact_of(rev))
    base = await proposal_base(rev, artifact)
    pending = stage_semantic_annotations(artifact, proposal or payload(base), base_artifact=base)
    rev.parse_provenance = {**rev.parse_provenance, "structured_artifact": artifact}
    return pending


async def approve(rev):
    pending = await stage(rev)
    return await record_decision(rev, artifact_of(rev), pending["proposal_hash"], "reviewer545", "Checked TEST source", "approved")


@pytest.mark.asyncio
async def test_T01_pending_keeps_effective_graph_fields_facts(pair):
    await approve(pair)
    before = copy.deepcopy(artifact_of(pair))
    store = copy.deepcopy(pair.parse_provenance[STORE])
    await stage(pair)
    assert pair.parse_provenance[STORE] == store
    assert all(artifact_of(pair)[key] == before[key] for key in ("tables", "context_graph", "facts", "semantic_effective"))


@pytest.mark.asyncio
async def test_T03_T04_T05_T07_T13_rebuild_three_times_keeps_scope_state_unknown_and_consumer(pair):
    approved = await approve(pair)
    for _ in range(3):
        canonical, restored = await rebuild_projection(pair)
        assert semantic_fingerprint(restored) == semantic_fingerprint(approved)
        manifest = resolve_unit_manifest(canonical, restored)
        table = restored["tables"][0]
        row = table["row_unit_ids"][0]
        assert "qnu:g" in unit_context_ids(manifest, row, "c4")
        assert "qnu:g" not in unit_context_ids(manifest, row, "c3")
        assert (table["row_fields"][0][6]["raw"], table["row_fields"][0][6]["state"]) == ("Not published yet", "not_stated")
        assert (table["row_fields"][1][6]["raw"], table["row_fields"][1][6]["state"]) == ("/", "ambiguous")
        assert not any(fact["raw_data"]["column_id"] == "c7" and fact["raw_data"]["source_unit_id"] == row for fact in restored["facts"])
        chunks = structure_chunks(canonical, manifest, context_graph=restored["context_graph"])
        chunk = next(c for c in chunks if c["metadata"]["source_unit_id"] == row)
        assert "Only the 2026 column" in chunk["content"]
        assert chunk["metadata"]["source_unit"]["field_context_refs"] == {"c4": ["qnu:g"]}
        assert chunk["metadata"]["semantic_annotation_hash"] == restored["semantic_effective"]["semantic_hash"]
        assert len({fact["id"] for fact in restored["facts"]}) == len(restored["facts"])
    await prepare_standard_revision(pair)
    assert semantic_fingerprint(artifact_of(pair)) == semantic_fingerprint(approved)
    with pytest.raises(AppException) as error:
        source_ingestion_service._apply_review_decision(SimpleNamespace(active_source_revision_id=None), pair,
            artifact_of(pair), "approved", "Checked TEST source", "reviewer")
    assert error.value.code == "QNU_UNRESOLVED_CELLS"


@pytest.mark.asyncio
async def test_T06_export_persist_read_new_driver_external_untrusted_internal_restores(pair, storage, record_property):
    await approve(pair)
    exported = await export_revision_bundle(pair)
    await storage.save("export/bundle.zip", exported)
    data = await LocalStorageDriver(str(storage.base_path)).get("export/bundle.zip")
    external = await read_external_bundle(data)
    assert external["trusted"] is False and external["review_required"] is True
    assert external["candidate"]["notes"][0]["column_ids"] == ["c4"]
    canonical, restored = await restore_internal_bundle(data, pair)
    assert canonical == pair.canonical_markdown and restored["facts"] == artifact_of(pair)["facts"]
    assert semantic_fingerprint(restored) == semantic_fingerprint(artifact_of(pair))
    assert (await export_revision_bundle(pair)) == exported
    manifest = resolve_unit_manifest(canonical, restored)
    row = restored["tables"][0]["row_unit_ids"][0]
    chunks = structure_chunks(canonical, manifest, context_graph=restored["context_graph"])
    chunk = next(c for c in chunks if c["metadata"]["source_unit_id"] == row)
    report = {"scope": "deterministic TEST proposal, real LocalStorage, no ModelOps or publication",
        "source_identity": external["manifest"]["identity"], "effective": restored["semantic_effective"],
        "snapshot": pair.parse_provenance[STORE]["active"],
        "proposal_and_review": json.loads(await storage.get(pair.parse_provenance[STORE]["active"]["path"])),
        "before_fingerprint": semantic_fingerprint(artifact_of(pair)), "after_fingerprint": semantic_fingerprint(restored),
        "c3_context": unit_context_ids(manifest, row, "c3"), "c4_context": unit_context_ids(manifest, row, "c4"),
        "restored_cell": restored["tables"][0]["row_fields"][0][6],
        "facts_equal": restored["facts"] == artifact_of(pair)["facts"], "chunk": chunk,
        "external_trusted": external["trusted"]}
    await storage.save("evidence/roundtrip-report.json", (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
    record_property("roundtrip_report", str(storage.base_path / "evidence/roundtrip-report.json"))


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["origin", "revision", "binding", "hash", "missing", "path", "projection"])
async def test_T08_T09_T12_mismatch_is_error_not_unannotated_success(pair, storage, change):
    await approve(pair)
    ref = pair.parse_provenance[STORE]["active"]
    if change == "origin":
        pair.origin_file_hash = "f" * 64
    elif change == "revision":
        pair.id += "changed"
    elif change == "binding":
        pair.binding_id = "other"
    elif change == "hash":
        await storage.save(ref["path"], b"tampered")
    elif change == "missing":
        await storage.delete(ref["path"])
    elif change == "path":
        pair.parse_provenance[STORE]["active"]["path"] = "outside/snapshot.json"
    else:
        artifact_of(pair)["tables"][0]["row_fields"][0][6]["state"] = "present"
    with pytest.raises(AppException):
        await verify_effective_projection(pair, artifact_of(pair))


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["source.qnu-doc-v1.json", "source.qnu-semantic-v1.json", "manifest.json"])
async def test_T09_export_tampering_never_self_approves(pair, target):
    await approve(pair)
    with ZipFile(io.BytesIO(await export_revision_bundle(pair))) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    if target == "manifest.json":
        value = json.loads(members[target]); value["identity"]["binding_id"] = "another"
        members[target] = json.dumps(value).encode()
    else:
        members[target] += b"tamper"
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    with pytest.raises(AppException):
        await restore_internal_bundle(stream.getvalue(), pair)


@pytest.mark.asyncio
async def test_T10_replacement_removes_old_scope_rejection_keeps_effective_set(pair):
    await approve(pair)
    first = copy.deepcopy(pair.parse_provenance[STORE]["active"])
    old_hash = artifact_of(pair)["semantic_effective"]["semantic_hash"]
    pending = await stage(pair, payload(await proposal_base(pair, artifact_of(pair)), "c3"))
    await record_decision(pair, artifact_of(pair), pending["proposal_hash"], "reviewer", "Replacement TEST DATA", "approved")
    _, restored = await rebuild_projection(pair)
    row = restored["tables"][0]["row_unit_ids"][0]
    manifest = resolve_unit_manifest(pair.canonical_markdown, restored)
    assert "qnu:g" in unit_context_ids(manifest, row, "c3") and "qnu:g" not in unit_context_ids(manifest, row, "c4")
    assert old_hash != restored["semantic_effective"]["semantic_hash"]
    assert first in pair.parse_provenance[STORE]["history"]
    active = copy.deepcopy(pair.parse_provenance[STORE]["active"])
    pending = await stage(pair)
    await record_decision(pair, artifact_of(pair), pending["proposal_hash"], "reviewer", "Reject TEST proposal", "rejected")
    assert pair.parse_provenance[STORE]["active"] == active and len(pair.parse_provenance[STORE]["history"]) == 3
    assert semantic_fingerprint((await rebuild_projection(pair))[1]) == semantic_fingerprint(restored)


@pytest.mark.asyncio
async def test_T11_storage_failure_and_stale_review_preserve_prior_set(pair):
    await approve(pair)
    pending = await stage(pair)
    before = copy.deepcopy(pair.parse_provenance)
    with patch("app.modules.knowledge.services.semantic_store.storage_service.save", AsyncMock(side_effect=OSError("TEST unavailable"))), pytest.raises(AppException) as unavailable:
        await record_decision(pair, artifact_of(pair), pending["proposal_hash"], "reviewer", "Checked TEST source", "approved")
    assert pair.parse_provenance == before
    assert unavailable.value.code == "SEMANTIC_STORAGE_UNAVAILABLE"
    with pytest.raises(AppException) as error:
        await record_decision(pair, artifact_of(pair), "0" * 64, "reviewer", "Checked TEST source", "approved")
    assert error.value.code == "SEMANTIC_REVIEW_REQUIRED" and pair.parse_provenance == before


@pytest.mark.asyncio
async def test_T12_legacy_absent_verified_and_invalid_are_distinct(pair):
    assert not (await rebuild_projection(pair))[1].get("semantic_effective")
    pending = await stage(pair)
    verified = apply_reviewed_semantics(artifact_of(pair), pending["proposal_hash"], "reviewer", "Checked TEST source")
    pair.parse_provenance["structured_artifact"] = verified
    assert semantic_fingerprint((await rebuild_projection(pair))[1]) == semantic_fingerprint(verified)
    await prepare_standard_revision(pair)
    assert semantic_fingerprint(artifact_of(pair)) == semantic_fingerprint(verified)
    artifact_of(pair)["semantic_annotations"]["input_hash"] = "0" * 64
    with pytest.raises(AppException) as error:
        await rebuild_projection(pair)
    assert error.value.code == "SEMANTIC_LEGACY_REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_legacy_backfill_preserves_original_review_and_snapshot_enables_export(pair):
    pending = await stage(pair)
    verified = apply_reviewed_semantics(artifact_of(pair), pending["proposal_hash"], "original-reviewer", "Checked TEST source")
    review = copy.deepcopy(verified["semantic_annotations"]["review"])
    pair.parse_provenance["structured_artifact"] = verified
    migrated = await backfill_verified_semantics(pair)
    assert migrated["semantic_annotations"]["review"] == review
    assert pair.parse_provenance[STORE]["active"]
    assert semantic_fingerprint((await rebuild_projection(pair))[1]) == semantic_fingerprint(migrated)
    assert (await read_external_bundle(await export_revision_bundle(pair)))["trusted"] is False


@pytest.mark.asyncio
async def test_corrupt_storage_readback_is_not_committed_as_active(pair):
    pending = await stage(pair)
    before = copy.deepcopy(pair.parse_provenance)
    # Source pair reads remain real; only the new sidecar is corrupted at the I/O boundary.
    from app.modules.knowledge.services import semantic_store

    original = semantic_store.storage_service.get
    async def corrupt(path):
        return b"corrupt" if path.endswith(".qnu-semantic-v1.json") else await original(path)
    with patch.object(semantic_store.storage_service, "get", side_effect=corrupt), pytest.raises(AppException):
        await record_decision(pair, artifact_of(pair), pending["proposal_hash"], "reviewer", "Checked TEST source", "approved")
    assert pair.parse_provenance == before


@pytest.mark.asyncio
async def test_same_raw_text_different_scope_invalidates_derived_bundle_and_chunks(pair):
    from app.modules.knowledge.services.derived_bundle import source_fingerprint

    await approve(pair)
    first = source_fingerprint(pair, artifact_of(pair))
    raw_hash = pair.canonical_hash
    pending = await stage(pair, payload(await proposal_base(pair, artifact_of(pair)), "c3"))
    await record_decision(pair, artifact_of(pair), pending["proposal_hash"], "reviewer", "Checked new TEST scope", "approved")
    second = source_fingerprint(pair, artifact_of(pair))
    assert first["semantic_annotation_hash"] != second["semantic_annotation_hash"]
    assert first["unit_manifest_hash"] != second["unit_manifest_hash"]
    assert first["context_graph_hash"] != second["context_graph_hash"]
    assert first["fact_set_hash"] != second["fact_set_hash"]
    assert pair.canonical_hash == raw_hash


@pytest.mark.asyncio
async def test_enrichment_pinned_before_correction_no_model_during_restore(pair):
    from app.modules.knowledge.normalization.retrieval_models import UnitManifest
    from app.modules.knowledge.normalization.retrieval_units import manifest_digest

    artifact = artifact_of(pair)
    unit = next(u for u in artifact["retrieval_units"]["units"] if u["id"] == "qnu:g")
    unit["temporal"].update(role="data", data_years=[2026], status="proposed", evidence_quote="2026")
    artifact["unit_manifest_hash"] = manifest_digest(UnitManifest.model_validate(artifact["retrieval_units"]))
    artifact["unit_annotation"] = {"status": "proposed", "unit_ids": ["qnu:g"]}
    pending = await stage(pair)
    await record_decision(pair, artifact_of(pair), pending["proposal_hash"], "reviewer", "Checked TEST source", "approved")
    with patch("app.modules.knowledge.services.unit_annotation.enrich_source_units", AsyncMock(side_effect=AssertionError("No model"))):
        await prepare_standard_revision(pair)
    assert next(u for u in resolve_unit_manifest(pair.canonical_markdown, artifact_of(pair)).units if u.id == "qnu:g").temporal.data_years == [2026]


@pytest.mark.asyncio
async def test_pending_rebuild_retains_original_proposal_without_model_or_effect(pair):
    pending = await stage(pair)
    fingerprint = semantic_fingerprint(artifact_of(pair))
    with patch("app.modules.knowledge.services.unit_annotation.enrich_source_units", AsyncMock(side_effect=AssertionError("Do not regenerate pending proposal"))):
        await prepare_standard_revision(pair)
    assert artifact_of(pair)["semantic_annotations"] == pending
    assert semantic_fingerprint(artifact_of(pair)) == fingerprint
    assert STORE not in pair.parse_provenance


@pytest.fixture
async def database(storage):
    """Existing test isolation: NEW fixture rows only, no DDL, outer rollback of all commits."""
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        outer = await connection.begin()
        factory = async_sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        async with factory() as db:
            collection = KnowledgeCollection(name="Semantic lifecycle TEST ONLY", module_code=f"test545_{uuid4().hex[:12]}")
            db.add(collection); await db.flush()
            binding = KnowledgeBinding(collection_id=collection.id, status="pending")
            db.add(binding); await db.flush()
            revision = await make_pair(binding.id, collection.id)
            db.add(revision); await db.commit()
            ids = collection.id, binding.id, revision.id
        try:
            yield SimpleNamespace(factory=factory, ids=ids, storage=storage)
        finally:
            await outer.rollback()
    await engine.dispose()


def actor():
    return AuthActor(username="fixture545", actor_id="reviewer545", permissions=["ai.knowledge.update", "ai.knowledge.view"])


@pytest.mark.asyncio
async def test_T02_real_db_review_close_session_reload_and_real_storage(database):
    col, binding, rev_id = database.ids
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rev_id)
        pending = await stage(rev); await db.commit()
        await review_semantic_proposals(db, col, binding, rev_id, SemanticProposalReviewRequest(decision="approved",
            expected_semantic_proposal_hash=pending["proposal_hash"], comment="Checked TEST source"), actor())
        reference, fingerprint = copy.deepcopy(rev.parse_provenance[STORE]["active"]), semantic_fingerprint(artifact_of(rev))
    async with database.factory() as db:
        loaded = await db.get(KnowledgeSourceRevision, rev_id)
        assert loaded.parse_provenance[STORE]["active"] == reference
        snapshot = json.loads(await database.storage.get(reference["path"]))
        assert snapshot["identity"]["revision_id"] == rev_id and snapshot["proposal"]["proposal_hash"] == pending["proposal_hash"]
        assert snapshot["review"]["actor_id"] == "reviewer545" and snapshot["review"]["decision"] == "approved"
        assert semantic_fingerprint((await rebuild_projection(loaded))[1]) == fingerprint
        assert loaded.status == "review_required" and (await db.get(KnowledgeBinding, binding)).active_source_revision_id is None


@pytest.mark.asyncio
async def test_T09_wrong_collection_binding_and_second_stale_reviewer_rejected(database):
    col, binding, rev_id = database.ids
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rev_id)
        pending = await stage(rev); await db.commit()
        request = SemanticProposalReviewRequest(decision="approved", expected_semantic_proposal_hash=pending["proposal_hash"], comment="Checked TEST source")
        with pytest.raises(AppException):
            await review_semantic_proposals(db, "wrong-collection", binding, rev_id, request, actor())
        await db.rollback()
        with pytest.raises(AppException):
            await download_revision_bundle(db, col, "wrong-binding", rev_id, actor())
        await db.rollback()
    async with database.factory() as first:
        await review_semantic_proposals(first, col, binding, rev_id, request, actor())
    async with database.factory() as second:
        with pytest.raises(AppException) as error:
            await review_semantic_proposals(second, col, binding, rev_id, request, actor())
        assert error.value.code == "SEMANTIC_PROPOSAL_NOT_PENDING"


@pytest.mark.asyncio
async def test_T11_commit_failure_preserves_old_effective_pointer_in_db(database):
    col, binding, rev_id = database.ids
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rev_id)
        await approve(rev)
        pending = await stage(rev); await db.commit()
        previous = copy.deepcopy(rev.parse_provenance[STORE])
        with patch.object(db, "commit", AsyncMock(side_effect=RuntimeError("TEST commit failure"))), pytest.raises(RuntimeError):
            await review_semantic_proposals(db, col, binding, rev_id, SemanticProposalReviewRequest(decision="approved",
                expected_semantic_proposal_hash=pending["proposal_hash"], comment="Checked TEST replacement"), actor())
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rev_id)
        assert rev.parse_provenance[STORE] == previous and artifact_of(rev)["semantic_annotations"]["status"] == "proposed"


@pytest.mark.asyncio
async def test_T11_competing_review_calls_have_one_winner_with_serialized_db_lock(database):
    """Competing service calls, simulated lock scheduling + real PostgreSQL queries.

    The outer rollback fixture shares one connection, so the DB boundary
    serializes lock ownership; this is not a two-connection PostgreSQL stress test.
    """
    import asyncio

    col, binding, rev_id = database.ids
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rev_id)
        pending = await stage(rev)
        await db.commit()
    request = SemanticProposalReviewRequest(decision="approved", expected_semantic_proposal_hash=pending["proposal_hash"], comment="Checked TEST race")
    lock = asyncio.Lock()
    async def submit():
        async with database.factory() as db:
            class Boundary:
                owned = False
                async def execute(self, statement):
                    if getattr(statement, "_for_update_arg", None) is not None and not self.owned:
                        await lock.acquire()
                        self.owned = True
                    return await db.execute(statement)
                async def commit(self):
                    await db.commit()
                async def rollback(self):
                    await db.rollback()
                async def refresh(self, value):
                    await db.refresh(value)
            boundary = Boundary()
            try:
                return await review_semantic_proposals(boundary, col, binding, rev_id, request, actor())
            finally:
                await db.rollback()
                if boundary.owned:
                    lock.release()
    results = await asyncio.gather(submit(), submit(), return_exceptions=True)
    assert sum(isinstance(value, KnowledgeSourceRevision) for value in results) == 1
    errors = [value for value in results if isinstance(value, AppException)]
    assert len(errors) == 1 and errors[0].code == "SEMANTIC_PROPOSAL_NOT_PENDING"
    async with database.factory() as db:
        stored = await db.get(KnowledgeSourceRevision, rev_id)
        assert len(stored.parse_provenance[STORE]["history"]) == 1


@pytest.mark.asyncio
async def test_api_bundle_export_and_review_permissions_use_real_services(database):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.core.exceptions import register_exception_handlers
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.knowledge.router import router

    col, binding, rev_id = database.ids
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    current_actor = actor()
    app.dependency_overrides[get_current_actor] = lambda: current_actor
    async def get_test_db():
        async with database.factory() as db:
            yield db
    app.dependency_overrides[get_db] = get_test_db
    # Router may be included with a module prefix; use the observed path.
    path = next(path for path in app.openapi()["paths"] if path.endswith("/semantic-review")).replace(
        "{collection_id}", col).replace("{source_id}", binding).replace("{revision_id}", rev_id).removesuffix("/semantic-review")
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rev_id)
        pending = await stage(rev); await db.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        current_actor = AuthActor(username="viewer", actor_id="viewer", permissions=["ai.knowledge.view"])
        body = {"decision": "approved", "expected_semantic_proposal_hash": pending["proposal_hash"], "comment": "Checked TEST source"}
        forbidden = await client.post(path + "/semantic-review", json=body)
        assert forbidden.status_code == 403
        current_actor = actor()
        response = await client.post(path + "/semantic-review", json=body)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "review_required"
        exported = await client.get(path + "/qnu-markdown?format=bundle")
        assert exported.status_code == 200 and exported.headers["content-type"] == "application/zip"
        assert (await read_external_bundle(exported.content))["trusted"] is False
        current_actor = AuthActor(username="nobody", actor_id="nobody", permissions=[])
        assert (await client.get(path + "/qnu-markdown?format=bundle")).status_code == 403


@pytest.mark.asyncio
async def test_new_content_revision_does_not_inherit_approval(database):
    from app.modules.knowledge.normalization.qnu_markdown import render_qnu_markdown
    from app.modules.knowledge.services.qnu_revision import update_standard_revision
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair

    _, binding_id, rev_id = database.ids
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rev_id)
        await approve(rev); await db.commit()
        old = copy.deepcopy(rev.parse_provenance[STORE])
        document = await verify_revision_pair(rev)
        markdown = render_qnu_markdown(document, document_id=binding_id, revision_id=rev_id)
        updated = await update_standard_revision(db, await db.get(KnowledgeBinding, binding_id), rev,
            markdown.replace("Only the 2026 column", "Only the revised column"), actor_id="reviewer",
            reason="TEST content edit", expected_hash=rev.canonical_hash)
        assert updated.id != rev_id and STORE not in updated.parse_provenance
        assert updated.parse_provenance["semantic_review_required_from_revision"] == rev_id
        assert updated.status == "review_required" and not artifact_of(updated).get("semantic_effective")
        assert rev.parse_provenance[STORE] == old


@pytest.mark.asyncio
async def test_T14_actual_docx_pair_sidecar_scope_roundtrip(storage, record_property):
    from app.modules.knowledge.parsers.docling_office_parser import DoclingOfficeParser
    from app.modules.knowledge.parsers.docling_structure import build_qnu_structured_document
    from app.modules.knowledge.services.qnu_docx_artifacts import build_qnu_markdown_artifact
    from app.modules.knowledge.services.source_extraction import SourceExtraction

    path = Path(__file__).resolve().parents[2] / "docs/tai_lieu/tuyen_sinh/tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx"
    if not path.is_file():
        pytest.skip("NOT RUN: actual DOCX fixture missing")
    raw = path.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    record_property("fixture_sha256", checksum)
    assert checksum == "58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274"
    parsed = await DoclingOfficeParser("docx").parse(raw, path.name)
    document = build_qnu_structured_document(parsed.docling_document, filename=path.name, sha256=checksum,
        header_evidence=parsed.docx_header_evidence, source_evidence=parsed.docx_source_evidence)
    rev = KnowledgeSourceRevision(id="actual545", binding_id="actual-binding545", revision_no=1,
        origin_document_id="actual545", origin_file_hash=checksum, snapshot_storage_path="snapshots/actual545/source.docx",
        snapshot_metadata={}, parse_provenance={}, citation_metadata={}, quality_report={}, page_manifest=[], status="review_required")
    reference = await build_qnu_markdown_artifact(extraction=SourceExtraction(parsed.raw_text, 0,
        qnu_document=document, office_resources=parsed.docx_source_evidence["resources"]), document_id=rev.binding_id,
        revision_id=rev.id, title=None, snapshot_path=rev.snapshot_storage_path)
    assert reference["status"] == "ready", reference
    rev.snapshot_metadata = {"qnu_markdown": reference}
    await prepare_standard_revision(rev)
    artifact = artifact_of(rev)
    assert len(artifact["tables"]) == 10 and len(artifact["tables"][1]["rows"]) == 49
    manifest = resolve_unit_manifest(rev.canonical_markdown, artifact)
    column_note = next(u for u in manifest.units if u.kind == "paragraph" and "(C-2027)" in u.text)
    row_note = next(u for u in manifest.units if u.kind == "paragraph" and "(D-AM-0007)" in u.text)
    table = artifact["tables"][0]
    target_row = next(rid for rid, row in zip(table["row_unit_ids"], table["rows"], strict=True) if "AM-0007" in row)
    year_columns = [c["id"] for c in table["columns"] if any("2027" in p for p in c["header_path"])]
    assert len(year_columns) == 3
    notes = [{"note_unit_id": column_note.id, "evidence_quote": column_note.text, "table_id": table["id"], "scope": "column", "column_ids": year_columns},
             {"note_unit_id": row_note.id, "evidence_quote": row_note.text, "table_id": table["id"], "scope": "row", "row_unit_ids": [target_row]}]
    pending = await stage(rev, SemanticAnnotations(notes=notes))
    await record_decision(rev, artifact_of(rev), pending["proposal_hash"], "fixture-reviewer", "Deterministic TEST annotations only", "approved")
    canonical, restored = await restore_internal_bundle(await export_revision_bundle(rev), rev)
    rebuilt = resolve_unit_manifest(canonical, restored)
    for c in table["columns"]:
        assert (column_note.id in unit_context_ids(rebuilt, target_row, c["id"])) == (c["id"] in year_columns)
    other_row = next(rid for rid in table["row_unit_ids"] if rid != target_row)
    assert row_note.id not in unit_context_ids(rebuilt, other_row)


@pytest.mark.asyncio
async def test_duplicate_note_text_keeps_independent_table_identity_after_roundtrip(pair):
    from app.modules.knowledge.normalization.qnu_markdown import QnuBlock, QnuSourceLocation
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair

    document = await verify_revision_pair(pair)
    other_table = next(b for b in document.blocks if b.id == "t").model_copy(deep=True)
    other_table.id, other_table.context_refs = "second", []
    other_row = next(b for b in document.blocks if b.id == "r1").model_copy(deep=True)
    other_row.id, other_row.parent_id = "secondrow", "second"
    document.blocks.extend([other_table, other_row])
    for suffix in ("A", "B"):
        document.blocks.append(QnuBlock(id=f"duplicate{suffix}", type="text", body="Same TEST condition, independent source occurrence.",
            source_locations=[QnuSourceLocation(locator=f"test/duplicate/{suffix}")]))
    pair.id = "synthetic-duplicate545"
    reference = await save_qnu_document(document, document_id=pair.binding_id, revision_id=pair.id, snapshot_path=pair.snapshot_storage_path)
    assert reference["status"] == "ready"
    pair.snapshot_metadata, pair.parse_provenance = {"qnu_markdown": reference}, {}
    await prepare_standard_revision(pair)
    notes = [{"note_unit_id": f"qnu:duplicate{suffix}", "table_id": artifact_of(pair)["tables"][index]["id"],
              "scope": "table", "evidence_quote": "Same TEST condition, independent source occurrence."} for index, suffix in ((0, "A"), (1, "B"))]
    pending = await stage(pair, SemanticAnnotations(notes=notes))
    await record_decision(pair, artifact_of(pair), pending["proposal_hash"], "reviewer", "Checked synthetic TEST notes", "approved")
    canonical, restored = await restore_internal_bundle(await export_revision_bundle(pair), pair)
    manifest = resolve_unit_manifest(canonical, restored)
    for index, own, other in ((0, "A", "B"), (1, "B", "A")):
        row = restored["tables"][index]["row_unit_ids"][0]
        refs = unit_context_ids(manifest, row)
        assert f"qnu:duplicate{own}" in refs and f"qnu:duplicate{other}" not in refs
