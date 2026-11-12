"""Retrieval → evidence → ModelOps generation → citation and current-source validation."""

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.query_scope import result_scopes
from qnu.domains.knowledge.index.schemas import SearchRequest
from qnu.domains.knowledge.index.validation import validate_results
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.public_api import resolve_chat_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.rag.answer.cells import PROJECTION_VERSION, materialize
from qnu.domains.rag.answer.cells import VERSION as CELLS_VERSION
from qnu.domains.rag.answer.context import expand_context
from qnu.domains.rag.answer.coverage import VERSION as COVERAGE_VERSION
from qnu.domains.rag.answer.coverage import assess, referenced_ids
from qnu.domains.rag.answer.drafting import (
    PROMPT_VERSION,
    output_schema,
    parse_answer,
    payload_metrics,
    response_observation,
    sources_for,
)
from qnu.domains.rag.answer.narrative import continuation_supports
from qnu.domains.rag.answer.packing import pack_messages as _pack_messages
from qnu.domains.rag.answer.projection import PAYLOAD_VERSION
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
    persona: str = "",
    checkpoint: Callable[[], Awaitable[None]] | None = None,
    reranker: Reranker | None = None,
) -> AnswerResponse:
    answer_id = "ans_" + uuid.uuid4().hex
    trace = AnswerTrace(
        prompt_version=PROMPT_VERSION,
        verification={"mode": req.verification_mode, "status": "not_run"},
    )
    request_started = time.monotonic()
    retrieval = await search(
        db,
        blob,
        embedding,
        vectors,
        actor,
        workspace_id,
        collection_id,
        SearchRequest(
            query=retrieval_query or req.question,
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
    response = AnswerResponse(
        id=answer_id,
        status="insufficient_evidence",
        index_run_id=retrieval.index_run_id,
        generation=retrieval.generation,
        trace=trace,
    )
    context_started = time.monotonic()
    bundles = {}
    retrieval, trace.context = await expand_context(
        db,
        blob,
        actor,
        workspace_id,
        collection_id,
        retrieval,
        req,
        bundles=bundles,
        resolved_question=retrieval_query,
    )
    trace.stage_ms["context"] = round((time.monotonic() - context_started) * 1000, 3)
    if not retrieval.hits:
        response.reason = retrieval.status
        trace.verification["skip_reason"] = "no_evidence"
        trace.stage_ms["total"] = round((time.monotonic() - request_started) * 1000, 3)
        return response
    selected_hits, selection = select_hits(
        retrieval.hits,
        trace.context,
        req.question,
        resolved_question=retrieval_query,
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
    await attach_source_text(db, blob, workspace_id, collection_id, sources, bundles=bundles)
    packing_started = time.monotonic()
    messages, cells, envelope, evidence_bytes, skipped = _pack_messages(
        req,
        sources,
        trace.context,
        resolved_question=retrieval_query,
        persona=persona,
        metadata_filter=(
            {
                "any_of": [
                    s.model_dump(mode="json", exclude_none=True)
                    for s in result_scopes(retrieval, req.metadata_filter)
                ]
            }
            if req.scope_resolution == "catalog"
            else req.metadata_filter.model_dump(mode="json", exclude_none=True)
        ),
    )
    trace.stage_ms["packing"] = round((time.monotonic() - packing_started) * 1000, 3)
    if skipped:
        retrieval = retrieval.model_copy(update={"hits": retrieval.hits[: len(sources)]})
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
    proof_started = time.monotonic()
    proof = await validate_results(
        db, blob, vectors, actor, workspace_id, collection_id, retrieval, req.document_ids
    )
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
        reasoning_task="answer",
        max_output_tokens=req.max_output_tokens,
        output_schema=answer_schema,
    )
    trace.stage_ms["model_prepare"] = round((time.monotonic() - prepare_started) * 1000, 3)
    inference_hash = runtime.inference_configuration_hash("answer")
    trace.inference_configuration_hash = inference_hash
    trace.reasoning = runtime.reasoning_trace("answer")
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
                "metadata_filter": req.metadata_filter.model_dump(mode="json", exclude_none=True),
            }
        ),
        budget.total_reserved_tokens,
        runtime.provider_id,
    )
    trace.evidence_sha256, trace.usage_id = proof, usage.id
    trace.provider_id, trace.model_name = runtime.provider_id, runtime.model_name
    trace.configuration_hash = runtime.configuration_hash
    trace.routing = list(runtime.routing_trace)
    try:
        # Reservation commits. Recheck before HTTP, then release locks during inference.
        if proof != await validate_results(
            db, blob, vectors, actor, workspace_id, collection_id, retrieval, req.document_ids
        ):
            raise Conflict("Evidence thay đổi trước khi gọi model.", code="answer_evidence_changed")
        current = await resolve_chat_runtime(db, workspace_id, runtime.provider_id)
        if current.inference_configuration_hash("answer") != inference_hash:
            raise Conflict("Model chat đã thay đổi.", code="chat_provider_changed")
        if checkpoint is not None:
            await checkpoint()
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
    try:
        proposed = parse_answer(result.content, sources)
        draft = materialize(proposed, sources, cells)
        coverage = assess(draft, sources, trace.context)
    except AppException as exc:
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
            },
        )
        await db.commit()
        raise
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
        {key: cell[key] for key in ("cell_id", "evidence_ids", "source_cells")}
        for table in cells["tables"]
        for cell in table["cells"]
        if cell["cell_id"] in trace.grounding["selected_cells"]
    ]
    started = time.monotonic()

    async def safety_check():
        if proof != await validate_results(
            db, blob, vectors, actor, workspace_id, collection_id, retrieval, req.document_ids
        ):
            raise Conflict("Evidence thay đổi khi model trả lời.", code="answer_evidence_changed")
        current = await resolve_chat_runtime(db, workspace_id, runtime.provider_id)
        if current.inference_configuration_hash("answer") != inference_hash:
            raise Conflict("Model chat đã thay đổi khi trả lời.", code="chat_provider_changed")
        if checkpoint is not None:
            await checkpoint()

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
    else:
        response.reason = "model_abstained"
        trace.verification["skip_reason"] = "model_abstained"
    trace.stage_ms["total"] = round((time.monotonic() - request_started) * 1000, 3)
    logger.info(
        "rag_answer_completed",
        answer_id=answer_id,
        status=response.status,
        index_run_id=retrieval.index_run_id,
        sources=len(response.sources),
        provider_id=runtime.provider_id,
        total_tokens=result.total_tokens,
        stage_ms=trace.stage_ms,
    )
    return response
