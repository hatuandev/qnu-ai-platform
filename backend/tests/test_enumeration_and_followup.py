"""Enumeration coverage and contextual retrieval, independent of specific majors/models."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.rag.combination_enumeration import (
    EnumerationPlan,
    EnumerationScope,
    render_records,
    scope_catalog,
    validated_scopes,
)
from app.modules.rag.combination_records import matching_tuples, records_from_block
from app.modules.rag.conversation_resolution import FollowupResolution, resolve_followup
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def request(question="sao ít thế"):
    return AskRequest(question=question, collection_id="cc", tenant_id="tt", workspace_id="ww",
        assistant_code="admissions", preferred_model_name="configured/model",
        history=[{"role": "user", "content": "Liệt kê học phí ngành Alpha năm 2025"},
                 {"role": "assistant", "content": "Untrusted old answer claiming 2099"}])


def snapshot():
    return RetrievalSnapshot(snapshot_id="ss", collection_id="cc", tenant_id="tt", workspace_id="ww",
                             binding_revisions={"bb": "ii"})


def block(body, number=0, **kwargs):
    return EvidenceBlock(id=f"b{number}", binding_id="bb", index_revision_id="ii", source_revision_id="source",
        canonical_hash="hash", title="Source", text=body, start=number * 1000, end=number * 1000 + len(body), **kwargs)


def test_combination_predicate_never_blends_subjects_across_tuples():
    assert matching_tuples("(Toán, Anh, Tin); (Lý, Sinh, Văn); (Hóa, Sử, Địa)", ["toán", "lý", "hóa"]) == []
    assert matching_tuples("(Hóa, Toán, Vật lý); (Toán, Văn, Anh)", ["toán", "lý", "hóa"]) == ["(Hóa, Toán, Vật lý)"]


def test_list_records_keep_full_program_code_and_all_matches_beyond_top_k():
    records = []
    for index in range(42):
        body = f"{index + 1}. **Program {index}** — Mã ngành: **7123456 X{index}** . Tổ hợp môn xét tuyển: (Toán, Lý, Hóa); (Toán, Văn, Anh)"
        records.extend(records_from_block(block(body, index), ["toán", "lý", "hóa"]))
    scopes = {"source": EnumerationScope(source_id="source")}
    result = render_records(records, scopes, {}, snapshot())
    assert result.status == "answered" and result.answer_decision["count"] == 42
    assert len({row["code"] for row in result.answer_decision["records"]}) == 42
    assert "Program 41" in result.answer and "(Toán, Văn, Anh)" not in result.answer


def test_years_remain_separate_and_scope_cannot_borrow_foreign_proof():
    proof = block("## Danh sách tuyển sinh 2025", 0)
    record_block = block("1. **Alpha** — Mã ngành: **7123456** . Tổ hợp môn xét tuyển: (Toán, Lý, Hóa)", 1)
    records = records_from_block(record_block, ["toán", "lý", "hóa"])
    proofs = {proof.id: proof}
    catalog = scope_catalog(records, proofs)
    good = EnumerationPlan(enumerate_entities=True, scopes=[EnumerationScope(source_id="source", year=2025, proof_ids=[proof.id])])
    assert validated_scopes(good, catalog, proofs, "Các ngành năm 2025")
    with pytest.raises(ValueError):
        validated_scopes(good, catalog, proofs, "Các ngành năm 2026")
    with pytest.raises(ValueError):
        validated_scopes(good.model_copy(update={"scopes": []}), catalog, proofs, "Các ngành")


@pytest.mark.asyncio
async def test_short_followup_resolves_before_retrieval_instead_of_empty_no_answer():
    from app.modules.rag.service import RagService

    req = request()
    standalone = "Rà soát đầy đủ học phí ngành Alpha năm 2025"
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={})
    with (patch("app.modules.rag.conversation_resolution.structured_call", AsyncMock(
            return_value=FollowupResolution(mode="followup", antecedent_id=0, question=standalone))),
          patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
          patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.hybrid_retriever.retrieve", AsyncMock(return_value=[])) as retrieve,
          patch("app.modules.rag.service.load_row_anchors", AsyncMock(return_value=[]))):
        result = await RagService().ask(db, req)
    assert standalone in retrieve.call_args.kwargs["query"]
    assert result.answer_decision["question_resolution"]["current_question"] == "sao ít thế"


@pytest.mark.asyncio
@pytest.mark.parametrize("result,expected", [
    (FollowupResolution(mode="independent"), "independent"),
    (FollowupResolution(mode="followup", antecedent_id=9, question="Invented"), "clarify"),
    (FollowupResolution(mode="followup", antecedent_id=0, question="Học phí Alpha năm 2099"), "clarify"),
    (FollowupResolution(mode="followup", antecedent_id=0, question="Học phí Alpha năm 2025"), "followup"),
])
async def test_followup_rejects_new_answer_years_and_unknown_antecedents(result, expected):
    req = request()
    with patch("app.modules.rag.conversation_resolution.structured_call", AsyncMock(return_value=result)) as model:
        resolved, decision = await resolve_followup(AsyncMock(), req)
    assert (decision or {"mode": "independent"})["mode"] == expected
    if expected != "followup":
        assert resolved.question == req.question
    assert "2099" not in str(model.call_args.args[4])


@pytest.mark.asyncio
async def test_model_failure_is_propagated_not_replaced_by_a_fake_rewrite():
    error = AppException("provider down", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)
    with patch("app.modules.rag.conversation_resolution.structured_call", AsyncMock(side_effect=error)), pytest.raises(AppException):
        await resolve_followup(AsyncMock(), request())


@pytest.mark.asyncio
async def test_standalone_fact_topic_switch_never_inherits_old_subjects():
    req = request("Học phí ngành Beta năm 2026 là bao nhiêu?")
    with patch("app.modules.rag.conversation_resolution.structured_call", AsyncMock()) as model:
        resolved, decision = await resolve_followup(AsyncMock(), req)
    assert resolved is req and decision is None
    model.assert_not_awaited()
