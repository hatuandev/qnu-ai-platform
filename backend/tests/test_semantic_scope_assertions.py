"""Independent scopes and review gates; all decisions below are synthetic TEST intent."""
import copy

import pytest

import tests.test_semantic_lifecycle as lifecycle
from app.core.exceptions import AppException
from app.modules.knowledge.normalization.retrieval_models import UnitManifest
from app.modules.knowledge.normalization.retrieval_units import validate_manifest
from app.modules.knowledge.normalization.structure_chunks import structure_chunks
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    _validated_copy,
    apply_reviewed_semantics,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_evidence import make_binding, source_text
from app.modules.knowledge.services.semantic_store import rebuild_projection, record_decision
from app.modules.knowledge.services.source_links import unit_context_ids
from tests.test_semantic_selector_v2 import case, decision

pair, storage = lifecycle.pair, lifecycle.storage
database = lifecycle.database


def assertion(artifact, quote, *, scope="row", rows=None, columns=None, related=None):
    text = source_text(artifact, "qnu:g")
    start = text.index(quote)
    return {"note_unit_id": "qnu:g", "evidence_quote": quote,
        "evidence_binding": make_binding(artifact, "qnu:g", start, start + len(quote)).model_dump(),
        "table_id": artifact["tables"][0]["id"], "scope": scope,
        "row_unit_ids": rows or [], "column_ids": columns or [],
        "assertion_version": 1, "related_evidence": related or []}


def texts(manifest, row, column=None):
    units = {u.id: u for u in manifest.units}
    return [units[uid].text for uid in unit_context_ids(manifest, row, column)]


def test_T01_mixed_source_unit_never_spreads_other_assertions():
    clauses = ["1. General units are students.", "2. Group A equipment only in 2027, never group B.",
        "3. AM-0007 only, never AM-0070."]
    artifact, _ = case("\n".join(clauses))
    notes = [assertion(artifact, clauses[0], scope="table"),
        assertion(artifact, clauses[1], scope="group", rows=["qnu:r1"]),
        assertion(artifact, clauses[2], rows=["qnu:r1"])]
    revised = _validated_copy(artifact, SemanticAnnotations(notes=notes))
    manifest = UnitManifest.model_validate(revised["retrieval_units"])
    assert all(clause in texts(manifest, "qnu:r1") for clause in clauses)
    assert clauses[0] in texts(manifest, "qnu:r2")
    assert all(clause not in texts(manifest, "qnu:r2") for clause in clauses[1:])
    assert "\n".join(clauses) not in texts(manifest, "qnu:r2")


def test_T03_T04_year_groups_and_estimate_are_independent_in_facts_and_chunks():
    clauses = ["2025 closes on 31/12/2025.", "2026 closes on 30/09/2026.",
        "2027 is planned, not accepted.", "Estimate only, not recorded in 2025 or 2026."]
    artifact, _ = case(" ".join(clauses))
    cols = [c["id"] for c in artifact["tables"][0]["columns"]]
    notes = [assertion(artifact, text, scope="column", columns=[cols[index]]) for index, text in enumerate(clauses)]
    revised = _validated_copy(artifact, SemanticAnnotations(notes=notes))
    manifest = UnitManifest.model_validate(revised["retrieval_units"])
    for index, text in enumerate(clauses):
        context = texts(manifest, "qnu:r1", cols[index])
        assert text in context and all(other not in context for other in clauses if other != text)
    for fact in revised["facts"]:
        raw = fact["raw_data"]
        if raw["column_id"] in cols[:4]:
            assert set(raw["context_unit_ids"]) == set(unit_context_ids(manifest, raw["source_unit_id"], raw["column_id"]))


def test_T09_same_source_same_target_different_spans_are_not_duplicates():
    artifact, _ = case("First rule. Second rule.")
    notes = [assertion(artifact, text, scope="table") for text in ("First rule.", "Second rule.")]
    revised = _validated_copy(artifact, SemanticAnnotations(notes=notes))
    assert len(set(revised["context_graph"]["links"]["qnu:r1"])) >= 2
    with pytest.raises(ValueError, match="Duplicate"):
        _validated_copy(artifact, SemanticAnnotations(notes=[notes[0], notes[0]]))


