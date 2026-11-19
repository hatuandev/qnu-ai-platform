"""Unit tests for DN-04: Semantic Cache & Vietnamese Natural Query Normalization.

Tests verify:
1. Stripping conversational fillers while strictly preserving conditions, scopes, exceptions, and years.
2. Handling of Vietnamese decimal numbers (6.0, 6,0 -> 6.0) without splitting.
3. Strict key binding to (workspace_id, active_index_run_id).
4. RagPolicy semantic_cache toggle and TTL defaults.
"""

from __future__ import annotations

import pytest

from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.semantic_cache import (
    SemanticCacheEntry,
    get_semantic_cache,
    invalidate_semantic_cache,
    normalize_for_semantic_cache,
    semantic_cache_key,
    store_semantic_cache,
    ttl_seconds,
)


def test_dn04_normalization_strips_polite_fillers_consistently():
    # Conversational variants of the same core question
    variants = [
        "Dạ thầy cô cho em hỏi điểm chuẩn ngành CNTT năm 2025 là bao nhiêu ạ?",
        "Thầy cô cho tôi hỏi điểm chuẩn ngành CNTT năm 2025 là bao nhiêu?",
        "Cho em hỏi điểm chuẩn ngành CNTT năm 2025 là bao nhiêu với ạ?",
        "Vui lòng cho biết điểm chuẩn ngành CNTT năm 2025 là bao nhiêu?",
        "Nhờ bot tư vấn điểm chuẩn ngành CNTT năm 2025 là bao nhiêu nhé?",
        "Điểm chuẩn ngành CNTT năm 2025 là bao nhiêu?",
    ]
    canonical = "điểm chuẩn ngành cntt năm 2025 là bao nhiêu"
    for v in variants:
        assert normalize_for_semantic_cache(v) == canonical, f"Failed for variant: {v}"


def test_dn04_normalization_preserves_conditions_scopes_and_exceptions():
    # 1. Study modes
    q_chinh_quy = "Điều kiện xét tuyển hệ chính quy năm 2026"
    q_lien_thong = "Điều kiện xét tuyển hệ liên thông năm 2026"
    norm_cq = normalize_for_semantic_cache(q_chinh_quy)
    norm_lt = normalize_for_semantic_cache(q_lien_thong)
    assert "chính quy" in norm_cq
    assert "liên thông" in norm_lt
    assert norm_cq != norm_lt

    # 2. Negations and exclusions
    q_ap_dung = "Các trường hợp áp dụng quy đổi chứng chỉ ngoại ngữ"
    q_khong_ap_dung = "Các trường hợp không áp dụng quy đổi chứng chỉ ngoại ngữ"
    norm_ad = normalize_for_semantic_cache(q_ap_dung)
    norm_kad = normalize_for_semantic_cache(q_khong_ap_dung)
    assert "không áp dụng" in norm_kad
    assert "không áp dụng" not in norm_ad
    assert norm_ad != norm_kad

    # 3. Exceptions
    q_ngoai_le = "Trường hợp ngoại lệ về điều kiện sức khỏe ngành Sư phạm"
    norm_nl = normalize_for_semantic_cache(q_ngoai_le)
    assert "ngoại lệ" in norm_nl

    # 4. Years differentiation (2024 vs 2025 vs 2026)
    q_2024 = "Chỉ tiêu tuyển sinh năm 2024"
    q_2025 = "Chỉ tiêu tuyển sinh năm 2025"
    assert normalize_for_semantic_cache(q_2024) != normalize_for_semantic_cache(q_2025)
    assert "2024" in normalize_for_semantic_cache(q_2024)
    assert "2025" in normalize_for_semantic_cache(q_2025)


def test_dn04_normalization_preserves_decimals_and_converts_comma():
    # Vietnamese comma vs standard dot
    q_dot = "Cho em hỏi chứng chỉ VSTEP 6.0 quy đổi bao nhiêu điểm ạ?"
    q_comma = "Chứng chỉ VSTEP 6,0 quy đổi bao nhiêu điểm?"
    norm_dot = normalize_for_semantic_cache(q_dot)
    norm_comma = normalize_for_semantic_cache(q_comma)

    assert "6.0" in norm_dot
    assert "6.0" in norm_comma
    assert norm_dot == norm_comma == "chứng chỉ vstep 6.0 quy đổi bao nhiêu điểm"

    # Scale 7.0 vs 6.0
    q_7 = "Chứng chỉ VSTEP 7.0 quy đổi bao nhiêu điểm?"
    assert normalize_for_semantic_cache(q_7) != normalize_for_semantic_cache(q_dot)
    assert "7.0" in normalize_for_semantic_cache(q_7)


def test_dn04_rag_policy_semantic_cache_toggle():
    req_default = AnswerRequest(question="Quy chế tuyển sinh")
    assert req_default.semantic_cache is True

    req_disabled = AnswerRequest(question="Quy chế tuyển sinh", semantic_cache=False)
    assert req_disabled.semantic_cache is False

    assert ttl_seconds() == 3600


@pytest.mark.asyncio
async def test_dn04_strict_key_binding_and_invalidation():
    workspace = "ws_dn04"
    collection = "col_dn04"
    run_1 = "run_2026_v1"
    run_2 = "run_2026_v2"

    q1 = "Dạ cho em hỏi chỉ tiêu ngành CNTT năm 2025 ạ?"
    q2 = "Chỉ tiêu ngành CNTT năm 2025"

    norm1 = normalize_for_semantic_cache(q1)
    norm2 = normalize_for_semantic_cache(q2)
    assert norm1 == norm2

    key_run1 = semantic_cache_key(workspace, collection, run_1, norm1)
    key_run2 = semantic_cache_key(workspace, collection, run_2, norm2)

    # Different run ID yields completely distinct keys
    assert key_run1 != key_run2

    # Store in run_1
    entry = SemanticCacheEntry(
        workspace_id=workspace,
        collection_id=collection,
        index_run_id=run_1,
        normalized_query=norm1,
        raw_answer="Chỉ tiêu ngành CNTT năm 2025 là 172. [E1]",
        saved_tokens=220,
    )
    await store_semantic_cache(key_run1, entry, ttl_seconds=3600)

    # Lookup with variant q2 in run_1 -> HIT
    hit = await get_semantic_cache(key_run1)
    assert hit is not None
    assert hit.saved_tokens == 220
    assert "172" in hit.raw_answer

    # Lookup in run_2 -> MISS (zero cross-run contamination)
    miss_run2 = await get_semantic_cache(key_run2)
    assert miss_run2 is None

    # Invalidate run_1
    await invalidate_semantic_cache(workspace, run_1)
    assert await get_semantic_cache(key_run1) is None
