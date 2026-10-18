"""Session 536 findings: standard cell state, fact dependencies, temporal scope, page spans."""

import hashlib
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.qnu_markdown import (
    QNU_MARKDOWN_SCHEMA,
    QnuBlock,
    QnuSourceInfo,
    QnuSourceLocation,
    QnuStructuredDocument,
)
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.normalization.retrieval_units import (
    manifest_digest,
    resolve_unit_manifest,
)
from app.modules.knowledge.normalization.structure_chunks import structure_chunks
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
from app.modules.rag.evidence_blocks import load_published_blocks, pack_context
from app.modules.rag.evidence_dependencies import dependency_groups
from app.modules.rag.evidence_facts import reviewed_fact_blocks
from app.modules.rag.evidence_pipeline import decision_response
from app.modules.rag.evidence_schemas import QueryPlan, QuoteReference
from app.modules.rag.evidence_validation import bind_quote, citation_pages
from app.modules.rag.row_answer import answer_from_rows
from app.modules.rag.row_answer_contract import (
    MetricScope,
    RowAudit,
    RowSelection,
    build_catalog,
    close_empty_cells,
    render_cells,
    retain_scoped_cells,
    source_value_variants,
    validate_selection,
)
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.source_rows import source_rows

SHA = "a" * 64
STRUCTURED = "b" * 64
COLLECTION = "collection-536"
BINDING = "binding-536"
REVISION = "revision-536"
SOURCE = "source-536"
INDEX = "index-536"
QUESTION = "Chỉ tiêu và điểm chuẩn ngành Công nghệ ô tô năm 2026 là bao nhiêu?"
OTHER_QUESTION = "Chỉ tiêu ngành Kỹ thuật cơ khí năm 2026 là bao nhiêu?"


def reference(binding=BINDING, revision=REVISION):
    return {"schema_version": QNU_MARKDOWN_SCHEMA, "document_id": binding, "revision_id": revision,
            "sha256": SHA, "structured_sha256": STRUCTURED, "status": "ready"}


def fixture_document(c4_state="present", c4_value="0"):
    page2 = QnuSourceLocation(page=2, locator="physical/2/table/1", bbox=[1, 2, 3, 4], bbox_space="points")
    spanning = [QnuSourceLocation(page=2, locator="physical/2/row/1"),
                QnuSourceLocation(page=3, locator="physical/3/row/1")]
    columns = [
        {"id": "c1", "header_path": ["Mã ngành"]},
        {"id": "c2", "header_path": ["Ngành"]},
        {"id": "c3", "header_path": ["Chỉ tiêu", "2025"],
         "temporal": {"data_years": [2025], "basis_quote": "Chỉ tiêu / 2025"}},
        {"id": "c4", "header_path": ["Chỉ tiêu", "2026"],
         "temporal": {"data_years": [2026], "basis_quote": "Chỉ tiêu / 2026"}},
        {"id": "c5", "header_path": ["Chỉ tiêu", "2027"], "temporal": {"data_years": [2027]}},
        {"id": "c6", "header_path": ["Điểm chuẩn", "2026"],
         "temporal": {"data_years": [2026], "basis_quote": "Điểm chuẩn / 2026"}},
        {"id": "c7", "header_path": ["Ghi chú"]},
    ]
    first = {
        "c1": {"raw": "0012345", "state": "present", "normalized": None},
        "c2": {"raw": "Công nghệ ô tô", "state": "present", "normalized": None},
        "c3": {"raw": "–", "state": "not_applicable", "normalized": None},
        "c4": {"raw": c4_value, "state": c4_state, "normalized": 0 if c4_state == "present" else None},
        "c5": {"raw": "–", "state": "not_applicable", "normalized": None},
        "c6": {"raw": "18", "state": "present", "normalized": None},
        "c7": {"raw": "–", "state": "not_stated", "normalized": None},
    }
    second = {
        "c1": {"raw": "0012346", "state": "present", "normalized": None},
        "c2": {"raw": "Kỹ thuật cơ khí", "state": "present", "normalized": None},
        "c3": {"raw": "15", "state": "present", "normalized": 15},
        "c4": {"raw": "", "state": "blank", "normalized": None},
        "c5": {"raw": "20", "state": "present", "normalized": 20},
        "c6": {"raw": "7", "state": "present", "normalized": 7},
        "c7": {"raw": "Theo quy chế.", "state": "present", "normalized": None},
    }
    first_attributes = {"fields": first,
                        "field_sources": {"c4": {"page": 2, "locator": "physical/2/table/1/cell/3"}},
                        "field_origins": {"c4": {"kind": "docx_table_cell", "engine_used": "fixture"}}}
    return QnuStructuredDocument(
        title="Fixture tuyển sinh", source=QnuSourceInfo(filename="fixture-source.pdf", sha256=SHA, page_count=3),
        blocks=[
            QnuBlock(id="s", type="section", body="# Tuyển sinh 2026", source_locations=[page2]),
            QnuBlock(id="date", type="text", body="Ngày 15 tháng 7 năm 2026",
                     source_locations=[page2], section_path=["Tuyển sinh 2026"]),
            QnuBlock(id="t", parent_id="s", type="table", source_locations=[page2], context_refs=["n"],
                     section_path=["Tuyển sinh 2026"], attributes={"representation": "records", "columns": columns}),
            QnuBlock(id="r1", parent_id="t", type="table_row", source_locations=spanning, attributes=first_attributes),
            QnuBlock(id="r2", parent_id="t", type="table_row", source_locations=[page2],
                     attributes={"fields": second}),
            QnuBlock(id="n", parent_id="s", type="note",
                     body="Điều kiện áp dụng cho chỉ tiêu và điểm chuẩn năm 2026 của bảng này.",
                     source_locations=[page2], section_path=["Tuyển sinh 2026"]),
            QnuBlock(id="n2", parent_id="s", type="note",
                     body="Điều kiện áp dụng cho chỉ tiêu và điểm chuẩn năm 2026 của bảng này.",
                     source_locations=[page2], section_path=["Tuyển sinh 2026"]),
            QnuBlock(id="g", type="text", body="Quy định chung áp dụng cho toàn bảng.",
                     source_locations=[QnuSourceLocation(locator="physical/2/para/9")],
                     section_path=["Tuyển sinh 2026"]),
        ])


