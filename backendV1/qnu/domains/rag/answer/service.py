"""Retrieval → evidence → ModelOps generation → citation and current-source validation."""

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.schemas import SearchRequest
from qnu.domains.knowledge.index.search import search
from qnu.domains.knowledge.index.validation import validate_results
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.public_api import resolve_chat_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.rag.answer.context import expand_context
from qnu.domains.rag.answer.drafting import PROMPT_VERSION, messages_for, parse_answer, sources_for
from qnu.domains.rag.answer.schemas import AnswerRequest, AnswerResponse, AnswerTrace
from qnu.domains.rag.answer.verification import verify
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict
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
    started = time.monotonic()
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
            rrf_k=req.rrf_k,
        ),
        reranker=reranker,
    )
    trace.stage_ms["retrieval"] = round((time.monotonic() - started) * 1000, 3)
    trace.retrieval = retrieval.trace
    response = AnswerResponse(
        id=answer_id,
        status="insufficient_evidence",
        index_run_id=retrieval.index_run_id,
        generation=retrieval.generation,
        trace=trace,
    )
    context_started = time.monotonic()
    retrieval, trace.context = await expand_context(
        db, blob, actor, workspace_id, collection_id, retrieval, req
    )
    trace.stage_ms["context"] = round((time.monotonic() - context_started) * 1000, 3)
    if not retrieval.hits:
        response.reason = retrieval.status
        trace.verification["skip_reason"] = "no_evidence"
        return response
    sources = sources_for(retrieval)
    messages = messages_for(
        req.question,
        sources,
        resolved_question=retrieval_query,
        persona=persona,
        metadata_filter=req.metadata_filter.model_dump(mode="json", exclude_none=True),
    )
    proof = await validate_results(
        db, blob, vectors, actor, workspace_id, collection_id, retrieval, req.document_ids
    )
    runtime, request, budget = await prepare_chat_request(
        db,
        actor,
        workspace_id,
        messages,
        provider_id=req.provider_id,
        task="answer",
        max_output_tokens=req.max_output_tokens or get_settings().RAG_MAX_OUTPUT_TOKENS,
    )
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
                "prompt_version": PROMPT_VERSION,
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
        if current.configuration_hash != runtime.configuration_hash:
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
    draft = parse_answer(result.content, sources)
    started = time.monotonic()

    async def safety_check():
        if proof != await validate_results(
            db, blob, vectors, actor, workspace_id, collection_id, retrieval, req.document_ids
        ):
            raise Conflict("Evidence thay đổi khi model trả lời.", code="answer_evidence_changed")
        current = await resolve_chat_runtime(db, workspace_id, runtime.provider_id)
        if current.configuration_hash != runtime.configuration_hash:
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
    if draft.status == "answered":
        used = {e for s in draft.statements for e in s.evidence_ids}
        response.sources = [s for s in sources if s.evidence_id in used]
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
    else:
        response.reason = "model_abstained"
        trace.verification["skip_reason"] = "model_abstained"
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
