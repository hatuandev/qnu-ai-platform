"""Regression for review authority, packet budgets and atomic multi-packet runs."""
import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import tests.test_semantic_lifecycle as lifecycle
import tests.test_semantic_proposals as f
from app.core.exceptions import AppException
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    apply_reviewed_semantics,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_context import ContextBuilder, SemanticContextPolicy

storage = lifecycle.storage
pair = lifecycle.pair
database = lifecycle.database


@pytest.fixture
async def model_database():
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.config import settings
    url = make_url(settings.DATABASE_URL)
    assert settings.ENVIRONMENT == "test" and url.host in {"localhost", "127.0.0.1"} and url.database.startswith("qnu_test_")
    # Each pytest loop owns its ModelOps connections. The module-global app pool
    # can retain connections from earlier tests whose Proactor loop is closed.
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def unresolved():
    return {"coverage_complete": True, "scope": "document", "unresolved": [{"unit_ids": ["qnu:g"], "reason": "Missing mandatory condition"}]}


@pytest.mark.asyncio
async def test_issue_only_cannot_become_clean_empty(pair):
    artifact = lifecycle.artifact_of(pair)
    pending = stage_semantic_annotations(artifact, SemanticAnnotations(), context_review=unresolved())
    assert pending["status"] == "proposed"
    with pytest.raises(AppException) as error:
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "Generic comment")
    assert error.value.code == "SEMANTIC_CONTEXT_REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_mixed_generic_review_cannot_clear_missing_context(pair):
    artifact = lifecycle.artifact_of(pair)
    pending = stage_semantic_annotations(artifact, lifecycle.payload(artifact), context_review=unresolved())
    with pytest.raises(AppException) as error:
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "Generic comment")
    assert error.value.code == "SEMANTIC_CONTEXT_REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_reject_and_changes_requested_preserve_context_blockers(pair):
    from app.modules.knowledge.services.semantic_store import rebuild_projection, record_decision
    from app.modules.knowledge.services.source_limitations import evaluate_source_policy

    artifact = lifecycle.artifact_of(pair)
    pending = stage_semantic_annotations(artifact, lifecycle.payload(artifact), context_review={**unresolved(), "coverage_complete": False})
    await record_decision(pair, artifact, pending["proposal_hash"], "TEST", "Missing source; reject", "rejected")
    assert pair.parse_provenance["semantic_store"]["active"] is None
    _, restored = await rebuild_projection(pair)
    assert evaluate_source_policy(restored)["context_blocker_count"] > 0


def many_rows(count=40):
    document = f.fixture.fixture_document()
    rows = [b for b in document.blocks if b.type == "table_row"]
    for index in range(count):
        row = rows[index % len(rows)].model_copy(deep=True)
        row.id = f"TEST548-row-{index}"
        document.blocks.insert(-1, row)
    _, artifact = project_document(document, f.fixture.reference(), {})
    return document, artifact


def test_expand_table_counts_full_rows_not_only_private_ids():
    document, artifact = many_rows()
    builder = ContextBuilder(artifact, document, SemanticContextPolicy(max_units=6, max_packet_bytes=200000, max_packets=64, max_expansions=1))
    table = artifact["tables"][0]
    packet = builder._packet([(table, table["row_unit_ids"][:2])], [])
    before = copy.deepcopy(packet)
    with pytest.raises(ValueError, match="BUDGET"):
        builder.expand(packet, [table["id"]])
    assert packet == before


@pytest.mark.asyncio
async def test_packet_two_fails_after_real_first_binding_without_partial_stage():
    from app.modules.knowledge.services import semantic_annotations as annotations_module
    from app.modules.knowledge.services import semantic_modelops as runtime

    document, artifact = many_rows(18)
    before = copy.deepcopy(artifact)
    from tests.test_semantic_context_binding import note_payload
    calls = 0
    async def reply(_db, request):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise TimeoutError("TEST inner provider timeout")
        packet = json.loads(request.messages[-1].content)
        payload = note_payload(packet, scope="table", columns=[])
        return SimpleNamespace(content=json.dumps(payload), provider="TEST", model="TEST",
            is_fallback=False, prompt_tokens=1, completion_tokens=1, cost_usd=None)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=reply)) as generate, \
         patch.object(runtime, "bind_model_proposals", wraps=runtime.bind_model_proposals) as bind, \
         patch.object(annotations_module, "stage_semantic_annotations", wraps=stage_semantic_annotations) as stage, pytest.raises(TimeoutError):
        await annotations_module.propose_source_semantics(AsyncMock(), artifact, "TEST", "TEST", "TEST", document=document,
            context_policy={"max_units": 8, "max_calls": 64, "max_packets": 64, "max_total_bytes": 2000000})
    assert generate.await_count == 2 and bind.call_count == 1
    stage.assert_not_called()
    assert artifact == before


