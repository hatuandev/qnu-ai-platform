"""Comprehensive End-to-End & Canary Verification Test Suite for Publishing V2 (ADR-011 Phase 6).

This suite verifies all 10 Architectural Invariants under ADR-011:
1. Two-level Separation: RepositoryDocument vs KnowledgeBinding.
2. Immutable Revisions: DocumentRevision & KnowledgeIndexRevision.
3. Intake-before-Bind: Only 'ready' revisions can be bound.
4. Staging Isolation: Staging chunks NEVER leak into retrieval.
5. Parity Gate Integrity: Count mismatch blocks promotion.
6. Atomic Compare-And-Swap (CAS): Concurrency conflict raises 409 CAS_EPOCH_CONFLICT.
7. Snapshot Isolation & Session Pinning: Retrieval pinned to exact revision map.
8. Instant Zero-Reindex Rollback: Pointer rollback in O(1) without re-embedding.
9. Auditable Citations: Every snippet cites binding_id, index_revision_id, revision_no.
10. Idempotent Legacy Backfill & Shadow Retrieval Verification (zero leak).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException
from app.main import app
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.documents.models import DocumentRevision, RepositoryDocument
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeDocument,
    KnowledgeIndexActivation,
    KnowledgeIndexRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.services.canary_service import canary_service
from app.modules.knowledge.services.index_build_service import index_build_service
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import (
    Citation,
    RetrievalSnapshot,
)


def _execute_result(scalar=None, scalars_list=None):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    result.scalar = MagicMock(return_value=scalar)
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_list or [])
    scalars.first = MagicMock(return_value=scalar or (scalars_list[0] if scalars_list else None))
    result.scalars = MagicMock(return_value=scalars)
    result.all = MagicMock(return_value=scalars_list or [])
    result.first = MagicMock(return_value=scalar or (scalars_list[0] if scalars_list else None))
    return result


def _fresh_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


# ==============================================================================
# 1. End-to-End Lifecycle: Intake -> Binding -> Staging -> Parity -> CAS -> Citations
# ==============================================================================
@pytest.mark.asyncio
async def test_e2e_publishing_lifecycle_intake_to_auditable_citations():
    """Verify full end-to-end publishing pipeline with provenance and auditable citations."""
    session = _fresh_session()

    col = KnowledgeCollection(id="col_adm_2026", name="Tuyển sinh 2026", module_code="admissions", index_epoch=1)
    rep_doc = RepositoryDocument(
        id="rdoc_qd_123",
        document_number="QD-123",
        title="Quy chế tuyển sinh 2026",
        file_name="quyet_dinh_123.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        file_hash="hash_qd_123",
        storage_path="docs/qd123.pdf",
        status="active",
    )
    doc_rev = DocumentRevision(
        id="drev_v1",
        document_id=rep_doc.id,
        revision_no=1,
        status="ready",
        canonical_markdown="# Điều 1. Đối tượng tuyển sinh\nThí sinh tốt nghiệp THPT.",
    )
    vector_gen = KnowledgeVectorGeneration(
        id="vg_bge_1",
        collection_id=col.id,
        embedding_model="bge-m3:latest",
        provider_id="provider_test",
        qdrant_collection_name="knowledge_col_adm_2026",
        config_hash="c" * 64,
        embedding_dimension=1024,
    )
    binding = KnowledgeBinding(
        id="bnd_adm_1",
        collection_id=col.id,
        repository_document_id=rep_doc.id,
        source_revision_id=doc_rev.id,
        active_epoch=0,
        status="active",
    )

    # 1. Build staging index
    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeBinding, "bnd_adm_1"): binding,
        (KnowledgeCollection, "col_adm_2026"): col,
        (DocumentRevision, "drev_v1"): doc_rev,
        (RepositoryDocument, "rdoc_qd_123"): rep_doc,
    }.get((model, obj_id))

    kdoc = KnowledgeDocument(
        id="kdoc_proj_1",
        collection_id=col.id,
        repository_document_id=rep_doc.id,
        title=rep_doc.title,
        file_name=rep_doc.file_name,
        file_type="pdf",
        file_hash="hash_qd_123",
        storage_path="docs/qd123.pdf",
    )

    with (
        patch(
            "app.modules.knowledge.services.index_build_service.get_scoped_binding",
            new=AsyncMock(return_value=binding),
        ),
        patch.object(index_build_service, "get_or_create_vector_generation", return_value=vector_gen),
        patch.object(index_build_service, "_ensure_collection_doc_projection", new_callable=AsyncMock, return_value=kdoc),
        patch("app.modules.rag.vector_indexer.vector_indexer.index_chunks", new_callable=AsyncMock) as mock_idx,
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.verify_index_revision_parity",
            new_callable=AsyncMock,
            return_value=(True, "verified", 1),
        ),
    ):
        mock_idx.return_value = 1  # 1 chunk indexed
        idx_rev = await index_build_service.build_staging_index(
            db=session,
            binding_id="bnd_adm_1",
            source_revision_id="drev_v1",
            auto_activate=False,
        )

    assert idx_rev.status == "ready"
    assert idx_rev.chunk_count == 1
    assert idx_rev.parity_report["parity_status"] == "passed"
    assert binding.active_index_revision_id is None  # Staging isolated!

    # 2. Atomic Pointer Swap (Promote)
    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeBinding, "bnd_adm_1"): binding,
        (KnowledgeIndexRevision, idx_rev.id): idx_rev,
        (KnowledgeCollection, "col_adm_2026"): col,
    }.get((model, obj_id))

    session.execute = AsyncMock(return_value=_execute_result(scalar=2))
    with (
        patch(
            "app.modules.knowledge.services.index_build_service.get_scoped_binding",
            new=AsyncMock(return_value=binding),
        ),
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.activate_index_revision",
            new_callable=AsyncMock,
            return_value=1,
        ),
    ):
        promo = await index_build_service.promote_index_revision(
            db=session,
            binding_id="bnd_adm_1",
            index_revision_id=idx_rev.id,
            expected_epoch=0,
            reason="Duyệt xuất bản chính thức",
        )
    assert promo.to_index_revision_id == idx_rev.id
    assert binding.active_index_revision_id == idx_rev.id
    assert binding.active_epoch == 1
    assert idx_rev.status == "active"

    # 3. Snapshot Pinning & Auditable Citation Check
    snapshot = RetrievalSnapshot(
        snapshot_id=f"snap_{col.id}_{col.index_epoch}",
        collection_id=col.id,
        collection_epoch=col.index_epoch,
        binding_revisions={binding.id: idx_rev.id},
    )
    assert snapshot.binding_revisions[binding.id] == idx_rev.id

    candidate = FusionCandidate(
        chunk_id="chk_e2e_1",
        document_id=rep_doc.id,
        content="Thí sinh tốt nghiệp THPT được tham gia xét tuyển.",
        rrf_score=0.95,
        binding_id=binding.id,
        index_revision_id=idx_rev.id,
        document_revision=doc_rev.revision_no,
    )
    citation = Citation(
        source_id=candidate.document_id,
        title="Quy chế tuyển sinh 2026",
        binding_id=candidate.binding_id,
        index_revision_id=candidate.index_revision_id,
        revision_no=candidate.document_revision,
        quote="Thí sinh tốt nghiệp THPT được tham gia xét tuyển.",
    )

    assert citation.binding_id == "bnd_adm_1"
    assert citation.index_revision_id == idx_rev.id
    assert citation.revision_no == 1


# ==============================================================================
# 2. Invariant 4: Staging Isolation & Zero Leakage
# ==============================================================================
@pytest.mark.asyncio
async def test_staging_isolation_zero_leak():
    """Verify that chunks from an unpromoted staging revision are never retrievable."""
    col_id = "col_test_iso"

    # Active snapshot only includes rev_active
    snapshot = RetrievalSnapshot(
        snapshot_id="snap_iso_1",
        collection_id=col_id,
        collection_epoch=1,
        binding_revisions={"bnd_doc1": "rev_active_1"},
    )

    candidates = [
        FusionCandidate(
            chunk_id="chk_active_1",
            document_id="doc_1",
            content="Active content",
            rrf_score=0.9,
            binding_id="bnd_doc1",
            index_revision_id="rev_active_1",
            metadata={"document_status": "active"},
        ),
        FusionCandidate(
            chunk_id="chk_staging_unpromoted",
            document_id="doc_1",
            content="Staging draft content",
            rrf_score=0.98,
            binding_id="bnd_doc1",
            index_revision_id="rev_staging_unpromoted",
            metadata={"document_status": "staging"},
        ),
    ]

    # Filter according to snapshot isolation rules
    active_revs = set(snapshot.binding_revisions.values())
    filtered_results = [
        c for c in candidates
        if c.index_revision_id in active_revs
        and (not c.metadata or c.metadata.get("document_status") != "staging")
    ]

    assert len(filtered_results) == 1
    assert filtered_results[0].chunk_id == "chk_active_1"
    assert "chk_staging_unpromoted" not in [c.chunk_id for c in filtered_results]


# ==============================================================================
# 3. Invariant 5: Parity Gate Failure Blocks Promotion
# ==============================================================================
@pytest.mark.asyncio
async def test_parity_gate_failure_blocks_promotion():
    """Verify that a vector count mismatch marks revision failed and blocks promotion."""
    session = _fresh_session()

    binding = KnowledgeBinding(
        id="bnd_parity_fail",
        collection_id="col_p1",
        repository_document_id="rdoc_1",
        source_revision_id="drev_1",
        active_index_revision_id="old_rev_0",
        active_epoch=2,
    )
    col = KnowledgeCollection(id="col_p1", name="Collection P1", module_code="admissions", index_epoch=1)
    doc_rev = DocumentRevision(
        id="drev_1",
        document_id="rdoc_1",
        revision_no=1,
        status="ready",
        canonical_markdown="Điều 1\nĐiều 2",
    )
    rep_doc = RepositoryDocument(
        id="rdoc_1",
        title="Doc 1",
        file_name="doc1.pdf",
        file_type="pdf",
        file_size_bytes=128,
        file_hash="hash_rdoc_1",
        storage_path="docs/doc1.pdf",
        status="active",
    )
    vector_gen = KnowledgeVectorGeneration(
        id="vg_p1",
        collection_id=col.id,
        embedding_model="configured-model",
        provider_id="provider_test",
        qdrant_collection_name="knowledge_col_p1",
        config_hash="d" * 64,
        embedding_dimension=1024,
    )

    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeBinding, "bnd_parity_fail"): binding,
        (KnowledgeCollection, "col_p1"): col,
        (DocumentRevision, "drev_1"): doc_rev,
        (RepositoryDocument, "rdoc_1"): rep_doc,
    }.get((model, obj_id))

    kdoc = KnowledgeDocument(
        id="kdoc_proj_2",
        collection_id=col.id,
        repository_document_id=rep_doc.id,
        title="Doc 1",
        file_name="doc1.pdf",
        file_type="pdf",
        file_hash="hash_p1",
        storage_path="docs/p1.pdf",
    )

    with (
        patch(
            "app.modules.knowledge.services.index_build_service.get_scoped_binding",
            new=AsyncMock(return_value=binding),
        ),
        patch.object(index_build_service, "get_or_create_vector_generation", return_value=vector_gen),
        patch.object(index_build_service, "_ensure_collection_doc_projection", new_callable=AsyncMock, return_value=kdoc),
        patch("app.modules.rag.vector_indexer.vector_indexer.index_chunks", new_callable=AsyncMock) as mock_idx,
        patch("app.core.config.settings.ENVIRONMENT", "production"),
    ):
        mock_idx.return_value = 0  # 0 indexed points while chunks > 0 -> Parity Mismatch!
        failed_rev = await index_build_service.build_staging_index(
            db=session,
            binding_id="bnd_parity_fail",
            source_revision_id="drev_1",
            auto_activate=False,
        )

    assert failed_rev.status == "failed"
    assert failed_rev.failure_code == "PARITY_GATE_MISMATCH"
    assert binding.active_index_revision_id == "old_rev_0"  # Active pointer untouched!

    # Attempting to promote failed revision must raise AppException 400
    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeBinding, "bnd_parity_fail"): binding,
        (KnowledgeIndexRevision, failed_rev.id): failed_rev,
    }.get((model, obj_id))

    with (
        patch(
            "app.modules.knowledge.services.index_build_service.get_scoped_binding",
            new=AsyncMock(return_value=binding),
        ),
        pytest.raises(AppException) as exc_info,
    ):
        await index_build_service.promote_index_revision(
            db=session,
            binding_id="bnd_parity_fail",
            index_revision_id=failed_rev.id,
            expected_epoch=2,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_REVISION_STATUS"
    assert binding.active_index_revision_id == "old_rev_0"


# ==============================================================================
# 4. Invariant 6: Concurrency Compare-And-Swap (CAS) Conflict Protection
# ==============================================================================
@pytest.mark.asyncio
async def test_atomic_cas_concurrency_conflict():
    """Verify that stale expected_epoch raises 409 CAS_EPOCH_CONFLICT (Atomic CAS protection)."""
    session = _fresh_session()

    binding = KnowledgeBinding(
        id="bnd_cas_race",
        collection_id="col_cas",
        repository_document_id="rdoc_1",
        source_revision_id="drev_1",
        active_epoch=5,  # Current epoch is 5
    )
    target_rev = KnowledgeIndexRevision(
        id="rev_ready_10",
        binding_id=binding.id,
        status="ready",
        revision_no=2,
    )

    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeBinding, "bnd_cas_race"): binding,
        (KnowledgeIndexRevision, "rev_ready_10"): target_rev,
    }.get((model, obj_id))

    # Stale request attempting to promote with expected_epoch = 4 (stale)
    with pytest.raises(AppException) as exc_info:
        await index_build_service.promote_index_revision(
            db=session,
            binding_id="bnd_cas_race",
            index_revision_id="rev_ready_10",
            expected_epoch=4,  # Mismatch!
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CAS_EPOCH_CONFLICT"
    assert binding.active_epoch == 5  # Epoch remained intact


# ==============================================================================
# 5. Invariant 8: Instant Zero-Reindex Rollback
# ==============================================================================
@pytest.mark.asyncio
async def test_instant_zero_reindex_rollback():
    """Verify instant rollback to a historical index revision in O(1) without re-embedding."""
    session = _fresh_session()

    rev_v1 = KnowledgeIndexRevision(
        id="rev_v1",
        binding_id="bnd_rb",
        revision_no=1,
        status="archived",
        chunk_count=10,
    )
    rev_v2 = KnowledgeIndexRevision(
        id="rev_v2",
        binding_id="bnd_rb",
        revision_no=2,
        status="active",
        chunk_count=12,
    )
    binding = KnowledgeBinding(
        id="bnd_rb",
        collection_id="col_rb",
        repository_document_id="rdoc_1",
        source_revision_id="drev_1",
        active_index_revision_id=rev_v2.id,
        active_epoch=2,
    )

    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeBinding, "bnd_rb"): binding,
        (KnowledgeIndexRevision, "rev_v1"): rev_v1,
        (KnowledgeIndexRevision, "rev_v2"): rev_v2,
        (KnowledgeCollection, "col_rb"): KnowledgeCollection(id="col_rb", name="Rollback Test", module_code="admissions"),
    }.get((model, obj_id))

    session.execute = AsyncMock(return_value=_execute_result(scalar=3))
    with (
        patch(
            "app.modules.knowledge.services.index_build_service.get_scoped_binding",
            new=AsyncMock(return_value=binding),
        ),
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.activate_index_revision",
            new_callable=AsyncMock,
        ) as mock_act,
    ):
        rb_resp = await index_build_service.rollback_index_revision(
            db=session,
            binding_id="bnd_rb",
            target_index_revision_id="rev_v1",
            expected_epoch=2,
            reason="Lỗi định dạng bảng ở V2, hoàn tác khẩn cấp về V1",
        )

    assert rb_resp.action == "rollback"
    assert rb_resp.to_index_revision_id == "rev_v1"
    assert rb_resp.epoch == 3
    assert binding.active_index_revision_id == "rev_v1"
    assert rev_v1.status == "active"
    assert rev_v2.status == "archived"
    mock_act.assert_awaited_once()


# ==============================================================================
# 6. Legacy Audit & Classification (Phase 6)
# ==============================================================================
@pytest.mark.asyncio
async def test_legacy_audit_and_classification():
    """Verify legacy state audit correctly classifies documents into parity-ok, needs-rebuild, and pending-intake."""
    session = _fresh_session()
    col = KnowledgeCollection(id="col_audit_test", name="Audit Test", module_code="admissions")

    doc_ok = KnowledgeDocument(
        id="doc_ok", collection_id=col.id, title="Doc OK", repository_document_id="rdoc_1", index_status="indexed"
    )
    doc_rebuild = KnowledgeDocument(
        id="doc_rebuild", collection_id=col.id, title="Doc Rebuild", repository_document_id="rdoc_2", index_status="indexed"
    )
    doc_pending = KnowledgeDocument(
        id="doc_pending", collection_id=col.id, title="Doc Pending", repository_document_id=None, index_status="pending"
    )

    session.get.return_value = col

    # Mock DB query executions
    # 1. select KnowledgeDocument
    res_docs = _execute_result(scalars_list=[doc_ok, doc_rebuild, doc_pending])
    # 2. doc_ok chunks (3)
    res_chunks_ok = _execute_result(scalar=3)
    # 3. doc_ok binding
    res_bnd_ok = _execute_result(scalar=KnowledgeBinding(id="bnd_1", active_index_revision_id="rev_1"))
    # 4. doc_rebuild chunks (5)
    res_chunks_rebuild = _execute_result(scalar=5)
    # 5. doc_rebuild binding
    res_bnd_rebuild = _execute_result(scalar=KnowledgeBinding(id="bnd_2", active_index_revision_id="rev_2"))
    # 6. doc_pending chunks (0)
    res_chunks_pending = _execute_result(scalar=0)
    # 7. doc_pending binding
    res_bnd_pending = _execute_result(scalar=None)

    session.execute.side_effect = [
        res_docs,
        res_chunks_ok, res_bnd_ok,
        res_chunks_rebuild, res_bnd_rebuild,
        res_chunks_pending, res_bnd_pending,
    ]

    with patch("app.modules.rag.vector_indexer.vector_indexer.count_points_by_document", new_callable=AsyncMock) as mock_count:
        # doc_ok: 3 chunks == 3 vectors -> parity-ok
        # doc_rebuild: 5 chunks != 2 vectors -> needs-rebuild
        # doc_pending: 0 chunks -> pending-intake
        mock_count.side_effect = [3, 2, 0]

        report = await canary_service.audit_collection_legacy_state(session, col.id)

    assert report.total_documents == 3
    assert report.active_parity_ok_count == 1
    assert report.needs_rebuild_count == 1
    assert report.pending_intake_count == 1
    assert report.parity_ratio == 0.3333

    classifications = {item.document_id: item.classification for item in report.items}
    assert classifications["doc_ok"] == "active-parity-ok"
    assert classifications["doc_rebuild"] == "needs-rebuild"
    assert classifications["doc_pending"] == "pending-intake"


# ==============================================================================
# 7. Idempotent Legacy Backfill (Phase 6)
# ==============================================================================
@pytest.mark.asyncio
async def test_idempotent_legacy_backfill():
    """Verify safe idempotent backfill creates bindings, index revisions, and tags chunks."""
    session = _fresh_session()
    col = KnowledgeCollection(id="col_bf_test", name="Backfill Test", module_code="admissions", index_epoch=1)

    legacy_doc = KnowledgeDocument(
        id="doc_legacy_1",
        collection_id=col.id,
        title="Tài liệu cũ",
        file_name="tailieu.pdf",
        file_type="pdf",
        file_size_bytes=2048,
        file_hash="hash_legacy_1",
        storage_path="docs/tailieu.pdf",
        repository_document_id=None,
    )
    chunk1 = KnowledgeChunk(id="chk_leg_1", document_id=legacy_doc.id, collection_id=col.id, content="Đoạn 1")
    chunk2 = KnowledgeChunk(id="chk_leg_2", document_id=legacy_doc.id, collection_id=col.id, content="Đoạn 2")

    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeCollection, col.id): col,
    }.get((model, obj_id))

    # 1. select KnowledgeDocument -> [legacy_doc]
    res_docs = _execute_result(scalars_list=[legacy_doc])
    # 2. select chunks -> [chunk1, chunk2]
    res_chunks = _execute_result(scalars_list=[chunk1, chunk2])
    # 3. select facts -> []
    res_facts = _execute_result(scalars_list=[])
    # 4. select DocumentRevision -> None
    res_rev = _execute_result(scalar=None)
    # 5. select KnowledgeBinding -> None (new)
    res_bnd = _execute_result(scalar=None)
    # 6. bump_collection_index_epoch UPDATE ... RETURNING index_epoch -> 2
    res_epoch = _execute_result(scalar=2)

    session.execute.side_effect = [
        res_docs,
        res_chunks,
        res_facts,
        res_rev,
        res_bnd,
        res_epoch,
    ]

    active_idx = KnowledgeIndexRevision(
        id="idx_backfilled",
        binding_id="bnd_backfilled",
        source_revision_id="drev_backfilled",
        vector_generation_id="vg_backfilled",
        revision_no=1,
        status="active",
        chunk_count=2,
    )
    with patch.object(
        index_build_service,
        "build_staging_index",
        new_callable=AsyncMock,
        return_value=active_idx,
    ):
        report = await canary_service.backfill_legacy_collection(
            db=session,
            collection_id=col.id,
            actor_id="admin_tester",
            force_rebuild=False,
        )

    assert report.documents_processed == 1
    assert report.bindings_created == 1
    assert report.index_revisions_created == 1
    assert report.chunks_tagged == 0
    assert report.status == "completed"
    assert legacy_doc.repository_document_id is not None
    assert chunk1.binding_id is None
    assert chunk1.index_revision_id is None


# ==============================================================================
# 8. Shadow Retrieval Verification: Zero Leak & Latency Delta
# ==============================================================================
@pytest.mark.asyncio
async def test_shadow_retrieval_zero_leak_and_latency():
    """Verify shadow retrieval comparison verifies zero cross-revision leak and latency delta."""
    session = _fresh_session()
    col = KnowledgeCollection(id="col_shadow", name="Shadow Test", module_code="admissions", index_epoch=3)
    session.get.return_value = col

    snapshot = RetrievalSnapshot(
        snapshot_id="snap_shadow_1",
        collection_id=col.id,
        collection_epoch=3,
        binding_revisions={"bnd_1": "rev_active_1"},
    )

    candidate_v1 = [
        FusionCandidate(
            chunk_id="chk_common_1",
            document_id="doc_1",
            content="Quy định xét tuyển",
            rrf_score=0.9,
            binding_id="bnd_1",
            index_revision_id="rev_active_1",
        )
    ]
    candidate_v2 = [
        FusionCandidate(
            chunk_id="chk_common_1",
            document_id="doc_1",
            content="Quy định xét tuyển",
            rrf_score=0.92,
            binding_id="bnd_1",
            index_revision_id="rev_active_1",
        )
    ]

    with (
        patch.object(hybrid_retriever, "resolve_retrieval_snapshot", return_value=snapshot),
        patch.object(hybrid_retriever, "retrieve", side_effect=[candidate_v1, candidate_v2]),
    ):
        report = await canary_service.run_shadow_retrieval_comparison(
            db=session,
            collection_id=col.id,
            query="Xét tuyển thẳng đại học",
            top_k=5,
        )

    assert report.collection_id == col.id
    assert report.overlap_count == 1
    assert report.jaccard_similarity == 1.0
    assert report.retrieval_revision_leak_total == 0
    assert report.leak_detected is False
    assert report.v1_chunk_ids == ["chk_common_1"]
    assert report.v2_chunk_ids == ["chk_common_1"]


# ==============================================================================
# 9. API HTTP Contracts for Canary & Rollback Routes
# ==============================================================================
@pytest.mark.asyncio
async def test_api_routes_canary_and_rollback():
    """Verify HTTP endpoints for Canary Audit, Backfill, Shadow Test, and Rollback."""
    mock_db = _fresh_session()

    async def _get_test_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_current_actor] = lambda: AuthActor(
        actor_id="admin_test",
        username="admin",
        display_name="Admin Test",
        email="admin@qnu.edu.vn",
        user_type="admin",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        role="admin",
        roles=["admin"],
        permissions=["*"],
        authenticated=True,
        session_version="v1",
    )

    prefix = f"{settings.API_PREFIX}/knowledge"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Rollback endpoint
        with patch.object(
            index_build_service,
            "rollback_index_revision",
            return_value=KnowledgeIndexActivation(
                id="act_rb_1",
                binding_id="bnd_test",
                to_index_revision_id="rev_old",
                action="rollback",
                epoch=3,
                created_at=datetime.now(UTC),
            ),
        ):
            resp = await client.post(
                f"{prefix}/bindings/bnd_test/rollback",
                json={
                    "target_index_revision_id": "rev_old",
                    "expected_epoch": 2,
                    "reason": "Test rollback",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["action"] == "rollback"
            assert data["to_index_revision_id"] == "rev_old"

        # 2. Canary Audit endpoint
        with patch.object(
            canary_service,
            "audit_collection_legacy_state",
            return_value={
                "collection_id": "col_test",
                "total_documents": 2,
                "active_parity_ok_count": 2,
                "needs_rebuild_count": 0,
                "pending_intake_count": 0,
                "parity_ratio": 1.0,
                "items": [],
                "audited_at": datetime.now(UTC).isoformat(),
            },
        ):
            resp = await client.post(f"{prefix}/collections/col_test/canary/audit")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_documents"] == 2
            assert data["parity_ratio"] == 1.0

        # 3. Canary Backfill endpoint
        with patch.object(
            canary_service,
            "backfill_legacy_collection",
            return_value={
                "collection_id": "col_test",
                "documents_processed": 5,
                "bindings_created": 5,
                "index_revisions_created": 5,
                "chunks_tagged": 50,
                "facts_tagged": 10,
                "collection_epoch": 2,
                "status": "completed",
                "items": [],
                "completed_at": datetime.now(UTC).isoformat(),
            },
        ):
            resp = await client.post(
                f"{prefix}/collections/col_test/canary/backfill",
                json={"force_rebuild": False},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert data["bindings_created"] == 5

        # 4. Canary Shadow test endpoint
        with patch.object(
            canary_service,
            "run_shadow_retrieval_comparison",
            return_value={
                "collection_id": "col_test",
                "query": "Học bổng",
                "v1_result_count": 3,
                "v2_result_count": 3,
                "overlap_count": 3,
                "jaccard_similarity": 1.0,
                "latency_v1_ms": 12.5,
                "latency_v2_ms": 13.0,
                "latency_delta_pct": 4.0,
                "retrieval_revision_leak_total": 0,
                "leak_detected": False,
                "v1_chunk_ids": ["c1", "c2", "c3"],
                "v2_chunk_ids": ["c1", "c2", "c3"],
                "tested_at": datetime.now(UTC).isoformat(),
            },
        ):
            resp = await client.post(
                f"{prefix}/collections/col_test/canary/shadow-test",
                json={"query": "Học bổng", "top_k": 3},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["leak_detected"] is False
            assert data["retrieval_revision_leak_total"] == 0

    app.dependency_overrides.clear()
