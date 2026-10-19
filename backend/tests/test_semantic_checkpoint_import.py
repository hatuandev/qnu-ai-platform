"""Context555: synthetic TEST intent through authenticated staging and review."""
import copy

import pytest

import tests.test_semantic_lifecycle as lifecycle
from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.normalization.retrieval_models import UnitManifest
from app.modules.knowledge.normalization.structure_chunks import structure_chunks
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    _validated_copy,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_assertions import assertion_identity
from app.modules.knowledge.services.semantic_context_review import make_issue
from app.modules.knowledge.services.semantic_evidence import source_text
from app.modules.knowledge.services.source_links import unit_context_ids
from tests.test_semantic_scope_assertions import assertion
from tests.test_semantic_selector_v2 import case, decision

storage, database = lifecycle.storage, lifecycle.database


def workflow(base):
    return {**assertion(base, source_text(base, "qnu:g"), scope="group", rows=["qnu:r1"]),
        "context_kind": "workflow", "context_label": "TEST equipment dossier / 2027"}


def test_T01_T02_T03_T18_workflow_scope_has_own_chunk_not_student_fact_context():
    text = "Group A equipment 2027 only; inspection notice and training-office decision; at most 15 working days from original deadline; never B, quota or budget."
    base, _ = case(text)
    revised = _validated_copy(base, SemanticAnnotations(notes=[workflow(base)]))
    manifest = UnitManifest.model_validate(revised["retrieval_units"])
    root = next(u for u in manifest.units if u.semantic_scope.get("role") == "assertion")
    assert root.semantic_scope["context_kind"] == "workflow" and root.text == text
    assert root.semantic_scope["row_unit_ids"] == ["qnu:r1"]
    assert root.id not in unit_context_ids(manifest, "qnu:r1")
    assert root.id not in unit_context_ids(manifest, "qnu:r2")
    assert revised["tables"] == base["tables"]
    assert all(root.id not in fact["raw_data"]["context_unit_ids"] for fact in revised["facts"])


def test_T01_workflow_cannot_claim_numeric_columns():
    base, _ = case("Group A equipment dossier only, not student quantities.")
    note = {**workflow(base), "scope": "column", "column_ids": ["c4"]}
    with pytest.raises(ValueError, match="WORKFLOW"):
        _validated_copy(base, SemanticAnnotations(notes=[note]))


@pytest.mark.parametrize("role", ["direct", "protective", "conditional"])
def test_T04_T05_T06_T09_typed_reference_roles_are_advisory(role):
    base, _ = case("Equipment dossier condition. Not a calculation input.")
    notes = SemanticAnnotations(notes=[workflow(base)])
    issue = make_issue(base, "deferred_reference", ["qnu:n"], {"table_ids": [base["tables"][0]["id"]]}, "TEST review reference")
    link = {"assertion_id": assertion_identity(notes.notes[0]), "role": role,
        "evidence": issue["review_evidence"], "reason": "TEST reference role"}
    if role == "conditional": link["condition"] = "Only when used in this assessment workflow"
    pending = stage_semantic_annotations(base, notes, context_review={"issues": [issue],
        "reference_assessments": [{"issue_id": issue["issue_id"], "relevance": "related",
            "assertion_ids": [link["assertion_id"]], "links": [link], "evidence": issue["review_evidence"], "reason": "TEST typed mapping"}]})
    assert pending["context_review"]["reference_assessments"][0]["links"][0]["role"] == role
    assert not any(u.get("semantic_scope") for u in base["retrieval_units"]["units"])


def test_T06_conditional_link_needs_condition_and_target_set_must_match():
    from app.modules.knowledge.services.semantic_context_review import ReferenceAssessment
    with pytest.raises(ValueError):
        ReferenceAssessment.model_validate({"issue_id": "i", "relevance": "related", "assertion_ids": ["a"],
            "reason": "TEST", "links": [{"assertion_id": "a", "role": "conditional", "reason": "TEST", "evidence": []}]})


def package(base):
    proposal_base = copy.deepcopy(base)
    pending = stage_semantic_annotations(proposal_base, SemanticAnnotations(notes=[workflow(base)]))
    return {"contract": "qnu-semantic-checkpoint-v1", "source_artifact": base, "proposal": pending}