def build_state(binding=BINDING, revision=REVISION, source_id=SOURCE, index_id=INDEX,
                c4_state="present", c4_value="0"):
    canonical, draft = project_document(fixture_document(c4_state, c4_value), reference(binding, revision),
                                        {"filename": "tuyen-sinh-2027.pdf", "title": "Fixture tuyển sinh"})
    source = SimpleNamespace(
        id=revision, binding_id=binding, canonical_markdown=canonical,
        canonical_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        snapshot_metadata={"title": "Fixture tuyển sinh", "qnu_markdown": reference(binding, revision)},
        parse_provenance={"standard_required": True, "canonical_format": "qnu-rag-projection/v1",
                          "structured_artifact": draft},
        page_manifest=[{"page": 1}, {"page": 2}, {"page": 3}], citation_metadata={}, status="review_required")
    binding_model = SimpleNamespace(id=binding, status="active", active_source_revision_id=None)
    source_ingestion_service._apply_review_decision(
        binding_model, source, draft, "approved", "Đã đối chiếu fixture nguồn", "reviewer")
    approved = source.parse_provenance["structured_artifact"]
    manifest = resolve_unit_manifest(canonical, approved)
    chunks = structure_chunks(canonical, manifest, context_graph=approved["context_graph"])
    source_chunks = [SimpleNamespace(id=f"chunk-{index_id}-{chunk['index']}", binding_id=binding,
        index_revision_id=index_id, chunk_metadata=chunk["metadata"], content=chunk["content"],
        section=chunk["section"], page_number=chunk["page_number"]) for chunk in chunks]
    index = SimpleNamespace(id=index_id, binding_id=binding, chunk_count=len(chunks),
        parity_report={"parity_passed": True, "unit_manifest_hash": manifest_digest(manifest)})
    return SimpleNamespace(source=source, index=index, binding=binding_model, chunks=source_chunks,
        draft=draft, approved=approved, canonical=canonical, manifest=manifest)


def snapshot(bindings=None):
    return RetrievalSnapshot(snapshot_id="snapshot-536", collection_id=COLLECTION, tenant_id="tenant",
                             workspace_id="workspace", binding_revisions=bindings or {BINDING: INDEX})


def rows_for(state, questions=(QUESTION,)):
    return [row for question in questions
            for row in source_rows(state.source, state.index, state.binding, state.chunks, question)]


