"""Unit tests for Slice 6C: Semantic Cache, Read-Only Tool Registry & E2E Observability.

Verifies:
1. Normalization of natural queries into canonical semantic representations.
2. Semantic Cache hit/miss and strict binding to (workspace_id, active_index_run_id).
3. Cache invalidation upon index run swap.
4. Read-Only Tool Registry schemas, discovery, and execution.
5. End-to-End Trace Summary for APM and audit logging.
"""

import pytest

from qnu.domains.rag.answer.observability import build_e2e_trace_summary
from qnu.domains.rag.answer.semantic_cache import (
    SemanticCacheEntry,
    get_semantic_cache,
    invalidate_semantic_cache,
    normalize_for_semantic_cache,
    semantic_cache_key,
    store_semantic_cache,
)
from qnu.domains.rag.tools.registry import (
    ToolRegistry,
    default_tool_registry,
)


def test_normalize_for_semantic_cache():
    q1 = "Dạ cho em hỏi quy chế tuyển sinh năm 2026 ngành CNTT với ạ?"
    q2 = "Quy chế tuyển sinh năm 2026 ngành CNTT."
    q3 = "Thầy cô cho em hỏi quy chế tuyển sinh năm 2026 ngành CNTT ạ?"

    norm1 = normalize_for_semantic_cache(q1)
    norm2 = normalize_for_semantic_cache(q2)
    norm3 = normalize_for_semantic_cache(q3)

    assert norm1 == norm2 == norm3 == "quy chế tuyển sinh năm 2026 ngành cntt"

    # Preserves leading zeros in codes
    q_code = "Cho em hỏi mã ngành 0012 và 0120 khác nhau thế nào ạ?"
    norm_code = normalize_for_semantic_cache(q_code)
    assert "0012" in norm_code
    assert "0120" in norm_code


@pytest.mark.asyncio
async def test_semantic_cache_hit_and_invalidation():
    import uuid

    uid = uuid.uuid4().hex[:8]
    workspace = f"ws_test_{uid}"
    collection = f"col_test_{uid}"
    run_1 = f"run_2026_v1_{uid}"
    run_2 = f"run_2026_v2_{uid}"

    query_a = "Cho em hỏi điểm chuẩn ngành Sư phạm Toán năm 2025 ạ?"
    query_b = "Điểm chuẩn ngành Sư phạm Toán năm 2025"

    norm_a = normalize_for_semantic_cache(query_a)
    norm_b = normalize_for_semantic_cache(query_b)
    assert norm_a == norm_b

    key_run1 = semantic_cache_key(workspace, collection, run_1, norm_a)
    key_run2 = semantic_cache_key(workspace, collection, run_2, norm_b)

    # 1. Initially empty
    assert await get_semantic_cache(key_run1) is None

    # 2. Store entry for run_1
    entry = SemanticCacheEntry(
        workspace_id=workspace,
        collection_id=collection,
        index_run_id=run_1,
        normalized_query=norm_a,
        raw_answer="Điểm chuẩn ngành Sư phạm Toán năm 2025 là 27.5 điểm. [E1]",
        saved_tokens=150,
    )
    await store_semantic_cache(key_run1, entry)

    # 3. Hit via semantically equivalent query_b
    cached = await get_semantic_cache(key_run1)
    assert cached is not None
    assert cached.saved_tokens == 150
    assert "27.5 điểm" in cached.raw_answer

    # 4. Strict run binding: query_b on run_2 must miss (zero cross-run pollution)
    assert await get_semantic_cache(key_run2) is None

    # 5. Invalidation upon index swap
    cleared = await invalidate_semantic_cache(workspace, run_1)
    assert cleared >= 1
    assert await get_semantic_cache(key_run1) is None


def test_tool_registry_schemas_and_lookup():
    registry = ToolRegistry()
    tools = registry.list_tools()
    tool_names = {t.name for t in tools}
    assert "query_facts" in tool_names
    assert "get_table_schemas" in tool_names
    assert "procedure_lookup" in tool_names

    schemas = registry.schemas()
    assert len(schemas) == len(tools)
    for s in schemas:
        assert "name" in s
        assert "description" in s
        assert "parameters" in s
        assert s["parameters"]["type"] == "object"


