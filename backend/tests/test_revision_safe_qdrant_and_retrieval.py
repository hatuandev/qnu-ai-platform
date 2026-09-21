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
        # NOTE (session 179 team + 181 rebase): MAJOR_NAME_TO_CODE augments
        # "Công nghệ thông tin" -> entity 7480201, so a query pairing a
        # concrete major with "chỉ tiêu" now routes EXACT_FACT (fact-first).
        # A mixed narrative+fact query without a resolvable entity stays MIXED.
        analysis = classifier.analyze("Giải thích chính sách ưu tiên và chỉ tiêu tuyển sinh ngành Công nghệ thông tin")
        assert analysis.intent == QueryIntent.EXACT_FACT
        assert analysis.is_fact_first is True
        assert "7480201" in analysis.entity_codes

    def test_query_classifier_mixed_without_entity(self):
        classifier = QueryClassifier()
        analysis = classifier.analyze("Giải thích chính sách ưu tiên tuyển sinh cho sinh viên năm nhất như thế nào?")
        assert analysis.intent in (QueryIntent.MIXED, QueryIntent.NARRATIVE)


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

            # Check retrieve uses EXACT_FACT top_k (8/6 since team session 180
            # recall tuning; was 4/3 before). Query is entity-augmented, so
            # match on top_k/rerank + collection/scope instead of exact query.
            called_kwargs = mock_retrieve.await_args.kwargs
            assert called_kwargs["collection_id"] == "col_admissions"
            assert called_kwargs["top_k"] == 8
            assert called_kwargs["rerank_top_k"] == 6
            assert called_kwargs["tenant_id"] == "tenant_qnu"
            assert called_kwargs["workspace_id"] == "ws_main"
            assert "7480107" in called_kwargs["query"]

    @pytest.mark.asyncio
    async def test_rag_ask_applies_intent_weights_and_fact_temperature(self):
        """EXACT_FACT leans lexical + clamps temperature; NARRATIVE leans semantic."""
        from app.modules.rag.schemas import AskRequest

        async def run_ask(question: str, temperature: float):
            req = AskRequest(
                question=question,
                collection_id="col_admissions",
                module_code="admissions",
                tenant_id="tenant_qnu",
                workspace_id="ws_main",
                temperature=temperature,
            )
            mock_candidate = FusionCandidate(
                chunk_id="chk_01",
                document_id="doc_ts_2026",
                content="Mã ngành 7480107: Chỉ tiêu dự kiến 60 sinh viên.",
                rrf_score=0.9,
                dense_rank=1,
                sparse_rank=1,
                section="Chỉ tiêu",
                page_number=6,
                metadata={},
            )
            with (
                patch("app.modules.rag.service.semantic_cache.get", new_callable=AsyncMock) as mock_get,
                patch("app.modules.rag.service.semantic_cache.set", new_callable=AsyncMock),
                patch("app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock) as mock_lookup,
                patch("app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock) as mock_retrieve,
                patch("app.modules.rag.service.modelops_service.generate", new_callable=AsyncMock) as mock_generate,
            ):
                mock_get.return_value = None
                mock_lookup.return_value = []
                mock_retrieve.return_value = [mock_candidate]
                mock_llm_res = MagicMock()
                mock_llm_res.content = "Chỉ tiêu là 60 sinh viên."
                mock_generate.return_value = mock_llm_res
                resp = await rag_service.ask(AsyncMock(), req)
                return resp, mock_retrieve.await_args.kwargs, mock_generate.await_args.args[1]

        _, exact_retrieve, exact_llm = await run_ask("Mã ngành 7480107 có chỉ tiêu bao nhiêu?", 0.9)
        assert (exact_retrieve["dense_weight"], exact_retrieve["sparse_weight"]) == (1.0, 1.2)
        assert exact_llm.temperature == 0.2
        assert any("TẦNG 1" in m.content for m in exact_llm.messages if m.role == "user")

        _, narrative_retrieve, narrative_llm = await run_ask(
            "Quy định về bảo hiểm y tế cho sinh viên như thế nào?", 0.9
        )
        assert (narrative_retrieve["dense_weight"], narrative_retrieve["sparse_weight"]) == (1.2, 0.8)
        assert narrative_llm.temperature == 0.9
        assert all("TẦNG 1" not in m.content for m in narrative_llm.messages)

    @pytest.mark.asyncio
    async def test_rag_ask_sends_sparse_variants_and_neighbor_context(self):
        """Keyword-form variant query feeds sparse fusion; neighbors join the prompt."""
        from app.modules.rag.schemas import AskRequest

        req = AskRequest(
            question="các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học",
            collection_id="col_admissions",
            module_code="admissions",
            tenant_id="tenant_qnu",
            workspace_id="ws_main",
        )
        mock_candidate = FusionCandidate(
            chunk_id="chk_01",
            document_id="doc_ts_2026",
            content="Thông tin tuyển sinh ngành X: Các tổ hợp môn xét tuyển: Toán - Hóa - Anh.",
            rrf_score=0.9,
            dense_rank=1,
            sparse_rank=1,
            section="Ngành X",
            page_number=6,
            metadata={},
        )
        with (
            patch("app.modules.rag.service.semantic_cache.get", new_callable=AsyncMock) as mock_get,
            patch("app.modules.rag.service.semantic_cache.set", new_callable=AsyncMock),
            patch("app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock) as mock_lookup,
            patch("app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock) as mock_retrieve,
            patch(
                "app.modules.rag.service.hybrid_retriever.expand_with_neighbors",
                new_callable=AsyncMock,
            ) as mock_expand,
            patch("app.modules.rag.service.modelops_service.generate", new_callable=AsyncMock) as mock_generate,
        ):
            mock_get.return_value = None
            mock_lookup.return_value = []
            mock_retrieve.return_value = [mock_candidate]
            mock_expand.return_value = {"chk_01": ["Bối cảnh kề: điều kiện xét tuyển chung."]}
            mock_llm_res = MagicMock()
            mock_llm_res.content = "Các ngành có tổ hợp."
            mock_generate.return_value = mock_llm_res

            resp = await rag_service.ask(AsyncMock(), req)

            assert resp.status == "answered"
            variants = mock_retrieve.await_args.kwargs.get("sparse_variants") or []
            assert variants and any("toán" in v.lower() for v in variants)
            user_texts = [
                m.content for m in mock_generate.await_args.args[1].messages if m.role == "user"
            ]
            assert any("BỐI CẢNH MỞ RỘNG" in t for t in user_texts)

    @pytest.mark.asyncio
    async def test_rag_ask_skips_cache_for_context_dependent_short_query(self):
        """Short follow-ups with history ('có tôi muốn') must never hit shared cache."""
        req = AskRequest(
            question="có tôi muốn",
            collection_id="col_admissions",
            module_code="admissions",
            tenant_id="tenant_qnu",
            workspace_id="ws_main",
            history=[
                {"role": "user", "content": "điểm chuẩn CNTT bao nhiêu?"},
                {"role": "assistant", "content": "Điểm chuẩn là 24.5"},
            ],
        )
        mock_db = AsyncMock()
        mock_candidate = FusionCandidate(
            chunk_id="chk_01",
            document_id="doc_ts_2026",
            content="Chỉ tiêu tuyển sinh ngành Công nghệ thông tin và phương thức xét tuyển chi tiết.",
            rrf_score=0.9,
            dense_rank=1,
            sparse_rank=1,
            section="Chỉ tiêu",
            page_number=6,
            metadata={},
        )
        with (
            patch("app.modules.rag.service.semantic_cache.get", new_callable=AsyncMock) as mock_get,
            patch("app.modules.rag.service.semantic_cache.set", new_callable=AsyncMock) as mock_set,
            patch("app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock) as mock_lookup,
            patch("app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock) as mock_retrieve,
            patch("app.modules.rag.service.modelops_service.generate", new_callable=AsyncMock) as mock_generate,
        ):
            mock_lookup.return_value = []
            mock_retrieve.return_value = [mock_candidate]
            mock_llm_res = MagicMock()
            mock_llm_res.content = (
                "Chỉ tiêu tuyển sinh ngành Công nghệ thông tin và phương thức xét tuyển."
            )
            mock_generate.return_value = mock_llm_res

            resp = await rag_service.ask(mock_db, req)

            assert resp.status == "answered"
            mock_get.assert_not_awaited()
            mock_set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rag_ask_rejects_hallucinated_figures_via_numeric_gate(self):
        """Answers with figures absent from evidence fall back to No-Answer policy."""
        req = AskRequest(
            question="Điểm chuẩn ngành CNTT là bao nhiêu?",
            collection_id="col_admissions",
            module_code="admissions",
            tenant_id="tenant_qnu",
            workspace_id="ws_main",
        )
        mock_db = AsyncMock()
        mock_candidate = FusionCandidate(
            chunk_id="chk_01",
            document_id="doc_ts_2026",
            content="Điểm chuẩn ngành Công nghệ thông tin là 24.5 điểm.",
            rrf_score=0.9,
            dense_rank=1,
            sparse_rank=1,
            section="Điểm chuẩn",
            page_number=6,
            metadata={},
        )
        with (
            patch("app.modules.rag.service.semantic_cache.get", new_callable=AsyncMock) as mock_get,
            patch("app.modules.rag.service.semantic_cache.set", new_callable=AsyncMock),
            patch("app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock) as mock_lookup,
            patch("app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock) as mock_retrieve,
            patch("app.modules.rag.service.modelops_service.generate", new_callable=AsyncMock) as mock_generate,
        ):
            mock_get.return_value = None
            mock_lookup.return_value = []
            mock_retrieve.return_value = [mock_candidate]
            mock_llm_res = MagicMock()
            mock_llm_res.content = "Điểm chuẩn ngành Công nghệ thông tin là 29.9 điểm."
            mock_generate.return_value = mock_llm_res

            resp = await rag_service.ask(mock_db, req)

            assert resp.status == "insufficient_context"
            assert "29.9" not in resp.answer
            assert resp.citations == []