async def test_T12_T13_T14_T16_T17_T18_import_review_reload(database):
    from app.modules.knowledge.schemas import (
        SemanticCheckpointImportRequest,
        SemanticProposalReviewRequest,
    )
    from app.modules.knowledge.services.semantic_annotations import review_semantic_proposals
    from app.modules.knowledge.services.semantic_checkpoint import import_semantic_checkpoint
    from app.modules.knowledge.services.semantic_store import rebuild_projection
    col, binding, rid = database.ids
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rid)
        original = copy.deepcopy(lifecycle.artifact_of(rev))
        offline = copy.deepcopy(original)
        offline["qnu_input"].update(document_id="offline-TEST", revision_id="draft-TEST")
        upload = package(offline)
        request = SemanticCheckpointImportRequest(checkpoint=upload, comment="TEST source matched")
        await import_semantic_checkpoint(db, col, binding, rid, request, lifecycle.actor())
        pending = lifecycle.artifact_of(rev)["semantic_annotations"]
        assert pending["proposal_hash"] != upload["proposal"]["proposal_hash"]
        assert pending["annotations"]["notes"][0]["evidence_binding"]["source_identity"]["revision_id"] == rid
        assert pending["annotations"]["notes"][0]["evidence_binding"]["source_identity"]["document_id"] == binding
        assert all(lifecycle.artifact_of(rev)[k] == original[k] for k in ("tables", "facts", "context_graph"))
        assert not rev.parse_provenance.get("semantic_store", {}).get("active")
        # Retry is idempotent, but a different checkpoint cannot replace a pending proposal silently.
        await import_semantic_checkpoint(db, col, binding, rid, request, lifecycle.actor())
        intents = [decision(issue) for issue in pending["context_review"]["issues"]]
        await review_semantic_proposals(db, col, binding, rid, SemanticProposalReviewRequest(
            decision="approved", expected_semantic_proposal_hash=pending["proposal_hash"],
            comment="TEST authorized review only", context_decisions=intents), lifecycle.actor())
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rid)
        canonical, rebuilt = await rebuild_projection(rev)
        roots = [u for u in rebuilt["retrieval_units"]["units"] if u.get("semantic_scope", {}).get("context_kind") == "workflow"]
        assert roots and rebuilt["tables"] == original["tables"]
        assert all(root["id"] not in f["raw_data"]["context_unit_ids"] for root in roots for f in rebuilt["facts"])
        chunks = structure_chunks(canonical, UnitManifest.model_validate(rebuilt["retrieval_units"]), context_graph=rebuilt["context_graph"])
        assert any(c["metadata"]["source_unit_id"] == roots[0]["id"] for c in chunks)
        with pytest.raises(AppException):
            await import_semantic_checkpoint(db, col, binding, rid, request, lifecycle.actor())


@pytest.mark.parametrize("tamper", ["hash", "span", "source", "approved", "actor", "missing-revision", "schema", "projection", "wrong-collection", "wrong-binding"])
async def test_T12_T13_untrusted_checkpoint_rejected_without_write(database, tamper):
    from app.modules.knowledge.schemas import SemanticCheckpointImportRequest
    from app.modules.knowledge.services.semantic_annotations import _digest
    from app.modules.knowledge.services.semantic_checkpoint import import_semantic_checkpoint
    col, binding, rid = database.ids
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rid)
        before = copy.deepcopy(rev.parse_provenance)
        upload = package(copy.deepcopy(lifecycle.artifact_of(rev)))
        actor = lifecycle.actor()
        if tamper == "hash": upload["proposal"]["proposal_hash"] = "0" * 64
        elif tamper == "span":
            upload["proposal"]["annotations"]["notes"][0]["evidence_binding"]["end"] -= 1
            upload["proposal"]["proposal_hash"] = _digest({k:v for k,v in upload["proposal"].items() if k != "proposal_hash"})
        elif tamper == "source": upload["source_artifact"]["qnu_input"]["structured_sha256"] = "0" * 64
        elif tamper == "approved":
            upload["proposal"]["status"] = "verified"
            upload["proposal"]["review"] = {"actor_id": "forged", "decision": "approved"}
        elif tamper == "actor": actor = actor.model_copy(update={"permissions": [], "authenticated": False})
        elif tamper == "schema": upload["contract"] = "future-checkpoint-v99"
        elif tamper == "projection": upload["source_artifact"]["retrieval_units"]["units"][0]["text"] += "forged"
        elif tamper == "wrong-collection": col = "wrong-collection"
        elif tamper == "wrong-binding": binding = "wrong-binding"
        else: rid = "missing-revision"
        with pytest.raises(AppException):
            await import_semantic_checkpoint(db, col, binding, rid, SemanticCheckpointImportRequest(checkpoint=upload, comment="TEST rejects"), actor)
        await db.rollback()
    async with database.factory() as db:
        reloaded = await db.get(KnowledgeSourceRevision, database.ids[2])
        assert reloaded.parse_provenance == before


async def test_T12_T14_authenticated_import_endpoint_and_forged_approval(database):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.core.exceptions import register_exception_handlers
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.auth.schemas import AuthActor
    from app.modules.knowledge.router import router
    col, binding, rid = database.ids
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    current = AuthActor(username="TEST viewer", permissions=["ai.knowledge.view"])
    app.dependency_overrides[get_current_actor] = lambda: current
    async def get_test_db():
        async with database.factory() as db:
            yield db
    app.dependency_overrides[get_db] = get_test_db
    path = next(p for p in app.openapi()["paths"] if p.endswith("/semantic-checkpoint"))
    path = path.replace("{collection_id}", col).replace("{source_id}", binding).replace("{revision_id}", rid)
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rid)
        body = {"checkpoint": package(copy.deepcopy(lifecycle.artifact_of(rev))), "comment": "TEST authorized staging"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post(path,json=body)).status_code == 403
        current = lifecycle.actor()
        response = await client.post(path,json=body)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "review_required"
        async with database.factory() as db:
            artifact = lifecycle.artifact_of(await db.get(KnowledgeSourceRevision, rid))
        assert artifact["semantic_annotations"]["status"] == "proposed"
        assert not artifact.get("semantic_effective")
        pending = artifact["semantic_annotations"]
        stale = await client.post(path.removesuffix("semantic-checkpoint")+"semantic-review", json={
            "decision":"approved", "expected_semantic_proposal_hash":body["checkpoint"]["proposal"]["proposal_hash"], "comment":"TEST old offline hash"})
        assert stale.status_code == 409
        # Missing even one issue decision blocks the real review endpoint.
        denied = await client.post(path.removesuffix("semantic-checkpoint")+"semantic-review", json={
            "decision":"approved", "expected_semantic_proposal_hash":pending["proposal_hash"], "comment":"TEST missing decisions"})
        assert denied.status_code == 409
        assert denied.json()["code"] == "SEMANTIC_CONTEXT_REVIEW_REQUIRED"
