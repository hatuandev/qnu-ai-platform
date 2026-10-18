"""Exact-source proposals, explicit human review, field scope and draft boundaries."""

import copy
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import docx
import pymupdf
import pytest
from PIL import Image

import tests.test_review536_findings as fixture
from app.core.exceptions import AppException
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
from app.modules.knowledge.parsers.docling_office_parser import DoclingOfficeParser
from app.modules.knowledge.parsers.docling_structure import _Builder, build_qnu_structured_document
from app.modules.knowledge.parsers.docx_evidence import preview_image_locations
from app.modules.knowledge.schemas import SemanticProposalReviewRequest
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    apply_reviewed_semantics,
    generate_semantic_proposals,
    propose_source_semantics,
    review_semantic_proposals,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
from app.modules.knowledge.services.source_links import unit_context_ids
from app.modules.rag.evidence_bm25 import rank_blocks, tokens
from app.modules.rag.evidence_schemas import EvidenceBlock


def draft():
    model = fixture.fixture_document()
    model.blocks[-1].body = "Only the 2026 column has this condition."
    canonical, artifact = project_document(model, fixture.reference(), {})
    return canonical, artifact


def proposals(artifact):
    table = artifact["tables"][0]
    row = table["row_unit_ids"][0]
    return SemanticAnnotations(notes=[{
        "note_unit_id": "qnu:g", "table_id": table["id"], "scope": "column",
        "column_ids": ["c4"], "evidence_quote": "Only the 2026 column has this condition.",
    }], cells=[{
        "row_unit_id": row, "column_id": "c7", "raw": "–", "state": "not_applicable",
        "evidence_unit_id": "qnu:n", "evidence_quote": "Điều kiện áp dụng",
    }])


def test_staging_preserves_graph_fields_facts_until_exact_review():
    canonical, artifact = draft()
    before = copy.deepcopy(artifact)
    pending = stage_semantic_annotations(artifact, proposals(artifact))
    for key in ("facts", "tables", "retrieval_units", "context_graph", "unit_manifest_hash"):
        assert artifact[key] == before[key]
    with pytest.raises(AppException, match="đề xuất") as error:
        apply_reviewed_semantics(artifact, None, "reviewer", "Checked source")
    assert error.value.code == "SEMANTIC_REVIEW_REQUIRED"
    revised = apply_reviewed_semantics(artifact, pending["proposal_hash"], "reviewer", "Checked source")
    manifest = resolve_unit_manifest(canonical, revised)
    row = revised["tables"][0]["row_unit_ids"][0]
    assert "qnu:g" in unit_context_ids(manifest, row, "c4")
    assert "qnu:g" not in unit_context_ids(manifest, row, "c3")
    assert "qnu:g" in revised["context_graph"]["links"][row]
    for fact in revised["facts"]:
        raw = fact["raw_data"]
        assert ("qnu:g" in raw["context_unit_ids"]) == (raw["column_id"] == "c4")
        assert raw["unit_manifest_hash"] == revised["unit_manifest_hash"]
    assert revised["semantic_annotations"]["review"]["actor_id"] == "reviewer"
    assert artifact["semantic_annotations"]["status"] == "proposed"


@pytest.mark.parametrize("change", ["raw", "quote", "table", "row", "column", "duplicate", "zero", "blank", "sibling"])
def test_invalid_coordinates_and_borrowed_evidence_are_rejected_atomically(change):
    _, artifact = draft()
    value = proposals(artifact).model_dump()
    if change == "raw":
        value["cells"][0]["raw"] = "rewritten"
    elif change == "quote":
        value["notes"][0]["evidence_quote"] = "invented note"
    elif change == "table":
        value["notes"][0]["table_id"] = "unrelated"
    elif change == "row":
        value["notes"][0]["row_unit_ids"] = ["unknown"]
    elif change == "column":
        value["notes"][0]["column_ids"] = ["unknown"]
    elif change == "duplicate":
        value["notes"] *= 2
    elif change in {"zero", "blank"}:
        row_index, column = (0, 3) if change == "zero" else (1, 3)
        field = artifact["tables"][0]["row_fields"][row_index][column]
        value["cells"][0].update(row_unit_id=artifact["tables"][0]["row_unit_ids"][row_index],
                                   column_id=field["column_id"], raw=field["raw"])
    else:
        value["cells"][0].update(evidence_unit_id=value["cells"][0]["row_unit_id"],
                                   evidence_quote="Công nghệ ô tô")
    before = copy.deepcopy(artifact)
    with pytest.raises(ValueError):
        stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(value))
    assert artifact == before