@pytest.mark.parametrize("same_span", [True, False])
def test_T01_cell_interpretation_requires_the_exact_scoped_assertion_span(same_span):
    artifact, _ = case("Remarks do not apply. Separate instruction for another target.")
    quote = "Remarks do not apply."
    note = assertion(artifact, quote, scope="column", rows=["qnu:r2"], columns=["c7"])
    evidence = note if same_span else assertion(artifact, "Separate instruction for another target.")
    proposals = SemanticAnnotations(notes=[note], cells=[{"row_unit_id": "qnu:r2", "column_id": "c7",
        "raw": "Theo quy chế.", "state": "not_applicable", "evidence_unit_id": "qnu:g",
        "evidence_quote": evidence["evidence_quote"], "evidence_binding": evidence["evidence_binding"]}])
    if same_span:
        revised = _validated_copy(artifact, proposals)
        assert revised["tables"][0]["row_fields"][1][6]["state"] == "not_applicable"
    else:
        with pytest.raises(ValueError, match="explicitly scoped evidence"):
            _validated_copy(artifact, proposals)


def test_T10_new_assertion_always_requires_specific_human_scope_review():
    artifact, _ = case("General units. Separate exception.")
    pending = stage_semantic_annotations(artifact, SemanticAnnotations(notes=[assertion(artifact, "General units.", scope="table")]))
    issues = pending["context_review"]["issues"]
    assert len(issues) == 1 and issues[0]["review_evidence"][0]["evidence_quote"] == source_text(artifact, "qnu:g")
    with pytest.raises(AppException, match="ngữ cảnh"):
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "Agree generally")


@pytest.mark.parametrize("change", ["quote", "binding", "unbound", "related"])
def test_T09_bad_assertion_or_reference_cannot_be_staged(change):
    artifact, _ = case("General rule. Exclusion must remain.")
    note = assertion(artifact, "General rule.", scope="table")
    if change == "quote": note["evidence_quote"] = "invented"
    if change == "binding": note["evidence_binding"]["end"] += 1
    if change == "unbound": note["evidence_binding"] = None
    if change == "related":
        bad = copy.deepcopy(note["evidence_binding"]); bad["text_sha256"] = "0" * 64
        note["related_evidence"] = [bad]
    with pytest.raises(ValueError):
        stage_semantic_annotations(artifact, SemanticAnnotations(notes=[note]))


async def test_T02_T08_T11_persist_reload_rebuild_exact_span_and_string_codes(pair, storage):
    base = lifecycle.artifact_of(pair)
    text = source_text(base, "qnu:g")
    note = assertion(base, text, rows=["qnu:r1"])
    staged = copy.deepcopy(base)
    pending = stage_semantic_annotations(staged, SemanticAnnotations(notes=[note]))
    pair.parse_provenance = {**pair.parse_provenance, "structured_artifact": staged}
    approved = await record_decision(pair, staged, pending["proposal_hash"], "TEST-researcher", "TEST exact source scope", "approved",
        context_decisions=[decision(issue) for issue in pending["context_review"]["issues"]])
    before_fields = copy.deepcopy(base["tables"])
    from unittest.mock import patch

    from app.core.storage import LocalStorageDriver
    with patch("app.modules.knowledge.services.semantic_store.storage_service", LocalStorageDriver(str(storage.base_path))):
        canonical, rebuilt = await rebuild_projection(pair)
    manifest = UnitManifest.model_validate(rebuilt["retrieval_units"])
    validate_manifest(manifest, canonical)
    assert rebuilt["tables"] == before_fields
    assert texts(manifest, "qnu:r1").count(text) == 1 and text not in texts(manifest, "qnu:r2")
    chunks = structure_chunks(canonical, manifest, context_graph=rebuilt["context_graph"])
    assert any(text in chunk["content"] for chunk in chunks if chunk["metadata"]["source_unit_id"] == "qnu:r1")
    assert approved["semantic_effective"] == rebuilt["semantic_effective"]


def reference_case(relevance="related"):
    from app.modules.knowledge.services.semantic_assertions import assertion_identity
    from app.modules.knowledge.services.semantic_context_review import make_issue
    artifact, _ = case("Group B exception, never group A. All conditions remain required.")
    reference_unit = "qnu:g"
    if relevance == "unrelated":
        import tests.test_semantic_proposals as fixture
        from app.modules.knowledge.normalization.qnu_markdown import QnuBlock
        from app.modules.knowledge.normalization.qnu_projection import project_document
        document = fixture.fixture.fixture_document()
        document.blocks[-1].body = "Group B exception, never group A. All conditions remain required."
        document.blocks.append(QnuBlock(id="unrelated", type="text",
            body="Library opening hours apply to the separate visitor notice only; they do not govern program assessment.",
            source_locations=document.blocks[-1].source_locations))
        _, artifact = project_document(document, fixture.fixture.reference(), {})
        reference_unit = "qnu:unrelated"
    note = SemanticAnnotations(notes=[assertion(artifact, "Group B exception, never group A.", rows=["qnu:r2"])])
    issue = make_issue(artifact, "deferred_reference", [reference_unit], {"table_ids": [artifact["tables"][0]["id"]]}, "Check reference against exact target")
    evidence = issue["review_evidence"][0]
    assessment = {"issue_id": issue["issue_id"], "relevance": relevance,
        "assertion_ids": [assertion_identity(note.notes[0])] if relevance == "related" else [],
        "evidence": [evidence], "reason": "TEST checked all conditions against the specific assertion"}
    pending = stage_semantic_annotations(artifact, note, context_review={"issues": [issue], "reference_assessments": [assessment]})
    return artifact, pending, assessment


