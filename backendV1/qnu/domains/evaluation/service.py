"""One frozen candidate run per query; dense/hybrid/rerank comparisons share corpus and candidates."""

import time
import uuid
from functools import partial

from sqlalchemy import select

from qnu.domains.evaluation.answer_eval import evaluate_answer
from qnu.domains.evaluation.metrics import aggregate, retrieval_metrics
from qnu.domains.knowledge.index import hybrid
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.index.schemas import SearchRequest
from qnu.domains.knowledge.index.search import _eligible, search
from qnu.domains.knowledge.index.validation import validate_results
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.operations.service import authorize
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.service import answer as run_answer
from qnu.platform.errors import AppException, Conflict, DependencyUnavailable
from qnu.ports.reranker import Reranker


async def evaluate(
    db,
    blob,
    embedding,
    vectors,
    actor,
    workspace_id,
    collection_id,
    req,
    *,
    reranker: Reranker | None = None,
    chat_model=None,
):
    await authorize(db, actor, workspace_id, write=True)
    if req.include_rerank and reranker is None:
        raise DependencyUnavailable("Chưa có adapter rerank.", code="reranker_unavailable")
    if req.include_answer_evaluation and chat_model is None:
        raise DependencyUnavailable(
            "Chưa có adapter language model cho answer evaluation.", code="model_unavailable"
        )
    run = await db.scalar(
        select(IndexRun).where(
            IndexRun.id == req.index_run_id,
            IndexRun.workspace_id == workspace_id,
            IndexRun.collection_id == collection_id,
            IndexRun.is_active.is_(True),
            IndexRun.status == "completed",
        )
    )
    if run is None or run.manifest_sha256 != req.manifest_sha256:
        raise Conflict(
            "Snapshot đánh giá không còn hiện hành.", code="evaluation_snapshot_mismatch"
        )
    for query in req.queries:
        allowed, _ = await _eligible(db, blob, actor, run, query.document_ids)
        available = set(
            (
                await db.scalars(
                    select(IndexChunk.id).where(
                        IndexChunk.run_id == run.id,
                        IndexChunk.input_id.in_([b.id for b in allowed]),
                        IndexChunk.id.in_(query.gold_chunk_ids),
                    )
                )
            ).all()
        )
        if available != set(query.gold_chunk_ids):
            raise Conflict(
                "Gold IDs không thuộc snapshot/phạm vi đang đánh giá.",
                code="evaluation_gold_mismatch",
            )
    records = []
    for query in req.queries:
        strategies = ["dense", "hybrid"] + (["hybrid_rerank"] if req.include_rerank else [])
        started = time.monotonic()
        try:
            candidates = await search(
                db,
                blob,
                embedding,
                vectors,
                actor,
                workspace_id,
                collection_id,
                SearchRequest(
                    query=query.query,
                    mode="hybrid",
                    top_k=req.candidate_k,
                    candidate_k=req.candidate_k,
                    document_ids=query.document_ids,
                ),
            )
            if (
                candidates.index_run_id != req.index_run_id
                or candidates.trace.get("manifest_sha256") != req.manifest_sha256
            ):
                raise Conflict("Snapshot thay đổi khi đo.", code="evaluation_snapshot_mismatch")
            dense_ids = candidates.trace["dense_ranked_ids"]
            hybrid_ids = [h.chunk_id for h in candidates.hits]
            common = {
                "candidate_sha256": digest(hybrid_ids),
                "candidate_ids": hybrid_ids,
                "shared_retrieval_ms": round((time.monotonic() - started) * 1000, 3),
                "trace": candidates.trace,
            }

            ans_eval = None
            if req.include_answer_evaluation and query.expected_answer is not None:
                ans_res = await run_answer(
                    db,
                    blob,
                    embedding,
                    vectors,
                    chat_model,
                    actor,
                    workspace_id,
                    collection_id,
                    AnswerRequest(
                        question=query.query,
                        top_k=req.top_k,
                        document_ids=query.document_ids,
                        history=query.history,
                        calculation=query.calculation,
                        fact_query=query.fact_query,
                    ),
                    reranker=reranker,
                )
                ans_eval = evaluate_answer(ans_res, query.expected_answer)

            # dense is retrieval-only baseline
            records.append(record(query, "dense", dense_ids, req.top_k, common))
            # hybrid uses answer evaluation if requested
            records.append(
                record(query, "hybrid", hybrid_ids, req.top_k, common, answer_eval=ans_eval)
            )

            if req.include_rerank:
                trace = {"ranking": {}, "score_kinds": {}}

                checkpoint = partial(
                    validate_results,
                    db,
                    blob,
                    vectors,
                    actor,
                    workspace_id,
                    collection_id,
                    candidates,
                    query.document_ids,
                )

                reranked = (
                    await hybrid.rerank(
                        db,
                        actor,
                        workspace_id,
                        SearchRequest(
                            query=query.query,
                            mode="hybrid_rerank",
                            top_k=req.top_k,
                            candidate_k=req.candidate_k,
                            rerank_provider_id=req.rerank_provider_id,
                        ),
                        candidates.hits,
                        reranker,
                        trace,
                        checkpoint,
                    )
                    if candidates.hits
                    else []
                )
                changed = candidates.model_copy(update={"hits": reranked})
                await validate_results(
                    db,
                    blob,
                    vectors,
                    actor,
                    workspace_id,
                    collection_id,
                    changed,
                    query.document_ids,
                )
                records.append(
                    record(
                        query,
                        "hybrid_rerank",
                        [h.chunk_id for h in reranked],
                        req.top_k,
                        {**common, "rerank": trace},
                        answer_eval=ans_eval,
                    )
                )
        except AppException as exc:
            await db.rollback()
            existing = {r["strategy"] for r in records if r["query_id"] == query.id}
            for strategy in strategies:
                if strategy not in existing:
                    records.append(
                        {
                            "query_id": query.id,
                            "group": query.group,
                            "strategy": strategy,
                            "status": "error",
                            "error_code": exc.code,
                            "ranked_ids": [],
                            "metrics": None,
                        }
                    )

    if req.include_answer_evaluation:
        answer_records = [
            r for r in records
            if r.get("metrics") and r["metrics"].get("answer_passed") is not None
        ]
        total_eval = len(answer_records)
        passed_eval = sum(1 for r in answer_records if r["metrics"]["answer_passed"])
        failures_list = [
            {
                "query_id": r["query_id"],
                "strategy": r["strategy"],
                "failures": r["metrics"].get("answer_failures", []),
            }
            for r in answer_records
            if not r["metrics"]["answer_passed"]
        ]
        answer_eval_summary = {
            "status": "completed",
            "total_evaluated": total_eval,
            "passed_count": passed_eval,
            "failed_count": total_eval - passed_eval,
            "pass_rate": round(passed_eval / total_eval, 4) if total_eval else 0.0,
            "failures": failures_list,
        }
    else:
        answer_eval_summary = "NOT RUN"

    return {
        "schema_version": "qnu.retrieval-evaluation/v1",
        "id": "eval_" + uuid.uuid4().hex,
        "index_run_id": req.index_run_id,
        "manifest_sha256": req.manifest_sha256,
        "label_version": req.label_version,
        "label_status": req.label_status,
        "label_author": req.label_author,
        "top_k": req.top_k,
        "candidate_k": req.candidate_k,
        "records": records,
        "summary": aggregate(records),
        "answer_evaluation": answer_eval_summary,
        "publication_approval": False,
        "timing_boundary": "one shared embedding+dense+FTS+fusion per query; rerank incremental; no independent dense latency",
    }


def record(query, strategy, ranked, top_k, trace, *, answer_eval=None):
    return {
        "query_id": query.id,
        "group": query.group,
        "strategy": strategy,
        "status": "completed",
        "ranked_ids": ranked[:top_k],
        "candidate_trace": trace,
        "metrics": retrieval_metrics(
            ranked,
            query.gold_chunk_ids,
            top_k,
            answer_correctness=answer_eval.correctness_score if answer_eval else None,
            answer_groundedness=answer_eval.groundedness_score if answer_eval else None,
            answer_passed=answer_eval.passed if answer_eval else None,
            answer_failures=answer_eval.failures if answer_eval else None,
        ),
    }
