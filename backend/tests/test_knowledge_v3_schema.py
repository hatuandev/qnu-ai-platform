"""Unit and regression tests for Knowledge V3 Multi-Embedding schema & ADR-012."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import inspect

from app.modules.documents.models import (
    RepositoryDocument,
    RepositoryFileRevision,
)
from app.modules.documents.schemas import (
    RepositoryFileRevisionItem,
    RepositoryFileRevisionResponse,
)
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunkSet,
    KnowledgeCollection,
    KnowledgeImportBatch,
    KnowledgeImportItem,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.schemas import (
    CandidateListResponse,
    KnowledgeChunkSetResponse,
    KnowledgeImportBatchCreateRequest,
    KnowledgeImportBatchResponse,
    KnowledgeImportItemResponse,
    KnowledgeSourceRevisionResponse,
    RepositoryCandidateItem,
)


def test_repository_file_revision_mapper():
    """Verify SQLAlchemy mapper initialization for RepositoryFileRevision."""
    mapper = inspect(RepositoryFileRevision)
    assert mapper is not None
    assert mapper.columns["id"].type.length == 64
    assert mapper.columns["document_id"].type.length == 64
    assert mapper.columns["source_hash"].type.length == 64

    # Test eager instance creation
    file_rev = RepositoryFileRevision(
        document_id="rep_doc_123",
        revision_no=1,
        source_file_name="thong_bao_tuyen_sinh.pdf",
        source_file_type="pdf",
        source_size_bytes=10240,
        source_hash="sha256_mock_hash",
        source_storage_path="documents/tenant_qnu/workspace_qnu/originals/sha256_mock_hash/thong_bao_tuyen_sinh.pdf",
    )
    assert file_rev.id.startswith("file_rev_")
    assert file_rev.revision_no == 1
    assert file_rev.created_at is not None


def test_knowledge_source_revision_mapper():
    """Verify SQLAlchemy mapper initialization for KnowledgeSourceRevision."""
    mapper = inspect(KnowledgeSourceRevision)
    assert mapper is not None
    assert mapper.columns["id"].type.length == 64
    assert mapper.columns["binding_id"].type.length == 64
    assert mapper.columns["origin_document_id"].type.length == 64

    ks_rev = KnowledgeSourceRevision(
        binding_id="bnd_123",
        revision_no=1,
        origin_document_id="rep_doc_123",
        origin_file_hash="sha256_mock_hash",
        snapshot_storage_path="knowledge/tenant_qnu/workspace_qnu/snapshots/doc_123.pdf",
    )
    assert ks_rev.id.startswith("ks_rev_")
    assert ks_rev.status == "queued"
    assert ks_rev.lock_version == 1
    assert isinstance(ks_rev.page_manifest, list)
    assert isinstance(ks_rev.citation_metadata, dict)


def test_knowledge_chunk_set_mapper():
    """Verify SQLAlchemy mapper initialization for KnowledgeChunkSet."""
    mapper = inspect(KnowledgeChunkSet)
    assert mapper is not None
    assert mapper.columns["id"].type.length == 64
    assert mapper.columns["source_revision_id"].type.length == 64
    assert mapper.columns["config_hash"].type.length == 64

    chunk_set = KnowledgeChunkSet(
        source_revision_id="ks_rev_123",
        chunk_strategy="ClauseBasedChunker",
        chunk_config={"chunk_size": 1000, "overlap": 150},
        config_hash="cfg_hash_mock",
    )
    assert chunk_set.id.startswith("chk_set_")
    assert chunk_set.status == "building"
    assert chunk_set.chunk_count == 0


def test_knowledge_import_batch_and_item_mapper():
    """Verify mapper initialization for KnowledgeImportBatch and KnowledgeImportItem."""
    batch_mapper = inspect(KnowledgeImportBatch)
    assert batch_mapper is not None
    assert batch_mapper.columns["id"].type.length == 64

    item_mapper = inspect(KnowledgeImportItem)
    assert item_mapper is not None
    assert item_mapper.columns["id"].type.length == 64
    assert item_mapper.columns["batch_id"].type.length == 64

    batch = KnowledgeImportBatch(
        collection_id="col_tuyen_sinh",
        parser_profile="standard",
    )
    assert batch.id.startswith("imp_batch_")
    assert batch.status == "queued"
    assert batch.total_count == 0

    item = KnowledgeImportItem(
        batch_id=batch.id,
        origin_document_id="rep_doc_123",
        origin_file_hash="hash_123",
        origin_title="Tài liệu mẫu",
        origin_file_name="sample.pdf",
        origin_file_type="pdf",
    )
    assert item.id.startswith("imp_item_")
    assert item.phase == "snapshot"
    assert item.status == "queued"


def test_additive_relationship_extensions():
    """Verify additive relationship attributes on KnowledgeBinding and KnowledgeIndexRevision."""
    binding_mapper = inspect(KnowledgeBinding)
    assert "active_source_revision_id" in binding_mapper.columns
    assert "active_source_revision" in binding_mapper.relationships
    assert "source_revisions" in binding_mapper.relationships

    idx_mapper = inspect(KnowledgeIndexRevision)
    assert "source_revision_v2_id" in idx_mapper.columns
    assert "chunk_set_id" in idx_mapper.columns
    assert "source_revision_v2" in idx_mapper.relationships
    assert "chunk_set" in idx_mapper.relationships

    col_mapper = inspect(KnowledgeCollection)
    assert "import_batches" in col_mapper.relationships

    repo_doc_mapper = inspect(RepositoryDocument)
    assert "file_revisions" in repo_doc_mapper.relationships


def test_pydantic_schemas_v3_validation():
    """Verify serialization and validation of Pydantic DTOs for Knowledge V3."""
    # 1. Batch create request
    batch_req = KnowledgeImportBatchCreateRequest(
        document_ids=["rep_doc_1", "rep_doc_2"],
        parser_profile="vision_ocr",
        chunk_strategy="ClauseBasedChunker",
        chunk_config={"chunk_size": 800},
    )
    assert len(batch_req.document_ids) == 2
    assert batch_req.parser_profile == "vision_ocr"

    # 2. Candidate item
    now = datetime.now(UTC)
    cand_item = RepositoryCandidateItem(
        document_id="rep_doc_1",
        title="Đề án tuyển sinh 2026",
        file_name="de_an_2026.pdf",
        file_type="pdf",
        file_size_bytes=204800,
        file_hash="hash_de_an_2026",
        source_state="not_imported",
        vector_state="not_indexed",
        selectable=True,
    )
    assert cand_item.source_state == "not_imported"
    assert cand_item.selectable is True

    # 3. Candidate list response
    cand_resp = CandidateListResponse(
        items=[cand_item],
        total=1,
        vector_generation_id="vg_active",
    )
    assert cand_resp.total == 1

    # 4. Source revision response
    src_rev_dto = KnowledgeSourceRevisionResponse(
        id="ks_rev_123",
        binding_id="bnd_123",
        revision_no=1,
        origin_document_id="rep_doc_1",
        origin_file_hash="hash_de_an_2026",
        status="ready",
        created_at=now,
        updated_at=now,
    )
    assert src_rev_dto.status == "ready"

    # 5. Chunk set response
    chunk_set_dto = KnowledgeChunkSetResponse(
        id="chk_set_123",
        source_revision_id="ks_rev_123",
        chunk_strategy="ClauseBasedChunker",
        chunk_config={"chunk_size": 1000},
        config_hash="cfg_hash_123",
        chunk_count=12,
        fact_count=3,
        status="ready",
        created_at=now,
        updated_at=now,
    )
    assert chunk_set_dto.chunk_count == 12

    # 6. File revision DTOs
    file_rev_item = RepositoryFileRevisionItem(
        id="file_rev_123",
        document_id="rep_doc_1",
        revision_no=1,
        source_file_name="doc.pdf",
        source_file_type="pdf",
        source_size_bytes=1024,
        source_hash="sha256_mock",
        source_storage_path="path/to/doc.pdf",
        created_at=now,
    )
    file_rev_resp = RepositoryFileRevisionResponse(
        document_id="rep_doc_1",
        items=[file_rev_item],
        total=1,
    )
    assert file_rev_resp.total == 1

    # 7. Import batch & item response
    item_dto = KnowledgeImportItemResponse(
        id="imp_item_123",
        batch_id="imp_batch_123",
        origin_document_id="rep_doc_1",
        origin_title="Tài liệu",
        origin_file_name="doc.pdf",
        origin_file_type="pdf",
        origin_file_hash="sha256_mock",
        phase="snapshot",
        status="queued",
        created_at=now,
        updated_at=now,
    )
    batch_resp = KnowledgeImportBatchResponse(
        id="imp_batch_123",
        collection_id="col_123",
        parser_profile="standard",
        chunk_strategy="ClauseBasedChunker",
        total_count=1,
        queued_count=1,
        processing_count=0,
        review_required_count=0,
        succeeded_count=0,
        failed_count=0,
        skipped_count=0,
        status="queued",
        created_at=now,
        updated_at=now,
        items=[item_dto],
    )
    assert batch_resp.total_count == 1
    assert len(batch_resp.items) == 1


def test_alembic_migration_metadata():
    """Verify that the Alembic migration script for ADR-012 exists, is valid and connected."""
    migration_file = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20261010_decouple_storage_and_knowledge_v3.py"
    )
    assert migration_file.exists(), "Migration file 20261010_decouple_storage_and_knowledge_v3.py must exist."

    # Dynamically import the module to verify revision linkage
    spec = importlib.util.spec_from_file_location("migration_v3", str(migration_file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "20261010_decouple_storage_and_knowledge_v3"
    assert mod.down_revision == "20261010_knowledge_group_sources"
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")
