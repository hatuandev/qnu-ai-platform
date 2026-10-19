"""Phase 2: source limits are TEST human decisions, never inferred meanings."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import tests.test_semantic_lifecycle as lifecycle
from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
from app.modules.knowledge.normalization.structure_chunks import structure_chunks
from app.modules.knowledge.services.qnu_serving import prepare_standard_revision
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_bundle import (
    export_revision_bundle,
    restore_internal_bundle,
)
from app.modules.knowledge.services.semantic_store import (
    STORE,
    rebuild_projection,
    record_decision,
    semantic_fingerprint,
)
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service

artifact_of = lifecycle.artifact_of
database = lifecycle.database
pair = lifecycle.pair
storage = lifecycle.storage


def limitation_payload(artifact, *, basis="human_examined_scope", column="c7", raw="/"):
    table = artifact["tables"][0]
    return {
        "notes": [], "cells": [], "limitations": [{
            "row_unit_id": table["row_unit_ids"][1], "column_id": column, "raw": raw,
            "basis": basis, "evidence_unit_id": "qnu:g",
            "evidence_quote": "Only the 2026 column has this condition.",
            "examined_unit_ids": [unit["id"] for unit in artifact["retrieval_units"]["units"]],
        }],
    }


@pytest.mark.asyncio
async def test_T02_limit_acknowledgment_keeps_raw_unknown_after_rebuild(pair):
    from app.modules.knowledge.services.source_limitations import evaluate_source_policy

    before = copy.deepcopy(artifact_of(pair))
    proposal = stage_semantic_annotations(artifact_of(pair), SemanticAnnotations.model_validate(limitation_payload(before)))
    assert artifact_of(pair)["tables"] == before["tables"]
    with pytest.raises(AppException):
        await record_decision(pair, artifact_of(pair), proposal["proposal_hash"], "TEST-reviewer546", "Examined TEST source scope", "approved")
    reviewed = await record_decision(pair, artifact_of(pair), proposal["proposal_hash"], "TEST-reviewer546",
                                     "Examined every listed TEST unit; no definition found in this scope", "acknowledged_limits",
                                     policy_mode="acknowledged_limits")
    _, restored = await rebuild_projection(pair)
    field = restored["tables"][0]["row_fields"][1][6]
    assert (field["raw"], field["state"], field["normalized"]) == ("/", "ambiguous", None)
    assert field["usage"] == "description_only"
    assert restored["unresolved_cell_count"] == before["unresolved_cell_count"]
    assert restored["source_limitations"] == reviewed["source_limitations"]
    policy = evaluate_source_policy(restored, mode="acknowledged_limits")
    assert policy["acknowledged_limit_count"] == 1
    assert policy["semantic_unknown_count"] >= 1
    assert policy["publication_enabled"] is False
    assert evaluate_source_policy(restored)["mode"] == "strict"
    with pytest.raises(AppException):
        source_ingestion_service._apply_review_decision(type("Binding", (), {})(), pair, restored,
                                                       "approved", "TEST only", "TEST-reviewer546")


@pytest.mark.asyncio
async def test_T03_limit_cannot_waive_unreadable_or_invent_evidence(pair):
    artifact = artifact_of(pair)
    payload = limitation_payload(artifact)
    payload["limitations"][0]["evidence_quote"] = "Missing source quotation"
    with pytest.raises(ValueError):
        stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(payload))
    artifact["tables"][0]["row_fields"][1][6]["state"] = "unreadable"
    with pytest.raises(ValueError):
        stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(limitation_payload(artifact)))


@pytest.mark.asyncio
async def test_T04_T06_independent_integrity_scope_page_blockers_are_not_waived(pair):
    from app.modules.knowledge.services.source_limitations import evaluate_source_policy

    artifact = artifact_of(pair)
    for code in ("extraction_error", "note_scope_unresolved", "page_mapping_unknown"):
        artifact["issues"] = [{"code": code}]
        policy = evaluate_source_policy(artifact, mode="acknowledged_limits")
        assert code in policy["independent_blockers"]
        assert policy["eligible_for_limited_use"] is False


@pytest.mark.asyncio
async def test_T11_review_action_needs_pending_hash_and_actor(pair):
    proposal = stage_semantic_annotations(artifact_of(pair), SemanticAnnotations.model_validate(limitation_payload(artifact_of(pair))))
    for actor, digest in (("", proposal["proposal_hash"]), ("TEST-reviewer546", "0" * 64)):
        with pytest.raises(AppException):
            await record_decision(pair, artifact_of(pair), digest, actor, "TEST examination", "acknowledged_limits")


@pytest.mark.asyncio
async def test_T07_real_chunk_and_consumer_reject_limits_without_zero_coercion(pair):
    from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
    from app.modules.rag.fusion import FusionCandidate
    from app.modules.rag.row_answer_contract import _standard_fields

    artifact = artifact_of(pair)
    proposal = stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(limitation_payload(artifact)))
    await record_decision(pair, artifact, proposal["proposal_hash"], "TEST-reviewer546", "Examined TEST scope only", "acknowledged_limits")
    canonical, rebuilt = await rebuild_projection(pair)
    manifest = resolve_unit_manifest(canonical, rebuilt)
    table = rebuilt["tables"][0]
    row_id = table["row_unit_ids"][1]
    chunk = next(chunk for chunk in structure_chunks(canonical, manifest, context_graph=rebuilt["context_graph"])
                 if chunk["metadata"]["source_unit_id"] == row_id)
    assert chunk["metadata"]["source_unit"]["field_usage"] == {"c7": "description_only"}
    fields = table["row_fields"][1]
    assert not any(fact["raw_data"].get("source_unit_id") == row_id and fact["raw_data"].get("column_id") == "c7"
                   for fact in rebuilt["facts"])
    row = FusionCandidate("chunk", "doc", chunk["content"], 1, metadata={**chunk["metadata"],
        "row_fields": fields, "row_columns": table["columns"], "cell_state_source": "declared"})
    with pytest.raises(ValueError, match="quantitative"):
        _standard_fields(row, table["headers"], _split_gfm_row(row.metadata["source_unit"]["text"]))
    # Even if a downstream consumer loses the field flag, the sealed unit retains it.
    fields[-1].pop("usage")
    with pytest.raises(ValueError, match="quantitative"):
        _standard_fields(row, table["headers"], _split_gfm_row(row.metadata["source_unit"]["text"]))
    zero = table["row_fields"][0][3]
    assert (zero["raw"], zero["normalized"], zero["state"]) == ("0", 0, "present")


@pytest.mark.asyncio
async def test_T10_T13_pending_rejected_request_changes_preserve_active_limits(pair):
    artifact = artifact_of(pair)
    pending = stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(limitation_payload(artifact)))
    await record_decision(pair, artifact, pending["proposal_hash"], "TEST-reviewer546", "Examined TEST source", "acknowledged_limits")
    before = semantic_fingerprint(artifact_of(pair))
    for decision in ("rejected", "changes_requested"):
        pending = await lifecycle.stage(pair)
        assert semantic_fingerprint(artifact_of(pair)) == before
        await record_decision(pair, artifact_of(pair), pending["proposal_hash"], "TEST-reviewer546", "TEST follow up needed", decision)
        assert semantic_fingerprint(artifact_of(pair)) == before
        assert artifact_of(pair)["semantic_annotations"]["status"] == decision
    with patch("app.modules.knowledge.services.unit_annotation.enrich_source_units", AsyncMock(side_effect=AssertionError("No model"))):
        await prepare_standard_revision(pair)
        canonical, restored = await restore_internal_bundle(await export_revision_bundle(pair), pair)
    assert semantic_fingerprint(restored) == before
    assert resolve_unit_manifest(canonical, restored).semantic_annotation_hash


@pytest.mark.asyncio
async def test_T05_T11_T13_real_api_permissions_hash_and_db_reload(database, tmp_path):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.core.exceptions import register_exception_handlers
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.auth.schemas import AuthActor
    from app.modules.knowledge.router import router
    from app.modules.knowledge.services.source_limitations import evaluate_source_policy

    col, binding, rev_id = database.ids
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    current_actor = AuthActor(username="TEST-viewer546", actor_id="TEST-viewer546", permissions=["ai.knowledge.view"])
    app.dependency_overrides[get_current_actor] = lambda: current_actor
    async def get_test_db():
        async with database.factory() as db:
            yield db
    app.dependency_overrides[get_db] = get_test_db
    path = next(path for path in app.openapi()["paths"] if path.endswith("/semantic-review")).replace(
        "{collection_id}", col).replace("{source_id}", binding).replace("{revision_id}", rev_id)
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rev_id)
        artifact = copy.deepcopy(artifact_of(rev))
        pending = stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(limitation_payload(artifact)))
        rev.parse_provenance = {**rev.parse_provenance, "structured_artifact": artifact}
        await db.commit()
    body = {"decision": "acknowledged_limits", "policy_mode": "acknowledged_limits",
            "expected_semantic_proposal_hash": pending["proposal_hash"], "comment": "TEST actor examined every listed unit; no definition in this scope"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post(path, json=body)).status_code == 403
        current_actor = AuthActor(username="TEST-reviewer546", actor_id="TEST-reviewer546", permissions=["ai.knowledge.view", "ai.knowledge.update"])
        assert (await client.post(path, json={**body, "expected_semantic_proposal_hash": "0" * 64})).status_code == 409
        assert (await client.post(path.replace(binding, "wrong-binding"), json=body)).status_code == 404
        response = await client.post(path, json=body)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "review_required"
        assert (await client.post(path, json=body)).status_code == 409
    async with database.factory() as db:
        loaded = await db.get(KnowledgeSourceRevision, rev_id)
        reference = loaded.parse_provenance[STORE]["active"]
        snapshot = json.loads(await database.storage.get(reference["path"]))
        _, rebuilt = await rebuild_projection(loaded)
        assert snapshot["review"]["actor_id"] == "TEST-reviewer546"
        assert snapshot["review"]["action"] == "acknowledged_limits"
        assert rebuilt["source_policy"]["mode"] == "acknowledged_limits"
        assert evaluate_source_policy(rebuilt, mode="acknowledged_limits")["unfinished_count"] == 0
        assert evaluate_source_policy(rebuilt)["policy_blocker_count"] > 0
        assert (await db.get(lifecycle.KnowledgeBinding, binding)).active_source_revision_id is None
        dossier = {"test_approval_only": True, "snapshot": snapshot, "source_limitations": rebuilt["source_limitations"],
                   "policy": rebuilt["source_policy"], "projection_fingerprint": semantic_fingerprint(rebuilt)}
        (Path(__file__).parents[1] / "storage/annotation546-test-roundtrip.json").write_text(
            json.dumps(dossier, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


@pytest.mark.asyncio
async def test_T12_same_raw_new_source_evidence_invalidates_acknowledgment(pair):
    artifact = artifact_of(pair)
    pending = stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(limitation_payload(artifact)))
    await record_decision(pair, artifact, pending["proposal_hash"], "TEST-reviewer546", "Examined TEST source", "acknowledged_limits")
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair

    document = await verify_revision_pair(pair)
    document.blocks[-1].body += " New source legend defines the slash."
    with pytest.raises(AppException):
        await rebuild_projection(pair, document)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["provider", "timeout", "schema", "evidence"])
async def test_T08_T09_runner_failure_is_nonzero_and_not_workflow_pass(pair, failure):
    from scripts.verify_semantic_modelops import run_proposal

    async def invoke(artifact):
        if failure == "provider":
            raise AppException("TEST provider unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)
        if failure == "timeout":
            raise TimeoutError("TEST only")
        if failure == "schema":
            return {"status": "verified", "annotations": {"invented": True}}
        payload = limitation_payload(artifact)
        payload["limitations"][0]["evidence_quote"] = "Not in source"
        return stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(payload))
    code, report = await run_proposal(copy.deepcopy(artifact_of(pair)), invoke, proposal_only=True)
    assert code == 1 and report["stages"]["proposal"] == "FAIL"
    assert report["human_approved"] is False and report["end_to_end"] == "INCOMPLETE"


@pytest.mark.asyncio
@pytest.mark.parametrize("proposal_only,expected", [(True, 0), (False, 2)])
async def test_T08_T10_runner_pending_is_not_end_to_end_pass(pair, proposal_only, expected):
    from scripts.verify_semantic_modelops import run_proposal

    async def invoke(artifact):
        return stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(limitation_payload(artifact)))
    code, report = await run_proposal(copy.deepcopy(artifact_of(pair)), invoke, proposal_only=proposal_only)
    assert code == expected and report["status"] == "WAITING_FOR_REVIEW"
    assert report["stages"]["apply"] == "NOT_RUN"


@pytest.mark.asyncio
@pytest.mark.parametrize("mutate", ["raw", "target", "scope", "duplicate", "numeric"])
async def test_T03_T09_invalid_limit_never_becomes_acknowledged(pair, mutate):
    artifact = artifact_of(pair)
    payload = limitation_payload(artifact)
    limit = payload["limitations"][0]
    if mutate == "raw":
        limit["raw"] = "Something else"
    elif mutate == "target":
        limit["row_unit_id"] = "foreign-source"
    elif mutate == "scope":
        limit["examined_unit_ids"] = ["qnu:g"]
    elif mutate == "duplicate":
        payload["limitations"].append(copy.deepcopy(limit))
    else:
        limit.update(row_unit_id=artifact["tables"][0]["row_unit_ids"][0], column_id="c4", raw="0")
    with pytest.raises(ValueError):
        stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(payload))


@pytest.mark.asyncio
async def test_T01_states_and_explicit_unpublished_qualifier_survive_rebuild(pair):
    payload = lifecycle.payload(artifact_of(pair))
    pending = await lifecycle.stage(pair, payload)
    await record_decision(pair, artifact_of(pair), pending["proposal_hash"], "TEST-reviewer546", "TEST source meanings", "approved")
    for _ in range(3):
        _, rebuilt = await rebuild_projection(pair)
        first, second = rebuilt["tables"][0]["row_fields"]
        assert (first[3]["raw"], first[3]["state"], first[3]["normalized"]) == ("0", "present", 0)
        assert (second[3]["raw"], second[3]["state"], second[3]["normalized"]) == ("", "blank", None)
        assert (first[6]["raw"], first[6]["state"]) == ("Not published yet", "not_stated")
        assert first[6]["state_evidence"]["evidence_quote"] == "Not published yet"
        assert (first[2]["raw"], first[2]["state"]) == ("–", "not_applicable")
        assert (second[6]["raw"], second[6]["state"]) == ("/", "ambiguous")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["missing", "checksum"])
async def test_T04_acknowledgment_cannot_hide_storage_failure(pair, storage, failure):
    artifact = artifact_of(pair)
    pending = stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(limitation_payload(artifact)))
    await record_decision(pair, artifact, pending["proposal_hash"], "TEST-reviewer546", "TEST source examined", "acknowledged_limits")
    reference = pair.parse_provenance[STORE]["active"]
    if failure == "missing":
        await storage.delete(reference["path"])
    else:
        await storage.save(reference["path"], b'{"tampered":true}')
    with pytest.raises(AppException):
        await rebuild_projection(pair)


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit_override", [False, True])
async def test_T08_modelops_uses_persisted_fallback_only_for_default_chain(pair, explicit_override):
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair
    from app.modules.knowledge.services.semantic_annotations import propose_source_semantics
    from app.modules.modelops.schemas import SystemModelDefaults

    artifact = copy.deepcopy(artifact_of(pair))
    defaults = SystemModelDefaults(default_chat_provider_id="primary", default_chat_model="configured-model",
        default_chat_mode="combo", chat_combo_chain=[
            {"provider_id": "primary", "provider_name": "TEST primary", "model_name": "configured-model"},
            {"provider_id": "fallback", "provider_name": "TEST fallback", "model_name": "configured-fallback"}])
    async def respond(_db, request):
        packet = json.loads(request.messages[1].content)
        return SimpleNamespace(content=json.dumps({"context_id": packet["context_id"]}), provider="TEST-primary", model="TEST-model",
            is_fallback=False, prompt_tokens=1, completion_tokens=1, cost_usd=None)
    with patch("app.modules.modelops.services.model_catalog_service.model_catalog_service.get_system_model_defaults",
               AsyncMock(return_value=SimpleNamespace(defaults=defaults))), \
         patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=respond)) as generate:
        await propose_source_semantics(AsyncMock(), artifact, "TEST", **(
            {"model_name": "explicit-model", "provider_id": "explicit-provider"} if explicit_override else {}), document=await verify_revision_pair(pair))
    request = generate.call_args.args[1]
    assert request.preferred_provider_id == ("explicit-provider" if explicit_override else "primary")
    assert request.fallback_provider_id == (None if explicit_override else "fallback")
    assert request.fallback_model_name == (None if explicit_override else "configured-fallback")


@pytest.mark.asyncio
async def test_phase1_cached_projection_without_neutral_usage_field_remains_valid(pair):
    from app.modules.knowledge.services.semantic_store import verify_effective_projection

    await lifecycle.approve(pair)
    artifact = copy.deepcopy(artifact_of(pair))
    for unit in artifact["retrieval_units"]["units"]:
        unit.pop("field_usage", None)
    await verify_effective_projection(pair, artifact)