@pytest.mark.asyncio
async def test_multiyear_binding_requires_specific_canonical_scope_review(pair):
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair
    from app.modules.knowledge.services.semantic_binding import bind_model_proposals
    from app.modules.knowledge.services.semantic_evidence import make_binding
    from tests.test_semantic_context_binding import note_payload

    document = await verify_revision_pair(pair)
    document.blocks[-1].body = "Applies simultaneously in 2026 and 2027; read both column groups."
    _, artifact = project_document(document, f.fixture.reference(), {})
    packet = ContextBuilder(artifact, document).packets()[0]
    collector = []
    selected = note_payload(packet, columns=["c4", "c7"])
    annotations = bind_model_proposals(artifact, packet, selected, review_issues=collector)
    assert len(collector) == 1
    pending = stage_semantic_annotations(artifact, annotations,
        context_review={"coverage_complete": True, "scope": "document", "issues": collector})
    with pytest.raises(AppException):
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "Generic review")
    text = document.blocks[-1].body
    resolution = {"issue_id": collector[0]["issue_id"], "target": collector[0]["target"], "action": "scope_confirmed",
        "evidence_binding": make_binding(artifact, "qnu:g", 0, len(text)).model_dump(),
        "evidence_quote": text, "reason": "TEST reviewed the complete source and exact column groups"}
    approved = apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "Specific review", context_decisions=[resolution])
    assert approved["semantic_annotations"]["review"]["context_decisions"][0]["actor_id"] == "TEST"


@pytest.mark.asyncio
async def test_publication_guard_catches_legacy_empty_unresolved(pair):
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
    artifact = lifecycle.artifact_of(pair)
    pending = stage_semantic_annotations(artifact, SemanticAnnotations(), context_review=unresolved())
    pending["status"] = "empty"  # Historical state; never accepted as clean by publication.
    artifact["unresolved_cell_count"] = 0
    with pytest.raises(AppException) as error:
        source_ingestion_service._apply_review_decision(SimpleNamespace(status="active"), pair, artifact,
            "approved", "TEST source check", "TEST")
    assert error.value.code == "SEMANTIC_CONTEXT_REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_run_call_inner_timeout_and_cancellation_are_distinct():
    from app.modules.knowledge.services.semantic_run_budget import SemanticRunBudget
    async def slow():
        await asyncio.sleep(0.05)
    async def inner():
        raise TimeoutError("TEST transport")
    with pytest.raises(AppException) as call:
        await SemanticRunBudget(1).wait(slow, call_seconds=0.005)
    assert call.value.code == "SEMANTIC_CALL_DEADLINE"
    with pytest.raises(AppException) as run:
        await SemanticRunBudget(0.005).wait(slow, call_seconds=1)
    assert run.value.code == "SEMANTIC_RUN_DEADLINE"
    with pytest.raises(TimeoutError, match="transport"):
        await SemanticRunBudget(1).wait(inner)
    task = asyncio.create_task(SemanticRunBudget(1).wait(slow))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_scope_simple_conflict_unchanged_and_issue_identity_ignores_reason():
    from app.modules.knowledge.services.semantic_binding import bind_model_proposals
    from app.modules.knowledge.services.semantic_context_review import make_issue
    from tests.test_semantic_context_binding import note_payload
    document = f.fixture.fixture_document()
    document.blocks[-1].body = "Only year 2027 applies."
    _, artifact = project_document(document, f.fixture.reference(), {})
    packet = ContextBuilder(artifact, document).packets()[0]
    with pytest.raises(ValueError, match="YEAR_CONFLICT"):
        bind_model_proposals(artifact, packet, note_payload(packet, columns=["c4"]), review_issues=[])
    one = make_issue(artifact, "scope_confirmation_required", ["qnu:g"], {"column_ids": ["c4", "c7"]}, "First wording")
    two = make_issue(artifact, "scope_confirmation_required", ["qnu:g"], {"column_ids": ["c7", "c4"]}, "Changed wording")
    assert one["issue_id"] == two["issue_id"]
    three = make_issue(artifact, "scope_confirmation_required", ["qnu:g"], {"column_ids": ["c4"]}, "First wording")
    assert one["issue_id"] != three["issue_id"]


