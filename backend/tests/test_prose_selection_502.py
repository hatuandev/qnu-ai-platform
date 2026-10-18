"""Topic/context/audit regression; synthetic sources and no live dependencies."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.evidence_policy import EvidencePolicy
from app.core.exceptions import AppException
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.prose_fallback import answer_from_prose
from app.modules.rag.prose_selection import distinct_candidates, merge_candidates, topic_order
from app.modules.rag.response_audit import (
    VisibleAnswerAudit,
    VisibleAssertion,
    audit_visible_answer,
    validate_assertions,
)
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def block(key, text, start=0, **update):
    values = {"id": key, "text": text, "binding_id": "b", "index_revision_id": "i", "source_revision_id": "r",
              "title": "Source", "start": start, "end": start + len(text), "canonical_hash": "hash"}
    return EvidenceBlock(**{**values, **update})


def test_complete_body_topic_match_beats_short_boilerplate_and_filename():
    fee = block("fee", "Service application cost: set separately.")
    heading_only = block("heading", "Set separately.", title="Service application methods")
    useful = block("methods", "Service application methods include route Alpha and route Beta.")
    assert topic_order([fee, heading_only, useful], ["Service application methods"])[0] is useful
    assert topic_order([fee, heading_only], []) == [fee, heading_only]
    # No forced domain labels: arbitrary topics have the same behavior.
    other = block("contact", "Contact channels include email and the reception desk.")
    assert topic_order([fee, other], ["Contact channels"])[0] is other


def test_duplicate_candidates_only_removed_in_identical_source_and_scope():
    first = block("a", "Same paragraph.")
    repeated = first.model_copy(update={"id": "b", "start": 100, "end": 115})
    foreign = first.model_copy(update={"id": "c", "source_revision_id": "other"})
    year = first.model_copy(update={"id": "d", "scope_years": [2025]})
    parent = first.model_copy(update={"id": "e", "parent_id": "other-heading"})
    changed = first.model_copy(update={"id": "f", "text": "Same paragraph!"})
    assert [b.id for b in distinct_candidates([first, repeated, foreign, year, parent, changed])] == ["a", "c", "d", "e", "f"]


def test_channels_share_candidate_ceiling_without_losing_one_channel():
    a, b, c = [block(key, "Rule " + key) for key in "abc"]
    assert merge_candidates([a], [b, c], 2) == [a, b]
    assert merge_candidates([], [b, c], 2) == [b, c]
    assert merge_candidates([a, b], [a, c], 3) == [a, b, c]


@pytest.mark.asyncio
async def test_section_children_survive_short_lexical_competitors_without_crossing_heading():
    from app.modules.rag.evidence_blocks import split_source_blocks

    source = split_source_blocks("## Service application methods\n\nService application methods include Alpha and Beta.\n\n"
        "## Fees\n\nService application methods cost extra.", binding_id="b", index_id="i", source_id="r", title="Source")
    useful, wrong = source[1], source[3]
    req = AskRequest(question="Which service application methods?", collection_id="c", reranker_policy={"enabled": False})
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"})
    plan = QueryPlan(query=req.question, attribute="service application methods", coverage="enumeration")
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=source)),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=plan)),
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock(return_value=(
              SimpleNamespace(status="missing"), [], [], False))) as propose):
        await answer_from_prose(None, req, snapshot, EvidencePolicy(), "VISIBLE_ANSWER_NOT_SUPPORTED")
    assert propose.await_args.args[3][0].id == useful.id
    assert req._retrieval_diagnostics["prose_fallback"]["section_candidates"] == 1
    assert wrong.id != useful.id


@pytest.mark.asyncio
async def test_compact_passages_keep_all_original_ids_quotes_and_source_metadata():
    from app.modules.rag.evidence_claims import propose_bound_claims
    from app.modules.rag.evidence_passages import passage_catalog

    body = block("body", "Rule Alpha. Rule Beta.")
    captured = {}

    async def missing(_db, _req, contract, _instruction, payload, **_kw):
        captured.update(payload)
        return contract(status="missing", claims=[])

    with patch("app.modules.rag.evidence_claims.structured_call", side_effect=missing):
        await propose_bound_claims(None, AskRequest(question="Rules?", collection_id="c"),
            {"compact_passages": True, "evidence": [], "requested": {}}, [body])
    passages = {item["id"]: item["text"] for group in captured["passages"] for item in group["passages"]}
    assert passages == {key: ref.quote for key, ref in passage_catalog([body]).items() if "." in key}
    assert captured["passages"][0]["whole_passage_id"] == "e1"
    assert passage_catalog([body])["e1"].quote == body.text
    assert captured["passages"][0]["source_revision_id"] == body.source_revision_id
    assert "compact_passages" not in captured and "evidence" not in captured


def test_sparse_projection_keeps_false_zero_and_unknown_scope():
    from app.modules.rag.evidence_context import omit_empty_fields

    assert omit_empty_fields({"empty": [], "none": None, "blank": "", "map": {},
        "false": False, "zero": 0, "scope": {"status": "unknown", "data_years": []}}) == {
        "false": False, "zero": 0, "scope": {"status": "unknown"}}


def test_compact_whole_passage_keeps_uncatalogued_short_fragments():
    from app.modules.rag.evidence_passages import compact_passage_payload, passage_catalog

    body = block("body", "No. X.")
    payload = compact_passage_payload([body], passage_catalog([body]))
    assert payload[0]["whole_passage_id"] == "e1" and payload[0]["whole_text"] == body.text


@pytest.mark.asyncio
async def test_section_expansion_cannot_reintroduce_explicit_wrong_data_year():
    from app.modules.rag.evidence_blocks import split_source_blocks

    source = split_source_blocks("## Service methods\n\nService methods for data year 2025: Alpha.",
        binding_id="b", index_id="i", source_id="r", title="Source")
    source[1].scope_years = [2025]
    req = AskRequest(question="Which service methods in 2026?", collection_id="c", reranker_policy={"enabled": False})
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"})
    plan = QueryPlan(query=req.question, years=[2026], attribute="service methods", coverage="enumeration")
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=source)),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=plan)),
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock()) as propose):
        assert await answer_from_prose(None, req, snapshot, EvidencePolicy(), "VISIBLE_ANSWER_NOT_SUPPORTED") is None
    propose.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("code,expected_calls", [("MODEL_CONTEXT_EXCEEDED", 2), ("MODEL_UNAVAILABLE", 1)])
async def test_only_explicit_window_failure_gets_one_atomic_repack(code, expected_calls):
    req = AskRequest(question="Which service methods?", collection_id="c", reranker_policy={"enabled": False}, max_tokens=5000)
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"})
    source = [block(str(i), f"Service methods include route {i}.", start=i * 1000) for i in range(4)]
    plan = QueryPlan(query=req.question, attribute="service methods", coverage="enumeration")
    failure = AppException("Upstream failure", code=code, status_code=502)
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=source)),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=plan)),
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock(side_effect=[failure, failure])) as propose,
          pytest.raises(AppException) as error):
        await answer_from_prose(None, req, snapshot, EvidencePolicy(), "VISIBLE_ANSWER_NOT_SUPPORTED")
    assert error.value.code == code and propose.await_count == expected_calls
    if expected_calls == 2:
        original, fitted = propose.await_args_list
        assert len(original.args[3]) == 4 and len(fitted.args[3]) == 1
        assert original.args[1].max_tokens == fitted.args[1].max_tokens == 5000
        assert original.args[2]["requested"] == fitted.args[2]["requested"]
        assert {b.id for b in fitted.args[3]} <= {b.id for b in original.args[3]}


@pytest.mark.asyncio
async def test_window_repack_never_splits_atomic_list_to_force_a_response():
    req = AskRequest(question="Which service methods?", collection_id="c", reranker_policy={"enabled": False})
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"})
    source = [block(str(i), f"- Service methods route {i}.", start=i * 1000) for i in range(4)]
    plan = QueryPlan(query=req.question, attribute="service methods", coverage="enumeration")
    failure = AppException("Too long", code="MODEL_CONTEXT_EXCEEDED", status_code=502)
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=source)),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=plan)),
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock(side_effect=failure)) as propose,
          pytest.raises(AppException) as error):
        await answer_from_prose(None, req, snapshot, EvidencePolicy(), "VISIBLE_ANSWER_NOT_SUPPORTED")
    assert error.value.code == "MODEL_CONTEXT_EXCEEDED" and propose.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("configured", [False, True])
async def test_recovery_uses_configured_budget_and_keeps_topic_rank_after_reranking(configured):
    req = AskRequest(question="Which service application methods are available?", collection_id="c",
        max_tokens=5000, reranker_policy={"enabled": True})
    if configured:
        req.runtime_policy = {"knowledge_policy": {"retrieval_policy": {
            "profile": "configured", "max_context_chars": 18000, "context_top_k": 6}}}
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"})
    useful = block("body", "Service application methods: " + "Supported route with required conditions. " * 170)
    fee = block("fee", "Service application cost: set separately.", start=12000)
    plan = QueryPlan(query=req.question, attribute="service application methods", coverage="enumeration",
                     enumeration_subject="service application methods", requested_topics=["service application methods"])

    async def reverse_rank(_query, candidates, *_args):
        return list(reversed(candidates))  # Reranker short-paragraph preference must not win packing again.

    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=[useful, fee])),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=plan)),
          patch("app.modules.rag.prose_fallback.bounded_rerank", side_effect=reverse_rank) as rank,
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock(return_value=(
              SimpleNamespace(status="missing"), [], [], False))) as propose):
        assert await answer_from_prose(None, req, snapshot, EvidencePolicy(), "VISIBLE_ANSWER_NOT_SUPPORTED") is None
    assert rank.await_args.args[0] == plan.attribute + "\n" + req.question
    selected = propose.await_args.args[3]
    assert selected[0].id == useful.id and selected[0].text == useful.text
    assert propose.await_args.args[1].max_tokens == 5000
    trace = req._retrieval_diagnostics["prose_fallback"]
    assert trace["max_context_chars"] == (18000 if configured else 36000)
    assert trace["context_limit"] == (6 if configured else 10)
    assert trace["packing"]["packed_characters"] > 6000


@pytest.mark.asyncio
async def test_recovery_respects_small_explicit_budget_and_does_not_cut_a_list():
    req = AskRequest(question="Which routes?", collection_id="c", reranker_policy={"enabled": False},
        runtime_policy={"knowledge_policy": {"retrieval_policy": {
            "profile": "configured", "context_top_k": 2, "max_context_chars": 1000}}})
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"})
    source = [block(str(i), f"- Route {label}: " + "condition " * 60, start=i * 1000)
              for i, label in enumerate(("Alpha", "Beta", "Gamma"))]
    plan = QueryPlan(query=req.question, attribute="Route", coverage="enumeration", enumeration_subject="Route")
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=source)),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=plan)),
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock()) as propose):
        assert await answer_from_prose(None, req, snapshot, EvidencePolicy(), "VISIBLE_ANSWER_NOT_SUPPORTED") is None
    propose.assert_not_awaited()
    assert req._retrieval_diagnostics["prose_fallback"]["packing"]["dropped"]


def test_answer_span_reflow_does_not_reject_whitespace_only_changes():
    assertion = VisibleAssertion(answer_quote="Requirement A. Requirement B.", evidence_id="e0",
        evidence_quote="Requirement A. Requirement B.", entailed=True, relevant=True)
    evidence = {"e0": "Requirement A.\nRequirement B."}
    assert validate_assertions("Requirement A.\n\nRequirement B.", evidence, [assertion])[0]
    assert not validate_assertions("Requirement A. No requirement B.", evidence, [assertion])[0]


@pytest.mark.asyncio
async def test_negative_semantics_are_not_misreported_as_invalid_evidence_ids():
    req = AskRequest(question="Metric?", collection_id="c")
    snap = RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"})
    audit = VisibleAnswerAudit(all_assertions_supported=False, answers_original_question=True,
        essential_conditions_retained=True, conflict=False, evidence_ids=["e0"], assertions=[
            VisibleAssertion(answer_quote="Metric is 20.", evidence_id="e0",
                evidence_quote="Other metric is 20.", entailed=False, relevant=False)])
    candidate = FusionCandidate("x", "b", "Other metric is 20.", 1, binding_id="b", index_revision_id="i")
    with patch("app.modules.rag.response_audit.structured_call", AsyncMock(return_value=audit)):
        result = await audit_visible_answer(None, req, snap, "Metric is 20.", [candidate])
    assert result["evidence_ids_valid"] and not result["atomic_spans_valid"] and not result["accepted"]
    assert result["unsupported_assertions"] == 1 and result["quote_mismatch_count"] == 0
    assert "Other metric" not in str(result)  # No raw quote duplicated in diagnostics.


@pytest.mark.asyncio
async def test_visible_audit_honors_same_context_policy_instead_of_hidden_12000():
    req = AskRequest(question="What is the rule?", collection_id="c", runtime_policy={
        "knowledge_policy": {"retrieval_policy": {"profile": "configured", "max_context_chars": 18000}}})
    snap = RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"})
    long_proof = "Source context. " * 800 + "Rule A."
    candidate = FusionCandidate("x", "b", long_proof, 1, binding_id="b", index_revision_id="i")
    audit = VisibleAnswerAudit(all_assertions_supported=True, answers_original_question=True,
        essential_conditions_retained=True, conflict=False, evidence_ids=["e0"], assertions=[
            VisibleAssertion(answer_quote="Rule A.", evidence_id="e0", evidence_quote="Rule A.", entailed=True, relevant=True)])
    with patch("app.modules.rag.response_audit.structured_call", AsyncMock(return_value=audit)) as call:
        result = await audit_visible_answer(None, req, snap, "Rule A.", [candidate])
    assert result["accepted"] and call.await_args.args[4]["evidence"][0]["text"] == long_proof
    assert result["max_context_chars"] == 18000