@pytest.mark.parametrize("change", ["hash", "source", "proposal", "actor", "comment"])
def test_stale_or_unreviewed_proposals_cannot_apply(change):
    _, artifact = draft()
    pending = stage_semantic_annotations(artifact, proposals(artifact))
    expected, actor, comment = pending["proposal_hash"], "reviewer", "Checked source"
    if change == "hash":
        expected = "0" * 64
    elif change == "source":
        artifact["tables"][0]["row_fields"][0][0]["raw"] = "changed"
    elif change == "proposal":
        pending["annotations"]["notes"] = []
    elif change == "actor":
        actor = None
    else:
        comment = " "
    with pytest.raises(AppException):
        apply_reviewed_semantics(artifact, expected, actor, comment)


def test_declared_state_removes_only_affected_facts_and_preserves_unknown_symbol_gate():
    model = fixture.fixture_document()
    row = next(block for block in model.blocks if block.id == "r1")
    row.attributes["fields"]["c7"].update(raw="Not published yet", state="present")
    _, artifact = project_document(model, fixture.reference(), {})
    rid = artifact["tables"][0]["row_unit_ids"][0]
    proposal = SemanticAnnotations(cells=[{
        "row_unit_id": rid, "column_id": "c7", "raw": "Not published yet", "state": "not_stated",
        "evidence_unit_id": rid, "evidence_quote": "Not published yet",
    }])
    pending = stage_semantic_annotations(artifact, proposal)
    revised = apply_reviewed_semantics(artifact, pending["proposal_hash"], "reviewer", "Checked source")
    assert len(revised["facts"]) == len(artifact["facts"]) - 1
    assert revised["tables"][0]["row_fields"][0][6]["raw"] == "Not published yet"
    assert revised["tables"][0]["row_fields"][0][6]["state"] == "not_stated"
    assert revised["tables"][0]["row_fields"][0][3]["raw"] == "0"


@pytest.mark.asyncio
async def test_modelops_uses_configured_provider_and_keeps_proposals_unapplied():
    _, artifact = draft()
    response = SimpleNamespace(content=proposals(artifact).model_dump_json(), provider="configured",
        model="selected", is_fallback=False, prompt_tokens=100, completion_tokens=10, cost_usd=0.001)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=response)) as generate, \
         patch("app.modules.modelops.services.model_catalog_service.model_catalog_service.get_system_model_defaults",
               AsyncMock(return_value=SimpleNamespace(defaults=SimpleNamespace(
                   default_chat_model="selected", default_chat_provider_id="configured")))):
        result = await propose_source_semantics(AsyncMock(), artifact, "tenant")
    request = generate.call_args.args[1]
    assert request.preferred_model_name == "selected" and request.preferred_provider_id == "configured"
    assert "untrusted DATA" in request.messages[0].content
    assert result["status"] == "proposed"
    assert not any(unit["field_context_refs"] for unit in artifact["retrieval_units"]["units"])


@pytest.mark.asyncio
@pytest.mark.parametrize("decision", ["approved", "rejected"])
async def test_draft_review_handler_binds_actor_revision_hash_without_publishing(decision):
    state = fixture.build_state()
    state.source.status = "review_required"
    state.binding.active_source_revision_id = "old-published"
    canonical, artifact = draft()
    state.source.canonical_markdown = canonical
    state.source.canonical_hash = artifact["content_hash"]
    pending = stage_semantic_annotations(artifact, proposals(artifact))
    state.source.parse_provenance["structured_artifact"] = artifact
    payload = SemanticProposalReviewRequest(decision=decision,
        expected_semantic_proposal_hash=pending["proposal_hash"], comment="Checked source")
    actor = SimpleNamespace(actor_id="reviewer", tenant_id="tenant", workspace_id="workspace")
    db = AsyncMock()
    with patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()) as lock, \
         patch("app.modules.knowledge.services.source_reparse.ensure_source_idle", AsyncMock()), \
         patch("app.modules.knowledge.services.qnu_serving.verify_revision_pair", AsyncMock()), \
         patch("app.modules.knowledge.services.source_ingestion_service.source_ingestion_service._get_review_target",
               AsyncMock(return_value=(state.binding, state.source, artifact))) as target:
        await review_semantic_proposals(db, fixture.COLLECTION, fixture.BINDING, fixture.REVISION, payload, actor)
    assert target.call_args.args[-3:] == ("tenant", "workspace", "reviewer")
    lock.assert_awaited_once_with(db, fixture.BINDING)
    saved = state.source.parse_provenance["structured_artifact"]
    assert saved["semantic_annotations"]["status"] == ("verified" if decision == "approved" else "rejected")
    assert state.source.status == "review_required" and state.binding.active_source_revision_id == "old-published"
    db.commit.assert_awaited_once()
    if decision == "rejected":
        assert saved["facts"] == artifact["facts"] and saved["tables"] == artifact["tables"]