def request(question=QUESTION):
    return AskRequest(question=question, collection_id=COLLECTION, tenant_id="tenant", workspace_id="workspace",
        preferred_provider_id="configured", preferred_model_name="arbitrary/model", module_code="admissions",
        runtime_policy={"persona_scope": {"persona": "Configured institution", "allowed_topics": ["Topic"]}})


def table_of(artifact, index=0):
    return artifact["tables"][index]


def fields_by_header(artifact, row_index=0):
    table = table_of(artifact)
    return {field["header"]: field for field in table["row_fields"][row_index]}


def cell_key(catalog, row_id, header):
    return next(key for key, cell in catalog.cells.items() if cell.row_id == row_id and cell.header == header)


def row_of(catalog, entity):
    return next(key for key, row in catalog.rows.items() if row["entity"] == entity)


class _Result:
    def __init__(self, records):
        self.records = records

    def all(self):
        return self.records

    def scalars(self):
        return SimpleNamespace(all=lambda: self.records)


def db_for(records):
    return SimpleNamespace(execute=AsyncMock(return_value=_Result(records)))


def fact_objects(artifact, binding=BINDING, index=INDEX):
    facts = []
    for number, fact in enumerate(artifact["facts"]):
        raw = fact["raw_data"]
        facts.append(SimpleNamespace(id=f"fact-{number}", collection_id=COLLECTION, binding_id=binding,
            index_revision_id=index, entity_name=fact["entity_name"], attribute_name=fact["attribute_name"],
            attribute_value=fact["attribute_value"], applicability_year=None,
            entity_code=raw.get("entity_code"), raw_data=raw))
    return facts


# F1: declared cell state travels projection -> chunk -> source_rows -> catalog.

def test_cell_state_and_coordinates_reach_catalog_without_marker_rederivation():
    state = build_state()
    catalog = build_catalog(rows_for(state, (QUESTION, OTHER_QUESTION)), snapshot())
    first, second = row_of(catalog, "Công nghệ ô tô"), row_of(catalog, "Kỹ thuật cơ khí")
    assert catalog.rows[first]["entity_code"] == "0012345"
    states = {header: (catalog.cells[cell_key(catalog, first, header)].value,
                       catalog.cells[cell_key(catalog, first, header)].state)
              for header in ("Chỉ tiêu / 2025", "Chỉ tiêu / 2026", "Chỉ tiêu / 2027", "Ghi chú")}
    assert states["Chỉ tiêu / 2025"] == ("–", "not_applicable")
    assert states["Chỉ tiêu / 2026"] == ("0", "present")
    assert states["Chỉ tiêu / 2027"] == ("–", "not_applicable")
    assert states["Ghi chú"] == ("–", "not_stated")
    zero = catalog.cells[cell_key(catalog, first, "Chỉ tiêu / 2026")]
    assert zero.standard and zero.state_source == "declared" and zero.normalized == 0
    assert zero.column_id == "c4" and zero.header_path == ["Chỉ tiêu", "2026"]
    assert zero.field_source == {"page": 2, "locator": "physical/2/table/1/cell/3"}
    assert zero.field_origin == {"kind": "docx_table_cell", "engine_used": "fixture"}
    blank = catalog.cells[cell_key(catalog, second, "Chỉ tiêu / 2026")]
    assert (blank.value, blank.state) == ("", "blank")
    payload = catalog.payload()
    rendered_entry = next(cell for table in payload["tables"] for cell in table["cells"] if cell["id"] == cell_key(catalog, first, "Chỉ tiêu / 2026"))
    assert rendered_entry["state"] == "present" and rendered_entry["standard"] is True
    answer, cells, _ = render_cells(RowSelection(status="selected", cell_ids=[
        cell_key(catalog, first, "Chỉ tiêu / 2026"), cell_key(catalog, first, "Ghi chú")]), catalog)
    assert "| 0 |" in answer and "(nguồn không nêu)" in answer
    assert [cell["state"] for cell in cells] == ["present", "not_stated"]
    assert not source_value_variants(RowSelection(status="selected", cell_ids=[
        cell_key(catalog, first, "Chỉ tiêu / 2026")]), catalog, QUESTION)
    closed = close_empty_cells(RowSelection(status="selected", cell_ids=[
        cell_key(catalog, second, "Chỉ tiêu / 2025"), cell_key(catalog, second, "Chỉ tiêu / 2027")]), catalog)
    assert cell_key(catalog, second, "Chỉ tiêu / 2026") in closed.cell_ids
    assert catalog.cells[cell_key(catalog, second, "Chỉ tiêu / 2026")].state == "blank"


