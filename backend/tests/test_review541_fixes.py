"""Source-qualified temporal evidence, audited corrections and public cell rendering."""

import html
from copy import deepcopy
from unittest.mock import patch

import pytest

import tests.test_review536_findings as f
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.schemas import SourceContextEditRequest
from app.modules.knowledge.services.source_context import apply_context_edits, query_projection
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_facts import reviewed_fact_blocks
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.row_answer_contract import (
    RowSelection,
    build_catalog,
    render_cells,
    retain_scoped_cells,
    validate_selection,
)


def state_for(document):
    with patch.object(f, "fixture_document", return_value=document):
        return f.build_state()


@pytest.mark.parametrize("level", ["column", "field"])
def test_temporal_basis_cannot_borrow_a_sibling_header(level):
    document = f.fixture_document()
    table = next(block for block in document.blocks if block.id == "t")
    row = next(block for block in document.blocks if block.id == "r1")
    wrong = {"data_years": [2025], "basis_quote": "Chỉ tiêu / 2025"}
    target = table.attributes["columns"][3] if level == "column" else row.attributes["fields"]["c4"]
    target["temporal"] = wrong
    state = state_for(document)
    scope = f.fields_by_header(state.approved)["Chỉ tiêu / 2026"]["temporal"]
    assert scope["status"] == "ambiguous"
    assert scope["data_years"] == [2025]  # Keep the declaration; do not silently repair it.


def test_field_basis_cannot_borrow_a_sibling_value():
    document = f.fixture_document()
    row = next(block for block in document.blocks if block.id == "r1")
    row.attributes["fields"]["c7"]["raw"] = "Dữ liệu áp dụng 2025"
    row.attributes["fields"]["c4"]["temporal"] = {
        "data_years": [2025], "basis_quote": "Dữ liệu áp dụng 2025"
    }
    state = state_for(document)
    assert f.fields_by_header(state.approved)["Chỉ tiêu / 2026"]["temporal"]["status"] == "ambiguous"


def test_own_cell_year_conflicting_with_its_header_requires_resolution():
    document = f.fixture_document()
    row = next(block for block in document.blocks if block.id == "r1")
    row.attributes["fields"]["c4"].update(
        raw="Dữ liệu năm 2025", normalized=None,
        temporal={"data_years": [2025], "basis_quote": "Dữ liệu năm 2025"},
    )
    state = state_for(document)
    assert f.fields_by_header(state.approved)["Chỉ tiêu / 2026"]["temporal"]["status"] == "ambiguous"
    assert any(issue["code"] == "TEMPORAL_HEADER_CONFLICT" for issue in state.approved["issues"])


@pytest.mark.parametrize("level", ["row", "block"])
def test_explicit_enclosing_scope_can_be_inherited_without_sibling_guessing(level):
    document = f.fixture_document()
    table = next(block for block in document.blocks if block.id == "t")
    row = next(block for block in document.blocks if block.id == "r1")
    target = table if level == "block" else row
    basis = "Chỉ tiêu / 2026" if level == "block" else "Áp dụng năm 2026"
    if level == "row":
        row.attributes["fields"]["c7"]["raw"] = basis
    target.attributes["temporal"] = {"data_years": [2026], "basis_quote": basis}
    state = state_for(document)
    inherited = f.fields_by_header(state.approved)["Ghi chú"]["temporal"]
    assert inherited["status"] == "verified" and inherited["data_years"] == [2026]
    assert inherited["scope_level"] == level
    own = f.fields_by_header(state.approved)["Chỉ tiêu / 2025"]["temporal"]
    assert own["data_years"] == [2025] and own["scope_level"] == "column"


def test_invalid_basis_type_is_preserved_as_ambiguous_instead_of_crashing():
    document = f.fixture_document()
    table = next(block for block in document.blocks if block.id == "t")
    table.attributes["columns"][3]["temporal"]["basis_quote"] = [2026]
    _, artifact = project_document(document, f.reference(), {})
    scope = f.fields_by_header(artifact)["Chỉ tiêu / 2026"]["temporal"]
    assert scope["status"] == "ambiguous" and scope["unsupported"]["basis_quote"] == [2026]


def corrected_state(changes):
    state = f.build_state()
    target = next(fact for fact in state.approved["facts"]
                  if fact["entity_name"] == "Công nghệ ô tô" and fact["attribute_name"] == "Chỉ tiêu / 2026")
    request = SourceContextEditRequest(
        expected_fact_set_hash=state.approved["fact_set_hash"], reason="Đối chiếu căn cứ trong bản nguồn",
        facts=[{"fact_id": target["id"], **changes}],
    )
    edited = apply_context_edits(state.approved, request, "editor")
    source_ingestion_service._apply_review_decision(
        state.binding, state.source, edited, "approved", "Đã đối chiếu nguồn", "reviewer"
    )
    state.approved = state.source.parse_provenance["structured_artifact"]
    return state


