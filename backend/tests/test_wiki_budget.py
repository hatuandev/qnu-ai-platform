"""Whole-request limits and compact metadata keep large-source calls bounded."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.retrieval_models import SourceUnit, TemporalScope
from app.modules.knowledge.services.wiki_budget import compact_context, request_usage
from app.modules.knowledge.services.wiki_compiler import ANALYZE, GENERATE, packet_fits, packets
from app.modules.knowledge.wiki_schemas import WikiAnalysis, WikiGeneration, WikiPolicy


def units(count=80):
    path = ["Phạm vi dữ liệu nhiều năm và điều kiện gốc " * 4]
    scope = TemporalScope(data_years=[2025, 2026], role="data", status="proposed",
        basis_quote="Điều kiện và phạm vi " * 12)
    return [SourceUnit(id=f"unit-{i}", kind="paragraph", start=i*200, end=i*200+190,
        text=f"Dữ kiện {i}: giữ nguyên mã 0012 và ngoại lệ của dòng.", heading_path=path, temporal=scope)
        for i in range(count)]


def test_compaction_preserves_exact_units_and_shared_scope_without_repetition_or_source_mutation():
    group = units()
    before = deepcopy(group)
    context = compact_context(group, {"source_revision_id": "r"}, "Nguồn thử nghiệm")
    assert [u["text"] for u in context["units"]] == [u.text for u in group]
    assert [u["id"] for u in context["units"]] == [u.id for u in group]
    assert len(context["scopes"]) == 1
    shared = next(iter(context["scopes"].values()))
    assert shared["heading_path"] == group[0].heading_path
    assert shared["temporal"]["data_years"] == [2025, 2026]
    assert shared["temporal"]["basis_quote"] == group[0].temporal.basis_quote
    assert {u["scope_id"] for u in context["units"]} == set(context["scopes"])
    assert group == before


def test_request_budget_counts_instruction_contract_utf8_metadata_analysis_and_output_reserve():
    context = compact_context(units(2), {}, "Nguồn")
    policy = WikiPolicy()
    original = request_usage(WikiGeneration, GENERATE, context, policy)
    assert original["method"] == "utf8_upper_bound_with_framing"
    assert original["reserved_output_tokens"] == policy.max_output_tokens
    more = request_usage(WikiGeneration, GENERATE + " chỉ dẫn" * 20,
        {**context, "analysis": {"pages": [{"title": "Phạm vi" * 30}]}}, policy)
    assert more["input_upper_bound"] > original["input_upper_bound"]
    assert more["total_reserved"] > original["total_reserved"]


def test_packetizer_splits_on_serialized_scope_budget_before_dispatching_without_losing_units():
    group = units()
    for unit in group:
        unit.text *= 3
    policy = WikiPolicy()
    result = packets(group, policy)
    assert len(result) > 1
    assert {u.id for packet in result for u in packet} == {u.id for u in group}
    for packet in result:
        context = compact_context(packet, {}, "x" * 180)
        assert request_usage(WikiAnalysis, ANALYZE, context, policy)["fits"]
        assert packet_fits(packet, policy, {}, "x" * 180)


def test_unbounded_metadata_in_one_source_unit_fails_closed_instead_of_dropping_scope():
    group = units(1)
    group[0].temporal.basis_quote = "Phạm vi cần bảo toàn " * 3000
    before = deepcopy(group)
    with pytest.raises(AppException):
        packets(group, WikiPolicy())
    assert group == before


def test_whole_unit_reference_capacity_is_checked_before_generation_without_cropping_source():
    group = units(1)
    group[0].text = "A" * 6001
    before = deepcopy(group)
    with pytest.raises(AppException) as caught:
        packets(group, WikiPolicy())
    assert caught.value.details["reason"] == "source_unit_exceeds_reference_capacity"
    assert group == before


def test_vietnamese_utf8_and_repair_text_use_the_same_reservation_not_a_char_ratio():
    policy = WikiPolicy(context_budget_tokens=14000)
    ascii_usage = request_usage(WikiAnalysis, ANALYZE, {"text": "a" * 2000}, policy)
    utf8_usage = request_usage(WikiAnalysis, ANALYZE, {"text": "ệ" * 2000}, policy)
    assert utf8_usage["input_upper_bound"] - ascii_usage["input_upper_bound"] == 4000
    repaired = request_usage(WikiAnalysis, ANALYZE, {"text": "a" * 2000,
        "validation_feedback": "ệ" * 4000}, policy)
    assert not repaired["fits"]


@pytest.mark.parametrize("content,accepted", [("Mốc năm 2026.", True), ("Mã 0012.", True),
                                               ("Mã 12.", False), ("Giá trị 999.", False)])
def test_year_inside_exact_date_is_supported_but_numeric_identity_is_not_coerced(content, accepted):
    from app.modules.knowledge.services.wiki_compiler import validate_page
    from app.modules.knowledge.wiki_schemas import WikiPage
    unit = SourceUnit(id="date", kind="paragraph", text="Hạn 30/11/2026, mã 0012.", start=0, end=30)
    page = WikiPage(kind="concept", title="Mốc", sections=[{"heading": "Phạm vi", "text": content,
        "references": [{"unit_id": unit.id, "quote": unit.text}]}])
    if accepted:
        validate_page(page, {unit.id: unit})
    else:
        with pytest.raises(AppException) as caught:
            validate_page(page, {unit.id: unit})
        assert caught.value.details["page_title"] == page.title
        assert caught.value.details["unsupported_tokens"]


def test_packet_contract_rejects_verbose_generation_without_relaxing_source_validation():
    from pydantic import ValidationError

    from app.modules.knowledge.wiki_schemas import WikiPacketGeneration
    section = {"heading": "Phạm vi", "text": "Nội dung nguồn.", "references": ["u"]}
    with pytest.raises(ValidationError) as caught:
        WikiPacketGeneration.model_validate({"pages": [{"kind": "source", "title": "Nguồn",
            "sections": [section, section, section, section]}]})
    assert caught.value.errors()[0]["type"] == "too_long"


@pytest.mark.parametrize("bad_id", [None, "missing", "outside"])
def test_id_transport_binds_exact_original_text_and_rejects_unoffered_or_unoutlined_units(bad_id):
    from app.modules.knowledge.services.wiki_compiler import (
        bind_source_references,
        validate_generation,
    )
    from app.modules.knowledge.wiki_schemas import WikiPacketGeneration
    raw = "Phạm vi năm 2025\nMã 0012; ngoại lệ: giữ nguyên."
    unit = SourceUnit(id="u", kind="paragraph", text=raw, start=0, end=len(raw))
    other = SourceUnit(id="outside", kind="paragraph", text="Không thuộc outline.", start=100, end=122)
    before = deepcopy(unit)
    analysis = WikiAnalysis(pages=[{"kind": "source", "title": "Nguồn", "unit_ids": ["u"]}])
    draft = WikiPacketGeneration(pages=[{"kind": "source", "title": "Nguồn", "sections": [{
        "heading": "Phạm vi", "text": "Mã 0012, năm 2025.", "references": [bad_id or "u"],
        "temporal": [{"role": "data", "years": [2025], "references": ["u"]}]}]}])
    if bad_id:
        with pytest.raises(AppException) as caught:
            output = bind_source_references(draft, {"u": unit, "outside": other})
            validate_generation(output, analysis, {"u": unit, "outside": other})
        assert caught.value.details["reason"] == "quote_binding"
    else:
        output = bind_source_references(draft, {"u": unit})
        validate_generation(output, analysis, {"u": unit})
        section = output.pages[0].sections[0]
        assert section.references[0].quote == raw
        assert section.temporal[0].references[0].quote == raw
        assert draft.pages[0].sections[0].references == ["u"]
    assert unit == before


def test_legacy_quote_object_is_never_silently_corrected_by_id_binding():
    from app.modules.knowledge.services.wiki_compiler import bind_source_references, validate_page
    unit = SourceUnit(id="u", kind="paragraph", text="Dòng gốc\nMã 0012.", start=0, end=18)
    draft = WikiGeneration(pages=[{"kind": "source", "title": "Nguồn", "sections": [{
        "heading": "Phạm vi", "text": "Mã 0012.",
        "references": [{"unit_id": "u", "quote": "Dòng gốc Mã 0012."}]}]}])
    output = bind_source_references(draft, {"u": unit})
    assert output.pages[0].sections[0].references[0].quote == "Dòng gốc Mã 0012."
    with pytest.raises(AppException):
        validate_page(output.pages[0], {"u": unit})


def test_repair_candidates_are_exact_tokens_from_same_outline_and_do_not_add_references():
    from app.modules.knowledge.services.wiki_compiler import reference_candidates
    group = {u.id: u for u in units(4)}
    analysis = WikiAnalysis(pages=[{"kind": "source", "title": "Nguồn", "unit_ids": ["unit-0", "unit-1"]}])
    before = analysis.model_copy(deep=True)
    result = reference_candidates(analysis, group, {"page_title": "Nguồn", "page_kind": "source",
        "unsupported_tokens": ["1", "2", "12", "0012"]})
    assert result == {"1": ["unit-1"], "2": [], "12": [], "0012": ["unit-0", "unit-1"]}
    assert analysis == before


def test_generation_reports_multiple_section_failures_before_one_bounded_repair():
    from app.modules.knowledge.services.wiki_compiler import validate_generation
    group = {u.id: u for u in units(3)}
    analysis = WikiAnalysis(pages=[{"kind": "source", "title": "Nguồn", "unit_ids": ["unit-0"]}])
    output = WikiGeneration(pages=[{"kind": "source", "title": "Nguồn", "sections": [
        {"heading": "Giá trị", "text": "Giá trị 999.", "references": [{"unit_id": "unit-0", "quote": group["unit-0"].text}]},
        {"heading": "Phạm vi", "text": "Mã 0012.", "references": [{"unit_id": "unit-2", "quote": group["unit-2"].text}]}]}])
    with pytest.raises(AppException) as caught:
        validate_generation(output, analysis, group)
    findings = caught.value.details["validation_findings"]
    assert [(f["page_index"], f["section_index"], f["reason"]) for f in findings] == [
        (1, 1, "unsupported_value"), (1, 2, "quote_binding")]
    assert findings[1]["invalid_unit_ids"] == ["unit-2"]


def test_packet_and_outline_close_explicit_header_context_without_writing_source_or_adding_unlinked_notes():
    from app.modules.knowledge.services.wiki_compiler import close_outline_headings
    header = SourceUnit(id="header", kind="table", text="| Năm 2025 | Năm 2027 |", start=0, end=25)
    row = SourceUnit(id="row", kind="table", text="| Mã 0012 | 5 | 8 |", start=30, end=50,
        context_refs=[header.id], field_context_refs={"c1": [header.id]})
    note = SourceUnit(id="other-note", kind="paragraph", text="Ngoại lệ không liên kết.", start=60, end=85)
    group = [header, row, note]
    before = deepcopy(group)
    analysis = WikiAnalysis(pages=[{"kind": "entity", "title": "Mã", "unit_ids": [row.id]}])
    closed = close_outline_headings(analysis, {u.id: u for u in group})
    assert closed.pages[0].unit_ids == [row.id, header.id]
    assert analysis.pages[0].unit_ids == [row.id]
    result = packets([row, header, note], WikiPolicy())
    assert all(header.id in {u.id for u in packet} for packet in result if row in packet)
    context = compact_context([row, header], {}, "Nguồn")
    assert context["units"][0]["context_ids"] == [header.id]
    assert group == before


def test_missing_linked_context_fails_closed_and_duplicate_heading_uses_preceding_instance():
    from app.modules.knowledge.services.wiki_compiler import close_outline_headings
    path = ["Phạm vi"]
    old = SourceUnit(id="h1", kind="heading", text="# Phạm vi", heading_path=path, start=0, end=10)
    row = SourceUnit(id="r", kind="paragraph", text="Dữ liệu năm 2025.", heading_path=path, start=15, end=32)
    newer = old.model_copy(update={"id": "h2", "start": 100, "end": 110})
    analysis = WikiAnalysis(pages=[{"kind": "entity", "title": "Mã", "unit_ids": [row.id]}])
    closed = close_outline_headings(analysis, {u.id: u for u in [old, row, newer]})
    assert closed.pages[0].unit_ids == [row.id, old.id]
    row.context_refs = ["missing"]
    with pytest.raises(AppException) as caught:
        packets([old, row, newer], WikiPolicy())
    assert caught.value.details["reason"] == "missing_structural_context"


def test_year_feedback_requires_temporal_own_reference_even_when_section_has_correct_header():
    from app.modules.knowledge.services.wiki_compiler import validate_generation
    header = SourceUnit(id="h", kind="table", text="| Năm 2025 |", start=0, end=12)
    row = SourceUnit(id="r", kind="table", text="| Mã | 85 |", start=14, end=25)
    analysis = WikiAnalysis(pages=[{"kind": "source", "title": "Nguồn", "unit_ids": ["h", "r"]}])
    output = WikiGeneration(pages=[{"kind": "source", "title": "Nguồn", "sections": [{
        "heading": "Dữ liệu", "text": "Giá trị năm 2025.", "references": [{"unit_id": "h", "quote": header.text}],
        "temporal": [{"role": "data", "years": [2025], "references": [{"unit_id": "r", "quote": row.text}]}]}]}])
    with pytest.raises(AppException) as caught:
        validate_generation(output, analysis, {"h": header, "r": row})
    finding = caught.value.details["validation_findings"][0]
    assert (finding["reason"], finding["temporal_index"], finding["role"], finding["unsupported_tokens"]) == ("year_evidence", 1, "data", ["2025"])
    output.pages[0].sections[0].temporal[0].references = output.pages[0].sections[0].references
    validate_generation(output, analysis, {"h": header, "r": row})


@pytest.mark.asyncio
async def test_two_repair_budget_does_not_increase_global_call_limit_or_repair_invalid_evidence():
    from test_knowledge_wiki import model_outputs, section_patch, source_revision

    from app.modules.knowledge.services.wiki_compiler import compile_wiki

    source = source_revision()
    from app.modules.knowledge.services.wiki_compiler import source_units
    analysis, valid = model_outputs(source_units(source))
    wrong = valid.model_copy(deep=True)
    wrong.pages[0].sections[0].text = "Giá trị 999999."
    generate = AsyncMock(side_effect=[analysis, wrong, section_patch(wrong.pages[0].sections[0]), section_patch(valid.pages[0].sections[0])])
    bundle = await compile_wiki(source, "collection-a", WikiPolicy(max_calls=4), generate)
    assert bundle["calls"] == 4 and bundle["contract_retries"] == 2
    generate = AsyncMock(side_effect=[analysis, wrong, section_patch(wrong.pages[0].sections[0])])
    with pytest.raises(AppException) as caught:
        await compile_wiki(source, "collection-a", WikiPolicy(max_calls=3), generate)
    assert caught.value.code == "KNOWLEDGE_WIKI_BUDGET"
    assert generate.await_count == 3


@pytest.mark.asyncio
async def test_generation_adapter_rejects_oversized_whole_payload_without_provider_call():
    from app.modules.knowledge.services.wiki_build import generate_object
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock()) as model, pytest.raises(AppException) as caught:
        await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(context_budget_tokens=10000), [],
            WikiGeneration, GENERATE, {"validation_feedback": "Đ" * 20000})
    assert caught.value.code == "KNOWLEDGE_WIKI_BUDGET"
    model.assert_not_awaited()


@pytest.mark.asyncio
async def test_small_request_adapter_keeps_output_limit_and_never_sends_scope_as_permission():
    import json

    from app.modules.knowledge.services.wiki_build import generate_object
    response = SimpleNamespace(content=json.dumps({"pages": [{"kind": "source", "title": "Nguồn",
        "unit_ids": ["u0"]}]}), provider="configured", model="configured", is_fallback=False,
        prompt_tokens=500, completion_tokens=50)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response)) as model:
        metrics = []
        output = await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(), metrics, WikiAnalysis, ANALYZE,
                                       compact_context(units(1), {}, "Nguồn"))
    request = model.await_args.args[1]
    assert request.max_tokens == WikiPolicy().max_output_tokens
    assert metrics[0]["request_budget"]["fits"]
    assert metrics[0]["request_budget"]["observed_input_tokens"] == 500
    assert output.pages[0].unit_ids == ["unit-0"]


def test_request_handles_are_local_and_each_page_has_a_closed_evidence_contract():
    from pydantic import ValidationError

    from app.modules.knowledge.services.wiki_transport import prepare_transport, restore_source_ids
    from app.modules.knowledge.wiki_schemas import WikiPacketGeneration
    payload = {**compact_context(units(3), {}, "Nguồn"), "analysis": {"pages": [
        {"kind": "source", "title": "Nguồn", "unit_ids": ["unit-0", "unit-1"]},
        {"kind": "concept", "title": "Chủ đề", "unit_ids": ["unit-2"]}]},
        "validation_feedback": {"supporting_unit_candidates": {"0012": ["unit-0"]}}}
    before = deepcopy(payload)
    bound, wire, reverse = prepare_transport(WikiPacketGeneration, payload)
    assert [u["id"] for u in wire["units"]] == ["u0", "u1", "u2"]
    assert [u["text"] for u in wire["units"]] == [u["text"] for u in payload["units"]]
    assert wire["validation_feedback"]["supporting_unit_candidates"] == {"0012": ["u0"]}
    data = {"pages": [{"kind": "concept", "title": "Chủ đề", "sections": [{"heading": "Phạm vi",
        "text": "Mã 0012.", "references": ["u2"], "temporal": [{"role": "data", "years": [2025], "references": ["u2"]}]}]}]}
    output = restore_source_ids(WikiPacketGeneration, bound.model_validate(data), reverse)
    assert output.pages[0].sections[0].references == ["unit-2"]
    assert output.pages[0].sections[0].temporal[0].references == ["unit-2"]
    for wrong_id in ["u0", "u999", "unit-2"]:
        data["pages"][0]["sections"][0]["references"] = [wrong_id]
        with pytest.raises(ValidationError) as caught:
            bound.model_validate(data)
        assert len(caught.value.errors()) == 1
        assert "page1" in caught.value.errors()[0]["loc"]
    assert payload == before


def test_analysis_handles_cannot_invent_an_unoffered_source_unit():
    from pydantic import ValidationError

    from app.modules.knowledge.services.wiki_transport import prepare_transport, restore_source_ids
    bound, wire, reverse = prepare_transport(WikiAnalysis, compact_context(units(1), {}, "Nguồn"))
    data = {"pages": [{"kind": "source", "title": "Nguồn", "unit_ids": ["u0"]}]}
    output = restore_source_ids(WikiAnalysis, bound.model_validate(data), reverse)
    assert output.pages[0].unit_ids == ["unit-0"]
    data["pages"][0]["unit_ids"] = ["u1"]
    with pytest.raises(ValidationError):
        bound.model_validate(data)
    assert wire["units"][0]["id"] == "u0"


def test_handle_transport_keeps_full_persisted_reference_capacity_without_dropping_ids():
    from pydantic import ValidationError

    from app.modules.knowledge.services.wiki_transport import prepare_transport, restore_source_ids
    from app.modules.knowledge.wiki_schemas import WikiPacketGeneration
    payload = {**compact_context(units(21), {}, "Nguồn"), "analysis": {"pages": [
        {"kind": "source", "title": "Nguồn", "unit_ids": [f"unit-{i}" for i in range(21)]}]}}
    bound, _, reverse = prepare_transport(WikiPacketGeneration, payload)
    data = {"pages": [{"kind": "source", "title": "Nguồn", "sections": [{"heading": "Phạm vi",
        "text": "Nội dung nguồn.", "references": [f"u{i}" for i in range(20)]}]}]}
    output = restore_source_ids(WikiPacketGeneration, bound.model_validate(data), reverse)
    assert output.pages[0].sections[0].references == [f"unit-{i}" for i in range(20)]
    data["pages"][0]["sections"][0]["references"].append("u20")
    with pytest.raises(ValidationError):
        bound.model_validate(data)


@pytest.mark.asyncio
@pytest.mark.parametrize("envelope", ["{}", "```json\n{}```", "```json\n{}\n```"])
async def test_adapter_accepts_one_complete_json_object_or_one_outer_fence(envelope):
    import json

    from app.modules.knowledge.services.wiki_build import generate_object
    body = json.dumps({"pages": [{"kind": "source", "title": "Nguồn", "unit_ids": ["u"]}]})
    response = SimpleNamespace(content=envelope.replace("{}", body), provider="configured", model="configured",
        is_fallback=False, prompt_tokens=100, completion_tokens=100)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response)):
        output = await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(), [], WikiAnalysis, ANALYZE, {})
    assert output.pages[0].unit_ids == ["u"]


@pytest.mark.asyncio
@pytest.mark.parametrize("body,reason", [('private-source {', "json_syntax"),
    ('{"pages": [], "$.pages": []}', "json_contract"), ('{} {}', "json_syntax")])
async def test_adapter_reports_parse_failure_without_repairing_json_or_exposing_source(body, reason):
    from app.modules.knowledge.services.wiki_build import generate_object
    response = SimpleNamespace(content=body, provider="configured", model="configured", is_fallback=False,
        prompt_tokens=100, completion_tokens=100)
    metrics = []
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response)), pytest.raises(AppException) as caught:
        await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(), metrics, WikiAnalysis, ANALYZE, {})
    assert caught.value.code == "KNOWLEDGE_WIKI_INVALID"
    assert caught.value.details["reason"] == reason
    assert body not in str(caught.value.details)
    assert metrics[0]["contract_errors"][0]["field"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("handle,reported", [("u0", True), ("private-unoffered-value", False)])
async def test_page_reference_error_feedback_identifies_only_matching_page_and_safe_offered_handle(handle, reported):
    import json

    from app.modules.knowledge.services.wiki_build import generate_object
    from app.modules.knowledge.wiki_schemas import WikiPacketRepair
    payload = {**compact_context(units(3), {}, "Nguồn"), "analysis": {"pages": [
        {"kind": "source", "title": "Nguồn", "unit_ids": ["unit-0"]},
        {"kind": "concept", "title": "Chủ đề", "unit_ids": ["unit-2"]}]}}
    payload["repair_targets"] = [{"target_id": "repair0", "page_index": 2, "section_index": 1,
        "kind": "concept", "title": "Chủ đề", "section": {"heading": "Phạm vi", "text": "Nội dung.",
            "references": ["unit-2"]}}]
    body = {"patches": [{"target_id": "repair0", "section": {
        "heading": "Phạm vi", "text": "Nội dung.", "references": [handle]}}]}
    response = SimpleNamespace(content=json.dumps(body), provider="configured", model="configured", is_fallback=False,
        prompt_tokens=100, completion_tokens=100)
    metrics = []
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response)), pytest.raises(AppException) as caught:
        await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(), metrics, WikiPacketRepair, GENERATE, payload)
    errors = caught.value.details["validation_errors"]
    assert len(errors) == 1
    assert errors[0]["field"] == ["patches", 0, "section", "references", 0]
    assert errors[0].get("supplied_handle") == (handle if reported else None)
    assert "private-unoffered-value" not in str(caught.value.details)


@pytest.mark.asyncio
async def test_contract_feedback_includes_numeric_bounds_and_redacts_unknown_field_names():
    import json

    from app.modules.knowledge.services.wiki_build import generate_object
    from app.modules.knowledge.wiki_schemas import WikiPacketRepair
    payload = {**compact_context(units(1), {}, "Nguồn"), "analysis": {"pages": [
        {"kind": "source", "title": "Nguồn", "unit_ids": ["unit-0"]}]}}
    payload["repair_targets"] = [{"target_id": "repair0", "page_index": 1, "section_index": 1,
        "kind": "source", "title": "Nguồn", "section": {"heading": "Phạm vi", "text": "Nội dung.", "references": ["unit-0"]}}]
    body = {"patches": [{"target_id": "repair0", "section": {
        "heading": "Phạm vi", "text": "Nội dung.", "references": ["u0"] * 21,
        "private-field-name": "private-value", "repair099999999": "private-value"}}]}
    response = SimpleNamespace(content=json.dumps(body), provider="configured", model="configured", is_fallback=False,
        prompt_tokens=100, completion_tokens=100)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response)), pytest.raises(AppException) as caught:
        await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(), [], WikiPacketRepair, GENERATE, payload)
    errors = caught.value.details["validation_errors"]
    bound = next(e for e in errors if e["type"] == "too_long")
    assert bound["constraints"]["max_length"] == 20 and bound["constraints"]["actual_length"] == 21
    assert "private-field-name" not in str(errors) and "private-value" not in str(errors)
    assert "repair099999999" not in str(errors)
    assert any("[unknown-field]" in e["field"] for e in errors)