@pytest.mark.asyncio
async def test_tool_registry_execution():
    registry = default_tool_registry
    res = await registry.execute(
        name="procedure_lookup",
        db=None,
        actor=None,
        workspace_id="ws_1",
        collection_ids=["col_1"],
        params={"keyword": "hoãn thi"},
    )
    assert res.success is True
    assert res.tool_name == "procedure_lookup"
    assert res.items_count == 1
    assert "Quy trình hoãn thi" in res.data[0]["procedure_name"]
    assert res.execution_ms >= 0.0

    # Non-existent tool
    bad_res = await registry.execute(
        name="unknown_tool",
        db=None,
        actor=None,
        workspace_id="ws_1",
        collection_ids=["col_1"],
        params={},
    )
    assert bad_res.success is False
    assert "không tồn tại" in bad_res.error


def test_build_e2e_trace_summary():
    mock_response = {
        "id": "ans_123456",
        "status": "answered",
        "reason": None,
        "index_run_id": "run_test_v1",
        "generation": 3,
        "sources": [{"evidence_id": "E1"}],
        "statements": [{"text": "Ngành CNTT 2026.", "evidence_ids": ["E1"]}],
        "trace": {
            "prompt_version": "qnu.rag.answer/v40",
            "provider_id": "prov_deepseek",
            "model_name": "deepseek-v3",
            "stage_ms": {
                "retrieval": 15.2,
                "context": 4.1,
                "generation": 120.5,
                "cache_lookup": 1.1,
            },
            "rewriting": {
                "changed": True,
                "original_question": "Còn ngành CNTT thì sao ạ?",
                "rewritten_query": "Ngành Công nghệ thông tin năm 2026",
                "anaphora_detected": True,
            },
            "context": {
                "intent": "tabular_aggregation",
                "amendments": {"amendments_detected": True},
                "confusable_siblings": ["0012"],
                "rule_constraints": [{"applies_to": "K2026"}],
            },
            "retrieval": {
                "manifest_sha256": "abc123def456",
                "decomposition": {"sub_queries": ["chỉ tiêu CNTT 2026"]},
            },
            "reasoning": {
                "irac_analysis": "1. Issue: admission 2026. 2. Rule: regulation 2026.",
                "steps": ["Issue", "Rule", "Application", "Conclusion"],
            },
            "calculator": {
                "status": "success",
                "formula": "0.45*A + 0.35*B + 0.20*C",
                "result": 8.025,
            },
            "tools": [{"tool_name": "query_facts", "params": {"year": "2026"}}],
            "cache": {"status": "miss"},
            "semantic_cache": {"status": "hit", "saved_tokens": 350},
            "prompt_tokens": 800,
            "completion_tokens": 120,
            "total_tokens": 920,
        },
    }

    summary = build_e2e_trace_summary(mock_response)

    assert summary["answer_id"] == "ans_123456"
    assert summary["status"] == "answered"
    assert summary["prompt_version"] == "qnu.rag.answer/v40"
    assert summary["model"]["model_name"] == "deepseek-v3"

    assert summary["query_pipeline"]["rewritten"] is True
    assert summary["query_pipeline"]["intent"] == "tabular_aggregation"
    assert summary["query_pipeline"]["decomposed_subqueries"] == ["chỉ tiêu CNTT 2026"]

    assert summary["governance"]["amendments_detected"] is True
    assert summary["governance"]["confusable_siblings_detected"] is True
    assert summary["governance"]["rule_constraints_count"] == 1

    assert summary["reasoning"]["has_irac_analysis"] is True
    assert summary["calculator"]["result"] == 8.025
    assert len(summary["tools"]) == 1
    assert summary["cache"]["semantic_cache"] == "hit"
    assert summary["cache"]["saved_tokens"] == 350
    assert summary["timing_ms"]["total_measured_ms"] > 140.0