def test_same_raw_dash_with_different_declared_state_is_not_one_datum():
    first = build_state(binding="binding-a", revision="revision-a", source_id="source-a", index_id="index-a",
                        c4_state="not_applicable", c4_value="–")
    second = build_state(binding="binding-b", revision="revision-b", source_id="source-b", index_id="index-b",
                         c4_state="not_stated", c4_value="–")
    rows = rows_for(first) + rows_for(second)
    bindings = {"binding-a": "index-a", "binding-b": "index-b"}
    catalog = build_catalog(rows, snapshot(bindings))
    first_row = row_of(catalog, "Công nghệ ô tô")
    second_row = next(key for key, row in catalog.rows.items()
                      if row["entity"] == "Công nghệ ô tô" and key != first_row)
    selection = RowSelection(status="selected", cell_ids=[
        cell_key(catalog, first_row, "Chỉ tiêu / 2026"), cell_key(catalog, second_row, "Chỉ tiêu / 2026")])
    assert catalog.cells[selection.cell_ids[0]].value == catalog.cells[selection.cell_ids[1]].value == "–"
    assert {catalog.cells[key].state for key in selection.cell_ids} == {"not_applicable", "not_stated"}
    assert source_value_variants(selection, catalog, QUESTION)


def test_declared_ambiguous_cell_cannot_be_approved_or_reach_the_catalog():
    _, draft = project_document(fixture_document("ambiguous", "?"), reference(), {})
    revision = SimpleNamespace(parse_provenance={"standard_required": True})
    with pytest.raises(AppException) as error:
        source_ingestion_service._apply_review_decision(
            SimpleNamespace(status="active"), revision, draft, "approved", "Đã đối chiếu fixture", "reviewer")
    assert error.value.code == "QNU_UNRESOLVED_CELLS"
    state = build_state()
    tampered = deepcopy(state.approved)
    table_of(tampered)["row_fields"][0][3]["state"] = "ambiguous"
    source = SimpleNamespace(**{**state.source.__dict__,
        "parse_provenance": {**state.source.parse_provenance, "structured_artifact": tampered}})
    rows = [row for row in rows_for(state) if row.metadata["source_unit_id"] == "qnu:r1"]
    tampered_rows = source_rows(source, state.index, state.binding, state.chunks, QUESTION)
    with pytest.raises(AppException) as error:
        build_catalog(tampered_rows, snapshot())
    assert error.value.code == "ROW_ANSWER_SOURCE_INVALID"
    assert rows  # the untouched publication still resolves normally


def test_missing_state_is_never_present_and_non_present_values_carry_no_normalized():
    document = fixture_document()
    row = next(block for block in document.blocks if block.id == "r1")
    row.attributes["fields"]["c4"] = {"raw": "0", "normalized": 0}
    _, draft = project_document(document, reference(), {})
    field = fields_by_header(draft)["Chỉ tiêu / 2026"]
    assert field["state"] == "ambiguous" and field["normalized"] is None
    assert any(issue["code"] == "CELL_STATE_UNAVAILABLE" for issue in draft["issues"])
    assert any(issue["code"] == "CELL_NORMALIZED_UNSUPPORTED" for issue in draft["issues"])
    assert draft["unresolved_cell_count"] >= 1
    revision = SimpleNamespace(parse_provenance={"standard_required": True})
    with pytest.raises(AppException) as error:
        source_ingestion_service._apply_review_decision(
            SimpleNamespace(status="active"), revision, draft, "approved", "Đã đối chiếu fixture", "reviewer")
    assert error.value.code == "QNU_UNRESOLVED_CELLS"


# F2: reviewed facts keep exact rows and transitive dependency closure.

def published(records):
    return db_for(records)


