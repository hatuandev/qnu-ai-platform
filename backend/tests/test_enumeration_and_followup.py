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
from app.modules.rag.combination_records import matching_tuples, query_subjects, records_from_block
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
    record_block = block("1. **Alpha** — Mã ngành: **7123456** . Tổ hợp môn xét tuyển: (Toán, Lý, Hóa)", 1,
                         header_context=proof.text)
    records = records_from_block(record_block, ["toán", "lý", "hóa"])
    proofs = {proof.id: proof}
    catalog = scope_catalog(records, proofs)
    good = EnumerationPlan(enumerate_entities=True, scopes=[EnumerationScope(source_id="source", year=2025, proof_ids=[proof.id])])
    assert validated_scopes(good, catalog, proofs, "Các ngành năm 2025")
    assert render_records(records, validated_scopes(good, catalog, proofs, "Các ngành năm 2026"), proofs,
                          snapshot(), requested_years={2026}).status == "insufficient_context"
    unknown = validated_scopes(good.model_copy(update={"scopes": []}), catalog, proofs, "Các ngành")
    assert unknown["source"].year is None


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


def test_unknown_years_from_different_sources_are_not_silently_merged():
    body = "1. **Alpha** — Mã ngành: **7123456** . Tổ hợp môn xét tuyển: (Toán, Lý, Hóa)"
    first = block(body, 1)
    second = first.model_copy(update={"id": "other", "source_revision_id": "other-source", "binding_id": "other-binding"})
    records = records_from_block(first, ["toán", "lý", "hóa"]) + records_from_block(second, ["toán", "lý", "hóa"])
    scopes = {key: EnumerationScope(source_id=key) for key in ("source", "other-source")}
    result = render_records(records, scopes, {}, snapshot())
    assert result.answer_decision["count"] == 2
    assert all(row["year"] is None for row in result.answer_decision["records"])


@pytest.mark.asyncio
async def test_current_year_override_cannot_keep_the_previous_year():
    req = request("còn năm 2026 thì sao?")
    with patch("app.modules.rag.conversation_resolution.structured_call", AsyncMock(return_value=
            FollowupResolution(mode="followup", antecedent_id=0, question="Học phí Alpha năm 2025 và 2026"))):
        _, decision = await resolve_followup(AsyncMock(), req)
    assert decision["mode"] == "clarify"


@pytest.mark.asyncio
async def test_enumeration_scope_mismatch_rejected_before_db_or_model():
    from app.modules.rag.combination_enumeration import enumerate_combinations
    from app.modules.rag.query_router import query_classifier

    req = request("Liệt kê các ngành có tổ hợp Toán, Lý, Hóa")
    wrong = snapshot().model_copy(update={"collection_id": "foreign"})
    db = AsyncMock()
    with pytest.raises(AppException) as error:
        await enumerate_combinations(db, req, wrong, query_classifier.analyze(req.question, "admissions"))
    assert error.value.code == "ENUMERATION_SCOPE_MISMATCH"
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_failure_never_degrades_to_an_incomplete_top_k_list():
    from app.modules.rag.combination_enumeration import enumerate_combinations
    from app.modules.rag.query_router import query_classifier

    req = request("Liệt kê các ngành có tổ hợp Toán, Lý, Hóa")
    with patch("app.modules.rag.combination_enumeration.load_records", AsyncMock(side_effect=
            AppException("DB down", code="EVIDENCE_SOURCE_UNAVAILABLE", status_code=503))), pytest.raises(AppException):
        await enumerate_combinations(AsyncMock(), req, snapshot(), query_classifier.analyze(req.question, "admissions"))


@pytest.mark.asyncio
async def test_reviewed_records_exhaustive_mode_uses_keyset_pages_not_ranked_subset():
    from app.modules.rag.evidence_facts import reviewed_fact_blocks
    from app.modules.rag.evidence_schemas import QueryPlan

    facts = [SimpleNamespace(id=f"f{i:04}", index_revision_id="ii", binding_id="bb", applicability_year=2025,
        entity_name=f"Program {i}", attribute_name="Tổ hợp môn", attribute_value="(Toán, Lý, Hóa)",
        raw_data={"table_id": "table", "row_index": i, "column_index": 1}) for i in range(503)]
    db = AsyncMock()
    db.execute.side_effect = [SimpleNamespace(scalars=lambda page=page: SimpleNamespace(all=lambda: page))
                             for page in (facts[:500], facts[500:])]
    result = await reviewed_fact_blocks(db, request(), snapshot(), QueryPlan(query="list"), [block("Source")], exhaustive=True)
    assert len(result) == 503 and db.execute.await_count == 2
    assert len(records_from_block(result[-1], ["toán", "lý", "hóa"])) == 1


def test_subject_run_ignores_subject_words_in_unrelated_prose():
    assert query_subjects("Liệt kê Toán, Lý, Hóa theo cẩm nang tuyển sinh 2025") == ["toán", "lý", "hóa"]
    assert query_subjects("Các ngành có Toán Lý Hóa giúp tôi") == ["toán", "lý", "hóa"]
    assert query_subjects("Các ngành có Toán, Hóa và Sinh") == ["toán", "hóa", "sinh"]


