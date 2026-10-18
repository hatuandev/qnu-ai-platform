"""Evidence claim invariants: values cannot borrow unrelated source context."""

import pytest


def test_numeric_claim_must_match_its_own_exact_quote():
    from app.modules.rag.evidence_validation import numbers_supported

    assert numbers_supported("Tổng chỉ tiêu là 5.173.", ["Tổng chỉ tiêu: 5173"])
    assert not numbers_supported("Điểm sàn là 20.", ["Điểm chuẩn là 20.25."])
    assert not numbers_supported("Nam cao tối thiểu 1,65 m.", ["Nữ cao tối thiểu 1,55 m."])
    assert numbers_supported("Nam cao tối thiểu 1,65 m, nặng 45 kg.", ["Nam 1,65m, nặng 45kg."])


def test_span_rejects_fabricated_quote_and_keeps_page_revision():
    from app.modules.rag.evidence_schemas import EvidenceBlock, QuoteReference
    from app.modules.rag.evidence_validation import bind_quote

    block = EvidenceBlock(id="block", binding_id="b", index_revision_id="i", source_revision_id="s",
        title="Official", page_number=3, text="Tổng chỉ tiêu là 5.173.", start=100, end=123)
    assert bind_quote(QuoteReference(block_id="block", quote="5.173"), {"block": block})["page_number"] == 3
    with pytest.raises(ValueError):
        bind_quote(QuoteReference(block_id="block", quote="6.000"), {"block": block})


def test_whitespace_reflow_binds_original_span_but_never_repairs_words():
    from app.modules.rag.evidence_schemas import EvidenceBlock, QuoteReference
    from app.modules.rag.evidence_validation import bind_quote

    text = "Tổng điểm 2 môn\nvăn hóa + 2/3 điểm ƯT ≥\n13,34"
    block = EvidenceBlock(id="b", binding_id="binding", index_revision_id="i", source_revision_id="s",
                          title="TEST", text=text, start=100, end=100 + len(text))
    ref = bind_quote(QuoteReference(block_id="b", quote=text.replace("\n", " ")), {"b": block})
    assert ref["quote"] == text and ref["start"] == 100 and ref["end"] == 100 + len(text)
    with pytest.raises(ValueError):
        bind_quote(QuoteReference(block_id="b", quote=text.replace("13,34", "14,34")), {"b": block})


def test_adjacent_enumeration_keeps_siblings_but_does_not_cross_prose_boundary():
    from app.modules.rag.evidence_blocks import enumeration_neighbors, split_source_blocks

    blocks = split_source_blocks("+ Method A\n\n+ Method B\n\n+ Method C\n\nUnrelated paragraph\n\n+ Other list",
        binding_id="b", index_id="i", source_id="s", title="TEST")
    assert [b.text for b in enumeration_neighbors(blocks, [blocks[1]], 6)] == ["+ Method A", "+ Method B", "+ Method C"]


def test_planner_cannot_invent_a_year_or_reuse_unrelated_history():
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.evidence_validation import validate_plan_years

    plan = QueryPlan(query="Điểm sàn năm 2026", years=[2026], requires_year=True)
    with pytest.raises(ValueError):
        validate_plan_years(plan, "Điểm sàn?", [], None)
    validate_plan_years(plan, "Điểm sàn năm 2026?", [], None)


def test_structural_blocks_keep_original_offsets_and_do_not_infer_filename_year():
    from app.modules.rag.evidence_blocks import split_source_blocks

    markdown = "# Tuyển sinh\n\n<!-- Trang 2 -->\n## Điều kiện\n\nNam: 1,65 m; nữ: 1,55 m."
    blocks = split_source_blocks(markdown, binding_id="b", index_id="i", source_id="s", title="File2026")
    assert all(markdown[b.start:b.end] == b.text for b in blocks)
    assert blocks[-1].page_number == 2
    assert not hasattr(blocks[-1], "year")


