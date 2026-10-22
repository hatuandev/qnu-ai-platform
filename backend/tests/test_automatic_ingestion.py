"""Automatic content readiness is independent of optional semantic proposals."""
import copy
import hashlib
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from docx import Document
from docx.oxml import OxmlElement

import tests.test_semantic_lifecycle as lifecycle
from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.parsers import get_document_parser
from app.modules.knowledge.parsers.docling_structure import build_qnu_structured_document
from app.modules.knowledge.services.automatic_ingestion import content_readiness, evaluate_content
from app.modules.knowledge.services.qnu_docx_artifacts import save_qnu_document
from app.modules.knowledge.services.qnu_serving import prepare_standard_revision
from app.modules.knowledge.services.semantic_annotations import SemanticAnnotations
from app.modules.knowledge.services.source_artifact import get_structured_review_state

storage, database = lifecycle.storage, lifecycle.database


@pytest.fixture(autouse=True)
def offline_wiki_provider():
    # These tests verify native content/indexing. Wiki compilation has separate
    # adapter and persistence tests; its optional provider must not perform I/O
    # or borrow application pool connections across pytest event loops here.
    with patch("app.modules.knowledge.services.wiki_build.model_generator", AsyncMock(
        side_effect=AppException("TEST provider unavailable", code="KNOWLEDGE_WIKI_MODEL_REQUIRED", status_code=409)
    )):
        yield


async def native_pair(database, value="12"):
    document = Document()
    document.add_paragraph("Điều kiện bổ sung chỉ là nội dung nguồn để đọc; chưa xác minh quan hệ với bảng bên dưới.")
    table = document.add_table(rows=2, cols=3)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for cell, text in zip(table.rows[0].cells, ["Mã", "Chương trình", "Số lượng"], strict=True):
        cell.text = text
    for cell, text in zip(table.rows[1].cells, ["0012", "Chương trình mẫu", value], strict=True):
        cell.text = text
    buffer = BytesIO()
    document.save(buffer)
    raw = buffer.getvalue()
    parsed = await get_document_parser("docx").parse(raw, "independent.docx")
    structured = build_qnu_structured_document(parsed.docling_document, header_evidence=parsed.docx_header_evidence,
        filename="independent.docx", sha256=hashlib.sha256(raw).hexdigest(), projection_markdown=parsed.raw_text,
        page_ranges=[], render_sha256=None, render_page_count=None)
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        rev.origin_file_hash = structured.source.sha256
        await database.storage.save(rev.snapshot_storage_path, raw)
        ref = await save_qnu_document(structured, document_id=rev.binding_id, revision_id=rev.id,
            snapshot_path=rev.snapshot_storage_path)
        assert ref["status"] == "ready"
        rev.snapshot_metadata, rev.parse_provenance, rev.quality_report = {"qnu_markdown": ref}, {}, {"overall_status": "passed"}
        await prepare_standard_revision(rev, automatic=True)
        rev.status = "ready" if rev.quality_report["overall_status"] == "passed" else "review_required"
        if rev.status == "ready":
            binding = await db.get(KnowledgeBinding, rev.binding_id)
            binding.active_source_revision_id, binding.status = rev.id, "active"
        await db.commit()
        return rev


async def test_clean_docx_is_auto_ready_without_human_semantic_approval(database):
    rev = await native_pair(database)
    assert content_readiness(rev)["status"] == "AUTO_READY"
    assert rev.quality_report["overall_status"] == "passed"
    assert not get_structured_review_state(rev)[1]
    assert not rev.parse_provenance.get("semantic_store")


async def test_wiki_policy_is_sealed_before_automatic_readiness_and_cannot_change_silently(database):
    rev = await native_pair(database)
    assert rev.parse_provenance["knowledge_wiki_policy"]["enabled"]
    assert content_readiness(rev)["status"] == "AUTO_READY"
    provenance = copy.deepcopy(rev.parse_provenance)
    provenance["knowledge_wiki_policy"]["max_calls"] += 1
    rev.parse_provenance = provenance
    report = content_readiness(rev)
    assert report["status"] == "NEEDS_ATTENTION"
    assert report["blockers"][0]["reason_code"] == "CONTENT_READINESS_STALE"


