"""Source-backed arithmetic, stale/missing data and authenticated tool boundaries."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppException
from app.modules.rag.score_conversion import calculate_verified_score, convert_admission_score
from app.modules.rag.score_conversion_chat import ConversionIntent, maybe_convert_score
from app.modules.rag.score_conversion_schemas import (
    CombinationMapping,
    ConversionPoint,
    ConversionRule,
    ScoreConversionRequest,
    SourceCell,
    parse_score,
)
from tests.test_enumeration_and_followup import block, request, snapshot

REVIEWED_HASH = "a" * 64
CODE_LABEL = "Mã tổ hợp"
BASE_LABEL = "Tổ hợp gốc tương đương"
CANONICAL_PROOF = (
    "THÔNG BÁO Về việc quy đổi tương đương điểm giữa các phương thức tuyển sinh đại học chính quy năm 2026\n"
    "Công thức quy đổi điểm Việc quy đổi điểm giữa các phương thức được thực hiện bằng phương pháp nội suy "
    "tuyến tính trong từng khoảng giữa hai mốc bách phân vị liền kề.\n"
    "07 tổ hợp gốc gồm A00, A01, B00, C00, C01, D01 và D07.\n"
    "- Kết quả chỉ được làm tròn một lần ở bước cuối cùng đến hai chữ số thập phân."
)
PROOF_QUOTES = [
    "quy đổi tương đương điểm giữa các phương thức tuyển sinh đại học chính quy năm 2026",
    "nội suy tuyến tính trong từng khoảng giữa hai mốc bách phân vị liền kề",
    "07 tổ hợp gốc gồm A00, A01, B00, C00, C01, D01 và D07",
    "Kết quả chỉ được làm tròn một lần ở bước cuối cùng đến hai chữ số thập phân",
]
# Real Phụ lục 1 shape for A01: ĐNL descends while the percentile row index ascends.
ANNEX_ROWS = (("1024", "28.75"), ("818", "25.13"), ("790", "21.5"), ("764", "20.75"), ("27", "4.4"))


def percentile_rule(rows, *, combination="Z01", base="Alpha", source_attribute="Alpha / Source",
                    target_attribute="Alpha / Target", source_method="Source", target_method="Target",
                    year=2026, rounding="ROUND_HALF_UP", code_label=CODE_LABEL, code_context="default",
                    subject="Toán, Vật lí, Sinh học", proof_text=CANONICAL_PROOF):
    """Percentile grid rows plus one mapping row identified by its subject list, as in Phụ lục 2."""
    blocks = {}
    points = []
    for index, (source, target) in enumerate(rows):
        cells = [{"fact_id": f"dnl{index}", "attribute": source_attribute, "value": source},
                 {"fact_id": f"thpt{index}", "attribute": target_attribute, "value": target}]
        row = block(f"Top % {index}\n{source_attribute}: {source}\n{target_attribute}: {target}", index + 1,
                    origin="reviewed_fact", fact_id=cells[0]["fact_id"],
                    fact_context={"entity_name": f"Top % {index}", "row_context": [], "cells": cells})
        blocks[row.id] = row
        points.append(ConversionPoint(source=SourceCell(block_id=row.id, **cells[0]),
                                      target=SourceCell(block_id=row.id, **cells[1])))
    base_cells = [{"fact_id": "map", "attribute": BASE_LABEL, "value": base}]
    mapping = block(f"{subject}\n{BASE_LABEL}: {base}", 90, origin="reviewed_fact", fact_id="map",
        fact_context={"entity_name": subject, "cells": base_cells,
                      "row_context": [[code_label, combination]] if code_context == "default" else code_context})
    proof = block(proof_text, 91)
    blocks[mapping.id] = mapping
    blocks[proof.id] = proof
    for item in blocks.values():
        item.canonical_hash = REVIEWED_HASH
    rule = ConversionRule(id="reviewed-test-rule", status="verified", reviewed_by="reviewer",
        reviewed_at=datetime.now(UTC), binding_id="bb", index_revision_id="ii", source_revision_id="source",
        canonical_hash=REVIEWED_HASH, year=year, source_method=source_method, target_method=target_method,
        source_attribute=source_attribute, target_attribute=target_attribute, base_combination=base,
        combination_context_attribute=code_label,
        mappings=[CombinationMapping(combination=combination, base_combination=base,
            proof=SourceCell(block_id=mapping.id, **base_cells[0]))],
        points=points, operation="piecewise_linear", decimal_places=2, rounding=rounding,
        rule_proofs=[{"block_id": proof.id, "quote": quote} for quote in PROOF_QUOTES])
    return rule, blocks


def fixture_rule():
    return percentile_rule((("700", "20"), ("750", "22"), ("800", "24")))


def managed_metadata(rule):
    """Runtime rules now require a distinct server-owned activation state."""
    return {"score_conversion_registry": {"items": [{
        "definition": rule.model_dump(mode="json", exclude={"status", "reviewed_by", "reviewed_at"}),
        "status": "active", "created_by": "operator", "created_at": rule.reviewed_at.isoformat(),
        "reviewed_by": rule.reviewed_by, "reviewed_at": rule.reviewed_at.isoformat()}]}}


def annex_rule(**over):
    return percentile_rule(ANNEX_ROWS, combination="A02", base="A01", source_attribute="ĐNL",
                           target_attribute="A01 / THPT", source_method="ĐNL", target_method="THPT", **over)


def conversion_request(score="780", **over):
    return ScoreConversionRequest.model_validate({"collection_id": "cc", "year": 2026,
        "source_method": "Source", "combination": "Z01", "score": score, **over})


def annex_request(score="780", **over):
    return ScoreConversionRequest.model_validate({"collection_id": "cc", "year": 2026,
        "source_method": "ĐNL", "combination": "A02", "score": score, **over})


def tamper(blocks, cell_ref, mutate):
    holder = blocks[cell_ref.block_id]
    cell = next(item for item in holder.fact_context["cells"] if item["fact_id"] == cell_ref.fact_id)
    mutate(cell, holder)


@pytest.mark.parametrize("score,expected", [("700", "20.00"), ("750", "22.00"), ("780", "23.20"), ("800", "24.00")])
def test_exact_interpolation_and_shared_boundaries(score, expected):
    rule, blocks = fixture_rule()
    result = calculate_verified_score(conversion_request(score), rule, blocks, snapshot())
    assert result.result == expected and result.status == "calculated"
    assert result.citations and result.snapshot_id == "ss"


def test_descending_percentile_rows_keep_matching_columns():
    rule, blocks = fixture_rule()
    rule.points.reverse()
    assert calculate_verified_score(conversion_request(), rule, blocks, snapshot()).result == "23.20"


def test_independent_oracle_from_the_published_annex_marks():
    """ĐNL 780 sits between 764 → 20,75 and 790 → 21,50; HALF_UP gives 21,21."""
    rule, blocks = annex_rule()
    result = calculate_verified_score(annex_request(), rule, blocks, snapshot())
    assert result.status == "calculated" and result.result == "21.21"
    assert (result.x1, result.y1, result.x2, result.y2) == ("764", "20.75", "790", "21.5")
    assert result.base_combination == "A01" and result.combination == "A02"


@pytest.mark.parametrize("score,expected", [("27", "4.40"), ("764", "20.75"), ("790", "21.50"), ("1024", "28.75")])
def test_range_endpoints_and_exact_marks_use_the_reviewed_cells(score, expected):
    rule, blocks = annex_rule()
    assert calculate_verified_score(annex_request(score), rule, blocks, snapshot()).result == expected


@pytest.mark.parametrize("score", ["26.99", "1024.01", "2000"])
def test_scores_outside_the_reviewed_range_are_never_extrapolated(score):
    rule, blocks = annex_rule()
    result = calculate_verified_score(annex_request(score), rule, blocks, snapshot())
    assert result.status == "missing" and result.reason == "SCORE_OUTSIDE_VERIFIED_RANGE"
    assert result.result is None and not result.citations


def test_decimal_comma_input_lands_in_the_same_bracket():
    rule, blocks = annex_rule()
    assert calculate_verified_score(annex_request("780,00"), rule, blocks, snapshot()).result == "21.21"


@pytest.mark.parametrize("rounding,expected", [
    ("ROUND_HALF_UP", "24.13"), ("ROUND_HALF_EVEN", "24.12"), ("ROUND_DOWN", "24.12")])
def test_a_midpoint_follows_the_reviewed_rounding_mode(rounding, expected):
    rule, blocks = percentile_rule((("100", "24.12"), ("200", "24.13")), rounding=rounding)
    result = calculate_verified_score(conversion_request("150"), rule, blocks, snapshot())
    assert result.result == expected and result.rounding == rounding


@pytest.mark.asyncio
async def test_reviewed_rows_expose_their_provenance_row_context():
    from app.modules.rag.evidence_facts import reviewed_fact_blocks
    from app.modules.rag.evidence_schemas import QueryPlan

    facts = [SimpleNamespace(id="f1", index_revision_id="ii", binding_id="bb", applicability_year=None,
        entity_name="Toán, Vật lí, Sinh học", entity_code=None, attribute_name=BASE_LABEL, attribute_value="A01",
        raw_data={"table_id": "table_2", "row_index": 3, "column_index": 2,
                  "row_context": [[CODE_LABEL, "A02"]]})]
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: facts))
    rows = await reviewed_fact_blocks(db, request(), snapshot(), QueryPlan(query="list"),
                                      [block("Source")], exhaustive=True)
    assert rows[0].fact_context["row_context"] == [[CODE_LABEL, "A02"]]


@pytest.mark.parametrize("code_context", [
    [],
    [["Mã tổ hợp gốc", "A02"]],
    [[CODE_LABEL, "A01"]],
    [[CODE_LABEL, "A02"], [CODE_LABEL, "A02"]],
    [[CODE_LABEL, "A02", "extra"]],
    "A02",
    None,
])
def test_the_combination_code_must_come_from_one_reviewed_row_context_cell(code_context):
    rule, blocks = annex_rule(code_context=code_context)
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_a_subject_list_entity_name_never_authorizes_the_mapping():
    rule, blocks = annex_rule(code_context=[])
    blocks[rule.mappings[0].proof.block_id].fact_context["entity_name"] = "A02"
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_a_reviewed_code_label_that_matches_no_source_column_is_rejected():
    rule, blocks = annex_rule()
    rule.combination_context_attribute = "Mã ngành"
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_a_point_borrowing_another_exam_column_is_rejected():
    rule, blocks = annex_rule()
    rule.points[2].source.attribute = "A01 / SPT"
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_marks_from_two_different_percentile_rows_cannot_form_a_bracket():
    rule, blocks = annex_rule()
    rule.points[2].target = rule.points[3].target
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_duplicate_source_marks_are_rejected_instead_of_repaired():
    rule, blocks = annex_rule()
    tamper(blocks, rule.points[1].source, lambda cell, _: cell.update(value="1024"))
    rule.points[1].source.value = "1024"
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_a_missing_cell_is_never_filled_in():
    rule, blocks = annex_rule()
    tamper(blocks, rule.points[3].target,
           lambda cell, holder: holder.fact_context["cells"].remove(cell))
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_a_tampered_target_cell_breaks_the_proof_chain():
    rule, blocks = annex_rule()
    tamper(blocks, rule.points[2].target, lambda cell, _: cell.update(value="21.51"))
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_a_mapping_proof_moved_to_another_source_revision_is_rejected():
    rule, blocks = annex_rule()
    blocks[rule.mappings[0].proof.block_id].source_revision_id = "ks_rev_other"
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_the_year_comes_from_the_reviewed_rule_not_the_file_name():
    rule, blocks = annex_rule()
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(year=2025), rule, blocks, snapshot())


def test_rule_proofs_must_be_exact_quotes_of_the_published_source():
    rule, blocks = annex_rule(proof_text=CANONICAL_PROOF.replace("năm 2026", "năm 2025"))
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


def test_a_rule_pinned_to_a_superseded_index_revision_is_rejected():
    rule, blocks = annex_rule()
    rule.index_revision_id = "old"
    with pytest.raises(ValueError):
        calculate_verified_score(annex_request(), rule, blocks, snapshot())


@pytest.mark.parametrize("score", ["NaN", "Infinity", "-2", "1,000", "1.234,5", "2e3", "1/0"])
def test_ambiguous_or_executable_numbers_are_rejected(score):
    with pytest.raises((ValueError, ValidationError)):
        conversion_request(score)


def test_decimal_comma_is_not_binary_float():
    assert str(parse_score("24,5")) == "24.5"


@pytest.mark.parametrize("corruption", ["duplicate", "target_decrease", "foreign", "changed", "method", "year",
                                        "mapping", "column"])
def test_corrupted_stale_or_mismatched_evidence_cannot_calculate(corruption):
    rule, blocks = fixture_rule()
    req = conversion_request()
    if corruption == "duplicate":
        rule.points[1] = rule.points[0]
    elif corruption == "target_decrease":
        rule.points[1].target = rule.points[0].target
    elif corruption == "foreign":
        blocks[rule.points[0].source.block_id].binding_id = "foreign"
    elif corruption == "changed":
        rule.points[0].source.value = "701"
    elif corruption == "method":
        req.source_method = "Other exam"
    elif corruption == "year":
        req.year = 2025
    elif corruption == "mapping":
        blocks[rule.mappings[0].proof.block_id].fact_context["row_context"] = [[CODE_LABEL, "Z02"]]
    else:
        rule.points[0].source.attribute = "Other / Source"
    with pytest.raises(ValueError):
        calculate_verified_score(req, rule, blocks, snapshot())


def test_outside_range_never_clamps_or_extrapolates():
    rule, blocks = fixture_rule()
    result = calculate_verified_score(conversion_request("900"), rule, blocks, snapshot())
    assert result.status == "missing" and result.result is None


@pytest.mark.asyncio
async def test_no_verified_rules_returns_missing_without_loading_or_inventing_table():
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(tenant_id="tt", workspace_id="ww", collection_metadata={})
    with (patch("app.modules.rag.retriever.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
          patch("app.modules.rag.score_conversion.load_published_blocks", AsyncMock()) as load):
        result = await convert_admission_score(db, conversion_request(), tenant_id="tt", workspace_id="ww")
    assert result.reason == "NO_VERIFIED_CONVERSION_RULE" and result.result is None
    load.assert_not_awaited()


@pytest.mark.asyncio
async def test_tool_database_outage_is_not_no_answer():
    db = AsyncMock()
    db.get.side_effect = RuntimeError("DB down")
    with (patch("app.modules.rag.retriever.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
          pytest.raises(AppException) as error):
        await convert_admission_score(db, conversion_request(), tenant_id="tt", workspace_id="ww")
    assert error.value.code == "SCORE_RULE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_tool_rejects_missing_collection():
    db = AsyncMock()
    db.get.return_value = None
    with (patch("app.modules.rag.retriever.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
          pytest.raises(AppException) as error):
        await convert_admission_score(db, conversion_request(), tenant_id="tt", workspace_id="ww")
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_outage_while_resolving_the_snapshot_is_a_service_error_not_an_unhandled_500():
    db = AsyncMock()
    db.get.side_effect = RuntimeError("DB down")
    with pytest.raises(AppException) as error:
        await convert_admission_score(db, conversion_request(), tenant_id="tt", workspace_id="ww")
    assert error.value.code == "SCORE_RULE_UNAVAILABLE" and error.value.status_code == 503


@pytest.mark.asyncio
async def test_a_scope_refusal_is_never_masked_as_a_database_outage():
    db = AsyncMock()
    db.get.return_value = None
    with pytest.raises(AppException) as error:
        await convert_admission_score(db, conversion_request(), tenant_id="tt", workspace_id="ww")
    assert error.value.code != "SCORE_RULE_UNAVAILABLE" and error.value.status_code == 404


@pytest.mark.asyncio
async def test_theory_question_does_not_trigger_calculator_or_model():
    with patch("app.modules.rag.score_conversion_chat.structured_call", AsyncMock()) as model:
        assert await maybe_convert_score(AsyncMock(), request("Công thức quy đổi tổ hợp A01 năm 2026 thế nào?")) is None
    model.assert_not_awaited()


@pytest.mark.asyncio
async def test_extracted_year_or_score_must_exist_in_original_question():
    intent = ConversionIntent(intent="calculate", score="2026", year=2026, source_method="Source", combination="Z01")
    with (patch("app.modules.rag.score_conversion_chat.structured_call", AsyncMock(return_value=intent)),
          patch("app.modules.rag.score_conversion_chat.convert_admission_score", AsyncMock()) as calculate):
        result = await maybe_convert_score(AsyncMock(), request("Source 780 điểm Z01 năm 2026 quy đổi?"))
    assert result.answer_decision["reason"] == "CONVERSION_INPUT_INCOMPLETE"
    calculate.assert_not_awaited()


@pytest.mark.asyncio
async def test_snapshot_scope_mismatch_stops_before_reading_rules():
    db = AsyncMock()
    wrong = snapshot().model_copy(update={"collection_id": "foreign"})
    with (patch("app.modules.rag.retriever.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=wrong)),
          pytest.raises(AppException) as error):
        await convert_admission_score(db, conversion_request(), tenant_id="tt", workspace_id="ww")
    assert error.value.code == "SCORE_SCOPE_FORBIDDEN"
    db.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_rule_cannot_load_old_published_blocks():
    rule, _ = fixture_rule()
    rule.index_revision_id = "old"
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(tenant_id="tt", workspace_id="ww",
        collection_metadata={"score_conversion_registry": {"items": [{
            "definition": rule.model_dump(mode="json", exclude={"status", "reviewed_by", "reviewed_at"}),
            "status": "active", "created_by": "operator", "created_at": rule.reviewed_at.isoformat(),
            "reviewed_by": rule.reviewed_by, "reviewed_at": rule.reviewed_at.isoformat()}]}})
    with (patch("app.modules.rag.retriever.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
          patch("app.modules.rag.score_conversion.load_published_blocks", AsyncMock()) as load,
          pytest.raises(AppException) as error):
        await convert_admission_score(db, conversion_request(), tenant_id="tt", workspace_id="ww")
    assert error.value.code == "SCORE_RULE_STALE"
    load.assert_not_awaited()


def test_public_input_cannot_supply_reviewed_rules_or_authorization():
    with pytest.raises(ValidationError):
        ScoreConversionRequest.model_validate({**conversion_request().model_dump(), "tenant_id": "other", "rule": {}})


@pytest.mark.asyncio
async def test_verified_tool_loads_current_facts_and_returns_deterministic_result():
    rule, blocks = fixture_rule()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(tenant_id="tt", workspace_id="ww",
        collection_metadata=managed_metadata(rule))
    with (patch("app.modules.rag.retriever.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
          patch("app.modules.rag.score_conversion.load_published_blocks", AsyncMock(return_value=list(blocks.values()))),
          patch("app.modules.rag.score_conversion.reviewed_fact_blocks", AsyncMock(return_value=[]))):
        result = await convert_admission_score(db, conversion_request(), tenant_id="tt", workspace_id="ww")
    assert result.result == "23.20" and result.citations


@pytest.mark.asyncio
async def test_original_user_input_cannot_be_completed_by_model_rewrite():
    req = request("Source 780 điểm Z01 năm 2026 quy đổi?")
    req.original_question = "Source 780 điểm Z01 quy đổi?"
    intent = ConversionIntent(intent="calculate", score="780", year=2026, source_method="Source", combination="Z01")
    with (patch("app.modules.rag.score_conversion_chat.structured_call", AsyncMock(return_value=intent)) as model,
          patch("app.modules.rag.score_conversion_chat.convert_admission_score", AsyncMock()) as calculate):
        result = await maybe_convert_score(AsyncMock(), req)
    assert result.answer_decision["reason"] == "CONVERSION_INPUT_INCOMPLETE"
    assert model.call_args.args[4]["question"] == req.original_question
    calculate.assert_not_awaited()


@pytest.mark.asyncio
async def test_chat_never_generates_a_numeric_answer_when_rule_is_missing():
    from app.modules.rag.score_conversion_schemas import ScoreConversionResult

    intent = ConversionIntent(intent="calculate", score="780", year=2026, source_method="Source", combination="Z01")
    missing = ScoreConversionResult(status="missing", reason="NO_VERIFIED_CONVERSION_RULE", message="Chưa có bảng đã duyệt.")
    with (patch("app.modules.rag.score_conversion_chat.structured_call", AsyncMock(return_value=intent)) as model,
          patch("app.modules.rag.score_conversion_chat.convert_admission_score", AsyncMock(return_value=missing))):
        result = await maybe_convert_score(AsyncMock(), request("Source 780 điểm Z01 năm 2026 quy đổi?"))
    assert result.status == "insufficient_context" and result.answer == missing.message
    assert not result.citations and model.await_count == 1


@pytest.mark.asyncio
async def test_chat_renders_only_server_computed_numbers():
    rule, blocks = annex_rule()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(tenant_id="tt", workspace_id="ww",
        collection_metadata=managed_metadata(rule))
    intent = ConversionIntent(intent="calculate", score="780", year=2026, source_method="ĐNL", combination="A02")
    question = "ĐNL 780 điểm tổ hợp A02 năm 2026 quy đổi sang THPT được bao nhiêu?"
    with (patch("app.modules.rag.retriever.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
          patch("app.modules.rag.score_conversion.load_published_blocks", AsyncMock(return_value=list(blocks.values()))),
          patch("app.modules.rag.score_conversion.reviewed_fact_blocks", AsyncMock(return_value=[])),
          patch("app.modules.rag.score_conversion_chat.structured_call", AsyncMock(return_value=intent)) as model):
        response = await maybe_convert_score(db, request(question))
    assert response.status == "answered" and "21.21" not in question
    assert "21.21" in response.answer and "764" in response.answer and response.citations
    assert model.await_count == 1 and response.answer_decision["status"] == "calculated"


@pytest.mark.asyncio
async def test_router_takes_scope_from_the_actor_never_from_the_body():
    from app.modules.rag.router import convert_score

    actor = SimpleNamespace(tenant_id="tt", workspace_id="ww")
    with patch("app.modules.rag.score_conversion.convert_admission_score", AsyncMock()) as tool:
        await convert_score(conversion_request(), AsyncMock(), actor)
    assert tool.await_args.kwargs == {"tenant_id": "tt", "workspace_id": "ww"}