@pytest.mark.asyncio
async def test_scope_decisions_snapshot_reload_session_and_tamper(database):
    from app.modules.knowledge.models import KnowledgeSourceRevision
    from app.modules.knowledge.services.semantic_context_review import make_issue
    from app.modules.knowledge.services.semantic_store import (
        _semantic_hash,
        rebuild_projection,
        record_decision,
    )
    from app.modules.knowledge.services.source_limitations import evaluate_source_policy
    _collection, _binding, revision_id = database.ids
    async with database.factory() as db:
        revision = await db.get(KnowledgeSourceRevision, revision_id)
        artifact = lifecycle.artifact_of(revision)
        issue = make_issue(artifact, "scope_confirmation_required", ["qnu:g"], {"table_id": artifact["tables"][0]["id"], "column_ids": ["c4"]}, "TEST confirm source scope")
        pending = stage_semantic_annotations(artifact, lifecycle.payload(artifact), context_review={"coverage_complete": True, "issues": [issue]})
        intent = {"issue_id": issue["issue_id"], "target": issue["target"], "action": "scope_confirmed",
            **issue["review_evidence"][0], "reason": "TEST entire canonical condition and exact target"}
        approved = await record_decision(revision, artifact, pending["proposal_hash"], "TEST-reviewer548", "TEST specific scope", "approved", context_decisions=[intent])
        assert evaluate_source_policy(approved)["context_blocker_count"] == 0
        await db.commit()
    async with database.factory() as db:
        revision = await db.get(KnowledgeSourceRevision, revision_id)
        with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=AssertionError("No model replay"))):
            _, restored = await rebuild_projection(revision)
        review = restored["semantic_annotations"]["review"]
        assert review["context_decisions"][0]["actor_id"] == "TEST-reviewer548"
        assert restored["source_policy"]["context_blocker_count"] == 0
        from app.modules.knowledge.services.semantic_store import effective_snapshot
        _, snapshot = await effective_snapshot(revision)
        assert snapshot["semantic_hash_version"] == 2
        changed = copy.deepcopy(snapshot)
        changed["review"]["context_decisions"][0]["target"] = {"column_ids": ["c7"]}
        assert _semantic_hash(changed) != snapshot["semantic_hash"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["issue", "target", "actor", "span", "missing"])
async def test_context_resolution_cannot_be_forged_or_close_missing_source(pair, mutation):
    from app.modules.knowledge.services.semantic_context_review import make_issue
    artifact = lifecycle.artifact_of(pair)
    issue = make_issue(artifact, "missing_context" if mutation == "missing" else "scope_confirmation_required", ["qnu:g"], {"column_ids": ["c4"]}, "TEST issue")
    if mutation == "missing":
        from app.modules.knowledge.services.semantic_evidence import make_binding, source_text
        text = source_text(artifact, "qnu:g")
        evidence = {"evidence_binding": make_binding(artifact, "qnu:g", 0, len(text)).model_dump(), "evidence_quote": text}
    else:
        evidence = issue["review_evidence"][0]
    intent = {"issue_id": issue["issue_id"], "target": issue["target"], "action": "scope_confirmed", **evidence, "reason": "TEST exact review"}
    pending = stage_semantic_annotations(artifact, lifecycle.payload(artifact), context_review={"coverage_complete": True, "issues": [issue]})
    if mutation == "issue": intent["issue_id"] += "forged"
    if mutation == "target": intent["target"] = {"column_ids": ["c7"]}
    if mutation == "actor": intent["actor_id"] = "ADMIN-CLIENT"
    if mutation == "span": intent["evidence_binding"]["end"] -= 1
    with pytest.raises(AppException):
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "TEST comment", context_decisions=[intent])


