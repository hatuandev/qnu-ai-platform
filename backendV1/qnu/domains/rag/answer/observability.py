"""End-to-End Observability & Trace Logging for QNU RAG (Trụ cột 4).

Generates a unified, structured audit log per answer request, capturing:
- IndexRunID, ModelID, PromptVersion
- Multi-turn rewriting and Query decomposition sub-queries
- Intent routing branches
- Chunks / Row-Cards retrieved & Rerank scores
- Universal facts queries and Tool executions
- Calculator formulas and missing variable refusal checks
- IRAC reasoning trace (<phan_tich>)
- Cross-document partial amendment resolutions
- Latency across all stages (retrieval, context, reasoning, generation, cache)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from qnu.domains.rag.answer.schemas import AnswerResponse


def build_e2e_trace_summary(response: AnswerResponse | dict[str, Any]) -> dict[str, Any]:
    """Generate an end-to-end structured trace summary for auditing and APM logging."""
    if isinstance(response, BaseModel):
        data = response.model_dump()
    else:
        data = response

    trace = data.get("trace") or {}
    context = trace.get("context") or {}
    retrieval = trace.get("retrieval") or {}
    rewriting = trace.get("rewriting") or {}
    calculator = trace.get("calculator") or {}
    reasoning = trace.get("reasoning") or {}
    cache = trace.get("cache") or {}
    semantic_cache = trace.get("semantic_cache") or {}
    stage_ms = trace.get("stage_ms") or {}

    total_time_ms = sum(v for v in stage_ms.values() if isinstance(v, (int, float)))

    return {
        "answer_id": data.get("id"),
        "status": data.get("status"),
        "reason": data.get("reason"),
        "index_run_id": data.get("index_run_id"),
        "generation": data.get("generation"),
        "prompt_version": trace.get("prompt_version"),
        "model": {
            "provider_id": trace.get("provider_id"),
            "model_name": trace.get("model_name"),
        },
        "query_pipeline": {
            "rewritten": rewriting.get("changed", False),
            "original_query": rewriting.get("original_question"),
            "effective_query": rewriting.get("rewritten_query"),
            "anaphora_detected": rewriting.get("anaphora_detected", False),
            "intent": context.get("intent", "direct_lookup"),
            "decomposed_subqueries": retrieval.get("decomposition", {}).get("sub_queries", []),
        },
        "retrieval": {
            "sources_count": len(data.get("sources") or []),
            "statements_count": len(data.get("statements") or []),
            "manifest_sha256": retrieval.get("manifest_sha256"),
            "rerank_included": "rerank" in trace.get("stage_ms", {}),
        },
        "governance": {
            "amendments_detected": context.get("amendments", {}).get("amendments_detected", False),
            "confusable_siblings_detected": bool(context.get("confusable_siblings")),
            "rule_constraints_count": len(context.get("rule_constraints") or []),
        },
        "reasoning": {
            "has_irac_analysis": bool(reasoning.get("analysis") or reasoning.get("irac_analysis")),
            "steps": reasoning.get("steps", []),
        },
        "calculator": {
            "executed": bool(calculator),
            "status": calculator.get("status"),
            "formula": calculator.get("formula"),
            "result": calculator.get("result"),
            "missing_variables": calculator.get("missing_variables", []),
        },
        "tools": trace.get("tools", []),
        "cache": {
            "exact_cache": cache.get("status", "disabled"),
            "semantic_cache": semantic_cache.get("status", "disabled"),
            "saved_tokens": cache.get("saved_tokens") or semantic_cache.get("saved_tokens"),
        },
        "timing_ms": {
            **stage_ms,
            "total_measured_ms": round(total_time_ms, 3),
        },
        "token_usage": {
            "prompt_tokens": trace.get("prompt_tokens"),
            "completion_tokens": trace.get("completion_tokens"),
            "total_tokens": trace.get("total_tokens"),
        },
    }