@pytest.mark.parametrize("relevance,action", [("related", "related_context_reviewed"), ("unrelated", "not_applicable_to_target")])
def test_T05_T06_reference_analysis_is_not_approval_and_accepts_only_specific_intent(relevance, action):
    artifact, pending, assessment = reference_case(relevance)
    before = copy.deepcopy(artifact)
    with pytest.raises(AppException):
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "Agree generally")
    assert artifact == before
    requests = []
    for issue in pending["context_review"]["issues"]:
        intent = decision(issue)
        if issue["kind"] == "deferred_reference":
            intent.update(action=action, supporting_evidence=[e["evidence_binding"] for e in assessment["evidence"]])
        requests.append(intent)
    applied = apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "TEST specific reference checked", context_decisions=requests)
    assert applied["semantic_annotations"]["status"] == "verified"


@pytest.mark.parametrize("change", ["not_applicable", "no_body", "wrong_body", "insufficient"])
def test_T05_T07_cannot_clear_related_reference_with_unrelated_or_missing_evidence(change):
    artifact, pending, assessment = reference_case("insufficient" if change == "insufficient" else "related")
    requests = []
    for issue in pending["context_review"]["issues"]:
        intent = decision(issue)
        if issue["kind"] == "deferred_reference":
            intent.update(action="related_context_reviewed", supporting_evidence=[e["evidence_binding"] for e in assessment["evidence"]])
            if change == "not_applicable": intent["action"] = "not_applicable_to_target"
            if change == "no_body": intent["supporting_evidence"] = []
            if change == "wrong_body": intent["supporting_evidence"][0]["text_sha256"] = "0" * 64
        requests.append(intent)
    with pytest.raises(AppException) as failure:
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "TEST must reject", context_decisions=requests)
    assert failure.value.code == "SEMANTIC_PROPOSAL_INVALID"


def test_T07_heading_expansion_keeps_nested_body_and_respects_budget():
    import tests.test_semantic_proposals as fixture
    from app.modules.knowledge.normalization.qnu_markdown import QnuBlock
    from app.modules.knowledge.normalization.qnu_projection import project_document
    from app.modules.knowledge.services.semantic_context import (
        ContextBuilder,
        SemanticContextPolicy,
    )
    doc = fixture.fixture.fixture_document()
    location = doc.blocks[-1].source_locations
    doc.blocks += [QnuBlock(id="remote", type="section", body="## Remote exception", source_locations=location),
        QnuBlock(id="nested", parent_id="remote", type="section", body="### Conditions", source_locations=location),
        QnuBlock(id="body", parent_id="nested", type="text", body="Only group B. Never group A. Valid for thirty days.", source_locations=location)]
    _, artifact = project_document(doc, fixture.fixture.reference(), {})
    builder = ContextBuilder(artifact, doc)
    review = builder.review_context(["qnu:remote"], [artifact["tables"][0]["id"]])
    assert {u["id"] for u in review["units"]} == {"qnu:remote", "qnu:nested", "qnu:body"}
    assert not review["heading_without_body"]
    packet = builder.packets([artifact["tables"][0]["id"]])[0]
    if "qnu:body" not in packet["_unit_ids"]:
        expanded = builder.expand(packet, ["qnu:remote"])
        assert "qnu:body" in expanded["_unit_ids"]
    with pytest.raises(ValueError, match="BYTES_BUDGET"):
        ContextBuilder(artifact, doc, SemanticContextPolicy(max_total_bytes=2000)).review_context(["qnu:remote"], [artifact["tables"][0]["id"]])
    doc.blocks = [b for b in doc.blocks if b.id != "body"]
    _, empty = project_document(doc, fixture.fixture.reference(), {})
    assert ContextBuilder(empty, doc).review_context(["qnu:remote"], [empty["tables"][0]["id"]])["heading_without_body"] == ["qnu:remote"]


