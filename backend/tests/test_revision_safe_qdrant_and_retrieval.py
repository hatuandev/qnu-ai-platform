"""Tests for Revision-Safe Qdrant Indexing, Fact-First Query Routing, and Citation Grounding."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.http import models as qmodels

from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.query_router import QueryClassifier, QueryIntent
from app.modules.rag.schemas import AskRequest
from app.modules.rag.service import rag_service
from app.modules.rag.vector_indexer import VectorIndexer


class TestQueryClassifier:
    """Test suite for query intent analysis and routing."""

    def test_query_classifier_exact_fact_admissions(self):
        classifier = QueryClassifier()
        analysis = classifier.analyze("Mã ngành 7480107 chỉ tiêu tuyển sinh năm nay là bao nhiêu?")
        assert analysis.intent == QueryIntent.EXACT_FACT
        assert analysis.is_fact_first is True
        assert "7480107" in analysis.entity_codes
        assert "expected_quota" in analysis.fact_attributes

    def test_query_classifier_exact_fact_plan_task(self):
        classifier = QueryClassifier()
        analysis = classifier.analyze("Nhiệm vụ 6.8 đơn vị nào chủ trì và hạn hoàn thành khi nào?")
        assert analysis.intent == QueryIntent.EXACT_FACT
        assert analysis.is_fact_first is True
        assert "6.8" in analysis.entity_codes
        assert "lead_unit" in analysis.fact_attributes
        assert "end_date" in analysis.fact_attributes

    def test_query_classifier_ielts_vstep(self):
        classifier = QueryClassifier()
        analysis = classifier.analyze("Bằng IELTS 6.5 quy đổi sang điểm xét tuyển đại học là mấy điểm?")
        assert analysis.intent == QueryIntent.EXACT_FACT
        assert analysis.is_fact_first is True
        assert "certificate_conversion" in analysis.entity_codes
        assert "converted_score" in analysis.fact_attributes

    def test_query_classifier_narrative(self):
        classifier = QueryClassifier()
        analysis = classifier.analyze("Quy chế xét chuyển ngành học cho sinh viên năm nhất thực hiện như thế nào?")
        assert analysis.intent == QueryIntent.NARRATIVE
        assert analysis.is_fact_first is False
        assert len(analysis.entity_codes) == 0

    def test_query_classifier_mixed(self):
        classifier = QueryClassifier()
        analysis = classifier.analyze("Giải thích chính sách ưu tiên và chỉ tiêu tuyển sinh ngành Công nghệ thông tin")
        assert analysis.intent == QueryIntent.MIXED
        assert analysis.is_fact_first is True


class TestRevisionSafeQdrantIndexing:
    """Test suite for revision-safe staging, parity verification, atomic activation, and purge."""

    @pytest.mark.asyncio
    async def test_verify_revision_parity_success(self):
        indexer = VectorIndexer(qdrant_url="http://localhost:6333")
        indexer.client = MagicMock()
        indexer.client.collection_exists = AsyncMock(return_value=True)

        mock_count_res = MagicMock()
        mock_count_res.count = 12
        indexer.client.count = AsyncMock(return_value=mock_count_res)

        is_parity, reason = await indexer.verify_revision_parity(
            collection_id="col_admissions",
            document_id="doc_ts_2026",
            target_revision=2,
            expected_count=12,
        )

        assert is_parity is True
        assert "12/12 points match" in reason
        indexer.client.count.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_revision_parity_mismatch(self):
        indexer = VectorIndexer(qdrant_url="http://localhost:6333")
        indexer.client = MagicMock()
        indexer.client.collection_exists = AsyncMock(return_value=True)

        mock_count_res = MagicMock()
        mock_count_res.count = 8
        indexer.client.count = AsyncMock(return_value=mock_count_res)

        is_parity, reason = await indexer.verify_revision_parity(
            collection_id="col_admissions",
            document_id="doc_ts_2026",
            target_revision=2,
            expected_count=12,
        )

        assert is_parity is False
        assert "Lệch số lượng point Qdrant: tìm thấy 8 points, kỳ vọng 12 chunks" in reason

    @pytest.mark.asyncio
    async def test_activate_document_revision(self):
        indexer = VectorIndexer(qdrant_url="http://localhost:6333")
        indexer.client = MagicMock()
        indexer.client.set_payload = AsyncMock()

        mock_count_res = MagicMock()
        mock_count_res.count = 12
        indexer.client.count = AsyncMock(return_value=mock_count_res)

        activated_count = await indexer.activate_document_revision(
            collection_id="col_admissions",
            document_id="doc_ts_2026",
            target_revision=2,
        )

        assert activated_count == 12
        indexer.client.set_payload.assert_awaited_once()
        call_kwargs = indexer.client.set_payload.await_args.kwargs
        assert call_kwargs["payload"] == {"is_retrievable": True, "document_status": "ready"}

    @pytest.mark.asyncio
    async def test_purge_stale_revisions(self):
        indexer = VectorIndexer(qdrant_url="http://localhost:6333")
        indexer.client = MagicMock()

        mock_count_res = MagicMock()
        mock_count_res.count = 10
        indexer.client.count = AsyncMock(return_value=mock_count_res)
        indexer.client.delete = AsyncMock()

        purged_count = await indexer.purge_stale_revisions(
            collection_id="col_admissions",
            document_id="doc_ts_2026",
            current_revision=2,
        )

        assert purged_count == 10
        indexer.client.delete.assert_awaited_once()
        call_kwargs = indexer.client.delete.await_args.kwargs
        filter_selector = call_kwargs["points_selector"]
        assert isinstance(filter_selector, qmodels.FilterSelector)


class TestCitationGroundingAndFactFirst:
    """Test suite for Citation Guard extraction and Fact-First RAG flow."""

    def test_citation_guard_extracts_source_pages_and_entity_key(self):
        candidate = FusionCandidate(
            chunk_id="chk_01",
            document_id="doc_ts_2026",
            content="Chỉ tiêu ngành Trí tuệ nhân tạo là 60 sinh viên.",
            rrf_score=0.95,
            dense_rank=1,
            sparse_rank=1,
            section="Danh mục chỉ tiêu",
            page_number=6,
            metadata={
                "source_pages": [6, 7],
                "entity_key": "program:7480107",
            },
        )

        citations = citation_guard.build_citations([candidate])
        assert len(citations) == 1
        cite = citations[0]
        assert cite.source_pages == [6, 7]
        assert cite.entity_key == "program:7480107"
        assert cite.page_number == 6
        assert "Trí tuệ nhân tạo" in (cite.quote or "")

    @pytest.mark.asyncio
    async def test_rag_ask_flow_with_fact_first_routing(self):
        req = AskRequest(
            question="Mã ngành 7480107 có chỉ tiêu bao nhiêu?",
            collection_id="col_admissions",
            module_code="admissions",
            tenant_id="tenant_qnu",
            workspace_id="ws_main",
        )

        mock_db = AsyncMock()

        mock_fact = MagicMock()
        mock_fact.entity_name = "Trí tuệ nhân tạo"
        mock_fact.attribute_name = "expected_quota"
        mock_fact.attribute_value = "60"

        mock_candidate = FusionCandidate(
            chunk_id="chk_01",
            document_id="doc_ts_2026",
            content="Mã ngành 7480107: Chỉ tiêu dự kiến 60 sinh viên.",
            rrf_score=0.92,
            dense_rank=1,
            sparse_rank=1,
            section="Chỉ tiêu 2026",
            page_number=6,
            metadata={"source_pages": [6], "entity_key": "program:7480107"},
        )

        with (
            patch("app.modules.rag.service.semantic_cache.get", new_callable=AsyncMock) as mock_cache_get,
            patch("app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock) as mock_lookup,
            patch("app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock) as mock_retrieve,
            patch("app.modules.rag.service.modelops_service.generate", new_callable=AsyncMock) as mock_generate,
            patch("app.modules.rag.service.semantic_cache.set", new_callable=AsyncMock),
        ):
            mock_cache_get.return_value = None
            mock_lookup.return_value = [mock_fact]
            mock_retrieve.return_value = [mock_candidate]

            mock_llm_res = MagicMock()
            mock_llm_res.content = "Ngành Trí tuệ nhân tạo mã 7480107 có chỉ tiêu là 60 sinh viên."
            mock_generate.return_value = mock_llm_res

            resp = await rag_service.ask(mock_db, req)

            assert resp.status == "answered"
            assert "60" in resp.answer
            assert len(resp.facts_used) == 1
            assert resp.facts_used[0]["val"] == "60"

            # Check that retrieve was called with exact fact top_k=4
            mock_retrieve.assert_awaited_once_with(
                db=mock_db,
                collection_id="col_admissions",
                query=req.question,
                top_k=4,
                rerank_top_k=3,
                tenant_id="tenant_qnu",
                workspace_id="ws_main",
            )
