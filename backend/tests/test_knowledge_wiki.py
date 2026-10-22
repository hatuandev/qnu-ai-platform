"""Derived wiki pages keep source identities, temporal roles and exact evidence."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.knowledge.services.wiki_compiler import compile_wiki, validate_wiki_bundle
from app.modules.knowledge.wiki_schemas import WikiAnalysis, WikiGeneration, WikiPolicy


def source_revision():
    text = ("# Tuyển sinh năm 2024\n\nBan hành ngày 22/12/2023.\n\n"
            "## Phương thức năm 2024\n\nPT3: Đánh giá năng lực hai đơn vị.\n\n"
            "# Tuyển sinh năm 2025\n\nPT3: mã 402A.\n\nPT4: mã 402B.\n\n"
            "PT5: mã 405, chỉ áp dụng ngành có thi năng khiếu.\n\nPT6: mã 301.")
    import hashlib
    return SimpleNamespace(id="rev-a", binding_id="binding-a", canonical_markdown=text,
        canonical_hash=hashlib.sha256(text.encode()).hexdigest(), status="ready",
        snapshot_metadata={"title": "Nguồn nhiều năm"},
        parse_provenance={"structured_artifact": build_source_artifact(text, 1, {})})


def model_outputs(units):
    refs = [{"unit_id": unit.id, "quote": unit.text} for unit in units if not unit.is_container]
    y24 = next(r for r in refs if "Tuyển sinh năm 2024" in r["quote"])
    issued = next(r for r in refs if "22/12/2023" in r["quote"])
    method = next(r for r in refs if "mã 402B" in r["quote"])
    section = {"heading": "Phạm vi", "text": "Nội dung tuyển sinh năm 2024.",
        "conditions": [], "exceptions": [], "references": [y24, issued],
        "temporal": [{"role": "data", "years": [2024], "references": [y24]},
                     {"role": "publication", "years": [2023], "references": [issued]}]}
    pages = [{"kind": kind, "title": title, "sections": [deepcopy(section)]}
             for kind, title in [("source", "Nguồn nhiều năm"), ("entity", "Đơn vị đào tạo"),
                                 ("concept", "Phương thức xét tuyển")]]
    pages[-1]["sections"].append({"heading": "Phương thức", "text": "PT4: mã 402B.",
        "conditions": [], "exceptions": [], "references": [method], "temporal": []})
    analysis = WikiAnalysis.model_validate({"pages": [{"kind": p["kind"], "title": p["title"],
        "unit_ids": [r["unit_id"] for r in refs]} for p in pages]})
    return analysis, WikiGeneration.model_validate({"pages": pages})


def section_patch(section, target_id="repair0"):
    from app.modules.knowledge.wiki_schemas import WikiPacketRepair
    data = section.model_dump()
    data["references"] = [ref["unit_id"] for ref in data["references"]]
    for scope in data["temporal"]:
        scope["references"] = [ref["unit_id"] for ref in scope["references"]]
    return WikiPacketRepair(patches=[{"target_id": target_id, "section": data}])


@pytest.mark.asyncio
async def test_compilation_creates_three_page_types_with_distinct_year_roles_and_no_source_write():
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    source = source_revision()
    before = deepcopy(vars(source))
    units = resolve_unit_manifest(source.canonical_markdown,
        source.parse_provenance["structured_artifact"]).units
    call = AsyncMock(side_effect=model_outputs(units))
    bundle = await compile_wiki(source, "collection-a", WikiPolicy(), call)
    assert call.await_count == 2
    assert {p["kind"] for p in bundle["pages"]} == {"source", "entity", "concept"}
    assert "Năm dữ liệu: 2024" in bundle["pages"][0]["markdown"]
    assert "Năm ban hành: 2023" in bundle["pages"][0]["markdown"]
    assert bundle["usage"] == "navigation_only"
    assert vars(source) == before
    validate_wiki_bundle(bundle, source, "collection-a")


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["quote", "year", "unit", "number", "code", "duplicate", "missing_source"])
async def test_compilation_rejects_invented_evidence_and_incomplete_contract(mutation):
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    source = source_revision()
    units = resolve_unit_manifest(source.canonical_markdown,
        source.parse_provenance["structured_artifact"]).units
    analysis, generation = model_outputs(units)
    section = generation.pages[0].sections[0]
    if mutation == "quote": section.references[0].quote = "Thông tin không tồn tại trong nguồn"
    if mutation == "year": section.temporal[0].years = [2026]
    if mutation == "unit": section.references[0].unit_id = "other-source-unit"
    if mutation == "number": section.text = "Chỉ tiêu chính thức là 999999."
    if mutation == "code": generation.pages[-1].sections[-1].text = "PT4: mã 402Z."
    if mutation == "duplicate": generation.pages.append(generation.pages[0])
    if mutation == "missing_source": generation.pages = generation.pages[1:]
    with pytest.raises(AppException):
        await compile_wiki(source, "collection-a", WikiPolicy(generation_retries=0), AsyncMock(side_effect=[analysis, generation]))


@pytest.mark.asyncio
async def test_invalid_generation_can_retry_once_with_frozen_evidence_without_relaxing_validation():
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    source = source_revision()
    units = resolve_unit_manifest(source.canonical_markdown, source.parse_provenance["structured_artifact"]).units
    analysis, valid = model_outputs(units)
    wrong = valid.model_copy(deep=True)
    wrong.pages[0].sections[0].text = "Giá trị 999999."
    generate = AsyncMock(side_effect=[analysis, wrong, section_patch(valid.pages[0].sections[0])])
    bundle = await compile_wiki(source, "collection-a", WikiPolicy(max_calls=3, generation_retries=1), generate)
    assert bundle["calls"] == 3 and bundle["contract_retries"] == 1
    assert generate.await_args_list[1].args[2]["units"] == generate.await_args_list[2].args[2]["units"]
    assert generate.await_args_list[2].args[2]["validation_feedback"]["reason"] == "unsupported_value"


@pytest.mark.asyncio
async def test_invalid_generation_retry_never_exceeds_the_total_call_budget():
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    source = source_revision()
    units = resolve_unit_manifest(source.canonical_markdown, source.parse_provenance["structured_artifact"]).units
    analysis, wrong = model_outputs(units)
    wrong.pages[0].sections[0].text = "Giá trị 999999."
    generate = AsyncMock(side_effect=[analysis, wrong])
    with pytest.raises(AppException) as caught:
        await compile_wiki(source, "collection-a", WikiPolicy(max_calls=2), generate)
    assert caught.value.code == "KNOWLEDGE_WIKI_BUDGET"
    assert generate.await_count == 2


@pytest.mark.asyncio
async def test_bundle_cannot_be_moved_to_another_revision_collection_or_changed_after_sealing():
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    source = source_revision()
    units = resolve_unit_manifest(source.canonical_markdown,
        source.parse_provenance["structured_artifact"]).units
    bundle = await compile_wiki(source, "collection-a", WikiPolicy(),
        AsyncMock(side_effect=model_outputs(units)))
    for key in ["source_revision_id", "collection_id", "canonical_hash"]:
        changed = deepcopy(bundle)
        changed[key] = "other"
        with pytest.raises(AppException): validate_wiki_bundle(changed, source, "collection-a")
    changed = deepcopy(bundle)
    changed["pages"][0]["markdown"] += "\nGiá trị khác."
    with pytest.raises(AppException): validate_wiki_bundle(changed, source, "collection-a")


@pytest.mark.asyncio
async def test_input_budget_is_checked_before_any_model_call():
    source = source_revision()
    call = AsyncMock()
    with pytest.raises(AppException, match="ngân sách"):
        await compile_wiki(source, "collection-a", WikiPolicy(max_total_chars=100), call)
    call.assert_not_awaited()


def test_packet_boundary_repeats_exact_scope_heading_without_borrowing_another_year():
    from app.modules.knowledge.normalization.retrieval_models import SourceUnit
    from app.modules.knowledge.services.wiki_compiler import packets
    heading = SourceUnit(id="h24", kind="heading", text="# Năm dữ liệu 2024", start=0, end=18,
        heading_path=["Năm dữ liệu 2024"])
    first = SourceUnit(id="p1", kind="paragraph", text="A" * 700, start=20, end=720,
        heading_path=heading.heading_path)
    last = SourceUnit(id="p2", kind="paragraph", text="B" * 700, start=722, end=1422,
        heading_path=heading.heading_path)
    groups = packets([heading, first, last], WikiPolicy(packet_chars=1000))
    assert len(groups) == 2
    assert [unit.id for unit in groups[1]] == ["h24", "p2"]


@pytest.mark.asyncio
async def test_body_only_outline_keeps_its_real_heading_available_for_year_quotes():
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    source = source_revision()
    units = resolve_unit_manifest(source.canonical_markdown, source.parse_provenance["structured_artifact"]).units
    analysis, generation = model_outputs(units)
    # Model selects the body; the generator must still be allowed to cite its
    # actual ancestor heading to establish the source's DATA year.
    for outline in analysis.pages:
        outline.unit_ids = [unit.id for unit in units if unit.kind != "heading" and not unit.is_container]
    generate = AsyncMock(side_effect=[analysis, generation])
    bundle = await compile_wiki(source, "collection-a", WikiPolicy(), generate)
    assert bundle["status"] == "ready"
    headings = {unit.id for unit in units if unit.kind == "heading"}
    for outline in generate.await_args_list[1].args[2]["analysis"]["pages"]:
        assert headings.intersection(outline["unit_ids"])


@pytest.mark.asyncio
async def test_historical_source_does_not_call_model_or_change_metadata():
    from unittest.mock import patch

    from app.modules.knowledge.services.wiki_build import build_revision_wiki
    source = source_revision()
    collection = SimpleNamespace(id="collection-a", tenant_id="tenant_qnu")
    with patch("app.modules.knowledge.services.wiki_build.model_generator", AsyncMock()) as generate:
        assert await build_revision_wiki(AsyncMock(), source, collection) is None
    generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_model_failure_is_visible_and_cannot_turn_into_ready_pages():
    from unittest.mock import patch

    from app.modules.knowledge.services.wiki_build import build_revision_wiki
    source = source_revision()
    source.parse_provenance["knowledge_wiki_policy"] = {}
    collection = SimpleNamespace(id="collection-a", tenant_id="tenant_qnu")
    failure = AppException("Provider không sẵn sàng", code="MODEL_PROVIDER_UNAVAILABLE", status_code=503)
    with patch("app.modules.knowledge.services.wiki_build.model_generator", AsyncMock(side_effect=failure)):
        bundle = await build_revision_wiki(AsyncMock(), source, collection)
    assert bundle["status"] == "unavailable" and not bundle["pages"]
    assert bundle["failure_code"] == "MODEL_PROVIDER_UNAVAILABLE"
    assert source.status == "ready"
    validate_wiki_bundle(bundle, source, collection.id)


@pytest.mark.asyncio
async def test_model_adapter_uses_configured_provider_model_and_explicit_fallback():
    import json
    from unittest.mock import patch

    from app.modules.knowledge.services.wiki_build import model_generator
    source = source_revision()
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    units = resolve_unit_manifest(source.canonical_markdown, source.parse_provenance["structured_artifact"]).units
    analysis, _ = model_outputs(units)
    defaults = SimpleNamespace(default_chat_model="configured-primary", default_chat_provider_id="provider-a",
        default_chat_mode="combo", chat_combo_chain=[SimpleNamespace(is_active=True, provider_id="provider-a",
        model_name="configured-primary"), SimpleNamespace(is_active=True, provider_id="provider-b", model_name="configured-fallback")])
    response = SimpleNamespace(content=json.dumps(analysis.model_dump(), ensure_ascii=False), provider="Provider A",
        model="configured-primary", is_fallback=False, prompt_tokens=100, completion_tokens=20)
    with patch("app.modules.modelops.services.model_catalog_service.model_catalog_service.get_system_model_defaults",
               AsyncMock(return_value=SimpleNamespace(defaults=defaults))), \
         patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response)) as inference:
        metrics = []
        generate = await model_generator(AsyncMock(), "tenant_qnu", WikiPolicy(), metrics)
        assert await generate(WikiAnalysis, "Analyze", {}) == analysis
    request = inference.await_args.args[1]
    assert (request.preferred_provider_id, request.preferred_model_name) == ("provider-a", "configured-primary")
    assert (request.fallback_provider_id, request.fallback_model_name) == ("provider-b", "configured-fallback")
    assert metrics[0]["prompt_tokens"] == 100


@pytest.mark.asyncio
async def test_model_json_fence_is_transport_only_and_cannot_hide_extra_text_or_change_quotes():
    import json
    from unittest.mock import patch

    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    from app.modules.knowledge.services.wiki_build import generate_object
    source = source_revision()
    units = resolve_unit_manifest(source.canonical_markdown, source.parse_provenance["structured_artifact"]).units
    _, generation = model_outputs(units)
    data = json.dumps(generation.model_dump(), ensure_ascii=False)
    response = SimpleNamespace(content="```json\n" + data + "\n```", provider="custom", model="configured",
        is_fallback=False, prompt_tokens=100, completion_tokens=200)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response)):
        result = await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(), [], WikiGeneration, "Generate", {})
        assert result == generation
        response.content += "\nUnsupported commentary"
        with pytest.raises(AppException) as caught:
            await generate_object(AsyncMock(), "tenant_qnu", {}, WikiPolicy(), [], WikiGeneration, "Generate", {})
        assert caught.value.code == "KNOWLEDGE_WIKI_INVALID"
        assert caught.value.details["reason"] == "json_syntax"
        assert "Unsupported commentary" not in str(caught.value.details)