@pytest.mark.asyncio
async def test_dag_preserves_clarification_and_partial_evidence():
    from app.modules.workflows.nodes.base import WorkflowContext
    from app.modules.workflows.nodes.no_answer_node import OutputNoAnswerNodeHandler
    from app.modules.workflows.schemas import WorkflowNodeSpec

    decision = {"version": "evidence-claims-v1", "status": "partial", "answer": "Có căn cứ cho một phần; phần còn lại chưa rõ."}
    citations = [{"source_id": "b", "quote": "Verified excerpt"}]
    context = WorkflowContext(workflow_id="wf", tenant_id="tenant", conversation_id=None, inputs={},
                              node_data={"answer_decision": decision, "citations": citations})
    result = await OutputNoAnswerNodeHandler().execute(WorkflowNodeSpec(id="no", type="output.no_answer"), context)
    assert result.output["answer"] == decision["answer"]
    assert result.output["citations"] == citations


def test_precedence_is_revision_and_year_scoped_and_requires_exact_quotes():
    from app.core.evidence_policy import EvidencePolicy, EvidenceSourcePreference
    from app.modules.rag.evidence_precedence import active_preferences, validate_superseding_quotes
    from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan, QuoteReference

    rule = EvidenceSourcePreference(preferred_source_revision_id="new", superseded_source_revision_ids=["old"],
        years=[2026], authorization_note="Approved by operator")
    policy = EvidencePolicy(source_preferences=[rule])
    block = EvidenceBlock(id="new-block", binding_id="b", index_revision_id="i", source_revision_id="new",
                          title="Updated", text="Chỉ tiêu: 5173", start=0, end=13)
    assert active_preferences(policy, QueryPlan(query="Chỉ tiêu", years=[2026]), [block]) == [rule]
    assert not active_preferences(policy, QueryPlan(query="Chỉ tiêu", years=[2027]), [block])
    assert not active_preferences(policy, QueryPlan(query="Chỉ tiêu", years=[]), [block])
    assert not active_preferences(policy, QueryPlan(query="Chỉ tiêu", years=[2026]), [])
    proof = [QuoteReference(block_id="new-block", quote="Chỉ tiêu: 5173")]
    assert validate_superseding_quotes("old", proof, [rule], {block.id: block})
    assert not validate_superseding_quotes("unrelated", proof, [rule], {block.id: block})
    assert not validate_superseding_quotes("old", [], [rule], {block.id: block})
    with pytest.raises(ValueError):
        validate_superseding_quotes("old", [QuoteReference(block_id=block.id, quote="6000")], [rule], {block.id: block})


def test_claim_cannot_borrow_year_heading_from_another_source():
    from app.modules.rag.evidence_validation import same_source

    refs = [{"binding_id": "b1", "index_revision_id": "i1", "source_revision_id": "s1"},
            {"binding_id": "b2", "index_revision_id": "i2", "source_revision_id": "s2"}]
    assert not same_source(refs)
    assert same_source([refs[0], refs[0]])


def test_current_year_uses_vietnam_midnight_and_explicit_history_is_scoped():
    from datetime import UTC, datetime

    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_pipeline import reference_year
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.evidence_validation import validate_plan_years

    policy = EvidencePolicy(reference_year_mode="current_year")
    assert reference_year(policy, datetime(2026, 12, 31, 16, 59, tzinfo=UTC)) == 2026
    assert reference_year(policy, datetime(2026, 12, 31, 17, 0, tzinfo=UTC)) == 2027
    assert reference_year(EvidencePolicy(reference_year_mode="clarify")) is None
    old = QueryPlan(query="Điểm năm 2025", years=[2025])
    validate_plan_years(old, "Điểm năm 2025?", [], 2026)
    with pytest.raises(ValueError):
        validate_plan_years(old, "Điểm?", [{"content": "năm 2025"}], 2026)
    old.uses_history = True
    validate_plan_years(old, "Còn ngành đó thì sao?", [{"content": "năm 2025"}], 2026)