@pytest.mark.asyncio
async def test_reviewed_fact_pulls_header_note_and_transitive_dependency():
    state = build_state()
    blocks = await load_published_blocks(published([(state.source, state.index, state.binding)]), snapshot())
    facts = fact_objects(state.approved)
    fact_blocks = await reviewed_fact_blocks(db_for(facts), request(), snapshot(),
        QueryPlan(query=QUESTION, years=[2026]), blocks, exhaustive=True)
    fact = next(block for block in fact_blocks if block.origin == "reviewed_fact"
                and block.fact_context["entity_name"] == "Công nghệ ô tô"
                and len(block.fact_context["cells"]) == 2)
    assert fact.fact_context["verified_dependencies"] is True
    assert {cell["attribute"] for cell in fact.fact_context["cells"]} == {"Chỉ tiêu / 2026", "Điểm chuẩn / 2026"}
    groups = dependency_groups(blocks + fact_blocks)
    member_units = {block.unit_id for block in groups[fact.id]}
    assert {"qnu:n", "qnu:t:header"} <= member_units
    assert "qnu:n2" not in member_units  # identical text on the same page is not cross-linked
    note = next(block for block in blocks if block.unit_id == "qnu:n")
    assert not {"qnu:r1", "qnu:r2"}.intersection({block.unit_id for block in groups.get(note.id, [])})
    selected = pack_context(blocks + fact_blocks, [fact], [], 10, 10_000_000)
    selected_units = {block.unit_id for block in selected}
    assert fact.id in {block.id for block in selected}
    assert {"qnu:n", "qnu:s", "qnu:t:header"} <= selected_units
    refused = pack_context(blocks + fact_blocks, [fact], [], 10, 1)
    assert fact.id not in {block.id for block in refused}


@pytest.mark.asyncio
async def test_missing_cross_revision_or_wrong_hash_dependencies_reject_the_fact():
    state = build_state()
    blocks = await load_published_blocks(published([(state.source, state.index, state.binding)]), snapshot())
    fact_blocks = await reviewed_fact_blocks(db_for(fact_objects(state.approved)), request(), snapshot(),
        QueryPlan(query=QUESTION, years=[2026]), blocks, exhaustive=True)
    without_note = [block for block in blocks if block.unit_id != "qnu:n"]
    with pytest.raises(AppException) as error:
        dependency_groups(without_note + fact_blocks)
    assert error.value.code == "EVIDENCE_CONTEXT_MISSING"
    note = next(block for block in blocks if block.unit_id == "qnu:n")
    cross_revision = note.model_copy(update={"source_revision_id": "another-revision"})
    with pytest.raises(AppException) as error:
        dependency_groups([block for block in blocks if block.unit_id != "qnu:n"] + [cross_revision] + fact_blocks)
    assert error.value.code == "EVIDENCE_CONTEXT_MISSING"
    wrong_hash = fact_objects(state.approved)
    for fact in wrong_hash:
        fact.raw_data = {**fact.raw_data, "unit_manifest_hash": "0" * 64}
    rejected = await reviewed_fact_blocks(db_for(wrong_hash), request(), snapshot(),
        QueryPlan(query=QUESTION, years=[2026]), blocks, exhaustive=True)
    assert rejected == []


@pytest.mark.asyncio
async def test_standard_fact_year_filter_excludes_declared_other_years():
    state = build_state()
    blocks = await load_published_blocks(published([(state.source, state.index, state.binding)]), snapshot())
    fact_blocks = await reviewed_fact_blocks(db_for(fact_objects(state.approved)), request(), snapshot(),
        QueryPlan(query=QUESTION, years=[2026]), blocks, exhaustive=True)
    attributes = [cell["attribute"] for block in fact_blocks for cell in block.fact_context.get("cells", [])]
    assert "Chỉ tiêu / 2026" in attributes and "Điểm chuẩn / 2026" in attributes
    assert not [attribute for attribute in attributes if "2025" in attribute or "2027" in attribute]
    unknown = next(block for block in fact_blocks if block.fact_context["entity_name"] == "Kỹ thuật cơ khí"
                   and any(cell["attribute"] == "Ghi chú" for cell in block.fact_context["cells"]))
    assert next(cell for cell in unknown.fact_context["cells"] if cell["attribute"] == "Ghi chú")[
        "temporal_context"]["status"] == "unknown"


# F3: typed temporal metadata stays at its declared level and needs review to verify.