@pytest.mark.asyncio
async def test_published_or_busy_sources_cannot_generate_or_apply():
    state = fixture.build_state()
    actor = SimpleNamespace(actor_id="reviewer", tenant_id="tenant", workspace_id="workspace")
    db = AsyncMock()
    with patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()), \
         patch("app.modules.knowledge.services.source_reparse.ensure_source_idle", AsyncMock()), \
         patch("app.modules.knowledge.services.source_ingestion_service.source_ingestion_service._get_review_target",
               AsyncMock(return_value=(state.binding, state.source, state.draft))), \
         patch("app.modules.knowledge.services.semantic_annotations.propose_source_semantics", AsyncMock()) as generate, \
         pytest.raises(AppException) as error:
        await generate_semantic_proposals(db, fixture.COLLECTION, fixture.BINDING, fixture.REVISION, actor)
    assert error.value.code == "SEMANTIC_DRAFT_REQUIRED"
    generate.assert_not_awaited()
    db.commit.assert_not_awaited()


def test_numeric_rows_benefit_from_header_context_without_retrieving_header_as_data():
    def block(uid, text, header="", parent=None):
        return EvidenceBlock(id=uid, unit_id=uid, parent_id=parent, text=text, header_context=header,
            binding_id="binding", index_revision_id="index", source_revision_id="revision", title="",
            fact_context={"source_kind": "table"},
            start=0, end=len(text))
    blocks = [block("t:header", "Independent identifier", parent="t"),
              block("r", "00027", "Independent identifier", "t"),
              block("other", "00027", "Unrelated section", "u")]
    ranked = rank_blocks(blocks, ["Independent identifier 00027"], 5)
    assert ranked[0].id == "r"
    assert "t:header" not in {b.id for b in ranked}
    assert "program" in tokens("program_code_0012") and "0012" in tokens("program_code_0012")
    assert "00027" in tokens("00027") and "27" not in tokens("00027")


def test_unique_native_page_and_letter_list_marker_keep_literal_digits():
    builder = _Builder(True, {3: "a) Preserve identifier 00027", 4: "Preserve identifier 27"})
    assert builder.map_unit("Preserve identifier 00027", [], 0, "", full_lines=True)[0] == [3]
    builder.render_pages[4] = "b) Preserve identifier 00027"
    assert builder.map_unit("Preserve identifier 00027", [], 0, "", full_lines=True)[0] == []


def test_ordered_short_rows_resolve_only_between_same_page_anchors():
    document = docx.Document()
    table = document.add_table(rows=4, cols=1)
    for row, value in zip(table.rows, ["Start unique anchor", "0", "00027", "End unique anchor"], strict=True):
        row.cells[0].text = value
    stream = io.BytesIO()
    document.save(stream)
    parsed = DoclingOfficeParser("docx")._parse_sync(stream.getvalue(), "test.docx")
    for same_page in (True, False):
        pages = {1: "Start unique anchor\nEnd unique anchor"} if same_page else {1: "Start unique anchor", 2: "End unique anchor"}
        model = build_qnu_structured_document(parsed.docling_document, filename="test.docx", sha256="a" * 64,
            header_evidence=parsed.docx_header_evidence, source_evidence={"render_pages": pages})
        rows = [b for b in model.blocks if b.type == "table_row"]
        assert [r.attributes["fields"]["c01"]["raw"] for r in rows] == ["Start unique anchor", "0", "00027", "End unique anchor"]
        assert rows[1].source_locations[0].page == (1 if same_page else None)


def test_unique_exact_image_pixels_get_page_but_duplicate_occurrence_abstains():
    image = io.BytesIO()
    Image.new("RGB", (16, 13), (12, 101, 207)).save(image, format="PNG")
    resources = [{"data": image.getvalue(), "source_ref": "picture"}]
    document = pymupdf.open()
    document.new_page().insert_image(pymupdf.Rect(5, 5, 21, 18), stream=image.getvalue())
    result = preview_image_locations(document.tobytes(), resources)
    assert result["picture"]["page"] == 1
    document.new_page().insert_image(pymupdf.Rect(5, 5, 21, 18), stream=image.getvalue())
    assert preview_image_locations(document.tobytes(), resources) == {}
    document.close()


def test_pending_or_unavailable_semantics_cannot_be_approved_by_source_review():
    state = fixture.build_state()
    _, artifact = draft()
    pending = stage_semantic_annotations(artifact, proposals(artifact))
    with pytest.raises(AppException) as error:
        source_ingestion_service._apply_review_decision(state.binding, state.source, artifact,
            "approved", "Checked source", "reviewer")
    assert error.value.code == "SEMANTIC_REVIEW_REQUIRED"
    artifact["semantic_annotations"] = {"status": "unavailable"}
    with pytest.raises(AppException) as error:
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "reviewer", "Checked source")
    assert error.value.code == "SEMANTIC_PROPOSAL_UNAVAILABLE"