@pytest.mark.asyncio
async def test_structured_model_repairs_once_and_fails_closed_after_two_invalid_results():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.core.exceptions import AppException
    from app.modules.rag.evidence_model import structured_call
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.schemas import AskRequest

    req = AskRequest(question="Điểm?", collection_id="test", preferred_model_name="configured-model",
                     preferred_provider_id="configured-provider")
    def result(content):
        return SimpleNamespace(content=content, provider="configured-provider", model="configured-model")
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=[
        result('{"unexpected": true}'), result('{"query":"Điểm?"}')])) as generate:
        repaired = await structured_call(None, req, QueryPlan, "Plan only", {}, max_tokens=1000)
        assert repaired.query == "Điểm?" and generate.await_count == 2
        assert generate.call_args.args[1].preferred_model_name == "configured-model"
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(return_value=result("invalid"))) as generate:
        with pytest.raises(AppException) as error:
            await structured_call(None, req, QueryPlan, "Plan only", {}, max_tokens=1000)
        assert error.value.code == "EVIDENCE_MODEL_CONTRACT_INVALID" and generate.await_count == 2


@pytest.mark.asyncio
async def test_structured_model_repair_budget_accounts_for_input_growth():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.rag.evidence_model import structured_call
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.schemas import AskRequest

    req = AskRequest(question="Điểm chuẩn năm 2026?", collection_id="test",
                     preferred_model_name="configured-model", preferred_provider_id="configured-provider")
    def result(content):
        return SimpleNamespace(content=content, provider="configured-provider", model="configured-model")
    # Long wrong output: the old formula kept ~full budget while input grew.
    oversized_invalid = '{"unexpected": true, "padding": "' + "x" * 4000 + '"}'
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=[
            result(oversized_invalid), result('{"query":"Điểm?"}')])) as generate:
        repaired = await structured_call(None, req, QueryPlan, "Plan only",
                                         {"câu": "Nội dung tiếng Việt có dấu"}, max_tokens=1600)
        assert repaired.query == "Điểm?"
        first_budget = generate.call_args_list[0].args[1].max_tokens
        second = generate.call_args_list[1].args[1]
        assert first_budget == 1600
        assert second.max_tokens == first_budget
        # Evidence payload is never cut to make room.
        assert second.messages[1].content == generate.call_args_list[0].args[1].messages[1].content


@pytest.mark.asyncio
async def test_structured_model_repair_preserves_provider_context_rejection():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.core.exceptions import AppException
    from app.modules.rag.evidence_model import structured_call
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.schemas import AskRequest

    req = AskRequest(question="Điểm chuẩn các ngành năm 2026?", collection_id="test",
                     preferred_model_name="configured-model", preferred_provider_id="configured-provider")
    def result(content):
        return SimpleNamespace(content=content, provider="configured-provider", model="configured-model")
    # A character estimate cannot prove overflow. Keep the requested contract
    # budget and propagate the authoritative provider window rejection.
    large_payload = {"bằng_chứng": "Trích dẫn tiếng Việt có dấu. " * 600}
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=[
            result('{"unexpected": true}'), AppException("Context exceeded", code="MODEL_CONTEXT_EXCEEDED", status_code=502)])) as generate:
        with pytest.raises(AppException) as error:
            await structured_call(None, req, QueryPlan, "Plan only", large_payload, max_tokens=400)
        assert error.value.code == "MODEL_CONTEXT_EXCEEDED"
        assert generate.await_count == 2
        assert generate.call_args_list[1].args[1].max_tokens == 400
        # Evidence was never cut to make room.
        assert "Trích dẫn tiếng Việt có dấu." in generate.call_args_list[0].args[1].messages[1].content


@pytest.mark.asyncio
async def test_structured_model_large_input_with_room_still_repairs():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.rag.evidence_model import structured_call
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.schemas import AskRequest

    req = AskRequest(question="Điểm?", collection_id="test", preferred_model_name="configured-model",
                     preferred_provider_id="configured-provider")
    def result(content):
        return SimpleNamespace(content=content, provider="configured-provider", model="configured-model")
    # Strict track with room: large input but a base budget that still leaves
    # viable output after input growth and reserve.
    large_payload = {"bằng_chứng": "Trích dẫn tiếng Việt có dấu. " * 600}
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=[
            result('{"unexpected": true}'), result('{"query":"Điểm?"}')])) as generate:
        assert (await structured_call(None, req, QueryPlan, "Plan only", large_payload,
                                      max_tokens=1600)).query == "Điểm?"
        assert generate.await_count == 2
        repair_budget = generate.call_args_list[1].args[1].max_tokens
        assert repair_budget == 1600