def test_temporal_scope_survives_projection_and_review_per_cell():
    state = build_state()
    draft_fields = fields_by_header(state.draft)
    assert draft_fields["Chỉ tiêu / 2025"]["temporal"]["status"] == "proposed"
    assert draft_fields["Chỉ tiêu / 2026"]["temporal"]["status"] == "proposed"
    assert draft_fields["Chỉ tiêu / 2027"]["temporal"]["status"] == "ambiguous"
    assert draft_fields["Ghi chú"]["temporal"] is None
    assert any(issue["code"] == "TEMPORAL_BASIS_MISSING" for issue in state.draft["issues"])
    approved_fields = fields_by_header(state.approved)
    assert approved_fields["Chỉ tiêu / 2025"]["temporal"]["status"] == "verified"
    assert approved_fields["Chỉ tiêu / 2026"]["temporal"]["status"] == "verified"
    assert approved_fields["Điểm chuẩn / 2026"]["temporal"]["status"] == "verified"
    assert approved_fields["Chỉ tiêu / 2027"]["temporal"]["status"] == "ambiguous"
    assert approved_fields["Chỉ tiêu / 2027"]["temporal"]["data_years"] == [2027]
    assert approved_fields["Chỉ tiêu / 2026"]["temporal"]["basis_quote"] == "Chỉ tiêu / 2026"
    assert [field["temporal"]["data_years"] for field in table_of(state.approved)["row_fields"][0] if field.get("temporal")] == [
        [2025], [2026], [2027], [2026]]
    facts = {fact["attribute_name"]: fact for fact in state.approved["facts"]
             if fact["entity_name"] == "Công nghệ ô tô"}
    assert facts["Chỉ tiêu / 2026"]["raw_data"]["temporal_context"]["status"] == "verified"
    assert facts["Chỉ tiêu / 2026"]["raw_data"]["temporal_context"]["year"] == 2026
    row_unit = next(unit for unit in state.manifest.units if unit.id == "qnu:r1")
    table_unit = next(unit for unit in state.manifest.units if unit.id == "qnu:t")
    header_unit = next(unit for unit in state.manifest.units if unit.id == "qnu:t:header")
    assert not row_unit.temporal.data_years and not table_unit.temporal.data_years
    assert not header_unit.temporal.data_years
    assert row_unit.temporal.status != "verified"
    assert state.approved["temporal_metadata"]["issued_date"]["value"] == "2026-07-15"
    assert row_unit.temporal.issued_date == "2026-07-15"
    filename_years = state.approved["temporal_metadata"]["filename_years"]
    assert filename_years["values"] == [2027] and filename_years["status"] == "proposed"
    assert facts["Chỉ tiêu / 2026"]["raw_data"]["temporal_context"]["years"] == [2026]


def test_declared_verified_status_and_heading_year_do_not_self_certify():
    document = fixture_document().model_copy(deep=True)
    table = next(block for block in document.blocks if block.id == "t")
    table.attributes["columns"][3]["temporal"]["status"] = "verified"
    _, artifact = project_document(document, reference(), {"filename": "tuyen-sinh-2027.pdf"})
    field = fields_by_header(artifact)["Chỉ tiêu / 2026"]
    assert field["temporal"]["status"] == "proposed"
    assert field["temporal"]["unsupported"]["status"] == "verified"
    assert any(issue["code"] == "TEMPORAL_STATUS_NOT_ACCEPTED" for issue in artifact["issues"])
    draft = simple_projection(document)
    heading = next(unit for unit in draft.units if unit.id == "qnu:s")
    assert heading.temporal.data_years == [] and heading.temporal.status != "verified"
    assert artifact["temporal_metadata"]["filename_years"]["values"] == [2027]
    assert all(unit.temporal.data_years == [] for unit in draft.units)


def simple_projection(document):
    canonical, artifact = project_document(document, reference(), {})
    return resolve_unit_manifest(canonical, artifact)


