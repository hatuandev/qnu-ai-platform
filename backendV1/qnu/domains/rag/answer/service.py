"""Retrieval → evidence → ModelOps generation → citation and current-source validation."""

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.multi import validate_collections
from qnu.domains.knowledge.index.query_scope import result_scopes
from qnu.domains.knowledge.index.schemas import SearchRequest
from qnu.domains.knowledge.index.validation import validate_results
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.public_api import resolve_chat_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.rag.answer import cache as answer_cache
from qnu.domains.rag.answer.cells import PROJECTION_VERSION, materialize
from qnu.domains.rag.answer.cells import VERSION as CELLS_VERSION
from qnu.domains.rag.answer.context import expand_collections, expand_context
from qnu.domains.rag.answer.coverage import VERSION as COVERAGE_VERSION
from qnu.domains.rag.answer.coverage import assess, plan_for, plan_ready, referenced_ids
from qnu.domains.rag.answer.drafting import (
    APPEAL_VERSION,
    PROMPT_VERSION,
    REPAIR_INSTRUCTIONS,
    appeal_messages,
    name_repair_schema,
    output_schema,
    parse_answer,
    payload_metrics,
    response_observation,
    sources_for,
)
from qnu.domains.rag.answer.fallback import compose as compose_fallback
from qnu.domains.rag.answer.hygiene import clean_model_answer
from qnu.domains.rag.answer.intent_router import classify_intent
from qnu.domains.rag.answer.narrative import continuation_supports
from qnu.domains.rag.answer.packing import pack_messages as _pack_messages
from qnu.domains.rag.answer.projection import PAYLOAD_VERSION
from qnu.domains.rag.answer.reasoning import split_reasoning_and_answer
from qnu.domains.rag.answer.retrieval import search
from qnu.domains.rag.answer.schemas import AnswerRequest, AnswerResponse, AnswerTrace
from qnu.domains.rag.answer.selection import select_hits
from qnu.domains.rag.answer.source_text import attach_source_text
from qnu.domains.rag.answer.verification import verify
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel, ChatResponseError
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.provider_execution import bind_usage
from qnu.ports.reranker import Reranker
from qnu.ports.vector_store import VectorStore

logger = get_logger(__name__)