@pytest.mark.asyncio
async def test_structured_model_short_wrong_output_still_repairs_with_room():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.rag.evidence_model import structured_call
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.schemas import AskRequest

    req = AskRequest(question="Điểm?", collection_id="test", preferred_model_name="configured-model",
                     preferred_provider_id="configured-provider")
    def result(content):
        return SimpleNamespace(content=content, provider="configured-provider", model="configured-model")
    # Short field-missing output: the valid object may need MORE room, and the
    # budget rule still grants the fitting remainder instead of the old size.
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=[
            result('{"unexpected": true}'), result('{"query":"Điểm?"}')])) as generate:
        assert (await structured_call(None, req, QueryPlan, "Plan only", {}, max_tokens=1000)).query == "Điểm?"
        assert generate.await_count == 2
        assert generate.call_args_list[1].args[1].max_tokens >= 256


@pytest.mark.asyncio
async def test_structured_model_repair_names_schema_echo_explicitly():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.rag.evidence_model import structured_call
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.schemas import AskRequest

    req = AskRequest(question="Điểm?", collection_id="test", preferred_model_name="configured-model",
                     preferred_provider_id="configured-provider")
    def result(content):
        return SimpleNamespace(content=content, provider="configured-provider", model="configured-model")
    schema_echo = '{"properties": {"query": {"type": "string"}}, "$defs": {}}'
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=[
            result(schema_echo), result('{"query":"Điểm?"}')])) as generate:
        assert (await structured_call(None, req, QueryPlan, "Plan only", {}, max_tokens=1000)).query == "Điểm?"
        repair_note = generate.call_args_list[1].args[1].messages[-1].content
        assert "schema keys" in repair_note


def test_decision_integrity_rejects_swapped_revision_digest_or_unsupported_numbers():
    from app.modules.rag.evidence_validation import (
        VERSION,
        evidence_digest,
        validate_decision_integrity,
    )

    ref = {"binding_id": "b", "index_revision_id": "i", "source_revision_id": "s", "page_number": 2, "quote": "Chỉ tiêu 5173"}
    claim = {"id": "c", "text": "Chỉ tiêu 5173", "references": [ref], "verified": True}
    decision = {"version": VERSION, "status": "supported", "answer": "Chỉ tiêu 5173",
                "claim_bindings": [claim], "evidence_digest": evidence_digest([claim])}
    assert validate_decision_integrity(decision, decision["answer"], [ref])
    assert not validate_decision_integrity(decision, decision["answer"], [{**ref, "source_revision_id": "different"}])
    claim["text"] = "Chỉ tiêu 6000"
    decision["evidence_digest"] = evidence_digest([claim])
    assert not validate_decision_integrity(decision, decision["answer"], [ref])