async def test_optional_pending_assertion_does_not_block_verified_content(database):
    from app.modules.knowledge.services.chunk_set_service import chunk_set_service
    from app.modules.knowledge.services.semantic_evidence import make_binding

    rev = await native_pair(database)
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rev.id)
        before = copy.deepcopy(lifecycle.artifact_of(rev))
        note = next(u for u in before["retrieval_units"]["units"] if u["kind"] == "paragraph" and not u["is_container"])
        binding = make_binding(before, note["id"], 0, len(note["text"]))
        await lifecycle.stage(rev, SemanticAnnotations(notes=[{"note_unit_id": note["id"], "evidence_quote": note["text"],
            "evidence_binding": binding, "table_id": before["tables"][0]["id"], "scope": "table", "assertion_version": 1}]))
        await db.commit()
        assert content_readiness(rev)["status"] == "AUTO_READY"
        assert not get_structured_review_state(rev)[1]
        assert lifecycle.artifact_of(rev)["semantic_annotations"]["status"] == "proposed"
        assert all(lifecycle.artifact_of(rev)[k] == before[k] for k in ["tables", "facts", "context_graph", "retrieval_units"])
        chunks = await chunk_set_service.get_or_create_chunk_set(db, rev.id)
        assert chunks.status == "ready" and chunks.chunk_count > 0
        assert "semantic_store" not in rev.parse_provenance


async def test_raw_uninterpreted_symbol_is_a_limitation_not_a_numeric_fact(database):
    rev = await native_pair(database, "/")
    report = content_readiness(rev)
    assert report["status"] == "READY_WITH_LIMITATIONS"
    assert report["limitations"][0]["raw"] == "/"
    assert report["limitations"][0]["basis"] == "literal_uninterpreted"
    artifact = lifecycle.artifact_of(rev)
    field = artifact["tables"][0]["row_fields"][0][-1]
    assert field["raw"] == "/" and field["state"] == "ambiguous"
    assert not any(f["raw_data"].get("column_id") == field["column_id"] for f in artifact["facts"])


@pytest.mark.parametrize("change", ["table", "quality", "canonical"])
async def test_content_certificate_invalidates_on_material_changes(database, change):
    rev = await native_pair(database)
    if change == "table": lifecycle.artifact_of(rev)["tables"][0]["row_fields"][0][-1]["raw"] = "999"
    elif change == "quality": rev.quality_report = {"overall_status": "failed"}
    else: rev.canonical_hash = "0" * 64
    assert content_readiness(rev)["status"] == "NEEDS_ATTENTION"
    assert get_structured_review_state(rev)[1]


async def test_unreadable_or_missing_table_remains_blocking(database):
    rev = await native_pair(database)
    artifact = copy.deepcopy(lifecycle.artifact_of(rev))
    artifact["tables"][0]["row_fields"][0][-1]["state"] = "unreadable"
    assert evaluate_content(artifact, rev.quality_report)["status"] == "NEEDS_ATTENTION"
    assert evaluate_content(lifecycle.artifact_of(rev), {"overall_status": "passed", "warning_flags": ["tables_detected_but_missing_in_markdown"]})["status"] == "NEEDS_ATTENTION"


async def test_automatic_unknown_builds_staging_vectors_without_publishing(database):
    from unittest.mock import AsyncMock, patch

    from sqlalchemy import select

    from app.modules.knowledge.models import (
        KnowledgeCollection,
        KnowledgeFact,
        KnowledgeVectorGeneration,
    )
    from app.modules.knowledge.services.vector_generation_service import vector_generation_service

    rev = await native_pair(database, "/")
    collected = []
    async def index_chunks(**kwargs):
        collected.extend(kwargs["chunks"])
        return len(kwargs["chunks"])
    async with database.factory() as db:
        generation = KnowledgeVectorGeneration(collection_id=database.ids[0], embedding_model="synthetic-embedding",
            provider_id="TEST-only", qdrant_collection_name="test-automatic", config_hash="a" * 64,
            embedding_dimension=3, status="building")
        db.add(generation)
        await db.commit()
        before = (await db.get(KnowledgeCollection, database.ids[0])).index_epoch
        with patch("app.modules.knowledge.services.vector_generation_service.vector_indexer.index_chunks", side_effect=index_chunks), patch(
                "app.modules.knowledge.services.vector_generation_service.vector_indexer.verify_index_revision_parity",
                AsyncMock(side_effect=lambda **kw: (True, "TEST adapter parity", len(kw["expected_points"])))):
            index = await vector_generation_service.build_generation_for_source(db, *database.ids[:2], generation.id,
                expected_source_revision_id=rev.id)
        assert index.status == "ready" and index.source_revision_v2_id == rev.id
        wiki = index.parity_report["knowledge_wiki"]
        assert wiki["status"] == "unavailable" and wiki["pages"] == []
        assert wiki["failure_code"] == "KNOWLEDGE_WIKI_MODEL_REQUIRED"
        assert collected and all(c["is_retrievable"] is False and c["document_status"] == "staging" for c in collected)
        binding = await db.get(KnowledgeBinding, database.ids[1])
        assert binding.active_index_revision_id is None
        assert (await db.get(KnowledgeCollection, database.ids[0])).index_epoch == before
        facts = (await db.scalars(select(KnowledgeFact).where(KnowledgeFact.index_revision_id == index.id))).all()
        unknown_column = lifecycle.artifact_of(await db.get(KnowledgeSourceRevision, rev.id))["tables"][0]["row_fields"][0][-1]["column_id"]
        assert not any(f.raw_data.get("column_id") == unknown_column for f in facts)
        from app.modules.knowledge.models import KnowledgeChunk
        from app.modules.rag.source_rows import source_rows

        chunks = (await db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.index_revision_id == index.id))).all()
        current = await db.get(KnowledgeSourceRevision, rev.id)
        rows = source_rows(current, index, binding, chunks, "Chương trình mẫu mã 0012")
        assert rows, "The canonical row must remain available to candidate evidence."
        unknown = next(f for f in rows[0].metadata["row_fields"] if f["column_id"] == unknown_column)
        assert unknown["raw"] == "/" and unknown["state"] == "ambiguous"


