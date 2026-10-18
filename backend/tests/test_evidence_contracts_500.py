"""Schema-echo mitigation and exact verdict IDs without live inference."""

import json
from types import SimpleNamespace
from typing import Literal
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel, Field, ValidationError

from app.core.exceptions import AppException
from app.modules.rag.evidence_blocks import split_source_blocks
from app.modules.rag.evidence_claims import bind_claims
from app.modules.rag.evidence_contracts import data_field_guide, verification_contract
from app.modules.rag.evidence_indexed_audit import audit_contract
from app.modules.rag.evidence_model import structured_call
from app.modules.rag.evidence_schemas import (
    AnswerProposal,
    EvidenceClaim,
    QueryPlan,
    QuoteReference,
)
from app.modules.rag.evidence_verification import verify_bound_answer
from app.modules.rag.schemas import AskRequest


def request():
    return AskRequest(question="What are the requirements?", collection_id="test",
                      preferred_provider_id="internal", preferred_model_name="configured")


def result(content):
    return SimpleNamespace(content=content if isinstance(content, str) else json.dumps(content),
                           provider="internal", model="configured")


def verdict(key, supported=True):
    return {"claim_id": key, "entailed": supported, "relevant": True,
            "scope_compatible": True, "reason": "Evaluated from own source"}


def bound():
    blocks = split_source_blocks("Applicants must satisfy condition A.\n\nApplicants must satisfy condition B.",
        binding_id="b", index_id="i", source_id="s", title="Official")
    proposal = AnswerProposal(status="supported", claims=[EvidenceClaim(id=f"claim-{index}",
        text=block.text, references=[QuoteReference(block_id=block.id, quote=block.text)])
        for index, block in enumerate(blocks)])
    claims, errors = bind_claims(proposal, blocks)
    assert not errors and len(claims) == 2
    return blocks, claims


def test_data_guide_resolves_nested_types_and_keeps_constraints_without_schema_blob():
    class Item(BaseModel):
        key: Literal["first", "second"]
        quote: str = Field(min_length=3, max_length=4000)
    class Output(BaseModel):
        items: list[Item] = Field(min_length=1, max_length=2)
        coverage: dict[str, bool]
        optional: int | None = None
    guide = data_field_guide(Output)
    assert "$.items (required): array of (object at $.items[]" in guide
    assert 'one of ["first", "second"]' in guide
    assert '"minLength": 3' in guide and '"maxLength": 4000' in guide
    assert '"minItems": 1' in guide and '"maxItems": 2' in guide
    assert "$.coverage other keys: boolean" in guide
    assert "optional (optional): integer OR null" in guide
    assert '"$defs"' not in guide and '"properties"' not in guide


@pytest.mark.asyncio
async def test_schema_echo_repairs_once_with_same_evidence_budget_and_routes(caplog):
    req = request()
    payload = {"evidence": "Private source unchanged"}
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=[
        result(QueryPlan.model_json_schema()), result('{"query":"Grounded search"}')])) as generate:
        output = await structured_call(None, req, QueryPlan, "Plan only", payload, max_tokens=800)
    assert output.query == "Grounded search" and generate.await_count == 2
    first, second = [call.args[1] for call in generate.call_args_list]
    assert "OUTPUT DATA FIELDS" in first.messages[0].content
    assert '"properties"' not in first.messages[0].content
    assert "schema keys" in second.messages[-1].content
    assert first.messages[1].content == second.messages[1].content
    assert first.max_tokens == second.max_tokens == 800
    assert first.preferred_provider_id == second.preferred_provider_id == "internal"
    assert first.preferred_model_name == second.preferred_model_name == "configured"
    assert "Private source" not in caplog.text


@pytest.mark.asyncio
async def test_persistent_schema_echo_is_an_error_not_missing_data():
    with (patch("app.modules.rag.evidence_model.modelops_service.generate",
                AsyncMock(return_value=result(QueryPlan.model_json_schema()))) as generate,
          pytest.raises(AppException) as error):
        await structured_call(None, request(), QueryPlan, "Plan", {}, max_tokens=800)
    assert error.value.code == "EVIDENCE_MODEL_CONTRACT_INVALID"
    assert error.value.status_code == 502 and generate.await_count == 2