@pytest.mark.asyncio
async def test_database_outage_is_not_a_missing_answer():
    from unittest.mock import AsyncMock

    from app.core.exceptions import AppException
    from app.modules.rag.evidence_blocks import load_published_blocks
    from app.modules.rag.evidence_facts import reviewed_fact_blocks
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

    db = AsyncMock()
    db.execute.side_effect = ConnectionError("DB unavailable")
    snapshot = RetrievalSnapshot(snapshot_id="test", collection_id="test", tenant_id="t", workspace_id="w",
                                 binding_revisions={"b": "i"})
    with pytest.raises(AppException) as error:
        await load_published_blocks(db, snapshot)
    assert error.value.code == "EVIDENCE_SOURCE_UNAVAILABLE"
    with pytest.raises(AppException) as error:
        await reviewed_fact_blocks(db, AskRequest(question="Test", collection_id="test"), snapshot,
                                   QueryPlan(query="Test"), [])
    assert error.value.code == "EVIDENCE_FACT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_default_year_also_scopes_general_information_not_only_numeric_queries():
    import time
    from unittest.mock import AsyncMock, patch

    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_pipeline import _answer
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

    with (patch("app.modules.rag.evidence_pipeline.reference_year", return_value=2026),
          patch("app.modules.rag.evidence_pipeline.structured_call", AsyncMock(return_value=QueryPlan(query="Địa chỉ?", requires_year=False))) as planner,
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(return_value=[])) as select_context):
        response = await _answer(None, AskRequest(question="Địa chỉ?", collection_id="test",
            runtime_policy={"persona_scope": {"persona": "Administrator configured university"}}),
            RetrievalSnapshot(snapshot_id="test", collection_id="test"), EvidencePolicy(reference_year_mode="current_year"),
            time.perf_counter(), False)
    assert response.answer_decision["requested"]["years"] == [2026]
    assert select_context.call_args.args[3].years == [2026]
    assert "2026" in response.answer
    assert planner.call_args.args[4]["assistant_scope"]["persona"] == "Administrator configured university"


@pytest.mark.asyncio
@pytest.mark.parametrize("module_code", ["", "general"])
async def test_direct_rag_cannot_skip_collection_policy_by_omitting_module(module_code):
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock

    from app.modules.rag.evidence_runtime import resolve_evidence_request
    from app.modules.rag.schemas import AskRequest

    config = {"knowledge_policy": {"evidence_policy": {"enabled": True}},
              "persona_scope": {"persona": "Institution configured by administrator"}}
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={"evidence_answers_enabled": True},
        module_code="configured-assistant", tenant_id="tenant", workspace_id="workspace")
    record = SimpleNamespace(code="configured-assistant", config=config, updated_at=datetime.now(UTC))
    db.execute.return_value = Mock(scalar_one_or_none=Mock(return_value=record))
    resolved, policy = await resolve_evidence_request(db, AskRequest(question="Test", collection_id="c",
        tenant_id="tenant", workspace_id="workspace", module_code=module_code))
    assert policy.enabled and resolved.assistant_code == record.code
    assert "configured-assistant" in db.execute.call_args.args[0].compile().params.values()


@pytest.mark.asyncio
async def test_policy_database_outage_fails_closed_before_legacy_answering():
    from unittest.mock import AsyncMock

    from app.core.exceptions import AppException
    from app.modules.rag.evidence_runtime import resolve_evidence_request
    from app.modules.rag.schemas import AskRequest

    db = AsyncMock()
    db.get.side_effect = ConnectionError("DB offline")
    with pytest.raises(AppException) as error:
        await resolve_evidence_request(db, AskRequest(question="Test", collection_id="c", module_code=""))
    assert error.value.code == "EVIDENCE_POLICY_UNAVAILABLE"


@pytest.mark.asyncio
@pytest.mark.parametrize("cross_tenant", [True, False])
async def test_required_collection_policy_rejects_disabled_assistant_regardless_of_legacy_scope(cross_tenant):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock

    from app.core.exceptions import AppException
    from app.modules.rag.evidence_runtime import resolve_evidence_request
    from app.modules.rag.schemas import AskRequest

    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={"evidence_answers_enabled": True},
        tenant_id="other" if cross_tenant else "tenant", workspace_id="workspace", module_code="configured")
    db.execute.return_value = Mock(scalar_one_or_none=Mock(return_value=SimpleNamespace(config={})))
    with pytest.raises(AppException) as error:
        await resolve_evidence_request(db, AskRequest(question="Test", collection_id="c",
            tenant_id="tenant", workspace_id="workspace"))
    assert error.value.code == "EVIDENCE_POLICY_UNAVAILABLE"
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("repair_succeeds", [True, False])
async def test_quote_repair_is_bounded_and_never_accepts_unsupported_numbers(repair_succeeds):
    from unittest.mock import AsyncMock, patch

    from app.modules.rag.evidence_claims import propose_bound_claims
    from app.modules.rag.evidence_passages import PassageClaim, PassageProposal
    from app.modules.rag.evidence_schemas import EvidenceBlock
    from app.modules.rag.schemas import AskRequest

    block = EvidenceBlock(id="b", binding_id="binding", index_revision_id="index", source_revision_id="source",
        title="Official", text="Value: 20", start=0, end=9)
    def proposal(value):
        return PassageProposal(status="supported", claims=[PassageClaim(id="c", text=f"Value: {value}",
            evidence_ids=["e1.1"])])
    invalid = proposal(30)
    invalid.claims[0].evidence_ids = ["unknown"]
    with patch("app.modules.rag.evidence_claims.structured_call", AsyncMock(side_effect=[
        invalid, proposal(20) if repair_succeeds else invalid])) as generate:
        _, claims, rejected, repaired = await propose_bound_claims(None,
            AskRequest(question="Value?", collection_id="test"), {"evidence": [block.model_dump()]}, [block])
    assert generate.await_count == 2 and repaired
    assert bool(claims) == repair_succeeds and bool(rejected) != repair_succeeds
    assert "binding_errors" in generate.call_args.args[4]