@pytest.mark.asyncio
async def test_recheck_replays_the_actual_request_not_model_authored_explanation():
    req = request()
    with patch("app.modules.rag.conversation_resolution.structured_call", AsyncMock(return_value=
            FollowupResolution(mode="recheck", antecedent_id=0))):
        resolved, decision = await resolve_followup(AsyncMock(), req)
    assert resolved.question == req.history[0]["content"]
    assert decision["action"] == "recheck" and decision["current_question"] == req.question


@pytest.mark.asyncio
async def test_recheck_cannot_discard_current_new_year():
    with patch("app.modules.rag.conversation_resolution.structured_call", AsyncMock(return_value=
            FollowupResolution(mode="recheck", antecedent_id=0))):
        resolved, decision = await resolve_followup(AsyncMock(), request("còn năm 2026 thì sao?"))
    assert decision["mode"] == "clarify" and "2026" in resolved.question


def test_unproven_year_is_rejected_but_omitted_source_remains_unknown():
    body = "1. **Alpha** — Mã ngành: **7123456** . Tổ hợp môn xét tuyển: (Toán, Lý, Hóa)"
    records = records_from_block(block(body), ["toán", "lý", "hóa"])
    catalog = scope_catalog(records, {})
    invalid = EnumerationPlan(enumerate_entities=True, scopes=[EnumerationScope(source_id="source", year=2026)])
    with pytest.raises(ValueError, match="no same-source proof"):
        validated_scopes(invalid, catalog, {}, "Các ngành")
    plan = EnumerationPlan(enumerate_entities=True)
    assert validated_scopes(plan, catalog, {}, "Các ngành")["source"].year is None
    assert render_records(records, validated_scopes(plan, catalog, {}, "Các ngành năm 2026"), {},
                          snapshot(), requested_years={2026}).status == "insufficient_context"


def test_historical_combination_columns_never_inherit_another_column_or_document_year():
    body = "| Mã ngành | Tên ngành | Tổ hợp môn 2022 | Tổ hợp môn 2023 |\n| --- | --- | --- | --- |\n| 7123456 | Alpha | (Toán, Lý, Hóa) | (Toán, Văn, Anh) |"
    records = records_from_block(block(body, scope_years=[2026]), ["toán", "lý", "hóa"])
    assert len(records) == 1 and records[0].years == (2022,)
    scopes = {"source": EnumerationScope(source_id="source", year=2026)}
    result = render_records(records, scopes, {}, snapshot())
    assert result.answer_decision["records"][0]["year"] == 2022
    assert render_records(records, scopes, {}, snapshot(), requested_years={2023}).status == "insufficient_context"
    assert render_records(records, scopes, {}, snapshot(), requested_years={2022}).status == "answered"


@pytest.mark.asyncio
async def test_enumeration_service_bypasses_top_k_cache_and_free_generation():
    from app.modules.rag.service import RagService

    req = request("Liệt kê các ngành có tổ hợp Toán, Lý, Hóa")
    body = "1. **Alpha** — Mã ngành: **7123456** . Tổ hợp môn xét tuyển: (Toán, Lý, Hóa)"
    records = records_from_block(block(body), ["toán", "lý", "hóa"])
    with (patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
          patch("app.modules.rag.combination_enumeration.load_records", AsyncMock(return_value=(records, {}))),
          patch("app.modules.rag.combination_enumeration.structured_call", AsyncMock(return_value=EnumerationPlan(enumerate_entities=True))),
          patch("app.modules.rag.service.semantic_cache.get", AsyncMock()) as cache,
          patch("app.modules.rag.service.hybrid_retriever.retrieve", AsyncMock()) as retrieve,
          patch("app.modules.rag.service.modelops_service.generate", AsyncMock()) as generate):
        response = await RagService().ask(AsyncMock(), req)
    assert response.status == "answered" and response.answer_decision["count"] == 1
    cache.assert_not_awaited()
    retrieve.assert_not_awaited()
    generate.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("all_years,expected", [(False, "insufficient_context"), (True, "answered")])
async def test_initial_multi_year_list_requires_scope_unless_explicit_comparison(all_years, expected):
    from app.modules.rag.combination_enumeration import enumerate_combinations
    from app.modules.rag.query_router import query_classifier

    req = request("Liệt kê các ngành có tổ hợp Toán, Lý, Hóa" + (" qua các năm" if all_years else ""))
    body = "1. **Alpha** — Mã ngành: **7123456** . Tổ hợp môn xét tuyển: (Toán, Lý, Hóa)"
    records = []
    for index, year in enumerate((2025, 2026)):
        row = block(body, index, scope_years=[year]).model_copy(update={"source_revision_id": str(year)})
        records.extend(records_from_block(row, ["toán", "lý", "hóa"]))
    with (patch("app.modules.rag.combination_enumeration.load_records", AsyncMock(return_value=(records, {}))),
          patch("app.modules.rag.combination_enumeration.structured_call", AsyncMock(return_value=
              EnumerationPlan(enumerate_entities=True, all_years_requested=all_years)))):
        result = await enumerate_combinations(AsyncMock(), req, snapshot(), query_classifier.analyze(req.question, "admissions"))
    assert result.status == expected
    if all_years:
        assert result.answer_decision["count"] == 2
    else:
        assert result.answer_decision["reason"] == "ENUMERATION_YEAR_AMBIGUOUS"
        assert "| Năm" not in result.answer
