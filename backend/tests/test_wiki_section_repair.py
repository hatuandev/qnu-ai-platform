"""Local corrections keep every previously validated section byte-for-byte."""

from copy import deepcopy

import pytest
from pydantic import ValidationError
from test_knowledge_wiki import model_outputs, section_patch, source_revision
from test_wiki_budget import units

from app.core.exceptions import AppException
from app.modules.knowledge.services.wiki_budget import compact_context
from app.modules.knowledge.services.wiki_compiler import (
    bind_source_references,
    source_units,
    validate_generation,
)
from app.modules.knowledge.services.wiki_repair import (
    merge_section_patches,
    repair_context,
    repair_targets,
)
from app.modules.knowledge.services.wiki_transport import prepare_transport, restore_source_ids
from app.modules.knowledge.wiki_schemas import WikiPacketRepair


def test_section_repair_keeps_all_other_sections_and_source_unchanged():
    source = source_revision()
    group = source_units(source)
    by_id = {u.id: u for u in group}
    analysis, original = model_outputs(group)
    candidate = original.model_copy(deep=True)
    candidate.pages[0].sections[0].text = "Số liệu 999999."
    before_source, before_candidate = deepcopy(vars(source)), candidate.model_dump()
    targets = repair_targets(candidate, [{"page_index": 1, "section_index": 1}])
    result = merge_section_patches(candidate, section_patch(original.pages[0].sections[0]), targets,
        lambda draft: bind_source_references(draft, by_id))
    validate_generation(result, analysis, by_id)
    assert result == original
    assert candidate.model_dump() == before_candidate and vars(source) == before_source


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_section_patch_requires_exact_complete_targets_and_never_mutates_on_failure(mutation):
    source = source_revision()
    group = source_units(source)
    _, candidate = model_outputs(group)
    targets = repair_targets(candidate, [{"page_index": 1, "section_index": 1}, {"page_index": 3, "section_index": 2}])
    first = section_patch(candidate.pages[0].sections[0]).patches[0]
    second = section_patch(candidate.pages[2].sections[1], "repair1").patches[0]
    patches = [first] if mutation == "missing" else [first, first] if mutation == "duplicate" else [
        first, second.model_copy(update={"target_id": "unoffered"})]
    before = candidate.model_dump()
    with pytest.raises(AppException) as caught:
        merge_section_patches(candidate, WikiPacketRepair(patches=patches), targets,
            lambda draft: bind_source_references(draft, {u.id: u for u in group}))
    assert caught.value.details["reason"] == "repair_target_identity"
    assert candidate.model_dump() == before


def test_repair_scope_omits_other_pages_but_keeps_original_handle_identity_and_closed_ids():
    payload = {**compact_context(units(3), {}, "Nguồn"), "analysis": {"pages": [
        {"kind": "source", "title": "Nguồn", "unit_ids": ["unit-0", "unit-1"]},
        {"kind": "entity", "title": "Đối tượng", "unit_ids": ["unit-2"]}]}}
    targets = [{"target_id": "repair0", "page_index": 2, "section_index": 1, "kind": "entity", "title": "Đối tượng",
        "section": {"heading": "Phạm vi", "text": "Mã 0012.", "references": ["unit-0"], "temporal": []}}]
    scoped = repair_context(payload, targets)
    assert [unit["id"] for unit in scoped["units"]] == ["unit-2"]
    assert len(scoped["analysis"]["pages"]) == 1
    bound, wire, reverse = prepare_transport(WikiPacketRepair, scoped)
    assert wire["units"][0]["id"] == "u2" and "_request_handles" not in wire
    assert wire["repair_targets"][0]["section"]["references"] == ["[outside_outline]"]
    data = {"patches": [{"target_id": "repair0", "section": {"heading": "Phạm vi", "text": "Mã 0012.", "references": ["u2"]}}]}
    output = restore_source_ids(WikiPacketRepair, bound.model_validate(data), reverse)
    assert output.patches[0].section.references == ["unit-2"]
    data["patches"][0]["section"]["references"] = ["u0"]
    with pytest.raises(ValidationError):
        bound.model_validate(data)