@pytest.mark.asyncio
async def test_source_bound_claim_still_requires_semantic_verification_after_repair():
    import time
    from unittest.mock import AsyncMock, patch

    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_claims import bind_claims
    from app.modules.rag.evidence_pipeline import _answer
    from app.modules.rag.evidence_schemas import (
        AnswerProposal,
        ClaimVerdict,
        EvidenceBlock,
        EvidenceClaim,
        QueryPlan,
        QuoteReference,
        VerificationResult,
    )
    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

    block = EvidenceBlock(id="b", binding_id="binding", index_revision_id="index", source_revision_id="source",
        title="Official", text="Cutoff: 20", start=0, end=10)
    proposal = AnswerProposal(status="supported", claims=[EvidenceClaim(id="c", text="Floor: 20",
        references=[QuoteReference(block_id="b", quote=block.text)])])
    claims, rejected = bind_claims(proposal, [block])
    assert claims and not rejected  # Same number is NOT semantic proof for another attribute.
    verdict = VerificationResult(complete=False, verdicts=[ClaimVerdict(claim_id="c", entailed=False,
        relevant=False, scope_compatible=False, reason="Wrong requested attribute")])
    with (patch("app.modules.rag.evidence_pipeline.structured_call", AsyncMock(return_value=QueryPlan(query="Floor?"))),
          patch("app.modules.rag.evidence_verification.structured_call", AsyncMock(return_value=verdict)),
          patch("app.modules.rag.evidence_pipeline.propose_bound_claims", AsyncMock(return_value=(proposal, claims, [], True))),
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(return_value=[block]))):
        response = await _answer(None, AskRequest(question="Floor?", collection_id="test"),
            RetrievalSnapshot(snapshot_id="test", collection_id="test"), EvidencePolicy(), time.perf_counter(), False)
    assert response.answer_decision["status"] == "missing" and not response.citations
    assert "Floor: 20" not in response.answer


@pytest.mark.asyncio
async def test_context_budget_cannot_evict_reviewed_rows_when_scope_headers_are_added():
    from unittest.mock import AsyncMock, patch

    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_pipeline import select_context
    from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

    def block(bid, source, text, origin="canonical"):
        return EvidenceBlock(id=bid, binding_id=source, index_revision_id=source, source_revision_id=source,
            title="Official", text=text, start=0, end=len(text), origin=origin)
    paragraphs = [block(f"p{i}", f"s{i % 3}", "Related paragraph") for i in range(7)]
    headers = [block(f"h{i}", f"s{i}", "# SEASON 2026") for i in range(3)]
    headers.append(block("hf", "facts", "# SEASON 2026"))
    facts = [block("f1", "facts", "Target attribute: 20", "reviewed_fact"),
             block("f2", "facts", "Target condition: 13.34", "reviewed_fact")]
    with (patch("app.modules.rag.evidence_pipeline.retrieve_anchors", AsyncMock(return_value=[])),
          patch("app.modules.rag.evidence_pipeline.load_published_blocks", AsyncMock(return_value=[*paragraphs, *headers])),
          patch("app.modules.rag.evidence_pipeline.reviewed_fact_blocks", AsyncMock(return_value=facts)),
          patch("app.modules.rag.evidence_pipeline.rank_blocks", side_effect=lambda items, queries, limit, years: items[:limit])):
        selected = await select_context(None, AskRequest(question="Target", collection_id="test", reranker_policy={"enabled": False}),
            RetrievalSnapshot(snapshot_id="test", collection_id="test"), QueryPlan(query="Target", years=[2026]),
            EvidencePolicy(context_limit=10), candidate_mode=False)
    selected_ids = {b.id for b in selected}
    assert {"f1", "f2", "hf"}.issubset(selected_ids)
    assert len([b for b in selected if not b.text.startswith("#")]) <= 10


