"""Regression for observed 82-question failures; no corpus or live providers."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.core.evidence_policy import EvidencePolicy
from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.evidence_contracts import validate_data_instance, verification_contract
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.prose_fallback import answer_from_prose
from app.modules.rag.schemas import AskRequest, AskResponse, RetrievalSnapshot
from app.modules.rag.service import RagService


def test_root_envelope_preserves_negative_verdict_and_exact_identity():
    contract = verification_contract([{"id": "original"}])
    value = {"complete": False, "verdicts": [{"claim_id": "original", "entailed": False,
        "relevant": True, "scope_compatible": False, "reason": "Not established"}]}
    result = validate_data_instance(contract, json.dumps({"$": value}))
    assert not result.complete and not result.verdicts[0].entailed
    assert not result.verdicts[0].scope_compatible
    assert result.verdicts[0].claim_id == "original"


@pytest.mark.parametrize("value", [
    {"$": {"query": "A"}, "query": "B"}, {"$": {"$": {"query": "A"}}},
    {"$": {"query": "A", "properties": {}}}, {"$": "A"},
])
def test_root_envelope_never_merges_or_accepts_schema_or_nested_envelopes(value):
    with pytest.raises((ValidationError, ValueError)):
        validate_data_instance(QueryPlan, json.dumps(value))


@pytest.mark.parametrize("coverage", [None, {}, {"Topic A": True}, {"Wrong topic": True, "Topic B": True}])
def test_requested_topic_coverage_cannot_be_silently_omitted(coverage):
    contract = verification_contract([{"id": "a"}], ["Topic A", "Topic B"])
    value = {"complete": True, "verdicts": [{"claim_id": "a", "entailed": True,
        "relevant": True, "scope_compatible": True, "reason": "Supported"}]}
    if coverage is not None:
        value["topic_coverage"] = coverage
    with pytest.raises(ValidationError):
        contract.model_validate(value)
    value["topic_coverage"] = {"Topic A": True, "Topic B": False}
    assert contract.model_validate(value).topic_coverage["Topic B"] is False


def test_seasonless_scope_is_explicit_without_a_false_historical_prohibition():
    from app.modules.rag.prose_fallback import _prose_payload

    plan = QueryPlan(query="Contact?", historical_reference_allowed=False)
    payload = _prose_payload(plan.query, plan, [], [])
    assert payload["requested"]["years"] == []
    assert "historical_reference_allowed" not in payload["requested"]
    assert payload["question"] == plan.query
    explicit = _prose_payload("Contact in 2026?", plan.model_copy(update={"years": [2026]}), [], [])
    assert explicit["requested"]["years"] == [2026]
    assert explicit["requested"]["historical_reference_allowed"] is False


def test_five_selected_passages_keep_all_proofs_in_bounded_same_source_claims():
    from app.modules.rag.evidence_claims import bind_claims
    from app.modules.rag.evidence_passages import (
        passage_catalog,
        proposal_contract,
        resolve_proposal,
    )

    text = "Alpha rule. Beta rule. Gamma rule. Delta rule. Epsilon rule."
    block = EvidenceBlock(id="p", text=text, binding_id="b", index_revision_id="i",
        source_revision_id="r", title="Source", start=0, end=len(text))
    catalog = passage_catalog([block])
    ids = [key for key in catalog if "." in key]
    draft = proposal_contract(catalog).model_validate({"status": "supported",
        "claims": [{"id": "a", "text": "All rules", "evidence_ids": ids}]})
    proposal = resolve_proposal(draft, catalog, [block])
    assert len(proposal.claims) == 2
    assert all(len(claim.references) <= 4 for claim in proposal.claims)
    assert [ref.quote for claim in proposal.claims for ref in claim.references] == [catalog[key].quote for key in ids]
    bound, errors = bind_claims(proposal, [block])
    assert len(bound) == 2 and not errors


@pytest.mark.asyncio
async def test_zero_reranker_results_still_attempt_independent_canonical_binding():
    req = AskRequest(question="Which documents are required?", collection_id="c",
        reranker_policy={"enabled": True, "score_threshold": 0.8})
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="c", binding_revisions={"b": "i"})
    body = EvidenceBlock(id="p", binding_id="b", index_revision_id="i", source_revision_id="r",
        title="Source", text="Required documents include application Alpha and form Beta.", start=0, end=63)
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=[body])),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=QueryPlan(
              query=req.question, attribute="required documents"))),
          patch("app.modules.rag.prose_fallback.bounded_rerank", AsyncMock(return_value=[])),
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock(return_value=(
              SimpleNamespace(status="missing"), [], [], False))) as propose):
        assert await answer_from_prose(None, req, snapshot, EvidencePolicy(), "NO_HYBRID_CONTEXT") is None
    assert propose.await_args.args[3] == [body]
    assert req._retrieval_diagnostics["prose_fallback"]["rerank_empty"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("recovered", [True, False])
async def test_empty_hybrid_checks_same_snapshot_before_refusing(recovered):
    req = AskRequest(question="Học bạ được tính những lớp nào?", collection_id="c")
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="c", binding_revisions={"b": "i"})
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={})
    answer = AskResponse(status="answered", answer="Verified passage") if recovered else None
    with (patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot)),
          patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.decide_table_answer", return_value=None),
          patch("app.modules.rag.service.load_row_anchors", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.hybrid_retriever.retrieve", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.semantic_cache.get", AsyncMock(return_value=None)),
          patch("app.modules.rag.prose_fallback.answer_from_prose", AsyncMock(return_value=answer)) as fallback):
        result = await RagService().ask(db, req)
    fallback.assert_awaited_once()
    assert fallback.await_args.args[2] is snapshot
    assert result.status == ("answered" if recovered else "insufficient_context")
    if not recovered:
        assert result.answer_decision["reason"] == "NO_VERIFIED_CONTEXT"
        assert "hiện chưa có trong" not in result.answer and not result.citations


@pytest.mark.parametrize("module", ["admissions", "library", "general", "custom"])
def test_unverified_refusal_does_not_publish_contacts_or_claim_absence(module):
    answer = citation_guard.get_no_answer_response(module)
    assert not any(char.isdigit() for char in answer)
    assert "@" not in answer and "hiện không có" not in answer and "hiện chưa có" not in answer


def test_compact_claims_preserve_exact_proofs_order_unknown_year_and_foreign_revision():
    from copy import deepcopy

    from app.modules.rag.evidence_context import compact_claim_context

    ref = {"block_id": "body", "quote": "Threshold 0.75; not guaranteed.", "source_revision_id": "r",
        "binding_id": "b", "index_revision_id": "i", "canonical_hash": "hash", "start": 0, "end": 37,
        "temporal_scope": {"status": "unknown", "data_years": []}, "origin": "canonical"}
    foreign = {**ref, "source_revision_id": "other"}
    claims = [{"id": "a", "text": ref["quote"], "references": [ref, foreign]},
              {"id": "b", "text": "Not guaranteed.", "references": [ref]}]
    before = deepcopy(claims)
    output = compact_claim_context({"question": "Threshold?"}, claims)
    assert claims == before
    assert len(output["reference_catalog"]) == 2
    assert output["claims"][0]["references"] == ["ref0", "ref1"]
    assert output["claims"][1]["references"] == ["ref0"]
    assert output["reference_catalog"]["ref0"]["quote"] == ref["quote"]
    assert output["reference_catalog"]["ref0"]["temporal_scope"] == {"status": "unknown"}
    assert output["reference_catalog"]["ref1"]["source_revision_id"] == "other"
    assert len(json.dumps(output)) < len(json.dumps({"question": "Threshold?", "claims": claims}))


@pytest.mark.asyncio
async def test_compact_verifier_resolves_all_proofs_but_keeps_negative_verdict():
    from app.modules.rag.evidence_verification import verify_bound_answer

    reference = {"block_id": "p", "quote": "Condition Alpha is required.", "source_revision_id": "r",
        "binding_id": "b", "index_revision_id": "i", "canonical_hash": "hash", "start": 0, "end": 28}
    claim = {"id": "a", "text": reference["quote"], "references": [reference]}
    block = EvidenceBlock(id="p", text=reference["quote"], binding_id="b", index_revision_id="i",
        source_revision_id="r", title="Source", start=0, end=28)
    response = SimpleNamespace(content=json.dumps({"complete": False, "verdicts": [{"claim_id": "a",
        "entailed": False, "relevant": True, "scope_compatible": False, "reason": "Not applicable"}]}),
        model="internal", provider="internal")
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(return_value=response)) as generate:
        verified = await verify_bound_answer(None, AskRequest(question="Conditions?", collection_id="c"),
            {"compact_passages": True}, [claim], [block], QueryPlan(query="Conditions?"), [])
    assert not verified.complete and not verified.claims
    sent = json.loads(generate.await_args.args[1].messages[1].content)
    assert sent["claims"][0]["references"] == ["ref0"]
    assert sent["reference_catalog"]["ref0"]["quote"] == reference["quote"]
    assert claim["references"] == [reference]