async def answer(
    db: AsyncSession,
    blob: BlobStore,
    embedding: EmbeddingModel,
    vectors: VectorStore,
    chat: ChatModel,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    req: AnswerRequest,
    *,
    retrieval_query: str | None = None,
    clarify_source_reference: bool = False,
    persona: str = "",
    checkpoint: Callable[[], Awaitable[None]] | None = None,
    reranker: Reranker | None = None,
    compose_insufficient_message: bool = False,
    collection_ids: list[str] | None = None,
) -> AnswerResponse:
    answer_id = "ans_" + uuid.uuid4().hex
    ids = list(dict.fromkeys(collection_ids or [collection_id]))
    trace = AnswerTrace(
        prompt_version=PROMPT_VERSION,
        verification={"mode": req.verification_mode, "status": "not_run"},
    )
    request_started = time.monotonic()

    # Slice 5: Multi-turn Contextual Query Rewriter
    effective_query = retrieval_query or req.question
    if (req.history and len(req.history) >= 1) or req.conversation_memory:
        from qnu.domains.rag.answer.rewriter import rewrite_contextual_query

        effective_query, rewrite_trace = rewrite_contextual_query(
            effective_query, req.history, conversation_memory=req.conversation_memory
        )
        trace.rewriting = rewrite_trace

    # Slice 5: Deterministic Calculator
    if req.calculation is not None:
        from qnu.domains.rag.answer.calculator import CalculationRequest, evaluate_expression

        calc_req = CalculationRequest.model_validate(req.calculation)
        calc_result = evaluate_expression(calc_req)
        trace.calculator = calc_result.model_dump(mode="json")

    retrieval = await search(
        db,
        blob,
        embedding,
        vectors,
        actor,
        workspace_id,
        ids,
        SearchRequest(
            query=effective_query,
            top_k=req.top_k,
            document_ids=req.document_ids,
            mode=req.retrieval_mode,
            candidate_k=req.candidate_k,
            rerank_provider_id=req.rerank_provider_id,
            metadata_filter=req.metadata_filter,
            scope_resolution=req.scope_resolution,
            rrf_k=req.rrf_k,
        ),
        reranker=reranker,
        verify=False,
    )
    trace.stage_ms["retrieval"] = round((time.monotonic() - request_started) * 1000, 3)
    trace.retrieval = retrieval.trace
    if clarify_source_reference and len({hit.document_id for hit in retrieval.hits}) > 1:
        raise Conflict(
            "Có nhiều tài liệu phù hợp. Bạn muốn hỏi về văn bản nào?",
            code="conversation_clarification_required",
        )
    response = AnswerResponse(
        id=answer_id,
        status="insufficient_evidence",
        index_run_id=retrieval.index_run_id,
        generation=retrieval.generation,
        trace=trace,
    )

    async def compose_message(reason: str) -> None:
        started = time.monotonic()
        response.message, info = await compose_fallback(
            db,
            chat,
            actor,
            workspace_id,
            req.provider_id,
            req.question,
            reason,
            persona,
            idempotency=answer_id,
            checkpoint=checkpoint,
        )
        trace.fallback = info
        trace.stage_ms["fallback"] = round((time.monotonic() - started) * 1000, 3)

    context_started = time.monotonic()
    bundles = {}
    if len(ids) > 1:
        retrieval, trace.context = await expand_collections(
            db,
            blob,
            actor,
            workspace_id,
            retrieval,
            req,
            bundles=bundles,
            resolved_question=effective_query,
        )
    else:
        retrieval, trace.context = await expand_context(
            db,
            blob,
            actor,
            workspace_id,
            ids[0],
            retrieval,
            req,
            bundles=bundles,
            resolved_question=effective_query,
        )
    trace.stage_ms["context"] = round((time.monotonic() - context_started) * 1000, 3)
    trace.context["intent"] = classify_intent(effective_query)
    if req.calculation is not None:
        trace.context["calculation"] = trace.calculator
    if not retrieval.hits:
        if trace.calculator.get("status") == "missing_variables":
            response.reason = "missing_calculation_variables"
            response.message = trace.calculator.get("error")
            trace.verification["skip_reason"] = "missing_calculation_variables"
        else:
            response.reason = retrieval.status
            trace.verification["skip_reason"] = "no_evidence"
            if compose_insufficient_message:
                await compose_message(response.reason)
        trace.stage_ms["total"] = round((time.monotonic() - request_started) * 1000, 3)
        return response
    selected_hits, selection = select_hits(
        retrieval.hits,
        trace.context,
        req.question,
        resolved_question=effective_query,
    )
    ranking = trace.retrieval.get("ranking") or {}
    selection["candidate_count"] = len(
        trace.retrieval.get("fusion_ranked_ids") or trace.retrieval.get("dense_ranked_ids") or []
    )
    selection["reranked_count"] = len(ranking.get("rerank") or [])
    selection["rerank_applied"] = bool(ranking.get("rerank"))
    trace.context["selection"] = selection
    if len(selected_hits) != len(retrieval.hits):
        retrieval = retrieval.model_copy(update={"hits": selected_hits})
    sources = sources_for(retrieval)
    await attach_source_text(
        db,
        blob,
        workspace_id,
        ids[0],
        sources,
        scope=retrieval.trace.get("hit_scope") if len(ids) > 1 else None,
        bundles=bundles,
    )
    # Slice 5: Confusable siblings detection & rule constraints extraction
    from qnu.domains.rag.answer.confusable_siblings import scan_for_confusables
    from qnu.domains.rag.answer.rule_constraints import extract_constraints_for_sources

    confusables = scan_for_confusables(effective_query, sources)
    if confusables:
        trace.context["confusable_siblings"] = confusables

    constraints = extract_constraints_for_sources(sources)
    if constraints:
        trace.context["rule_constraints"] = constraints

    # Slice 6B: Partial Amendments Resolution & Scope Facets
    from qnu.domains.rag.answer.amendments import (
        detect_amendment_inquiry,
        filter_by_scope_facets,
        resolve_amendments,
    )

    is_amend_inq = detect_amendment_inquiry(effective_query)
    sources, amend_trace = resolve_amendments(sources, is_amendment_inquiry=is_amend_inq)
    if amend_trace.get("amendments_detected"):
        trace.context["amendments"] = amend_trace

    if req.metadata_filter and getattr(req.metadata_filter, "scope_facets", None):
        sources = filter_by_scope_facets(sources, req.metadata_filter.scope_facets)

    packing_started = time.monotonic()
    packing_metadata = (
        {
            "any_of": [
                s.model_dump(mode="json", exclude_none=True)
                for s in result_scopes(retrieval, req.metadata_filter)
            ]
        }
        if req.scope_resolution == "catalog"
        else req.metadata_filter.model_dump(mode="json", exclude_none=True)
    )
    messages, cells, envelope, evidence_bytes, skipped = _pack_messages(
        req,
        sources,
        trace.context,
        resolved_question=effective_query,
        persona=persona,
        metadata_filter=packing_metadata,
        conversation_memory=req.conversation_memory,
    )
    if req.conversation_memory:
        trace.context["conversation_memory"] = req.conversation_memory
    trace.stage_ms["packing"] = round((time.monotonic() - packing_started) * 1000, 3)
    if skipped:
        retrieval = retrieval.model_copy(update={"hits": retrieval.hits[: len(sources)]})
        if "added" in trace.context:
            trace.context["added"] = [
                item for item in trace.context["added"] if item["chunk_id"] not in skipped
            ]
        trace.context["skipped_envelope_budget"] = skipped
    trace.context["selection"]["envelope_skipped"] = skipped
    trace.context["selection"]["selected_count"] = len(sources)
    trace.context["selection"]["selected_ids"] = [source.chunk_id for source in sources]
    trace.context["bytes_used"] = evidence_bytes
    trace.context["table_selection"] = cells.get("selection", {})
    trace.context["reading_groups"] = len(envelope.get("reading", []))
    trace.context["reading_sha256"] = digest(envelope.get("reading", []))
    trace.grounding = {
        "version": CELLS_VERSION,
        "payload_version": PAYLOAD_VERSION,
        "available_cells": sum(len(t["cells"]) for t in cells["tables"]),
        "available_rows": len(
            {
                (table["evidence_id"], cell["cell_id"].split(":")[1])
                for table in cells["tables"]
                for cell in table["cells"]
            }
        ),
        "selectable_tables": sum(bool(t["cells"]) for t in cells["tables"]),
        "unresolved_tables": len(cells["issues"]),
        "catalog_sha256": digest(cells),
    }
    owners = retrieval.trace.get("hit_scope")

    async def evidence_proof() -> str:
        if len(ids) > 1:
            return await validate_collections(
                db, blob, vectors, actor, workspace_id, retrieval, req.document_ids, owners
            )
        return await validate_results(
            db, blob, vectors, actor, workspace_id, ids[0], retrieval, req.document_ids
        )

    proof_started = time.monotonic()
    proof = await evidence_proof()
    trace.stage_ms["proof"] = round((time.monotonic() - proof_started) * 1000, 3)
    answer_schema = output_schema(sources, cells=cells)
    trace.context["packing"] = payload_metrics(messages, answer_schema, evidence_bytes)
    prepare_started = time.monotonic()
    runtime, request, budget = await prepare_chat_request(
        db,
        actor,
        workspace_id,
        messages,
        provider_id=req.provider_id,
        task="answer",
        max_output_tokens=req.max_output_tokens,
        output_schema=answer_schema,
    )
    trace.stage_ms["model_prepare"] = round((time.monotonic() - prepare_started) * 1000, 3)
    inference_hash = runtime.inference_configuration_hash("answer")
    trace.inference_configuration_hash = inference_hash
    trace.reasoning = runtime.reasoning_trace() or {}
    cache_ttl = answer_cache.ttl_seconds()
    cache_material = {
        "version": answer_cache.VERSION,
        "workspace_id": workspace_id,
        "collection_id": collection_id,
        "question": req.question,
        "retrieval_query": effective_query,
        "persona": persona,
        "document_ids": sorted(req.document_ids or []),
        "retrieval": {
            "mode": req.retrieval_mode,
            "top_k": req.top_k,
            "candidate_k": req.candidate_k,
            "rrf_k": req.rrf_k,
            "rerank_provider_id": req.rerank_provider_id,
            "scope_resolution": req.scope_resolution,
            "context_window": req.context_window,
            "context_max_bytes": req.context_max_bytes,
            "metadata": packing_metadata,
        },
        "index_run_id": retrieval.index_run_id,
        "generation": retrieval.generation,
        "manifest_sha256": trace.retrieval.get("manifest_sha256"),
        "provider_id": runtime.provider_id,
        "configuration_hash": runtime.configuration_hash,
        "inference_configuration_hash": inference_hash,
        "prompt_version": PROMPT_VERSION,
        "appeal_version": APPEAL_VERSION,
        "messages_sha256": digest([{"role": m.role, "content": m.content} for m in messages]),
        "schema_sha256": digest(answer_schema),
        "evidence_sha256": proof,
        "catalog_sha256": trace.grounding["catalog_sha256"],
    }
    if len(ids) > 1:
        cache_material["collection_ids"] = sorted(ids)
        cache_material["collection_manifests"] = sorted(
            (trace.retrieval.get("manifests") or {}).items()
        )
    cache_key = answer_cache.key(cache_material) if cache_ttl else None
    cached = None
    if cache_key is not None:
        lookup_started = time.monotonic()
        cached = await answer_cache.load(cache_key)
        trace.stage_ms["cache_lookup"] = round((time.monotonic() - lookup_started) * 1000, 3)
    materialization = {}
    if cached is not None:
        # Derived values are rebuilt from this request's sources, cells and scope.
        try:
            internal_reasoning, clean_content = split_reasoning_and_answer(cached.content)
            if internal_reasoning:
                trace.reasoning["irac_analysis"] = internal_reasoning
            proposed = parse_answer(clean_content, sources)
            proposed, hygiene = clean_model_answer(proposed, req.question)
            draft = materialize(proposed, sources, cells, report=materialization)
            coverage = assess(draft, sources, trace.context, report=materialization)
            trace.grounding["hygiene"] = {"stage": "cache", **hygiene}
        except AppException:
            await answer_cache.discard(cache_key)
            cached = None

    # Slice 6C: Semantic Cache tied to (workspace_id, active_index_run_id)
    from qnu.domains.rag.answer.semantic_cache import (
        SemanticCacheEntry,
        get_semantic_cache,
        normalize_for_semantic_cache,
        semantic_cache_key,
        store_semantic_cache,
    )
    from qnu.domains.rag.answer.semantic_cache import (
        ttl_seconds as semantic_cache_ttl_seconds,
    )

    norm_q = normalize_for_semantic_cache(effective_query)
    sem_key = semantic_cache_key(workspace_id, collection_id, retrieval.index_run_id, norm_q)
    sem_cache_enabled = (
        getattr(req, "semantic_cache", True) and semantic_cache_ttl_seconds() > 0
    )
    sem_cache_ttl = semantic_cache_ttl_seconds() if sem_cache_enabled else 0
    if cached is None and sem_cache_ttl > 0:
        sem_cached = await get_semantic_cache(sem_key)
        if sem_cached is not None:
            try:
                internal_reasoning, clean_content = split_reasoning_and_answer(
                    sem_cached.raw_answer
                )
                if internal_reasoning:
                    trace.reasoning["irac_analysis"] = internal_reasoning
                proposed = parse_answer(clean_content, sources)
                proposed, hygiene = clean_model_answer(proposed, req.question)
                draft = materialize(proposed, sources, cells, report=materialization)
                coverage = assess(draft, sources, trace.context, report=materialization)
                trace.grounding["hygiene"] = {"stage": "semantic_cache", **hygiene}
                trace.semantic_cache = {
                    "status": "hit",
                    "key": sem_key,
                    "normalized_query": norm_q,
                    "saved_tokens": sem_cached.saved_tokens,
                }
                cached = answer_cache.Entry(
                    version=answer_cache.VERSION,
                    content=sem_cached.raw_answer,
                    contract=trace.contract,
                    total_tokens=sem_cached.saved_tokens,
                )
            except AppException:
                sem_cached = None
    trace.evidence_sha256 = proof
    trace.provider_id, trace.model_name = runtime.provider_id, runtime.model_name
    trace.configuration_hash = runtime.configuration_hash
    trace.routing = list(runtime.routing_trace)
    async def safety_check():
        if proof != await evidence_proof():
            raise Conflict("Evidence thay đổi khi model trả lời.", code="answer_evidence_changed")
        current = await resolve_chat_runtime(db, workspace_id, runtime.provider_id)
        if current.inference_configuration_hash("answer") != inference_hash:
            raise Conflict("Model chat đã thay đổi khi trả lời.", code="chat_provider_changed")
        if checkpoint is not None:
            await checkpoint()

    usage = None
    if cached is None:
        if req.fact_query is not None:
            from qnu.domains.rag.answer.fact_query import (
                FactQueryRequest,
                materialize_fact_query_answer,
                query_facts,
            )

            fact_req = FactQueryRequest.model_validate(req.fact_query)
            fact_result = await query_facts(db, actor, workspace_id, ids, fact_req)
            trace.context["fact_query"] = {
                "table_id": fact_req.table_id,
                "aggregation": fact_req.aggregation,
                "matched_rows": fact_result.total_matched_rows,
            }
            trace.tools.append(
                {
                    "tool_name": "query_facts",
                    "params": {"table_id": fact_req.table_id, "aggregation": fact_req.aggregation},
                    "matched_items": fact_result.total_matched_rows,
                }
            )
            materialization = {}
            draft = materialize_fact_query_answer(
                fact_result, sources, cells, report=materialization
            )
            coverage = assess(draft, sources, trace.context, report=materialization)
            proposed = draft
            first_error = None
            trace.stage_ms["generation"] = 0.0
            trace.prompt_tokens, trace.completion_tokens, trace.total_tokens = 0, 0, 0
            trace.contract = {
                "schema_sha256": digest(answer_schema),
                "finish_reason": "deterministic_facts",
                "output_budget": {},
            }
            trace.appeal = {"attempted": False}
        else:
            usage = await usage_service.reserve(
                db,
                actor,
                workspace_id,
                "chat",
                answer_id,
                digest(
                    {
                        "question": req.question,
                        "evidence": proof,
                        "config": runtime.configuration_hash,
                        "inference_config": inference_hash,
                        "prompt_version": PROMPT_VERSION,
                        "cell_catalog_sha256": trace.grounding["catalog_sha256"],
                        "metadata_filter": req.metadata_filter.model_dump(
                            mode="json", exclude_none=True
                        ),
                    }
                ),
                budget.total_reserved_tokens,
                runtime.provider_id,
            )
            trace.usage_id = usage.id
            try:
                # Reservation commits. Recheck before HTTP, then release locks during inference.
                await safety_check()
                await db.commit()
            except (Exception, asyncio.CancelledError):
                # No chat request was sent; this reservation consumed zero chat tokens.
                await usage_service.settle(db, usage.id, total_tokens=0, failed=True)
                raise
            try:
                started = time.monotonic()
                result = await chat.complete(messages, bind_usage(request, usage.id))
            except ChatResponseError as exc:
                await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
                raise
            except (Exception, asyncio.CancelledError):
                await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
                raise
            trace.stage_ms["generation"] = round((time.monotonic() - started) * 1000, 3)
            await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
            trace.prompt_tokens, trace.completion_tokens, trace.total_tokens = (
                result.prompt_tokens,
                result.completion_tokens,
                result.total_tokens,
            )
            trace.contract = {
                "schema_sha256": digest(answer_schema),
                "finish_reason": result.finish_reason,
                "output_budget": result.budget_trace,
                **response_observation(result),
            }
            materialization = {}
            first_error = None
            try:
                internal_reasoning, clean_content = split_reasoning_and_answer(result.content)
                if internal_reasoning:
                    trace.reasoning["irac_analysis"] = internal_reasoning
                proposed = parse_answer(clean_content, sources)
                proposed, hygiene = clean_model_answer(proposed, req.question)
                draft = materialize(proposed, sources, cells, report=materialization)
                coverage = assess(draft, sources, trace.context, report=materialization)
                trace.grounding["hygiene"] = {"stage": "generation", **hygiene}
            except AppException as exc:
                first_error = exc
                await record_workspace_event(
                    db,
                    workspace_id=workspace_id,
                    actor=actor,
                    action="answer.validation_failed",
                    detail={
                        "answer_id": answer_id,
                        "usage_id": usage.id,
                        "code": exc.code,
                        "issues": getattr(exc, "validation_issues", []),
                        "output_sha256": digest(result.content),
                        "finish_reason": result.finish_reason,
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                        "total_tokens": result.total_tokens,
                        "max_output_tokens": request.max_output_tokens,
                        "inference_configuration_hash": inference_hash,
                        "prompt_version": PROMPT_VERSION,
                        "reasoning": trace.reasoning,
                        "contract": trace.contract,
                        # IDs, counts and hashes only: a failed turn keeps the
                        # evidence shape without storing private source text.
                        "context_trace": {
                            "primary_ids": trace.context.get("primary_ids", []),
                            "added": trace.context.get("added", []),
                            "rank_band": trace.context.get("rank_band", []),
                            "table_support": trace.context.get("table_support"),
                            "unresolved_support_ids": trace.context.get("unresolved_support_ids", []),
                            "selection": trace.context.get("selection", {}),
                            "bytes_used": trace.context.get("bytes_used"),
                            "packing": trace.context.get("packing", {}),
                            "materialization": materialization,
                        },
                        "grounding": trace.grounding,
                    },
                )
                await db.commit()
                if first_error.code not in REPAIR_INSTRUCTIONS:
                    raise
            trace.appeal = {"attempted": False}
        if req.fact_query is None and (
            first_error is not None or draft.status == "insufficient_evidence"
        ):
            repair_code = first_error.code if first_error is not None else None
            trace.appeal = {
                "version": APPEAL_VERSION,
                "attempted": False,
                "trigger": repair_code or "insufficient_evidence",
                "outcome": "skipped_structure",
            }
            if plan_ready(plan_for(sources, trace.context)) or first_error is not None:
                needs = selection.get("needs", {})
                list_names = (
                    repair_code == "answer_table_value_not_extractive"
                    and needs.get("enumeration")
                    and not needs.get("single_value")
                )
                # A leading unselectable table may be the very list requested.
                # In that case names must come verbatim from its original text.
                unavailable = {item["evidence_id"] for item in cells["issues"]}
                prefer_names = list_names and sources[0].evidence_id not in unavailable
                names_schema = name_repair_schema(answer_schema, cells) if prefer_names else None
                retry_schema = names_schema or answer_schema
                retry_messages = appeal_messages(
                    messages,
                    repair_code,
                    names_only=names_schema is not None,
                    list_names=list_names,
                )
                try:
                    retry_runtime, retry_request, retry_budget = await prepare_chat_request(
                        db,
                        actor,
                        workspace_id,
                        retry_messages,
                        provider_id=runtime.provider_id,
                        task="answer",
                        max_output_tokens=req.max_output_tokens,
                        output_schema=retry_schema,
                    )
                except AppException as exc:
                    if exc.code not in {
                        "model_input_limit_exceeded",
                        "model_output_limit_exceeded",
                        "model_context_limit_exceeded",
                    }:
                        raise
                    trace.appeal.update({"outcome": "skipped_budget", "code": exc.code})
                else:
                    if retry_runtime.inference_configuration_hash("answer") != inference_hash:
                        raise Conflict("Model chat đã thay đổi.", code="chat_provider_changed")
                    trace.appeal.update({"attempted": True, "outcome": "failed"})
        if trace.appeal["attempted"]:
            trace.appeal["schema_sha256"] = digest(retry_schema)
            appeal_usage = await usage_service.reserve(
                db,
                actor,
                workspace_id,
                "chat",
                answer_id + ":appeal",
                digest(
                    {
                        "question": req.question,
                        "evidence": proof,
                        "config": runtime.configuration_hash,
                        "inference_config": inference_hash,
                        "prompt_version": PROMPT_VERSION,
                        "appeal_version": APPEAL_VERSION,
                        "trigger": trace.appeal["trigger"],
                        "messages_sha256": digest([m.content for m in retry_messages]),
                        "schema_sha256": trace.appeal["schema_sha256"],
                        "cell_catalog_sha256": trace.grounding["catalog_sha256"],
                        "metadata_filter": req.metadata_filter.model_dump(
                            mode="json", exclude_none=True
                        ),
                    }
                ),
                retry_budget.total_reserved_tokens,
                runtime.provider_id,
            )
            trace.appeal["usage_id"] = appeal_usage.id
            try:
                await safety_check()
                await db.commit()
            except (Exception, asyncio.CancelledError):
                await usage_service.settle(db, appeal_usage.id, total_tokens=0, failed=True)
                raise
            appeal_started = time.monotonic()
            try:
                appeal_result = await chat.complete(
                    retry_messages, bind_usage(retry_request, appeal_usage.id)
                )
            except ChatResponseError as exc:
                await usage_service.settle(
                    db, appeal_usage.id, total_tokens=exc.usage_tokens, failed=True
                )
                trace.appeal.update({"outcome": "provider_error", "code": exc.code})
            except (Exception, asyncio.CancelledError):
                await usage_service.settle(db, appeal_usage.id, total_tokens=None, failed=True)
                raise
            else:
                await usage_service.settle(
                    db, appeal_usage.id, total_tokens=appeal_result.total_tokens
                )
                trace.stage_ms["appeal"] = round((time.monotonic() - appeal_started) * 1000, 3)
                trace.appeal.update(
                    {
                        "prompt_tokens": appeal_result.prompt_tokens,
                        "completion_tokens": appeal_result.completion_tokens,
                        "total_tokens": appeal_result.total_tokens,
                    }
                )
                appeal_report = {}
                appeal_hygiene = {}
                try:
                    appeal_reasoning, appeal_clean = split_reasoning_and_answer(appeal_result.content)
                    if appeal_reasoning:
                        trace.appeal["irac_analysis"] = appeal_reasoning
                    appeal_proposed = parse_answer(appeal_clean, sources)
                    appeal_proposed, appeal_hygiene = clean_model_answer(
                        appeal_proposed, req.question
                    )
                    if names_schema is not None:
                        allowed_names = set(
                            names_schema["$defs"]["CellSelection"]["properties"]["cell_id"]["enum"]
                        )
                        if appeal_proposed.statements or any(
                            item.cell_id not in allowed_names for item in appeal_proposed.lookups
                        ):
                            raise AppException(
                                "Lượt sửa phải chọn tên trong danh mục.",
                                code="answer_cell_invalid",
                                status_code=502,
                            )
                    appeal_draft = materialize(
                        appeal_proposed, sources, cells, report=appeal_report
                    )
                    appeal_coverage = assess(
                        appeal_draft, sources, trace.context, report=appeal_report
                    )
                except AppException as exc:
                    trace.appeal.update(
                        {
                            "outcome": "invalid",
                            "code": exc.code,
                            "issues": getattr(exc, "validation_issues", [])[:20],
                        }
                    )
                else:
                    repaired_abstention = (
                        first_error is not None
                        and first_error.code == "answer_table_value_not_extractive"
                        and names_schema is None
                        and bool(appeal_draft.message)
                    )
                    if appeal_draft.status == "answered" or repaired_abstention:
                        trace.appeal["first_tokens"] = {
                            "prompt_tokens": trace.prompt_tokens,
                            "completion_tokens": trace.completion_tokens,
                            "total_tokens": trace.total_tokens,
                        }
                        result, proposed, draft = appeal_result, appeal_proposed, appeal_draft
                        coverage, materialization = appeal_coverage, appeal_report
                        trace.grounding["hygiene"] = {"stage": "appeal", **appeal_hygiene}
                        trace.prompt_tokens = result.prompt_tokens
                        trace.completion_tokens = result.completion_tokens
                        trace.total_tokens = result.total_tokens
                        trace.contract = {
                            "schema_sha256": digest(retry_schema),
                            "finish_reason": result.finish_reason,
                            "output_budget": result.budget_trace,
                            **response_observation(result),
                        }
                        trace.appeal["outcome"] = (
                            "answered" if draft.status == "answered" else "safe_abstention"
                        )
                        first_error = None
                    else:
                        trace.appeal["outcome"] = "still_insufficient"
        if first_error is not None:
            await record_workspace_event(
                db,
                workspace_id=workspace_id,
                actor=actor,
                action="answer.repair_failed",
                detail={"answer_id": answer_id, **trace.appeal},
            )
            await db.commit()
            raise first_error
    else:
        trace.cache = {
            "version": answer_cache.VERSION,
            "status": "hit",
            "key": cache_key or sem_key,
            "saved_tokens": cached.total_tokens,
        }
        trace.contract = dict(cached.contract)
        trace.stage_ms["generation"] = 0.0
        logger.info(
            "rag_answer_cache_hit",
            answer_id=answer_id,
            index_run_id=retrieval.index_run_id,
            saved_tokens=cached.total_tokens,
        )
    trace.grounding["selected_cells"] = [item.cell_id for item in proposed.lookups]
    trace.coverage = {"version": COVERAGE_VERSION, **coverage.model_dump()}
    trace.grounding["narrative_supports"] = continuation_supports(sources)
    trace.grounding["projection"] = {
        "version": PROJECTION_VERSION,
        "mode": (
            "mixed"
            if proposed.lookups and len(draft.statements) > len(proposed.lookups)
            else "selected_cells"
            if proposed.lookups
            else "narrative"
        ),
        "omitted_model_statements": len(proposed.statements)
        - (len(draft.statements) - len(proposed.lookups)),
    }
    trace.grounding["cell_proofs"] = [
        {
            key: cell[key]
            for key in ("cell_id", "evidence_ids", "source_cells", "data_year")
            if key in cell
        }
        for table in cells["tables"]
        for cell in table["cells"]
        if cell["cell_id"] in trace.grounding["selected_cells"]
    ]
    if materialization:
        trace.grounding["materialization"] = materialization
    started = time.monotonic()

    await safety_check()
    trace.stage_ms["validation"] = round((time.monotonic() - started) * 1000, 3)
    if draft.status == "answered" and req.verification_mode != "off":
        trace.verification = await verify(
            db, chat, actor, workspace_id, answer_id, req, draft.statements, sources, safety_check
        )
        trace.stage_ms["verification"] = trace.verification["ms"]
        await safety_check()
    response.status, response.statements = draft.status, draft.statements
    response.coverage = coverage
    visible = referenced_ids(draft, coverage)
    response.sources = [s for s in sources if s.evidence_id in visible]
    if draft.status == "answered":
        response.answer = "\n\n".join(
            s.text + " " + " ".join(f"[{e}]" for e in s.evidence_ids) for s in draft.statements
        )
        requested_years = set(cells.get("selection", {}).get("requested_years", []))
        proven_years = {
            item["data_year"] for item in trace.grounding["cell_proofs"] if "data_year" in item
        }
        missing_years = requested_years - proven_years
        if len(requested_years) > 1 and proven_years and missing_years and not proposed.statements:
            missing = ", ".join(map(str, sorted(missing_years)))
            response.answer += f"\n\nChưa xác minh được giá trị cho năm {missing} từ các ô đã đối chiếu."
            response.coverage = coverage.model_copy(update={"status": "partial"})
            trace.coverage["status"] = "partial"
            trace.grounding["missing_data_years"] = sorted(missing_years)
        if req.verification_mode == "enforce" and trace.verification["status"] != "supported":
            response.status = "insufficient_evidence"
            response.reason = (
                "answer_not_supported"
                if trace.verification["status"] == "unsupported"
                else "answer_verification_uncertain"
            )
            response.answer, response.statements = None, []
            response.coverage = coverage.model_copy(update={"status": "insufficient"})
            trace.coverage["status"] = "insufficient"
            if compose_insufficient_message:
                await compose_message(response.reason)
    else:
        response.reason = "model_abstained"
        trace.verification["skip_reason"] = "model_abstained"
        if draft.message:
            response.message = draft.message
            trace.fallback = {"source": "draft", "version": PROMPT_VERSION}
        elif compose_insufficient_message:
            await compose_message(response.reason)
    # Store exact answer cache
    if (
        cache_key is not None
        and cached is None
        and req.fact_query is None
        and response.status == "answered"
        and trace.verification["status"] in {"not_run", "supported"}
    ):
        await answer_cache.store(
            cache_key,
            answer_cache.Entry(
                version=answer_cache.VERSION,
                content=result.content,
                contract=trace.contract,
                total_tokens=result.total_tokens,
            ),
            cache_ttl,
        )
        logger.info(
            "rag_answer_cache_stored",
            answer_id=answer_id,
            total_tokens=result.total_tokens,
        )

    # Store semantic cache bound to (workspace_id, active_index_run_id, normalized_query)
    if (
        sem_cache_ttl > 0
        and cached is None
        and req.fact_query is None
        and response.status == "answered"
        and trace.verification["status"] in {"not_run", "supported"}
    ):
        await store_semantic_cache(
            sem_key,
            SemanticCacheEntry(
                workspace_id=workspace_id,
                collection_id=collection_id,
                index_run_id=retrieval.index_run_id,
                normalized_query=norm_q,
                raw_answer=result.content,
                saved_tokens=result.total_tokens,
            ),
            sem_cache_ttl,
        )
        logger.info(
            "rag_semantic_cache_stored",
            answer_id=answer_id,
            total_tokens=result.total_tokens,
        )
    if not trace.semantic_cache:
        trace.semantic_cache = {
            "status": "miss" if sem_cache_ttl > 0 else "disabled",
            "normalized_query": norm_q,
        }
    trace.stage_ms["total"] = round((time.monotonic() - request_started) * 1000, 3)
    logger.info(
        "rag_answer_completed",
        answer_id=answer_id,
        status=response.status,
        index_run_id=retrieval.index_run_id,
        sources=len(response.sources),
        provider_id=runtime.provider_id,
        total_tokens=trace.total_tokens,
        cache=trace.cache.get("status") or ("disabled" if cache_key is None else "miss"),
        stage_ms=trace.stage_ms,
    )
    return response