def test_context_pair_budget_counts_fact_metadata_and_never_keeps_orphan_header():
    from app.modules.rag.evidence_blocks import pack_context
    from app.modules.rag.evidence_schemas import EvidenceBlock

    header = EvidenceBlock(id="h", binding_id="b", index_revision_id="i", source_revision_id="s",
        title="Official", text="# SEASON 2026", start=0, end=13)
    fact = EvidenceBlock(id="f", binding_id="b", index_revision_id="i", source_revision_id="s",
        title="Official", text="Value: 20", start=0, end=9, origin="reviewed_fact",
        fact_context={"large_review_metadata": "x" * 7000})
    assert pack_context([header, fact], [fact], [2026], limit=1, max_chars=10000) == [header, fact]
    assert pack_context([header, fact], [fact], [2026], limit=10, max_chars=6000) == []
    assert [b.id for b in pack_context([header, fact], [fact], [2026], 10, 10000)] == ["h", "f"]


def test_incidental_issue_date_block_is_not_selected_as_season_heading():
    from app.modules.rag.evidence_blocks import scope_headers, source_heading_years
    from app.modules.rag.evidence_schemas import EvidenceBlock

    issue = EvidenceBlock(id="issue", binding_id="b", index_revision_id="i", source_revision_id="s",
        title="Official", text="Số: /TB-HĐTS\nGia Lai, ngày tháng năm 2026", start=0, end=50, page_number=1)
    heading = issue.model_copy(update={"id": "season", "text": "THÔNG BÁO\nTuyển sinh năm 2025", "start": 100})
    assert source_heading_years([issue, heading]) == [2025]
    assert scope_headers([issue, heading], [issue], [2026]) == []


@pytest.mark.asyncio
async def test_evidence_timeout_reports_stage_without_converting_to_no_answer():
    import asyncio
    from unittest.mock import patch

    from app.core.evidence_policy import EvidencePolicy
    from app.core.exceptions import AppException
    from app.modules.rag.evidence_pipeline import answer_with_evidence
    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

    timeout = asyncio.timeout
    async def stalled(*args):
        args[-1]["stage"] = "retrieval"
        await asyncio.sleep(1)
    with (patch("app.modules.rag.evidence_pipeline._answer", side_effect=stalled),
          patch("app.modules.rag.evidence_pipeline.asyncio.timeout", side_effect=lambda _: timeout(0.001)),
          pytest.raises(AppException) as error):
        await answer_with_evidence(None, AskRequest(question="Test", collection_id="test"),
            RetrievalSnapshot(snapshot_id="test", collection_id="test"), EvidencePolicy())
    assert error.value.code == "EVIDENCE_TIMEOUT" and "retrieval" in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["anchors", "rerank"])