@pytest.mark.asyncio
@pytest.mark.parametrize("decision", ["rejected", "changes_requested"])
async def test_reject_issue_over_active_keeps_effective_set_but_blocks_source(pair, decision):
    from app.modules.knowledge.services.semantic_store import (
        proposal_base,
        rebuild_projection,
        record_decision,
    )
    from app.modules.knowledge.services.source_limitations import evaluate_source_policy
    await lifecycle.approve(pair)
    before = copy.deepcopy(lifecycle.artifact_of(pair))
    active = copy.deepcopy(pair.parse_provenance["semantic_store"]["active"])
    base = await proposal_base(pair, before)
    pending = stage_semantic_annotations(lifecycle.artifact_of(pair), lifecycle.payload(base), base_artifact=base, context_review=unresolved())
    await record_decision(pair, lifecycle.artifact_of(pair), pending["proposal_hash"], "TEST", "Still missing source", decision)
    _, restored = await rebuild_projection(pair)
    assert pair.parse_provenance["semantic_store"]["active"] == active
    assert all(restored[key] == before[key] for key in ("tables", "facts", "context_graph", "semantic_effective"))
    assert restored["semantic_annotations"]["status"] == decision
    assert evaluate_source_policy(restored)["context_blocker_count"] > 0


def test_omission_retains_issue_and_reprocessing_requires_new_bound_source():
    from app.modules.knowledge.services.semantic_context_review import make_issue, normalize_review
    document = f.fixture.fixture_document()
    _, artifact = project_document(document, f.fixture.reference(), {})
    old = make_issue(artifact, "missing_context", ["qnu:g"], {"table_ids": [artifact["tables"][0]["id"]]}, "Missing condition")
    previous = normalize_review(artifact, {"coverage_complete": True, "issues": [old]})
    omitted = normalize_review(artifact, {"coverage_complete": True, "issues": []}, previous)
    assert old["issue_id"] in {i["issue_id"] for i in omitted["issues"]}
    new = make_issue(artifact, "scope_confirmation_required", ["qnu:g", "qnu:n"], old["target"], "Newly supplied canonical condition")
    rebuilt = normalize_review(artifact, {"coverage_complete": True, "issues": [new],
        "reprocessed_issues": [{"old_issue_id": old["issue_id"], "new_issue_id": new["issue_id"]}]}, previous)
    assert [item["issue_id"] for item in rebuilt["issues"]] == [new["issue_id"]]
    assert rebuilt["reconciliation"]["prior_issues"][0] == old


@pytest.mark.asyncio
async def test_deadline_during_stage_thread_never_mutates_caller(pair):
    import time

    from app.modules.knowledge.services import semantic_annotations as annotations_module
    artifact = lifecycle.artifact_of(pair)
    before = copy.deepcopy(artifact)
    # Use the verified fixture pair identity/text, rather than a partial fake source.
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair
    document = await verify_revision_pair(pair)
    real_stage = stage_semantic_annotations
    def delayed(*args, **kwargs):
        time.sleep(0.25)
        return real_stage(*args, **kwargs)
    async def reply(_db, request):
        packet = json.loads(request.messages[-1].content)
        return SimpleNamespace(content=json.dumps({"context_id": packet["context_id"]}), provider="TEST", model="TEST", is_fallback=False,
            prompt_tokens=1, completion_tokens=1, cost_usd=None)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=reply)), \
         patch.object(annotations_module, "stage_semantic_annotations", side_effect=delayed) as stage, pytest.raises(AppException) as error:
        await annotations_module.propose_source_semantics(AsyncMock(), artifact, "TEST", "TEST", "TEST", document=document,
            context_policy={"run_seconds": 0.15})
    assert error.value.code == "SEMANTIC_RUN_DEADLINE"
    assert stage.call_count == 1
    await asyncio.sleep(0.3)
    assert artifact == before