def test_T01_selector_v2_blocks_whole_numbered_unit_but_keeps_full_item_negation():
    from app.modules.knowledge.services.semantic_binding import bind_model_proposals
    from tests.test_semantic_selector_v2 import V2, wire
    artifact, packet = case("1. General units.\n2. Group A only, never group B.")
    with pytest.raises(ValueError, match="REQUIRES_ASSERTIONS"):
        bind_model_proposals(artifact, packet, wire(packet, version=V2, scope="table"), review_issues=[] ,selector_contract=V2)
    assert any(e["text"] == "2. Group A only, never group B." for e in packet["evidence"])


async def test_T11_test_actor_handler_db_reload_keeps_assertion_and_reference(database):
    from app.modules.knowledge.models import KnowledgeSourceRevision
    from app.modules.knowledge.schemas import SemanticProposalReviewRequest
    from app.modules.knowledge.services.semantic_annotations import review_semantic_proposals
    from app.modules.knowledge.services.semantic_store import semantic_fingerprint
    col, binding, rid = database.ids
    async with database.factory() as db:
        revision = await db.get(KnowledgeSourceRevision, rid)
        base = lifecycle.artifact_of(revision)
        staged = copy.deepcopy(base)
        reference = source_text(base, "qnu:n")
        note = assertion(base, source_text(base, "qnu:g"), rows=["qnu:r1"],
            related=[make_binding(base, "qnu:n", 0, len(reference)).model_dump()])
        from app.modules.knowledge.services.semantic_assertions import assertion_identity
        from app.modules.knowledge.services.semantic_context_review import make_issue
        annotation = SemanticAnnotations(notes=[note])
        issue = make_issue(base, "deferred_reference", ["qnu:n"], {"table_ids": [base["tables"][0]["id"]]}, "TEST read related condition")
        assessment = {"issue_id": issue["issue_id"], "relevance": "related",
            "assertion_ids": [assertion_identity(annotation.notes[0])], "reason": "TEST verified complete reference",
            "evidence": issue["review_evidence"]}
        pending = stage_semantic_annotations(staged, annotation,
            context_review={"issues": [issue], "reference_assessments": [assessment]})
        revision.parse_provenance = {**revision.parse_provenance, "structured_artifact": staged}
        await db.commit()
        intents = []
        for item in pending["context_review"]["issues"]:
            intent = decision(item)
            if item["kind"] == "deferred_reference":
                intent.update(action="related_context_reviewed", supporting_evidence=[e["evidence_binding"] for e in assessment["evidence"]])
            intents.append(intent)
        await review_semantic_proposals(db, col, binding, rid, SemanticProposalReviewRequest(decision="approved",
            expected_semantic_proposal_hash=pending["proposal_hash"], comment="TEST independently checked source",
            context_decisions=intents), lifecycle.actor())
        fingerprint = semantic_fingerprint(lifecycle.artifact_of(revision))
    async with database.factory() as db:
        reloaded = await db.get(KnowledgeSourceRevision, rid)
        rebuilt = (await rebuild_projection(reloaded))[1]
        assert semantic_fingerprint(rebuilt) == fingerprint
        manifest = UnitManifest.model_validate(rebuilt["retrieval_units"])
        assert reference in texts(manifest, "qnu:r1")
        assert all(u.semantic_scope.get("row_unit_ids") == ["qnu:r1"] for u in manifest.units if u.semantic_scope)
        assert reloaded.status == "review_required"


@pytest.mark.parametrize("tamper", ["file", "proposal", "source"])
def test_T09_checkpoint_file_envelope_and_source_hash_tampering_are_rejected(tmp_path, tamper):
    import hashlib
    import json

    from app.modules.knowledge.services.semantic_evidence import source_identity
    from scripts.prepare_semantic_review_checkpoint import verify_checkpoint
    artifact, _ = case("TEST source with an independent exception.")
    pending = stage_semantic_annotations(artifact, SemanticAnnotations(notes=[assertion(artifact, "TEST source", scope="table")]))
    from app.modules.knowledge.services.semantic_annotations import semantic_input_hash
    def write(name, value):
        (tmp_path / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    write("before.json", artifact)
    write("proposal.json", pending)
    write("checkpoint.json", {"proposal_hash": pending["proposal_hash"], "input_hash": semantic_input_hash(artifact), "source": source_identity(artifact)})
    def seal():
        write("manifest.json", {name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
            for name in ["before.json", "proposal.json", "checkpoint.json"]})
    seal()
    assert verify_checkpoint(tmp_path)["proposal"]["proposal_hash"] == pending["proposal_hash"]
    if tamper in {"file", "proposal"}:
        pending["model"] = {"tampered": True}
        write("proposal.json", pending)
    else:
        artifact["tables"][0]["row_fields"][0][0]["raw"] = "changed"
        write("before.json", artifact)
    if tamper != "file": seal()
    with pytest.raises(ValueError, match="CHECKPOINT_"):
        verify_checkpoint(tmp_path)