async def test_slow_remote_retrieval_is_cancelled_and_never_creates_fake_evidence(stage):
    import asyncio
    from unittest.mock import AsyncMock, patch

    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_retrieval import bounded_rerank, retrieve_anchors
    from app.modules.rag.fusion import FusionCandidate
    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

    timeout = asyncio.timeout
    cancelled = []
    async def stalled(*args, **kwargs):
        try:
            await asyncio.sleep(1)
        finally:
            cancelled.append(True)
    req = AskRequest(question="Test", collection_id="test", reranker_policy={
        "provider_id": "configured-provider", "model_name": "configured-model"})
    original = [FusionCandidate("real", "binding", "Real source", 0.1)]
    with (patch("app.modules.rag.evidence_retrieval.asyncio.timeout", side_effect=lambda _: timeout(0.001)),
          patch("app.modules.rag.evidence_retrieval.hybrid_retriever.retrieve", AsyncMock(side_effect=stalled)) as retrieve,
          patch("app.modules.rag.evidence_retrieval.reranker_client.rerank", AsyncMock(side_effect=stalled)) as rerank):
        if stage == "anchors":
            result = await retrieve_anchors(req, RetrievalSnapshot(snapshot_id="test", collection_id="test"),
                "Test", EvidencePolicy(), False)
            assert result == []
            assert retrieve.call_args.kwargs["reranker_policy"]["enabled"] is False
        else:
            result = await bounded_rerank("Test", original, 1, req, EvidencePolicy())
            assert result == original and result[0].relevance_score is None
            assert rerank.call_args.kwargs["preferred_provider_id"] == "configured-provider"
            assert rerank.call_args.kwargs["preferred_model_name"] == "configured-model"
    assert cancelled == [True]


@pytest.mark.asyncio
async def test_reviewed_rows_are_semantically_reranked_separately_not_just_bm25_appended():
    from unittest.mock import AsyncMock, patch

    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_pipeline import select_context
    from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

    header = EvidenceBlock(id="h", binding_id="b", index_revision_id="i", source_revision_id="s",
        title="Official", text="# SEASON 2026", start=0, end=13)
    fact = header.model_copy(update={"id": "fact", "text": "Target attribute: 20", "origin": "reviewed_fact"})
    req = AskRequest(question="Target", collection_id="test", reranker_policy={
        "provider_id": "configured-provider", "model_name": "configured-model"})
    async def rank(query, candidates, top_k, request, policy):
        assert request.reranker_policy == req.reranker_policy
        return candidates[:top_k]
    with (patch("app.modules.rag.evidence_pipeline.retrieve_anchors", AsyncMock(return_value=[])),
          patch("app.modules.rag.evidence_pipeline.load_published_blocks", AsyncMock(return_value=[header])),
          patch("app.modules.rag.evidence_pipeline.reviewed_fact_blocks", AsyncMock(return_value=[fact])),
          patch("app.modules.rag.evidence_pipeline.bounded_rerank", AsyncMock(side_effect=rank)) as rerank):
        selected = await select_context(None, req, RetrievalSnapshot(snapshot_id="test", collection_id="test"),
            QueryPlan(query="Target", years=[2026]), EvidencePolicy(), candidate_mode=False)
    assert rerank.await_count == 2
    assert [candidate.chunk_id for candidate in rerank.call_args.args[1]] == ["fact"]
    assert {"h", "fact"}.issubset({block.id for block in selected})


def test_reviewed_row_cannot_be_generalized_to_a_group_or_quote_only_its_value():
    from app.modules.rag.evidence_claims import bind_claims
    from app.modules.rag.evidence_schemas import (
        AnswerProposal,
        EvidenceBlock,
        EvidenceClaim,
        QuoteReference,
    )

    block = EvidenceBlock(id="b", binding_id="binding", index_revision_id="index", source_revision_id="source",
        title="Official", text="Entity A\nThreshold: 20", start=-1, end=-1, origin="reviewed_fact",
        fact_context={"entity_name": "Entity A"})
    def bind(text, quote):
        proposal = AnswerProposal(status="supported", claims=[EvidenceClaim(id="c", text=text,
            references=[QuoteReference(block_id="b", quote=quote)])])
        return bind_claims(proposal, [block])
    assert not bind("All entities have threshold 20", block.text)[0]
    # A valid row excerpt expands to the exact atomic reviewed row, not guessed text.
    assert bind("Entity A has threshold 20", "Threshold: 20")[0][0]["references"][0]["quote"] == block.text
    claims, errors = bind("Entity A has threshold 20", block.text)
    assert claims and not errors
    assert claims[0]["references"][0]["entity_name"] == "Entity A"