async def load_fact_blocks(state, years, *, facts=None):
    blocks = await load_published_blocks(f.db_for([(state.source, state.index, state.binding)]), f.snapshot())
    if facts is None:
        facts = f.fact_objects(state.approved)
        for fact in facts:
            fact.applicability_year = query_projection(fact.raw_data)["applicability_year"]
    result = await reviewed_fact_blocks(
        f.db_for(facts), f.request(), f.snapshot(), QueryPlan(query=f.QUESTION, years=years),
        blocks, exhaustive=True,
    )
    return [block for block in result if block.fact_context.get("entity_name") == "Công nghệ ô tô"
            and any(cell["attribute"] == "Chỉ tiêu / 2026" for cell in block.fact_context.get("cells", []))]


@pytest.mark.asyncio
@pytest.mark.parametrize(("changes", "year"), [({"year": 2026}, 2026), ({"year": 2025}, 2025),
                                               ({"year": None}, None), ({"method": "THPT"}, 2026),
                                               ({"unit": "người"}, 2026)])
async def test_approved_fact_corrections_survive_materialization_and_evidence(changes, year):
    state = corrected_state(changes)
    blocks = await load_fact_blocks(state, [year] if year else [])
    assert blocks
    block = blocks[0]
    assert block.scope_years == ([year] if year else [])
    assert block.temporal_scope.status == "verified"
    assert block.fact_context["verified_dependencies"] is True
    cell = next(cell for cell in block.fact_context["cells"] if cell["attribute"] == "Chỉ tiêu / 2026")
    assert cell["value"] == "0" and cell["state"] == "present"
    if year is not None:
        assert not await load_fact_blocks(state, [2027])


@pytest.mark.asyncio
async def test_legacy_audited_year_only_fact_is_adapted_without_rewriting_source():
    state = corrected_state({"year": 2026})
    facts = f.fact_objects(state.approved)
    target = next(fact for fact in facts if fact.entity_name == "Công nghệ ô tô"
                  and fact.attribute_name == "Chỉ tiêu / 2026")
    target.raw_data = deepcopy(target.raw_data)
    target.raw_data["temporal_context"] = {"type": "year", "year": 2026,
                                          "status": "verified", "evidence": "human_correction"}
    target.applicability_year = 2026
    original = deepcopy(target.raw_data)
    blocks = await load_fact_blocks(state, [2026], facts=facts)
    assert blocks and blocks[0].scope_years == [2026]
    assert target.raw_data == original


@pytest.mark.asyncio
@pytest.mark.parametrize("damage", ["missing_review", "rejected", "missing_editor"])
async def test_verified_label_without_complete_human_audit_cannot_certify_a_year(damage):
    state = corrected_state({"year": 2026})
    facts = f.fact_objects(state.approved)
    target = next(fact for fact in facts if fact.entity_name == "Công nghệ ô tô"
                  and fact.attribute_name == "Chỉ tiêu / 2026")
    audit = target.raw_data["context_review"]
    if damage == "missing_review":
        audit.pop("review")
    elif damage == "rejected":
        audit["review"]["decision"] = "rejected"
    else:
        audit.pop("actor_id")
    assert query_projection(target.raw_data)["applicability_year"] is None
    blocks = await load_fact_blocks(state, [2026], facts=facts)
    assert all(not block.scope_years and block.temporal_scope.status != "verified" for block in blocks)


@pytest.mark.parametrize("year", [2026, 2025, None])
def test_row_catalog_uses_the_same_approved_correction_and_never_revives_a_removed_year(year):
    state = corrected_state({"year": year})
    catalog = build_catalog(f.rows_for(state), f.snapshot())
    key = f.cell_key(catalog, f.row_of(catalog, "Công nghệ ô tô"), "Chỉ tiêu / 2026")
    selection = RowSelection(status="selected", cell_ids=[key])
    assert catalog.cells[key].temporal["data_years"] == ([year] if year else [])
    if year:
        validate_selection(selection, catalog, f.QUESTION.replace("2026", str(year)))
    with pytest.raises(ValueError):
        validate_selection(selection, catalog, f.QUESTION.replace("2026", "2027" if year else "2026"))
    retained = retain_scoped_cells(selection, catalog, f.QUESTION.replace("2026", "2027"))
    assert key not in retained.cell_ids


@pytest.mark.parametrize("raw", ["A & B", "A | B", r"A\B", r"A\|B", "<tag>", "Dòng một\nDòng hai"])
def test_public_markdown_round_trips_cell_values_with_one_escape(raw):
    document = f.fixture_document()
    row = next(block for block in document.blocks if block.id == "r1")
    row.attributes["fields"]["c7"] = {"raw": raw, "state": "present", "normalized": None}
    state = state_for(document)
    catalog = build_catalog(f.rows_for(state), f.snapshot())
    key = f.cell_key(catalog, f.row_of(catalog, "Công nghệ ô tô"), "Ghi chú")
    answer, cells, _ = render_cells(RowSelection(status="selected", cell_ids=[key]), catalog)
    columns = _split_gfm_row(answer.splitlines()[2])
    assert len(columns) == 3
    assert html.unescape(columns[2]) == raw.replace("\n", " ")
    assert cells[0]["value"] == raw