@pytest.mark.asyncio
async def test_adapter_draft_scope_error_is_rejected_then_fixed_only_through_closed_section_patch():
    import json
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.knowledge.services.wiki_build import generate_object
    from app.modules.knowledge.services.wiki_compiler import generate_packet
    from app.modules.knowledge.wiki_schemas import WikiAnalysis, WikiPolicy
    group = units(3)
    before = deepcopy(group)
    plan = WikiAnalysis(pages=[{"kind": "source", "title": "Nguồn", "unit_ids": ["unit-0"]},
        {"kind": "concept", "title": "Chủ đề", "unit_ids": ["unit-2"]}])
    bad = {"pages": [{"kind": "source", "title": "Nguồn", "sections": [{"heading": "Nguồn", "text": "Nội dung nguồn.", "references": ["u0"]}]},
        {"kind": "concept", "title": "Chủ đề", "sections": [{"heading": "Phạm vi", "text": "Mã 0012.", "references": ["u0"]}]}]}
    fixed = {"patches": [{"target_id": "repair0", "section": {"heading": "Phạm vi", "text": "Mã 0012.", "references": ["u2"]}}]}
    def response(body):
        return SimpleNamespace(content=json.dumps(body), provider="configured", model="configured", is_fallback=False,
            prompt_tokens=100, completion_tokens=100)
    async def generate(contract, instruction, payload):
        if contract is WikiAnalysis:
            return plan
        return await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(), [], contract, instruction, payload)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response(bad))), pytest.raises(AppException) as caught:
        await generate_packet(group, {}, "Nguồn", generate, 0)
    assert caught.value.details["reason"] == "quote_binding"
    assert caught.value.details["invalid_sections"] == [{"page_index": 2, "section_index": 1}]
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=[response(bad), response(fixed)])) as model:
        output = await generate_packet(group, {}, "Nguồn", generate, 1)
    assert output.pages[0].sections[0].references[0].unit_id == "unit-0"
    assert output.pages[1].sections[0].references[0].unit_id == "unit-2"
    request = json.loads(model.await_args_list[1].args[1].messages[1].content)
    assert request["repair_targets"][0]["section"]["references"] == ["[outside_outline]"]
    assert [unit["id"] for unit in request["units"]] == ["u2"]
    assert group == before


@pytest.mark.asyncio
@pytest.mark.parametrize("oversized", ["section", "temporal"])
async def test_candidate_capacity_can_be_read_for_repair_but_never_returns_as_valid_generation(oversized):
    import json
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.knowledge.normalization.retrieval_models import SourceUnit
    from app.modules.knowledge.services.wiki_build import generate_object
    from app.modules.knowledge.services.wiki_compiler import generate_packet
    from app.modules.knowledge.wiki_schemas import WikiAnalysis, WikiGeneration, WikiPolicy
    group = [SourceUnit(id="canonical-id", kind="paragraph", text="Năm dữ liệu 2025.", start=0, end=17)]
    plan = WikiAnalysis(pages=[{"kind": "source", "title": "Nguồn", "unit_ids": [group[0].id]}])
    section = {"heading": "Dữ liệu", "text": "Dữ liệu năm 2025.", "references": ["u0"] * (21 if oversized == "section" else 1),
        "temporal": [{"role": "data", "years": [2025], "references": ["u0"] * (21 if oversized == "temporal" else 1)}]}
    bad = {"pages": [{"kind": "source", "title": "Nguồn", "sections": [section]}]}
    corrected = {**section, "references": ["u0"], "temporal": [{"role": "data", "years": [2025], "references": ["u0"]}]}
    fixed = {"patches": [{"target_id": "repair0", "section": corrected}]}
    def response(body):
        return SimpleNamespace(content=json.dumps(body), provider="configured", model="configured", is_fallback=False,
            prompt_tokens=100, completion_tokens=100)
    async def generate(contract, instruction, payload):
        if contract is WikiAnalysis:
            return plan
        return await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(), [], contract, instruction, payload)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response(bad))), pytest.raises(AppException) as caught:
        await generate_packet(group, {}, "Nguồn", generate, 0)
    assert caught.value.details["reason"] == ("section_reference_budget" if oversized == "section" else "temporal_reference_budget")
    assert caught.value.details["invalid_sections"] == [{"page_index": 1, "section_index": 1}]
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=[response(bad), response(fixed)])):
        output = await generate_packet(group, {}, "Nguồn", generate, 1)
    assert type(output) is WikiGeneration
    assert len(output.pages[0].sections[0].references) == len(output.pages[0].sections[0].temporal[0].references) == 1
    assert output.pages[0].sections[0].references[0].quote == group[0].text


def test_ten_temporal_source_references_are_preserved_and_each_binding_is_still_checked():
    from app.modules.knowledge.normalization.retrieval_models import SourceUnit
    from app.modules.knowledge.wiki_schemas import (
        WikiAnalysis,
        WikiGeneration,
        WikiPacketGeneration,
    )
    group = [SourceUnit(id=f"evidence-{i}", kind="paragraph", text=f"Công việc {i}: thời hạn năm 2028.", start=i*100, end=i*100+40)
             for i in range(10)]
    by_id = {unit.id: unit for unit in group}
    ids = list(by_id)
    plan = WikiAnalysis(pages=[{"kind": "source", "title": "Nguồn", "unit_ids": ids}])
    draft = WikiPacketGeneration(pages=[{"kind": "source", "title": "Nguồn", "sections": [{
        "heading": "Thời hạn", "text": "Các thời hạn năm 2028.", "references": ids,
        "temporal": [{"role": "event", "years": [2028], "references": ids}]}]}])
    candidate = bind_source_references(draft, by_id)
    validate_generation(candidate, plan, by_id)
    stored = WikiGeneration.model_validate(candidate.model_dump())
    refs = stored.pages[0].sections[0].temporal[0].references
    assert [ref.unit_id for ref in refs] == ids
    assert [ref.quote for ref in refs] == [unit.text for unit in group]
    refs[0].unit_id = "unoffered"
    with pytest.raises(AppException) as caught:
        validate_generation(stored, plan, by_id)
    assert caught.value.details["reason"] == "quote_binding"