@pytest.mark.parametrize("ids", [[], ["a"], ["a", "a"], ["a", "unknown"]])
def test_verification_contract_rejects_missing_duplicate_and_foreign_ids(ids):
    contract = verification_contract([{"id": "a"}, {"id": "b"}])
    with pytest.raises(ValidationError):
        contract.model_validate({"complete": True, "verdicts": [verdict(key) for key in ids]})


def test_verification_contract_preserves_verdict_identity_not_position():
    contract = verification_contract([{"id": "a"}, {"id": "b"}])
    output = contract.model_validate({"complete": False, "verdicts": [verdict("b", False), verdict("a")]})
    assert [(check.claim_id, check.entailed) for check in output.verdicts] == [("b", False), ("a", True)]


@pytest.mark.parametrize("ids", [[], ["a"], ["a", "a"], ["a", "unknown"]])
def test_indexed_audit_checks_identity_coverage_inside_contract(ids):
    contract = audit_contract([{"id": "a"}, {"id": "b"}], {"e1": None})
    with pytest.raises(ValidationError):
        contract.model_validate({"complete": True,
            "claims": [{"claim_id": key, "all_assertions_supported": True} for key in ids]})


@pytest.mark.asyncio
async def test_actual_verification_boundary_repairs_ids_then_keeps_rejected_claim_rejected():
    blocks, claims = bound()
    invalid = {"complete": True, "verdicts": [verdict("claim-0"), verdict("claim-0")]}
    repaired = {"complete": False, "verdicts": [verdict("claim-1", False), verdict("claim-0")]}
    audit = {"complete": True, "claims": [{"claim_id": "claim-0", "all_assertions_supported": True}]}
    with patch("app.modules.rag.evidence_model.modelops_service.generate",
               AsyncMock(side_effect=[result(invalid), result(repaired), result(audit)])) as generate:
        output = await verify_bound_answer(None, request(), {}, claims, blocks,
                                          QueryPlan(query=request().question), [])
    assert generate.await_count == 3  # Two attempts for verifier, one independent audit.
    assert [claim["id"] for claim in output.claims] == ["claim-0"]
    assert output.verifier.verdicts[0].entailed is False
    first, second = [call.args[1] for call in generate.call_args_list[:2]]
    assert first.messages[1].content == second.messages[1].content
    assert '"duplicate_count": 1' in second.messages[-1].content
    assert first.max_tokens == second.max_tokens == min(2400, request().max_tokens)
    assert output.claims[0]["references"] == claims[0]["references"]


@pytest.mark.asyncio
@pytest.mark.parametrize("indexed_failure", [False, True])
async def test_id_repair_exhaustion_fails_closed_at_verification_boundary(indexed_failure):
    blocks, claims = bound()
    valid = {"complete": True, "verdicts": [verdict(c["id"]) for c in claims]}
    invalid = {"complete": True, "claims": []} if indexed_failure else {"complete": True, "verdicts": []}
    responses = ([result(valid)] if indexed_failure else []) + [result(invalid), result(invalid)]
    with (patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=responses)) as generate,
          pytest.raises(AppException) as error):
        await verify_bound_answer(None, request(), {}, claims, blocks, QueryPlan(query=request().question), [])
    assert error.value.code == "EVIDENCE_VERIFICATION_INVALID" and error.value.status_code == 502
    assert generate.await_count == (3 if indexed_failure else 2)


@pytest.mark.asyncio
async def test_provider_failure_is_not_repaired_as_a_json_or_evidence_problem():
    failure = AppException("Upstream unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)
    with (patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=failure)) as generate,
          pytest.raises(AppException) as error):
        await structured_call(None, request(), QueryPlan, "Plan", {}, max_tokens=800)
    assert error.value is failure and generate.await_count == 1