async def test_source_bytes_tamper_blocks_index_even_when_cached_marker_is_unchanged(database):
    from app.core.exceptions import AppException
    from app.modules.knowledge.services.chunk_set_service import chunk_set_service

    rev = await native_pair(database)
    await database.storage.save(rev.snapshot_storage_path, b"tampered TEST bytes")
    async with database.factory() as db:
        with pytest.raises(AppException) as error:
            await chunk_set_service.get_or_create_chunk_set(db, rev.id)
        assert error.value.code == "SOURCE_HASH_MISMATCH"


async def test_native_digital_pdf_is_ready_without_semantic_model_or_ocr(database):
    from unittest.mock import AsyncMock, patch

    import pymupdf

    from app.modules.documents.quality_gate import evaluate_revision_quality
    from app.modules.knowledge.parsers.pdf_inspector import PDFInspectionResult
    from app.modules.knowledge.services.qnu_docx_artifacts import build_qnu_markdown_artifact
    from app.modules.knowledge.services.source_extraction import extract_source

    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_textbox(pymupdf.Rect(50, 60, 540, 700),
            "Independent digital PDF with source identifiers and complete native text.\n" * 6)
        raw = pdf.tobytes()
    with patch("app.modules.knowledge.parsers.inspector_process.inspect_pdf_safely", AsyncMock(return_value=PDFInspectionResult())), patch(
            "app.modules.knowledge.services.source_extraction.prepare_header_rescue", return_value=None), patch(
            "app.modules.knowledge.services.source_extraction.OCRService.extract_document", AsyncMock()) as ocr:
        extraction = await extract_source(AsyncMock(), raw, "independent.pdf", "pdf", "standard", None, "TEST")
    ocr.assert_not_awaited()
    assert extraction.qnu_document is not None
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        rev.origin_file_hash = hashlib.sha256(raw).hexdigest()
        await database.storage.save(rev.snapshot_storage_path, raw)
        ref = await build_qnu_markdown_artifact(extraction=extraction, document_id=rev.binding_id, revision_id=rev.id,
            title="Independent PDF TEST", snapshot_path=rev.snapshot_storage_path)
        assert ref["status"] == "ready"
        rev.snapshot_metadata, rev.parse_provenance = {"qnu_markdown": ref}, {}
        rev.quality_report = evaluate_revision_quality(markdown=extraction.raw_text, page_count=1, tables_count=0, file_size_bytes=len(raw))
        await prepare_standard_revision(rev, automatic=True)
        assert content_readiness(rev)["status"] == "AUTO_READY"


@pytest.mark.parametrize("value,expected,basis", [("", "READY_WITH_LIMITATIONS", "source_blank"), ("0", "AUTO_READY", None)])
async def test_source_blank_and_actual_zero_remain_distinct(database, value, expected, basis):
    rev = await native_pair(database, value)
    report = content_readiness(rev)
    assert report["status"] == expected
    assert lifecycle.artifact_of(rev)["tables"][0]["row_fields"][0][-1]["raw"] == value
    if basis: assert report["limitations"][0]["basis"] == basis
