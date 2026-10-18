"""Scope-safe span audit, whole-group packing and public/proof role separation."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.modules.rag.evidence_blocks import pack_context
from app.modules.rag.evidence_claims import bind_claims
from app.modules.rag.evidence_passages import (
    passage_catalog,
    proposal_contract,
    resolve_proposal,
    source_grounded_claims,
)
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.response_audit import answer_spans, audit_visible_answer, span_audit_contract
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def block(key, text, start=0, **values):
    return EvidenceBlock(id=key, text=text, binding_id="b", index_revision_id="i", source_revision_id="r",
        title="Official", start=start, end=start + len(text), canonical_hash="hash", **values)


@pytest.mark.asyncio
@pytest.mark.parametrize("entailed", [True, False])
async def test_server_owned_answer_ids_keep_exact_text_and_negative_verdict(entailed):
    answer = "Applicants must rank this program first. Other ranks are excluded."
    spans = answer_spans(answer)
    value = {"all_assertions_supported": entailed, "answers_original_question": True,
        "essential_conditions_retained": True, "conflict": False, "evidence_ids": ["e0"],
        "assertions": [{"answer_span_id": key, "evidence_id": "e0", "evidence_quote": span,
            "entailed": entailed, "relevant": True} for key, span in spans.items()]}
    req = AskRequest(question="Which rank?", collection_id="c")
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="c", binding_revisions={"b": "i"})
    candidate = FusionCandidate("chunk", "b", answer, 1, binding_id="b", index_revision_id="i")

    async def audit(_db, _req, contract, _instruction, payload, **kwargs):
        assert payload["answer"] == answer and payload["answer_spans"] == spans
        return contract.model_validate(value)

    with patch("app.modules.rag.response_audit.structured_call", side_effect=audit):
        result = await audit_visible_answer(None, req, snapshot, answer, [candidate])
    assert result["accepted"] is entailed
    assert result["answer_span_mismatch_count"] == 0
    assert result["candidate_ids"] == ["chunk"]


@pytest.mark.parametrize("mutation", ["unknown", "missing", "duplicate", "false_quote"])
def test_span_contract_rejects_missing_foreign_or_invented_support(mutation):
    contract = span_audit_contract({"a0": "Rule A.", "a1": "Rule B."}, {"e0": "Rule A. Rule B."})
    checks = [{"answer_span_id": key, "evidence_id": "e0", "evidence_quote": text,
        "entailed": True, "relevant": True} for key, text in [("a0", "Rule A."), ("a1", "Rule B.")]]
    if mutation == "unknown":
        checks[1]["answer_span_id"] = "invented"
    elif mutation == "missing":
        checks.pop()
    elif mutation == "duplicate":
        checks[1]["answer_span_id"] = "a0"
    else:
        checks[0]["evidence_quote"] = "Rule NOT A."
    with pytest.raises(ValidationError):
        contract.model_validate({"all_assertions_supported": True, "answers_original_question": True,
            "essential_conditions_retained": True, "conflict": False, "assertions": checks})


def test_whole_atomic_group_over_k_is_opt_in_bounded_and_not_sliced():
    sources = [block("parent", "1. Calculation rule:")]
    sources += [block(str(i), "formula or legend " + str(i), start=100 * i) for i in range(1, 8)]
    unrelated = block("other", "2. An unrelated event.", start=1000)
    sources.append(unrelated)
    assert pack_context(sources, sources[:1], [], 5, 36000) == []
    trace = {}
    selected = pack_context(sources, [sources[0], unrelated], [], 5, 36000,
        allow_first_whole_group=True, diagnostics=trace)
    assert {b.id for b in selected} == {b.id for b in sources[:-1]}
    assert trace["whole_group_exceeds_block_k"] is True
    assert pack_context(sources, sources[:1], [], 5, 100, allow_first_whole_group=True) == []


def test_context_proof_is_not_promoted_to_public_fact_but_stays_bound():
    body = block("body", "The exam is required.")
    heading = block("heading", "## Program Alpha in 2026", start=100)
    catalog = passage_catalog([body, heading])
    draft = proposal_contract(catalog).model_validate({"status": "supported", "claims": [{
        "id": "a", "text": "Exam", "evidence_ids": ["e1"], "context_ids": ["e2"]}]})
    proposal = resolve_proposal(draft, catalog, [body, heading], separate_context=True)
    bound, errors = bind_claims(proposal, [body, heading])
    assert not errors
    public = source_grounded_claims(bound, [body, heading], primary_only=True)
    assert [c["text"] for c in public] == [body.text]
    assert {r["block_id"] for r in public[0]["references"]} == {"body", "heading"}


def test_context_cannot_borrow_another_sources_year():
    body = block("body", "The exam is required.")
    foreign = body.model_copy(update={"id": "foreign", "source_revision_id": "other", "text": "Year 2026."})
    catalog = passage_catalog([body, foreign])
    draft = proposal_contract(catalog).model_validate({"status": "supported", "claims": [{
        "id": "a", "text": "Exam", "evidence_ids": ["e1"], "context_ids": ["e2"]}]})
    proposal = resolve_proposal(draft, catalog, [body, foreign], separate_context=True)
    bound, errors = bind_claims(proposal, [body, foreign])
    assert not bound and errors


def test_focused_packing_does_not_force_an_entire_sibling_list():
    sources = [block(str(i), f"- Independent choice {i}.", start=100 * i) for i in range(1, 8)]
    assert pack_context(sources, sources[:1], [], 5, 36000, atomic_lists=False) == sources[:1]
    assert pack_context(sources, sources[:1], [], 5, 36000, atomic_lists=True) == []


@pytest.mark.asyncio
async def test_focused_reranker_order_not_undone_by_generic_topic_or_shared_numbers():
    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.prose_fallback import answer_from_prose

    original = "When should I pay the application fee for the initial round?"
    req = AskRequest(question=original, collection_id="c", reranker_policy={"enabled": True})
    req.runtime_policy = {"knowledge_policy": {"retrieval_policy": {
        "profile": "configured", "context_top_k": 1, "max_context_chars": 36000}}}
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="c", binding_revisions={"b": "i"})
    wrong = block("later", "Application fee round 250: later event and payment.")
    right = block("initial", "Initial round application fee payment is due before the published deadline.", start=1000)

    async def rank(query, candidates, *_args):
        assert original in query
        by_id = {c.chunk_id: c for c in candidates}
        return [by_id["initial"], by_id["later"]]

    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=[wrong, right])),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=QueryPlan(
              query=original, attribute="application fee", event="initial round payment"))),
          patch("app.modules.rag.prose_fallback.bounded_rerank", side_effect=rank),
          patch("app.modules.rag.prose_fallback.reference_priority") as priority,
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock(return_value=(
              SimpleNamespace(status="missing"), [], [], False))) as propose):
        await answer_from_prose(None, req, snapshot, EvidencePolicy(), "VISIBLE_ANSWER_NOT_SUPPORTED")
    priority.assert_not_called()
    assert [b.id for b in propose.await_args.args[3]] == ["initial"]
