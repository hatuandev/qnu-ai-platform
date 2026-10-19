"""QNU standard must not silently downgrade to legacy evidence."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuSourceInfo,
    QnuSourceLocation,
    QnuStructuredDocument,
    render_qnu_markdown,
)
from app.modules.knowledge.normalization.qnu_projection import VERSION, digest, project_document
from app.modules.knowledge.normalization.retrieval_models import UnitManifest
from app.modules.knowledge.normalization.retrieval_units import (
    manifest_digest,
    resolve_unit_manifest,
)
from app.modules.knowledge.normalization.structure_chunks import structure_chunks
from app.modules.knowledge.services.qnu_docx_artifacts import save_qnu_document
from app.modules.knowledge.services.qnu_serving import (
    document_from_edit,
    load_document,
    prepare_standard_revision,
)
from app.modules.knowledge.services.source_artifact import get_source_artifact

SHA = "a" * 64
PATH = "snapshots/collection/binding/source.pdf"


def document():
    location = QnuSourceLocation(page=2, locator="physical/2/table/1", bbox=[1, 2, 3, 4], bbox_space="points")
    return QnuStructuredDocument(title="Document 2026", source=QnuSourceInfo(filename="data.pdf", sha256=SHA, page_count=3),
        blocks=[QnuBlock(id="s", type="section", body="## Tuyển sinh", source_locations=[location]),
            QnuBlock(id="t", parent_id="s", type="table", source_locations=[location], context_refs=["n"],
                section_path=["Tuyển sinh"], attributes={"representation": "records", "columns": [
                    {"id": "c1", "header_path": ["Mã ngành"]}, {"id": "c2", "header_path": ["Ngành"]},
                    {"id": "c3", "header_path": ["2026", "Chỉ tiêu"]}]}),
            QnuBlock(id="r", parent_id="t", type="table_row", source_locations=[location], body="Original record display",
                attributes={"fields": {"c1": {"raw": "0012345", "state": "present", "normalized": None},
                    "c2": {"raw": "Công nghệ", "state": "present", "normalized": None},
                    "c3": {"raw": "0", "state": "present", "normalized": None}},
                    "field_sources": {"c3": location.model_dump()}}),
            QnuBlock(id="n", parent_id="s", type="note", body="Áp dụng kèm điều kiện trong bảng.", source_locations=[location])])


def reference():
    return {"schema_version": "qnu-rag-markdown/1.0", "document_id": "binding", "revision_id": "rev",
            "sha256": SHA, "structured_sha256": "b" * 64}


def project(model=None):
    return project_document(model or document(), reference(), {})


def test_projection_preserves_records_headers_zero_and_dependencies_without_metadata():
    canonical, artifact = project()
    assert "0012345" in canonical and "| 0 |" in canonical
    assert "2026 / Chỉ tiêu" in canonical
    assert "rag:block" not in canonical and "schema_version" not in canonical
    assert artifact["review"]["status"] == "required"
    manifest = resolve_unit_manifest(canonical, artifact)
    row = next(unit for unit in manifest.units if unit.id == "qnu:r")
    assert row.page_number == 2 and row.source_locations[0]["bbox"] == [1, 2, 3, 4]
    assert {"qnu:t:header", "qnu:n"} <= set(artifact["context_graph"]["links"][row.id])
    chunks = structure_chunks(canonical, manifest, context_graph=artifact["context_graph"])
    chunk = next(chunk for chunk in chunks if chunk["metadata"]["source_unit_id"] == row.id)
    assert "2026 / Chỉ tiêu" in chunk["content"] and "Áp dụng kèm điều kiện" in chunk["content"]
    fact = next(fact for fact in artifact["facts"] if fact["attribute_value"] == "0")
    assert fact["raw_data"]["field_source"]["bbox"] == [1, 2, 3, 4]
    assert fact["raw_data"]["source_unit_id"] == "qnu:r"
    assert artifact["derived_indexes"][0]["members"] == ["qnu:r"]


def test_unknown_year_is_not_promoted_from_filename_or_heading():
    canonical, artifact = project()
    assert all(unit["temporal"]["status"] != "verified" for unit in artifact["retrieval_units"]["units"])
    assert all(not unit["temporal"]["data_years"] for unit in artifact["retrieval_units"]["units"])
    assert "2026" not in canonical.splitlines()[0]


def test_missing_cell_and_ambiguous_value_do_not_turn_into_numeric_facts():
    model = document()
    model.blocks[2].attributes["fields"]["c3"] = {"raw": "—", "state": "ambiguous", "normalized": None}
    canonical, artifact = project(model)
    assert "—" in canonical
    assert not any(fact["attribute_value"] == "—" for fact in artifact["facts"])
    assert artifact["unresolved_cell_count"] == 1


@pytest.mark.parametrize("state", ["ambiguous", "unreadable"])
def test_numeric_uncertainty_cannot_be_overridden_by_whole_document_approval(state):
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
    model = document()
    model.blocks[2].attributes["fields"]["c3"] = {"raw": "28.5", "state": state, "normalized": None}
    _, artifact = project(model)
    revision = SimpleNamespace(parse_provenance={"standard_required": True})
    with pytest.raises(AppException) as error:
        source_ingestion_service._apply_review_decision(SimpleNamespace(), revision, artifact,
            "approved", "Đã xem toàn tài liệu", "reviewer")
    assert error.value.code == "QNU_UNRESOLVED_CELLS"


def test_multi_page_row_has_no_invented_single_page():
    model = document()
    model.blocks[2].source_locations.append(QnuSourceLocation(page=3, locator="physical/3/row"))
    canonical, artifact = project(model)
    row = next(unit for unit in resolve_unit_manifest(canonical, artifact).units if unit.id == "qnu:r")
    assert row.page_number is None and len(row.source_locations) == 2


def test_standard_explicit_note_reference_must_resolve():
    model = document()
    model.blocks[1].context_refs = ["missing"]
    with pytest.raises(ValueError, match="Context target"):
        project(model)


def test_self_context_reference_is_rejected_instead_of_silently_dropped():
    model = document()
    model.blocks[3].context_refs = ["n"]
    with pytest.raises(ValueError, match="itself"):
        project(model)


def test_derived_index_is_never_embedded_or_counted_as_source():
    model = document()
    model.blocks.append(QnuBlock(id="index", type="derived_index", body="UNTRUSTED GENERATED TOTAL 999"))
    canonical, artifact = project(model)
    assert "UNTRUSTED" not in canonical and artifact["derived_indexes"][0]["count"] == 1


def test_old_unit_manifest_seal_remains_compatible():
    from app.modules.knowledge.normalization.retrieval_units import build_unit_manifest
    manifest = build_unit_manifest("Old paragraph")
    old = manifest.model_dump()
    old.pop("semantic_annotation_hash")
    for unit in old["units"]:
        for key in ("qnu_block_id", "source_locations", "context_refs", "field_context_refs", "field_usage"):
            unit.pop(key)
    assert manifest_digest(UnitManifest.model_validate(old)) == digest(old)


def test_edited_standard_cannot_change_source_locations_or_approve_itself():
    model = document()
    original = render_qnu_markdown(model, document_id="binding", revision_id="rev")
    text = original.replace('review_status: "unreviewed"', 'review_status: "reviewed"')
    text = text.replace("Áp dụng kèm điều kiện", "Áp dụng có điều kiện")
    edited = document_from_edit(text, model, binding_id="binding", revision_id="rev")
    _, artifact = project(edited)
    assert artifact["review"]["status"] == "required"
    changed = original.replace('locator: "physical/2/table/1"', 'locator: "forged"')
    with pytest.raises(AppException):
        document_from_edit(changed, model, binding_id="binding", revision_id="rev")


@pytest.mark.asyncio
async def test_storage_pair_and_new_revision_projection_are_verified():
    stored = {}
    async def save(path, data):
        stored[path] = data
    storage = SimpleNamespace(save=AsyncMock(side_effect=save), get=AsyncMock(side_effect=lambda path: stored.get(path)),
                              exists=AsyncMock(side_effect=lambda path: path in stored))
    with patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service", storage), patch("app.modules.knowledge.services.qnu_serving.storage_service", storage):
        artifact = await save_qnu_document(document(), document_id="binding", revision_id="rev", snapshot_path=PATH)
        assert artifact["status"] == "ready"
        rev = SimpleNamespace(id="rev", binding_id="binding", origin_file_hash=SHA, snapshot_storage_path=PATH,
            snapshot_metadata={"qnu_markdown": artifact}, citation_metadata={}, parse_provenance={}, quality_report={})
        await prepare_standard_revision(rev)
        assert rev.parse_provenance["canonical_format"] == VERSION
        assert get_source_artifact(rev)["review"]["status"] == "required"
        assert hashlib.sha256(rev.canonical_markdown.encode()).hexdigest() == rev.canonical_hash
        stored[artifact["path"]] += b"tamper"
        with pytest.raises(AppException):
            await load_document(artifact, binding_id="binding", revision_id="rev", origin_hash=SHA, snapshot_path=PATH)


@pytest.mark.asyncio
async def test_failed_standard_remains_unapprovable_not_legacy_ready():
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
    rev = SimpleNamespace(snapshot_metadata={"qnu_markdown": {"status": "failed"}}, parse_provenance={
        "structured_artifact": {"issues": [], "facts": []}}, quality_report={})
    await prepare_standard_revision(rev)
    assert rev.quality_report["overall_status"] == "warning"
    with pytest.raises(AppException):
        source_ingestion_service._apply_review_decision(SimpleNamespace(), rev,
            rev.parse_provenance["structured_artifact"], "approved", "Checked source", "actor")


def test_shared_note_dependencies_are_directed_not_every_row():
    from app.modules.rag.evidence_dependencies import dependency_groups
    from app.modules.rag.evidence_schemas import EvidenceBlock
    def block(unit, start, refs=None):
        return EvidenceBlock(id=unit, unit_id=unit, binding_id="binding", index_revision_id="index", source_revision_id="rev",
            canonical_hash=SHA, title="Source", start=start, end=start + 1, text="text", fact_context={"context_unit_ids": refs or []})
    row1, row2, note = block("r1", 0, ["n"]), block("r2", 2, ["n"]), block("n", 4)
    groups = dependency_groups([row1, row2, note])
    assert {b.id for b in groups["r1"]} == {"r1", "n"}
    assert "n" not in groups


def test_edited_record_fields_rebuild_display_and_cannot_forge_cell_provenance():
    model = document()
    markdown = render_qnu_markdown(model, document_id="binding", revision_id="rev")
    edited = document_from_edit(markdown.replace('raw: "0"', 'raw: "10"'), model, binding_id="binding", revision_id="rev")
    assert "10" in edited.blocks[2].body
    canonical, artifact = project(edited)
    assert "| 10 |" in canonical and any(fact["attribute_value"] == "10" for fact in artifact["facts"])
    with pytest.raises(AppException):
        document_from_edit(markdown.replace('field_sources:', 'field_sources_changed:'), model, binding_id="binding", revision_id="rev")


def test_table_child_note_is_context_not_a_counted_row():
    model = document()
    model.blocks[3].parent_id = "t"
    _, artifact = project(model)
    assert "qnu:n" in artifact["context_graph"]["links"]["qnu:r"]
    assert artifact["derived_indexes"][0]["count"] == 1


def test_nested_list_parent_is_preserved_as_explicit_dependency():
    model = document()
    model.blocks.extend([QnuBlock(id="l", parent_id="s", type="list", body="1. Điều kiện:", source_locations=[]),
        QnuBlock(id="l2", parent_id="l", type="list", body="- Điều kiện con", source_locations=[])])
    _, artifact = project(model)
    assert "qnu:l" in artifact["context_graph"]["links"]["qnu:l2"]


def test_standard_model_context_omits_technical_provenance():
    from app.modules.rag.evidence_context import model_block
    from app.modules.rag.evidence_schemas import EvidenceBlock
    block = EvidenceBlock(id="x", binding_id="b", index_revision_id="i", source_revision_id="s", title="Source",
        start=0, end=4, text="Text", fact_context={"source_locations": [{"bbox": [1, 2, 3, 4]}],
            "context_unit_ids": ["qnu:n"], "qnu_block_id": "p", "source_kind": "paragraph"})
    assert model_block(block)["fact_context"] == {"source_kind": "paragraph"}


def test_standard_edit_roundtrip_preserves_raw_renderer_escaped_metadata():
    model = document()
    model.source.filename = "source{{literal}}.pdf"
    model.blocks[2].attributes["fields"]["c2"]["raw"] = "Tên {{literal}}"
    text = render_qnu_markdown(model, document_id="binding", revision_id="rev")
    edited = document_from_edit(text.replace("Áp dụng kèm điều kiện", "Áp dụng cùng điều kiện"), model,
        binding_id="binding", revision_id="rev")
    assert edited.source.filename == model.source.filename
    assert edited.blocks[2].attributes["fields"]["c2"]["raw"] == "Tên {{literal}}"


@pytest.mark.asyncio
async def test_enumeration_deduplicates_two_representations_not_different_sources():
    from app.modules.rag.combination_enumeration import load_records
    from app.modules.rag.evidence_schemas import EvidenceBlock
    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
    header = "| Mã ngành | Ngành | Tổ hợp 2026 |\n| --- | --- | --- |"
    canonical = EvidenceBlock(id="canon", unit_id="qnu:r", binding_id="binding", index_revision_id="i", source_revision_id="s",
        canonical_hash=SHA, title="Source", start=0, end=80, text="| 0012345 | Công nghệ | (Toán, Lý, Hóa) |", header_context=header)
    reviewed = canonical.model_copy(update={"id": "facts", "origin": "reviewed_fact", "unit_id": None, "fact_id": "f",
        "fact_context": {"source_unit_id": "qnu:r", "entity_name": "Công nghệ", "entity_code": "0012345", "cells": [
            {"attribute": "Mã ngành", "value": "0012345"}, {"attribute": "Tổ hợp 2026", "value": "(Toán, Lý, Hóa)"}]}})
    req = AskRequest(question="Các ngành có Toán, Lý, Hóa", collection_id="c")
    snapshot = RetrievalSnapshot(snapshot_id="snapshot", collection_id="c", binding_revisions={"binding": "i"})
    with patch("app.modules.rag.combination_enumeration.load_published_blocks", AsyncMock(return_value=[canonical])), patch(
        "app.modules.rag.combination_enumeration.reviewed_fact_blocks", AsyncMock(return_value=[reviewed])):
        records, _ = await load_records(None, req, snapshot, ["Toán", "Lý", "Hóa"], False)
        assert len(records) == 1 and records[0].block.origin == "reviewed_fact"


def test_standard_revision_rejects_missing_or_stale_projection():
    revision = SimpleNamespace(
        id="rev", binding_id="binding", canonical_markdown="Old content", canonical_hash="stale",
        page_manifest=[], citation_metadata={}, snapshot_metadata={},
        parse_provenance={"canonical_format": "qnu-rag-projection/v1"},
    )
    with pytest.raises(AppException):
        get_source_artifact(revision)