@pytest.mark.asyncio
async def test_api_whole_actual_document_uses_same_deadline_and_preserves_pending_scope(database, model_database, record_property):
    import hashlib
    from pathlib import Path

    from app.modules.knowledge.models import KnowledgeSourceRevision
    from app.modules.knowledge.parsers.docling_office_parser import DoclingOfficeParser
    from app.modules.knowledge.parsers.docling_structure import build_qnu_structured_document
    from app.modules.knowledge.services.qnu_docx_artifacts import build_qnu_markdown_artifact
    from app.modules.knowledge.services.qnu_serving import prepare_standard_revision
    from app.modules.knowledge.services.semantic_annotations import generate_semantic_proposals
    from app.modules.knowledge.services.source_extraction import SourceExtraction

    path = Path(__file__).resolve().parents[2] / "docs/tai_lieu/tuyen_sinh/tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx"
    data = path.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    assert checksum == "58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274"
    parsed = await DoclingOfficeParser("docx").parse(data, path.name)
    document = build_qnu_structured_document(parsed.docling_document, filename=path.name, sha256=checksum,
        header_evidence=parsed.docx_header_evidence, source_evidence=parsed.docx_source_evidence)
    collection, binding, revision_id = database.ids
    seen = []
    async def reply(_db, request):
        packet = json.loads(request.messages[-1].content)
        seen.append(packet)
        return SimpleNamespace(content=json.dumps({"context_id": packet["context_id"]}), provider="TEST", model="TEST", is_fallback=False,
            prompt_tokens=1, completion_tokens=1, cost_usd=None)
    async with database.factory() as db:
        revision = await db.get(KnowledgeSourceRevision, revision_id)
        revision.parse_provenance = {}
        revision.origin_file_hash = checksum
        ref = await build_qnu_markdown_artifact(extraction=SourceExtraction(parsed.raw_text, 0,
            qnu_document=document, office_resources=parsed.docx_source_evidence["resources"]), document_id=binding,
            revision_id=revision_id, title=None, snapshot_path=revision.snapshot_storage_path)
        assert ref["status"] == "ready"
        revision.snapshot_metadata = {"qnu_markdown": ref, "unit_temporal_annotation": {"semantic_context": {"run_seconds": 120, "call_seconds": 90}}}
        await prepare_standard_revision(revision)
        await db.commit()
        await db.refresh(revision)  # Compare persisted JSON on both sides of the handler reload.
        before = copy.deepcopy(lifecycle.artifact_of(revision))
        with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=reply)), patch("app.core.database.AsyncSessionFactory", model_database):
            await generate_semantic_proposals(db, collection, binding, revision_id, lifecycle.actor())
        result = lifecycle.artifact_of(revision)
        record_property("context_metrics_test_adapter_only", json.dumps(result["semantic_annotations"]["model"]["metrics"]))
        assert len(seen) > 10 and len({table["id"] for packet in seen for table in packet["tables"]}) == 10
        assert result["semantic_annotations"]["context_review"]["scope"] == "document"
        assert all(before[key] == result[key] for key in ("tables", "facts", "context_graph"))
        assert revision.status == "review_required" and not result.get("semantic_effective")


@pytest.mark.asyncio
async def test_api_deadline_retains_exact_code_and_draft(database, model_database):
    from app.modules.knowledge.models import KnowledgeSourceRevision
    from app.modules.knowledge.services.semantic_annotations import generate_semantic_proposals
    collection, binding, revision_id = database.ids
    async with database.factory() as db:
        revision = await db.get(KnowledgeSourceRevision, revision_id)
        revision.snapshot_metadata = {**revision.snapshot_metadata, "unit_temporal_annotation": {"semantic_context": {"run_seconds": 0.001}}}
        await db.commit()
        before = copy.deepcopy(revision.parse_provenance)
        with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock()) as model, patch("app.core.database.AsyncSessionFactory", model_database), pytest.raises(AppException) as error:
            await generate_semantic_proposals(db, collection, binding, revision_id, lifecycle.actor())
        assert error.value.code == "SEMANTIC_RUN_DEADLINE"
        model.assert_not_awaited()
        assert revision.parse_provenance == before


@pytest.mark.asyncio
async def test_cancellation_on_packet_two_is_not_output_error_or_partial_stage():
    from app.modules.knowledge.services import semantic_annotations as annotations_module
    document, artifact = many_rows(18)
    before = copy.deepcopy(artifact)
    calls = 0
    async def reply(_db, request):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise asyncio.CancelledError
        packet = json.loads(request.messages[-1].content)
        return SimpleNamespace(content=json.dumps({"context_id": packet["context_id"]}), provider="TEST", model="TEST", is_fallback=False,
            prompt_tokens=1, completion_tokens=1, cost_usd=None)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=reply)), \
         patch.object(annotations_module, "stage_semantic_annotations", wraps=stage_semantic_annotations) as stage, pytest.raises(asyncio.CancelledError):
        await annotations_module.propose_source_semantics(AsyncMock(), artifact, "TEST", "TEST", "TEST", document=document,
            context_policy={"max_units": 8, "max_calls": 64, "max_packets": 64, "max_total_bytes": 2000000})
    assert calls == 2
    stage.assert_not_called()
    assert artifact == before