def test_row_level_year_is_not_promoted_and_wrong_year_cells_are_rejected():
    state = build_state()
    rows = rows_for(state, (QUESTION, OTHER_QUESTION))
    catalog = build_catalog(rows, snapshot())
    first, second = row_of(catalog, "Công nghệ ô tô"), row_of(catalog, "Kỹ thuật cơ khí")
    scope = catalog.rows[second]["scope_candidates"][0]
    wrong_key = cell_key(catalog, second, "Chỉ tiêu / 2027")
    assert catalog.rows[second]["cells"] and catalog.cells[wrong_key].temporal["data_years"] == [2027]
    with pytest.raises(ValueError):
        validate_selection(RowSelection(status="selected", cell_ids=[wrong_key], scope_ids=[scope]), catalog, QUESTION)
    retained = retain_scoped_cells(RowSelection(status="selected", cell_ids=[wrong_key], scope_ids=[scope]), catalog, QUESTION)
    assert wrong_key not in retained.cell_ids
    allowed = cell_key(catalog, second, "Điểm chuẩn / 2026")
    validate_selection(RowSelection(status="selected", cell_ids=[allowed], scope_ids=[scope]), catalog, QUESTION)
    verified_2026 = catalog.cells[cell_key(catalog, first, "Chỉ tiêu / 2026")]
    assert verified_2026.temporal["status"] == "verified" and verified_2026.temporal["data_years"] == [2026]


# F4: server-verified source locations keep every spanning page.

@pytest.mark.asyncio
async def test_spanning_row_keeps_ordered_pages_and_single_page_stays_single():
    state = build_state()
    blocks = await load_published_blocks(published([(state.source, state.index, state.binding)]), snapshot())
    spanning = next(block for block in blocks if block.unit_id == "qnu:r1")
    single = next(block for block in blocks if block.unit_id == "qnu:r2")
    locator_only = next(block for block in blocks if block.unit_id == "qnu:g")
    assert spanning.page_number is None and len(spanning.fact_context["source_locations"]) == 2
    spanning_ref = bind_quote(QuoteReference(block_id=spanning.id, quote="Công nghệ ô tô"),
                              {spanning.id: spanning})
    assert spanning_ref["page_number"] is None and spanning_ref["source_pages"] == [2, 3]
    assert state.canonical[spanning_ref["start"]:spanning_ref["end"]] == "Công nghệ ô tô"
    single_ref = bind_quote(QuoteReference(block_id=single.id, quote="0012346"), {single.id: single})
    assert single_ref["page_number"] == 2 and single_ref["source_pages"] == [2]
    locator_ref = bind_quote(QuoteReference(block_id=locator_only.id, quote="Quy định chung"),
                             {locator_only.id: locator_only})
    assert locator_ref["page_number"] is None and citation_pages(locator_ref) is None
    assert locator_ref["source_locations"][0]["locator"] == "physical/2/para/9"
    response = decision_response(request(), snapshot(), "partial", "TEST_SPAN",
        bindings=[{"text": "Công nghệ ô tô", "references": [spanning_ref]}])
    assert response.citations[0].source_pages == [2, 3] and response.citations[0].page_number is None
    assert response.citations[0].canonical_hash == state.source.canonical_hash
    assert response.citations[0].span_start == spanning_ref["start"]


@pytest.mark.asyncio
async def test_row_answer_citations_keep_spanning_and_stated_values():
    state = build_state()
    rows = rows_for(state)
    catalog = build_catalog(rows, snapshot())
    row_id = row_of(catalog, "Công nghệ ô tô")
    cells = [cell_key(catalog, row_id, header) for header in ("Chỉ tiêu / 2026", "Điểm chuẩn / 2026", "Ghi chú")]
    scope = catalog.rows[row_id]["scope_candidates"][0]
    note = catalog.rows[row_id]["note_candidates"][0]
    selection = RowSelection(status="selected", cell_ids=cells, scope_ids=[scope], note_ids=[note])
    audit = RowAudit(compatible=True, scope_supported=True, complete=True,
                     required_cell_ids=cells, required_context_ids=[scope, note])
    with patch("app.modules.rag.row_answer.structured_call",
               AsyncMock(side_effect=[MetricScope(context_ids=[scope]), selection, audit])):
        response = await answer_from_rows(AsyncMock(), request(), snapshot(), rows)
    assert response.status == "answered"
    assert all(value in response.answer for value in ("0", "18", "(nguồn không nêu)"))
    assert [cell["state"] for cell in response.answer_decision["cells"]] == ["present", "present", "not_stated"]
    spanning = [citation for citation in response.citations if citation.source_pages == [2, 3]]
    assert spanning and spanning[0].page_number is None
    assert any(citation.source_pages == [2] and citation.page_number == 2 for citation in response.citations)
    assert all(citation.canonical_hash and citation.span_start is not None for citation in response.citations)