@pytest.mark.parametrize("scope", ["table", "row", "group"])
def test_shared_note_scope_names_exact_rows_and_never_links_back_from_note(scope):
    canonical, artifact = draft()
    table = artifact["tables"][0]
    targets = table["row_unit_ids"] if scope != "row" else table["row_unit_ids"][:1]
    proposal = SemanticAnnotations(notes=[{
        "note_unit_id": "qnu:g", "table_id": table["id"], "scope": scope,
        "row_unit_ids": [] if scope == "table" else targets,
        "evidence_quote": "Only the 2026 column has this condition.",
    }])
    pending = stage_semantic_annotations(artifact, proposal)
    result = apply_reviewed_semantics(artifact, pending["proposal_hash"], "reviewer", "Checked source")
    manifest = resolve_unit_manifest(canonical, result)
    for row in table["row_unit_ids"]:
        assert ("qnu:g" in unit_context_ids(manifest, row)) == (row in targets)
    assert not unit_context_ids(manifest, "qnu:g")


@pytest.mark.asyncio
async def test_busy_source_aborts_before_model_call_or_draft_write():
    actor = SimpleNamespace(actor_id="reviewer", tenant_id="tenant", workspace_id="workspace")
    db = AsyncMock()
    with patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()), \
         patch("app.modules.knowledge.services.source_reparse.ensure_source_idle",
               AsyncMock(side_effect=AppException("Busy", code="SOURCE_BUSY", status_code=409))), \
         patch("app.modules.knowledge.services.semantic_annotations.propose_source_semantics", AsyncMock()) as model, \
         pytest.raises(AppException) as error:
        await generate_semantic_proposals(db, "collection", "source", "revision", actor)
    assert error.value.code == "SOURCE_BUSY"
    model.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_model_failure_leaves_draft_unchanged_and_accounting_uses_separate_session():
    from unittest.mock import MagicMock

    state = fixture.build_state()
    state.source.status = "review_required"
    db, model_db = AsyncMock(), AsyncMock()
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=model_db)
    session.__aexit__ = AsyncMock(return_value=False)
    before = copy.deepcopy(state.source.parse_provenance)
    actor = SimpleNamespace(actor_id="reviewer", tenant_id="tenant", workspace_id="workspace")
    with patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()), \
         patch("app.modules.knowledge.services.source_reparse.ensure_source_idle", AsyncMock()), \
         patch("app.modules.knowledge.services.qnu_serving.verify_revision_pair", AsyncMock()), \
         patch("app.modules.knowledge.services.source_ingestion_service.source_ingestion_service._get_review_target",
               AsyncMock(return_value=(state.binding, state.source, state.draft))), \
         patch("app.core.database.AsyncSessionFactory", return_value=session), \
         patch("app.modules.knowledge.services.semantic_annotations.propose_source_semantics",
               AsyncMock(side_effect=ValueError("Unsupported evidence"))) as model, \
         pytest.raises(AppException) as error:
        await generate_semantic_proposals(db, fixture.COLLECTION, fixture.BINDING, fixture.REVISION, actor)
    assert error.value.code == "SEMANTIC_PROPOSAL_INVALID"
    assert model.call_args.args[0] is model_db and model_db is not db
    assert state.source.parse_provenance == before
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_scoped_fact_dependencies_survive_real_canonical_and_fact_loaders():
    from app.modules.rag.evidence_blocks import load_published_blocks
    from app.modules.rag.evidence_facts import reviewed_fact_blocks
    from app.modules.rag.evidence_schemas import QueryPlan

    state = fixture.build_state()
    canonical, artifact = draft()
    pending = stage_semantic_annotations(artifact, proposals(artifact))
    state.source.canonical_markdown = canonical
    state.source.canonical_hash = artifact["content_hash"]
    source_ingestion_service._apply_review_decision(state.binding, state.source, artifact,
        "approved", "RAM regression source review", "reviewer", pending["proposal_hash"])
    artifact = state.source.parse_provenance["structured_artifact"]
    state.index.parity_report["unit_manifest_hash"] = artifact["unit_manifest_hash"]
    canonical_blocks = await load_published_blocks(fixture.db_for([(state.source, state.index, state.binding)]), fixture.snapshot())
    facts = fixture.fact_objects(artifact)
    result = await reviewed_fact_blocks(fixture.db_for(facts), fixture.request(), fixture.snapshot(),
        QueryPlan(query=fixture.QUESTION, years=[2026]), canonical_blocks, exhaustive=True)
    assert result and any(b.fact_context.get("verified_dependencies") for b in result)
    refs = {ref for b in result for ref in b.fact_context.get("context_unit_ids", [])}
    assert "qnu:g" in refs