@pytest.mark.asyncio
async def test_v1_hash_recipe_remains_unchanged_but_unresolved_needs_review(pair):
    from app.modules.knowledge.services.semantic_annotations import _digest
    from app.modules.knowledge.services.semantic_store import (
        _apply_snapshot,
        _semantic_hash,
        base_projection,
        effective_snapshot,
    )
    await lifecycle.approve(pair)
    reference, snapshot = await effective_snapshot(pair)
    original_hash = snapshot["semantic_hash"]
    assert snapshot.get("semantic_hash_version", 1) == 1
    old = copy.deepcopy(snapshot)
    old["proposal"]["context_review"] = unresolved()
    old["proposal"]["proposal_hash"] = _digest({k: v for k, v in old["proposal"].items() if k != "proposal_hash"})
    assert _semantic_hash(old) == original_hash  # exact historical recipe; never rewrite saved bytes
    _, base = await base_projection(pair)
    with pytest.raises(AppException) as error:
        _apply_snapshot(base, old, reference)
    assert error.value.code == "SEMANTIC_CONTEXT_REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_reprocess_model_proof_becomes_new_human_issue_not_auto_resolution(pair):
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair
    from app.modules.knowledge.services.semantic_annotations import propose_source_semantics
    from app.modules.knowledge.services.semantic_context_review import make_issue
    artifact = lifecycle.artifact_of(pair)
    old = make_issue(artifact, "missing_context", ["qnu:g"], {"table_ids": [artifact["tables"][0]["id"]]}, "Read additional condition")
    stage_semantic_annotations(artifact, SemanticAnnotations(), context_review={"coverage_complete": True, "issues": [old]})
    async def reply(_db, request):
        packet = json.loads(request.messages[-1].content)
        evidence = next(item for item in packet["evidence"] if item["source_unit_id"] == "qnu:n")
        return SimpleNamespace(content=json.dumps({"context_id": packet["context_id"], "context_followups": [
            {"issue_id": old["issue_id"], "evidence_ids": [evidence["id"]], "reason": "TEST additional source read; human still checks scope"}]}),
            provider="TEST", model="TEST", is_fallback=False, prompt_tokens=1, completion_tokens=1, cost_usd=None)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=reply)):
        pending = await propose_source_semantics(AsyncMock(), artifact, "TEST", "TEST", "TEST", document=await verify_revision_pair(pair))
    issues = pending["context_review"]["issues"]
    assert len(issues) == 1 and issues[0]["kind"] == "scope_confirmation_required"
    assert "qnu:n" in issues[0]["unit_ids"] and pending["status"] == "proposed"
    with pytest.raises(AppException):
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "Generic comment")


@pytest.mark.asyncio
async def test_runner_context_missing_differs_from_specific_scope_review(pair):
    from app.modules.knowledge.services.semantic_context_review import make_issue
    from scripts.verify_semantic_modelops import run_proposal
    async def missing(artifact):
        return stage_semantic_annotations(artifact, SemanticAnnotations(), context_review=unresolved())
    code, report = await run_proposal(copy.deepcopy(lifecycle.artifact_of(pair)), missing, proposal_only=True)
    assert code == 2 and report["status"] == "WAITING_FOR_CONTEXT"
    async def scope(artifact):
        issue = make_issue(artifact, "scope_confirmation_required", ["qnu:g"], {"column_ids": ["c4"]}, "TEST scope review")
        return stage_semantic_annotations(artifact, lifecycle.payload(artifact), context_review={"coverage_complete": True, "issues": [issue]})
    code, report = await run_proposal(copy.deepcopy(lifecycle.artifact_of(pair)), scope)
    assert code == 2 and report["status"] == "WAITING_FOR_REVIEW" and not report["human_approved"]
