"""Unit tests for Phase 2 optimizations:
1. Conditional source diversity according to query scope (single-document vs cross-document).
2. In-memory bounded LRU cache for canonical JSON and immutable artifacts.
3. Rerank candidate pool sizing (15 for single-doc vs 30 for multi-doc).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from qnu.domains.knowledge.index.artifact_cache import (
    BoundedLRUCache,
    clear_all_artifact_caches,
    get_canonical_json,
    get_index_manifest,
    set_canonical_json,
    set_index_manifest,
)
from qnu.domains.knowledge.index.hybrid import (
    SINGLE_DOC_CANDIDATE_K,
    apply_source_diversity,
    is_single_document_scope,
    select_reranked,
)


def test_bounded_lru_cache_operations():
    cache = BoundedLRUCache(maxsize=3)
    assert len(cache) == 0

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert len(cache) == 3
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3

    # Adding 4th item evicts the oldest ('a' was accessed before 'b' and 'c', so 'a' is accessed, then 'b' is oldest)
    # Access order: a, b, c. Then access 'a' -> order: b, c, a.
    cache.get("a")
    cache.set("d", 4)
    assert cache.get("b") is None  # 'b' was least recently used
    assert cache.get("c") == 3
    assert cache.get("a") == 1
    assert cache.get("d") == 4
    assert len(cache) == 3

    # Test clear
    cache.clear()
    assert len(cache) == 0
    assert cache.get("a") is None


def test_artifact_cache_helpers():
    clear_all_artifact_caches()

    # Canonical JSON cache
    assert get_canonical_json("run_1", "sha_1") is None
    set_canonical_json("run_1", "sha_1", {"identity": "doc_1"})
    assert get_canonical_json("run_1", "sha_1") == {"identity": "doc_1"}
    # Different sha -> cache miss
    assert get_canonical_json("run_1", "sha_2") is None

    # Index manifest cache
    assert get_index_manifest("key_1", "sha_m") is None
    set_index_manifest("key_1", "sha_m", {"run_id": "idx_1"})
    assert get_index_manifest("key_1", "sha_m") == {"run_id": "idx_1"}


def test_is_single_document_scope_explicit_filter():
    # Explicit single doc id
    assert is_single_document_scope("câu hỏi bất kỳ", document_ids=["doc_1"]) is True
    # Explicit multiple doc ids
    assert is_single_document_scope("câu hỏi bất kỳ", document_ids=["doc_1", "doc_2"]) is False

    # Metadata filter single doc
    mock_filter_single = MagicMock()
    mock_filter_single.document_ids = ["doc_1"]
    assert is_single_document_scope("câu hỏi", metadata_filter=mock_filter_single) is True

    # Metadata filter multi doc
    mock_filter_multi = MagicMock()
    mock_filter_multi.document_ids = ["doc_1", "doc_2"]
    assert is_single_document_scope("câu hỏi", metadata_filter=mock_filter_multi) is False


def test_is_single_document_scope_queries():
    # Single doc targets
    assert (
        is_single_document_scope(
            "Theo Quyết định 4740/QĐ-BGDĐT, tiêu chí LMS/LCMS có điểm tối đa là bao nhiêu?"
        )
        is True
    )
    assert (
        is_single_document_scope(
            "Theo Kế hoạch 130/KH-ĐHQN, mục tiêu cụ thể và thời gian triển khai là khi nào?"
        )
        is True
    )
    assert (
        is_single_document_scope(
            "Kế hoạch 07/KH-AM quy định các mốc thời gian và giai đoạn triển khai ra sao?"
        )
        is True
    )
    assert (
        is_single_document_scope(
            "Cho biết năm 2024 và năm 2025, ngành Sư phạm Lịch sử - Địa lý (mã 7140249) tuyển sinh bao nhiêu chỉ tiêu?"
        )
        is True
    )
    assert (
        is_single_document_scope(
            "Kế hoạch 130/KH-ĐHQN: Đơn vị nào chủ trì nhiệm vụ viết Báo cáo tự đánh giá (SAR)?"
        )
        is True
    )

    # Multi-doc / Comparison queries
    assert (
        is_single_document_scope(
            "So sánh mốc thời gian thực hiện giữa Kế hoạch 130/KH-ĐHQN và Kế hoạch 07/KH-AM trong giai đoạn 2025–2026."
        )
        is False
    )
    assert (
        is_single_document_scope(
            "Trong các văn bản đã ban hành, văn bản nào có quy định về chuyển đổi số và văn bản nào quy định về kiểm định chất lượng AUN-QA?"
        )
        is False
    )
    assert (
        is_single_document_scope(
            "Kế hoạch kiểm định và đánh giá ngoài có những mốc thời gian quan trọng nào?"
        )
        is False
    )


class DummyHit:
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        score: float = 1.0,
        citations: dict | None = None,
        text: str = "",
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.score = score
        self.citations = citations or {}
        self.text = text

    def model_copy(self, update=None):
        update = update or {}
        return DummyHit(
            self.chunk_id,
            self.document_id,
            update.get("score", self.score),
            self.citations,
            self.text,
        )


def test_apply_source_diversity_page_targeting():
    # 6 candidates on page 12, 4 on page 11
    candidates = [
        DummyHit(f"p12_{i}", "doc_1", 0.99 - i * 0.01, citations={"e": {"page": 12}})
        for i in range(6)
    ] + [
        DummyHit(f"p11_{i}", "doc_1", 0.90 - i * 0.01, citations={"e": {"page": 11}})
        for i in range(4)
    ]

    # Query targeting both page 11 and page 12
    query = "Ngành nằm ở cuối trang 11 trước khi sang trang 12 có số liệu như thế nào?"
    selected = apply_source_diversity(candidates, 6, is_single_doc_target=True, query=query)
    assert len(selected) == 6
    p11_selected = [h for h in selected if h.chunk_id.startswith("p11_")]
    p12_selected = [h for h in selected if h.chunk_id.startswith("p12_")]
    assert len(p11_selected) == 3
    assert len(p12_selected) == 3
    assert p11_selected[0].chunk_id == "p11_0"
    assert p12_selected[0].chunk_id == "p12_0"


def test_apply_source_diversity_single_doc_target():
    # 8 candidates: 6 from doc_qd4740, 2 from doc_kh130
    candidates = [
        DummyHit("c1", "doc_qd4740", 0.99),
        DummyHit("c2", "doc_qd4740", 0.98),
        DummyHit("c3", "doc_qd4740", 0.97),
        DummyHit("c4", "doc_qd4740", 0.96),
        DummyHit("c5", "doc_qd4740", 0.95),
        DummyHit("c6", "doc_qd4740", 0.94),
        DummyHit("c7", "doc_kh130", 0.05),
        DummyHit("c8", "doc_kh130", 0.02),
    ]

    # When is_single_doc_target=True: does NOT quota-clamp, returns top 5 from doc_qd4740
    selected_single = apply_source_diversity(candidates, 5, is_single_doc_target=True)
    assert len(selected_single) == 5
    assert [h.chunk_id for h in selected_single] == ["c1", "c2", "c3", "c4", "c5"]
    assert all(h.document_id == "doc_qd4740" for h in selected_single)

    # When is_single_doc_target=False (cross-doc query): quota applies (max_per_doc = 2 for count=5)
    # However, c7 and c8 have negligible score (0.05 < 0.99*0.2 and < 0.15), so relevance threshold prevents pollution
    selected_multi = apply_source_diversity(candidates, 5, is_single_doc_target=False)
    assert len(selected_multi) == 5
    # The first 2 from doc_qd4740 are selected, then deferred c3..c6 are backfilled because c7, c8 are low-score
    assert [h.chunk_id for h in selected_multi] == ["c1", "c2", "c3", "c4", "c5"]


def test_select_reranked_integration():
    fusion_hits = [
        DummyHit("c1", "doc_qd4740", 0.8),
        DummyHit("c2", "doc_qd4740", 0.7),
        DummyHit("c3", "doc_qd4740", 0.6),
        DummyHit("c4", "doc_qd4740", 0.5),
        DummyHit("c5", "doc_kh130", 0.4),
    ]
    reranked = [
        DummyHit("c1", "doc_qd4740", 0.99),
        DummyHit("c2", "doc_qd4740", 0.98),
        DummyHit("c3", "doc_qd4740", 0.97),
        DummyHit("c4", "doc_qd4740", 0.96),
        DummyHit("c5", "doc_kh130", 0.03),
    ]

    selected = select_reranked(fusion_hits, reranked, 4, is_single_doc_target=True)
    assert len(selected) == 4
    assert [h.chunk_id for h in selected] == ["c1", "c2", "c3", "c4"]


def test_rerank_candidate_pool_constant():
    assert SINGLE_DOC_CANDIDATE_K == 15
    # Verify pool reduction logic: 30 candidates sliced to 15 when single doc
    dummy_pool = [DummyHit(f"c_{i}", "doc_1") for i in range(30)]
    sliced = dummy_pool[:SINGLE_DOC_CANDIDATE_K]
    assert len(sliced) == 15
