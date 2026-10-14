"""Direct chat, source passage identity and unsupported-claim regressions."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.assistants.runtime import build_runtime_profile
from app.modules.assistants.schemas import AssistantChatRequest, AssistantLifecycleConfig
from app.modules.assistants.services.assistant_chat_service import AssistantChatService
from app.modules.rag.evidence_audit import audit_coverage
from app.modules.rag.evidence_blocks import split_source_blocks
from app.modules.rag.evidence_claims import bind_claims
from app.modules.rag.evidence_indexed_audit import AuditedClaim, IndexedAudit, resolve_audit
from app.modules.rag.evidence_passages import (
    PassageClaim,
    PassageProposal,
    passage_catalog,
    resolve_proposal,
)
from app.modules.rag.schemas import AskResponse


def assistant():
    config = AssistantLifecycleConfig(execution_mode="rag")
    config.model_policy.primary_model = "configured-model"
    config.model_policy.preferred_provider_id = "configured-provider"
    config.model_policy.max_tokens = 5000
    return SimpleNamespace(id="a", code="custom", name="Trợ lý", is_active=True,
        tenant_id="tenant-x", collection_id="c", updated_at=None, config=config,
        system_prompt="Official knowledge assistant", sample_questions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
async def test_chat_bypasses_workflows_but_keeps_pii_policy_and_conversations(stream):
    record = assistant()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(tenant_id="tenant-x", workspace_id="workspace-x")
    service = AssistantChatService()
    result = AskResponse(answer="Verified answer", status="answered", latency_ms=5)
    with (patch("app.modules.assistants.services.assistant_chat_service._get_assistant_service") as lifecycle,
          patch.object(service, "_get_recent_conversation_history", AsyncMock(return_value=[])),
          patch("app.modules.assistants.services.assistant_rag_chat.rag_service.ask", AsyncMock(return_value=result)) as ask,
          patch("app.modules.assistants.services.assistant_rag_chat.conversation_service.record_message", AsyncMock()) as store,
          patch("app.modules.assistants.services.assistant_chat_service._get_workflow_service") as workflow):
        lifecycle.return_value.get_assistant = AsyncMock(return_value=record)
        request = AssistantChatRequest(message="Liên hệ test@example.com", conversation_id="conv-test")
        if stream:
            events = [event async for event in service.chat_stream(db, "custom", request)]
            assert any("event: done" in event for event in events)
            assert any("Verified answer" in event for event in events)
        else:
            response = await service.chat(db, "custom", request)
            assert response.answer == result.answer and response.execution_id is None
        workflow.assert_not_called()
        assert ask.call_args.args[1].question == "Liên hệ [EMAIL_ĐÃ_CHE]"
        req = ask.call_args.args[1]
        assert req.preferred_model_name == "configured-model"
        assert req.preferred_provider_id == "configured-provider" and req.max_tokens == 5000
        assert req.tenant_id == "tenant-x" and req.workspace_id == "workspace-x"
        assert store.await_count == 2


@pytest.mark.asyncio
async def test_direct_rag_provider_failure_is_not_a_fake_answer_or_workflow_fallback():
    from app.modules.assistants.services.assistant_rag_chat import chat_with_rag

    db = AsyncMock()
    db.get.return_value = SimpleNamespace(tenant_id="tenant-x", workspace_id="workspace-x")
    record = assistant()
    with (patch("app.modules.assistants.services.assistant_rag_chat.conversation_service.record_message", AsyncMock()),
          patch("app.modules.assistants.services.assistant_rag_chat.rag_service.ask", AsyncMock(
              side_effect=AppException("Unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503))),
          pytest.raises(AppException) as error):
        await chat_with_rag(db, record, AssistantChatRequest(message="Question?"), build_runtime_profile(record), [])
    assert error.value.code == "ALL_PROVIDERS_UNAVAILABLE"


def test_passage_ids_keep_exact_formula_unicode_and_offsets_without_model_copying():
    raw = "Formula: [(30 − total) / 7,5] × priority. Condition: from 22,5 points."
    blocks = split_source_blocks(raw, binding_id="b", index_id="i", source_id="s", title="Policy")
    catalog = passage_catalog(blocks)
    proposal = PassageProposal(status="supported", claims=[PassageClaim(id="c",
        text="Formula: [(30 − total) / 7,5] × priority.", evidence_ids=["e1.1"])])
    claims, errors = bind_claims(resolve_proposal(proposal, catalog), blocks)
    assert not errors
    ref = claims[0]["references"][0]
    assert raw[ref["start"]:ref["end"]] == ref["quote"]
    assert "−" in ref["quote"] and "×" in ref["quote"]


def test_unknown_passage_id_and_invented_number_are_rejected():
    blocks = split_source_blocks("Value: 20", binding_id="b", index_id="i", source_id="s", title="Policy")
    for ids, text in [(["invented"], "Value: 20"), (["e1.1"], "Value: 30")]:
        proposal = PassageProposal(status="supported", claims=[PassageClaim(id="c", text=text, evidence_ids=ids)])
        claims, errors = bind_claims(resolve_proposal(proposal, passage_catalog(blocks)), blocks)
        assert not claims and errors


@pytest.mark.parametrize("supported", [True, False])
def test_full_claim_audit_rejects_unsupported_compound_relation(supported):
    blocks = split_source_blocks("Method A uses result B", binding_id="b", index_id="i", source_id="s", title="Policy")
    text = "Method A uses result B" if supported else "Method A uses result B and accepts result C"
    proposal = PassageProposal(status="supported", claims=[PassageClaim(id="c", text=text, evidence_ids=["e1.1"])])
    claims, _ = bind_claims(resolve_proposal(proposal, passage_catalog(blocks)), blocks)
    indexed = IndexedAudit(claims=[AuditedClaim(claim_id="c", all_assertions_supported=supported,
        reason="Every relationship checked")], essential_conditions=[],
        complete=True, missing_constraints=[])
    audit = resolve_audit(indexed, claims, passage_catalog(blocks))
    accepted, _, _, complete = audit_coverage(audit, claims, blocks, [])
    assert bool(accepted) == supported and complete == supported


def test_default_evidence_assistant_uses_rag_and_explicit_workflow_is_preserved():
    record = assistant()
    record.config.execution_mode = None
    record.config.knowledge_policy.evidence_policy.enabled = True
    assert build_runtime_profile(record).execution_mode == "rag"
    record.config.execution_mode = "workflow"
    assert build_runtime_profile(record).execution_mode == "workflow"
