"""Extractive navigation cannot rewrite source data or borrow global date scope."""

from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from test_knowledge_wiki import source_revision

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.retrieval_models import SourceUnit
from app.modules.knowledge.services.wiki_compiler import (
    compile_wiki,
    digest,
    render_page,
    validate_wiki_bundle,
)
from app.modules.knowledge.services.wiki_extractive import excerpt_section
from app.modules.knowledge.services.wiki_transport import prepare_transport, restore_source_ids
from app.modules.knowledge.wiki_schemas import WikiPage, WikiPolicy, WikiSelection
from app.modules.rag.wiki_context import page_view

POLICY = WikiPolicy(compiler_version="qnu-wiki-compiler/v3", render_mode="extractive")


def units_for_table():
    header = "| Mã | 2027 |\n| --- | --- |"
    return {unit.id: unit for unit in [
        SourceUnit(id="header", kind="table", parent_id="table", text=header, start=0, end=len(header), header_context=header),
        SourceUnit(id="row", kind="table", parent_id="table", text="| AM-0070 | ? |", start=40, end=54,
            header_context=header, context_refs=["note"]),
        SourceUnit(id="note", kind="paragraph", text="Chỉ áp dụng nhóm A; ngoại lệ nhóm B giữ nguyên.", start=60, end=110),
    ]}


def test_excerpt_preserves_exact_row_unknown_header_and_condition_with_own_links():
    units = units_for_table()
    section = excerpt_section("row", units)
    assert section.text == units["header"].text + "\n" + units["row"].text + "\n\n" + units["note"].text
    assert {ref.unit_id for ref in section.references} == set(units)
    assert section.temporal == []  # The literal column year is not a guessed temporal role.
    assert "?" in section.text and "AM-0070" in section.text


@pytest.mark.parametrize("missing", ["header", "note"])
def test_missing_structural_evidence_is_blocker_not_a_shorter_excerpt(missing):
    units = units_for_table()
    del units[missing]
    with pytest.raises(AppException):
        excerpt_section("row", units)


@pytest.mark.asyncio
async def test_extractive_compiler_calls_only_selector_keeps_all_source_and_separates_year_roles():
    from app.modules.knowledge.services.wiki_compiler import source_units
    source = source_revision()
    before = deepcopy(vars(source))
    units = [unit for unit in source_units(source) if not unit.is_container]
    date = next(unit for unit in units if "22/12/2023" in unit.text)
    data = next(unit for unit in units if unit.text.startswith("# Tuyển sinh năm 2024"))
    selected = next(unit for unit in units if "mã 402B" in unit.text)
    plan = WikiSelection(pages=[
        {"kind": "source", "title": "Nguồn nhiều năm", "unit_ids": [date.id, data.id], "temporal": [
            {"role": "publication", "years": [2023], "references": [date.id]},
            {"role": "data", "years": [2024], "references": [data.id]}]},
        {"kind": "entity", "title": "Phương thức", "unit_ids": [selected.id]},
        {"kind": "concept", "title": "Quy định xét tuyển", "unit_ids": [selected.id]},
    ])
    generate = AsyncMock(return_value=plan)
    bundle = await compile_wiki(source, "collection-a", POLICY, generate)
    assert generate.await_count == 1 and generate.await_args.args[0] is WikiSelection
    assert bundle["calls"] == 1 and bundle["contract_retries"] == 0
    assert {section["excerpt_unit_id"] for section in bundle["pages"][0]["sections"]} == {unit.id for unit in units}
    sections = {section["excerpt_unit_id"]: section for section in bundle["pages"][0]["sections"]}
    assert sections[date.id]["temporal"][0]["role"] == "publication"
    assert not sections[selected.id]["temporal"]  # Date on the cover is not the row's year.
    assert vars(source) == before
    validate_wiki_bundle(bundle, source, "collection-a")


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["prose", "zero", "drop_link", "foreign_unit", "missing_excerpt"])
async def test_resealed_extractive_bundle_still_rejects_data_changes(mutation):
    from app.modules.knowledge.services.wiki_compiler import source_units
    source = source_revision()
    uid = source_units(source)[0].id
    generate = AsyncMock(return_value=WikiSelection(pages=[
        {"kind": "source", "title": "Nguồn nhiều năm", "unit_ids": [uid]}]))
    bundle = await compile_wiki(source, "collection-a", POLICY, generate)
    section = bundle["pages"][0]["sections"][-1]
    if mutation == "prose": section["text"] += " Chính sách đã được phê duyệt."
    if mutation == "zero": section["text"] = "Giá trị: 0."
    if mutation == "drop_link": section["references"] = section["references"][-1:]
    if mutation == "foreign_unit": section["excerpt_unit_id"] = "another-source:row"
    if mutation == "missing_excerpt": section["excerpt_unit_id"] = None
    page = bundle["pages"][0]
    identity = {key: bundle[key] for key in ("collection_id", "binding_id", "source_revision_id", "canonical_hash")}
    page["markdown"] = render_page(WikiPage.model_validate({key: page[key] for key in ("kind", "title", "sections")}), identity)
    bundle["sha256"] = digest({key: value for key, value in bundle.items() if key != "sha256"})
    with pytest.raises(AppException):
        validate_wiki_bundle(bundle, source, "collection-a")


def test_selection_transport_restores_temporal_references_and_rejects_foreign_handles():
    payload = {"units": [{"id": "header", "text": "Năm 2027"}, {"id": "row", "text": "?"}]}
    contract, _, reverse = prepare_transport(WikiSelection, payload)
    output = contract.model_validate({"pages": [{"kind": "source", "title": "Nguồn", "unit_ids": ["u0"],
        "temporal": [{"role": "data", "years": [2027], "references": ["u0"]}]}]})
    restored = restore_source_ids(WikiSelection, output, reverse)
    assert restored.pages[0].temporal[0].references == ["header"]
    with pytest.raises(ValueError):
        contract.model_validate({"pages": [{"kind": "source", "title": "Nguồn", "unit_ids": ["foreign"]}]})


def test_bounded_reader_selects_whole_matching_section_with_header_and_exception():
    units = units_for_table()
    relevant = excerpt_section("row", units).model_dump()
    other = {**relevant, "excerpt_unit_id": "other", "text": "Không liên quan. " * 2000,
             "references": [{"unit_id": "other", "quote": "Không liên quan."}]}
    identity = {"collection_id": "c", "binding_id": "b", "source_revision_id": "r", "canonical_hash": "h"}
    page = {"id": "p", "title": "Chỉ tiêu", "kind": "entity", "sections": [other, relevant], "identity": identity,
        "markdown": "x" * 20000, "block_ids": [*units, "other"], "reference_blocks": {uid: "r:" + uid for uid in [*units, "other"]}}
    before = deepcopy(page)
    view = page_view(page, "AM-0070 năm 2027", 1600)
    assert view["partial"] and view["total_sections"] == 2 and view["sections"] == [relevant]
    assert set(view["block_ids"]) == {"r:" + uid for uid in units}
    assert "ngoại lệ nhóm B" in view["markdown"] and "?" in view["markdown"]
    assert len(view["markdown"]) <= 1600 and page == before


def test_legacy_policy_keeps_generated_mode_and_new_version_is_explicit():
    assert WikiPolicy.model_validate({"compiler_version": "qnu-wiki-compiler/v2"}).render_mode == "generated"
    assert POLICY.compiler_version == "qnu-wiki-compiler/v3"
