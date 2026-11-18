"""Prepare, cancel and dispatch durable reviews with pinned targets and budgets."""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review import artifacts, parts, refinement, text_spans
from qnu.domains.knowledge.compilation.review.access import (
    REVIEW_ROLES,
    authorize,
    can_resume_segmented,
    checkpoint,
    expire,
    get_review,
    list_reviews,
    target_matches,
    untouched,
)
from qnu.domains.knowledge.compilation.review.literal import (
    assess_source_headings,
    assess_table_text_copies,
    retained_sections,
    source_prose_pairs,
)
from qnu.domains.knowledge.compilation.review.material import ReviewMaterial, load_material
from qnu.domains.knowledge.compilation.review.models import (
    CompilationReview,
    CompilationReviewSegment,
)
from qnu.domains.knowledge.compilation.review.readers import (
    artifacts_payload,
    progress,
    read_output,
    read_segment_artifact,
    read_segment_raw,
)
from qnu.domains.knowledge.compilation.review.report import (
    PROMPT_VERSION,
    SYSTEM,
    messages_for,
    output_schema,
)
from qnu.domains.knowledge.compilation.review.schemas import ReviewRequest
from qnu.domains.knowledge.compilation.service import get_run
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.document_processing import (
    configured_concurrency,
    resolve_document_group,
)
from qnu.domains.modelops.inference.service import (
    available_input_tokens,
    prepare_chat_limits,
    prepare_chat_request,
)
from qnu.domains.modelops.public_api import ChatRuntime, resolve_chat_runtime
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatMessage, ChatRequest
from qnu.ports.job_queue import JobQueue

__all__ = [
    "REVIEW_ROLES",
    "PreparedReview",
    "artifacts_payload",
    "authorize",
    "cancel_review",
    "checkpoint",
    "dispatch_review",
    "expire",
    "get_review",
    "list_reviews",
    "prepare",
    "progress",
    "read_output",
    "read_segment_artifact",
    "read_segment_raw",
    "target_matches",
    "untouched",
]

logger = get_logger(__name__)
SEGMENTED_CODES = {
    "model_context_limit_exceeded",
    "model_input_limit_exceeded",
    "model_output_limit_exceeded",
    "compilation_review_output_requires_segments",
}


@dataclass(frozen=True, slots=True)
class PreparedReview:
    run: CompilationRun
    review: CompilationReview
    material: ReviewMaterial | None
    runtime: ChatRuntime | None
    request: ChatRequest | None = None
    messages: list[ChatMessage] | None = None
    segmented: bool = False


async def prepare(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    req: ReviewRequest,
    key: str,
    *,
    enqueue: bool = False,
) -> PreparedReview:
    await authorize(db, actor, workspace_id, collection_id, write=True)
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    allow_structured = req.structured_output or "structured_output" not in req.model_fields_set
    if key == "auto:" + run_id:
        from qnu.domains.knowledge.compilation.workflow.models import AutoReviewJob

        parent = await db.get(AutoReviewJob, run_id, populate_existing=True)
        if parent is None or parent.status != "running":
            raise Conflict(
                "Review tự động không còn quyền thực thi.", code="compilation_auto_review_stopped"
            )
    request_hash = digest(
        {
            "run_id": run_id,
            "collection_id": collection_id,
            **req.model_dump(exclude={"structured_output"} if not req.structured_output else set()),
        }
    )
    previous = await db.scalar(
        select(CompilationReview).where(
            CompilationReview.workspace_id == workspace_id,
            CompilationReview.created_by == actor_ref(actor),
            CompilationReview.idempotency_key == key,
        )
    )
    if previous is not None:
        # Old rows used the compiler mode to choose the review contract. Replay
        # their existing plan even if today's automatic policy would choose another.
        stored_choice = previous.trace.get("allow_structured_review")
        if stored_choice is None:
            legacy_choice = run.source_first and allow_structured
            choice_matches = (
                previous.trace.get("concise_source_review", legacy_choice) == legacy_choice
            )
        else:
            choice_matches = stored_choice == allow_structured
        if previous.request_hash != request_hash or not choice_matches:
            raise Conflict("Idempotency-Key đã dùng cho review khác.", code="idempotency_conflict")
        if enqueue or previous.trace.get("background_review"):
            return PreparedReview(run, previous, None, None)
        await expire(db, previous)
        # Never resume a request that may still be in flight; a concurrent replay
        # could send the same part twice. Only a stopped review can continue, and a
        # stop before the first request is replayed because it sent nothing.
        if await can_resume_segmented(db, previous):
            segment_count = await db.scalar(
                select(func.count())
                .select_from(CompilationReviewSegment)
                .where(CompilationReviewSegment.review_id == previous.id)
            )
            if segment_count:
                runtime = await resolve_chat_runtime(db, workspace_id, previous.provider_id)
                if runtime.configuration_hash != previous.trace.get("configuration_hash"):
                    raise Conflict(
                        "Model review đã thay đổi; không thể tiếp tục.",
                        code="compilation_review_provider_changed",
                    )
                material = await target_matches(db, blob, previous, run)
                clock = refinement.resume_execution_trace(previous)
                if (
                    clock["execution_elapsed_seconds"]
                    >= refinement.limits_for(previous.trace, max(1, segment_count)).max_seconds
                ):
                    raise AppException(
                        "Review đã hết tổng ngân sách thời gian thực thi.",
                        code="compilation_review_budget_time_exceeded",
                        status_code=422,
                    )
                previous.status = "running"
                previous.trace = {
                    **clock,
                    "execution_token": new_id("rex"),
                }
                previous.error_code = None
                previous.finished_at = None
                previous.expires_at = utcnow() + timedelta(
                    seconds=max(900, runtime.timeout_seconds + 60) * max(1, segment_count)
                )
                await db.commit()
                return PreparedReview(
                    run=run,
                    review=previous,
                    material=material,
                    runtime=runtime,
                    segmented=True,
                )
        await db.commit()
        return PreparedReview(run, previous, None, None)
    material = await load_material(db, blob, run)
    # Review follows the document group's priority model unless the caller pinned one.
    review_provider = req.provider_id
    if review_provider is None:
        review_provider = (await resolve_document_group(db)).provider_id
    sections = (
        await asyncio.to_thread(retained_sections, material.payload, run.id)
        if allow_structured
        else []
    )
    concise = allow_structured and (run.source_first or bool(sections))
    structured = concise or req.structured_output
    schema = None
    single_call = (None, None)
    runtime: ChatRuntime
    plans: list[parts.ReviewPartPlan] = []
    span_layout: text_spans.SpanLayout = {}
    if not concise:
        messages = messages_for(material.payload, structured=structured)
        schema = output_schema(material.payload, require_references=2) if structured else None
        try:
            runtime, request, budget = await prepare_chat_request(
                db,
                actor,
                workspace_id,
                messages,
                provider_id=review_provider,
                task="compiler_review",
                max_output_tokens=req.max_output_tokens,
                output_schema=schema,
            )
            reasoning_dir = runtime.reasoning_directive()
            if not parts.requires_output_segmentation(
                material.payload,
                output_tokens=budget.max_output_tokens,
                structured=structured,
                reasoning_shares_budget=reasoning_dir is None or reasoning_dir.level != "off",
            ):
                single_call = (request, messages)
        except AppException as exc:
            if exc.code not in SEGMENTED_CODES:
                raise
    if single_call[0] is None:
        runtime, budget = await prepare_chat_limits(
            db,
            actor,
            workspace_id,
            provider_id=review_provider,
            task="compiler_review",
            max_output_tokens=req.max_output_tokens,
        )
        capacity = available_input_tokens(runtime.token_limits, budget.max_output_tokens)
        if capacity is None:
            raise AppException(
                "Chưa xác định được ngân sách review.",
                code="model_capacity_required",
                status_code=422,
            )
        reasoning_dir = runtime.reasoning_directive()
        reasoning_shares = reasoning_dir is None or reasoning_dir.level != "off"
        if concise:
            structural = assess_source_headings(material.payload, sections)
            if sections:
                structural += await asyncio.to_thread(assess_table_text_copies, material.payload)
            source_copies = source_prose_pairs(material.payload) if sections else None
            material, plans, span_layout = await asyncio.to_thread(
                text_spans.plan,
                material,
                capacity=capacity,
                output_tokens=budget.max_output_tokens,
                reasoning_shares_budget=reasoning_shares,
                structural_drafts=structural,
                source_copies=source_copies,
            )
        else:
            plans = await asyncio.to_thread(
                parts.plan_parts,
                material.payload,
                capacity=capacity,
                output_tokens=budget.max_output_tokens,
                structured=structured,
                reasoning_shares_budget=reasoning_shares,
            )
    reasoning = runtime.reasoning_directive()
    reasoning_shares = reasoning is None or reasoning.level != "off"
    out_budget = parts.output_budget(
        budget.max_output_tokens, reasoning_shares_budget=reasoning_shares
    )
    trace = {
        "background_review": enqueue,
        "literal_check_version": 1,
        "review_concurrency": await configured_concurrency(db, runtime.provider_id),
        "context_resolution_version": 2,
        "reference_contract_version": 2,
        "execution_token": new_id("rex"),
        "execution_started_at": utcnow().isoformat(),
        "execution_elapsed_seconds": 0.0,
        "execution_budget_basis": "cumulative_active/v1",
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": digest(SYSTEM),
        "provider_id": runtime.provider_id,
        "model_name": runtime.model_name,
        "configuration_hash": runtime.configuration_hash,
        "routing": list(runtime.routing_trace),
        "reasoning": reasoning.public_dict() if reasoning is not None else None,
        "reasoning_trace": runtime.reasoning_trace(),
        "compiler_provider_id": run.provider_id,
        "source_unit_count": len(material.payload["source_units"]),
        "draft_unit_count": len(material.payload["draft_units"]),
        "max_output_tokens": budget.max_output_tokens,
        "automatic_output_budget": req.max_output_tokens is None,
        "usable_output_tokens": out_budget.usable_output_tokens,
        "reasoning_reserve_tokens": out_budget.reasoning_reserve_tokens,
        "framing_reserve_tokens": out_budget.framing_reserve_tokens,
        "total_reserved_tokens": budget.total_reserved_tokens,
        "concise_source_review": concise,
        "allow_structured_review": allow_structured,
        "structured_output": structured,
        "output_schema_sha256": digest(schema) if schema is not None else None,
    }
    if plans:
        trace.update(
            {
                "workflow_version": "qnu.compiler.review.workflow/v2",
                "segmentation": {
                    "planner_version": parts.PLANNER_VERSION,
                    "prompt_version": plans[0].prompt_version,
                    "segment_count": len(plans),
                    "input_capacity_tokens": available_input_tokens(
                        runtime.token_limits, budget.max_output_tokens
                    ),
                    "output_tokens": budget.max_output_tokens,
                    "usable_output_tokens": out_budget.usable_output_tokens,
                    "reasoning_reserve_tokens": out_budget.reasoning_reserve_tokens,
                    "framing_reserve_tokens": out_budget.framing_reserve_tokens,
                    "manifest_sha256": None,
                },
            }
        )
    if span_layout:
        trace[text_spans.VERSION] = span_layout
    seconds = max(900, runtime.timeout_seconds + 60) * max(1, len(plans))
    row = CompilationReview(
        id=new_id("rvw"),
        compilation_run_id=run_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        created_by=actor_ref(actor),
        idempotency_key=key,
        request_hash=request_hash,
        status="queued" if enqueue else "running",
        provider_id=runtime.provider_id,
        input_sha256=material.bundle.input_sha256,
        draft_sha256=material.bundle.draft_sha256,
        bundle_sha256=material.bundle.bundle_sha256,
        expires_at=utcnow() + timedelta(seconds=seconds),
        trace=trace,
    )
    db.add(row)
    await db.flush()
    await artifacts.store(db, blob, row, "input_snapshot", artifacts_payload(material))
    if plans:
        await _store_segments(db, blob, row, run, plans, material, runtime, budget)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="compilation.review_requested",
        detail={
            "review_id": row.id,
            "compilation_run_id": run_id,
            "bundle_sha256": row.bundle_sha256,
            "provider_id": runtime.provider_id,
            "segments": len(plans),
        },
    )
    await db.commit()
    request, messages = single_call
    return PreparedReview(
        run=run,
        review=row,
        material=material,
        runtime=runtime,
        request=request,
        messages=messages,
        segmented=bool(plans),
    )


async def cancel_review(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
) -> CompilationReview:
    await authorize(db, actor, workspace_id, collection_id, write=True)
    row = await get_review(db, actor, workspace_id, collection_id, run_id, review_id)
    await db.refresh(row, with_for_update=True)
    if row.status in {"queued", "running"}:
        row.status, row.finished_at = "cancelled", utcnow()
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="compilation.review_cancelled",
            detail={"review_id": row.id},
        )
    await db.commit()
    return row


async def dispatch_review(queue: JobQueue | None, review_id: str) -> bool:
    if queue is None:
        return False
    try:
        async with asyncio.timeout(3):
            return await queue.enqueue(
                "manual_compiler_review_job",
                review_id,
                job_id=f"qnu:v1:manual-review:{review_id}:{int(utcnow().timestamp()) // 300}",
            )
    except Exception:
        logger.warning("manual_review_dispatch_pending", review_id=review_id)
        return False


async def _store_segments(
    db: AsyncSession,
    blob: BlobStore,
    row: CompilationReview,
    run: CompilationRun,
    plans: list[parts.ReviewPartPlan],
    material: ReviewMaterial,
    runtime: ChatRuntime,
    budget,
) -> None:
    reasoning_dir = runtime.reasoning_directive()
    reasoning_shares = reasoning_dir is None or reasoning_dir.level != "off"
    manifest = parts.manifest_for(
        row,
        plans,
        material.payload,
        capacity=available_input_tokens(runtime.token_limits, budget.max_output_tokens) or 0,
        output_tokens=budget.max_output_tokens,
        reasoning_shares_budget=reasoning_shares,
    )
    payload = json_bytes(manifest)
    await artifacts.store(db, blob, row, "segment_manifest", payload)
    row.trace = {
        **row.trace,
        "segmentation": {
            **row.trace["segmentation"],
            "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        },
    }
    config = {
        "provider_id": runtime.provider_id,
        "configuration_hash": runtime.configuration_hash,
        "max_output_tokens": budget.max_output_tokens,
        "structured_output": bool(row.trace.get("structured_output")),
        "reasoning": row.trace.get("reasoning"),
    }
    for plan in plans:
        db.add(
            CompilationReviewSegment(
                id=new_id("rvs"),
                review_id=row.id,
                segment_index=plan.index,
                status="pending",
                attempt_count=0,
                scope=plan.scope_dict(),
                input_sha256=plan.input_sha256,
                prompt_version=plan.prompt_version,
                schema_sha256=plan.schema_sha256,
                config=config,
                request_hash=digest(
                    {
                        "review_id": row.id,
                        "segment_index": plan.index,
                        "input_sha256": plan.input_sha256,
                        "schema_sha256": plan.schema_sha256,
                        "configuration_hash": runtime.configuration_hash,
                        "max_output_tokens": budget.max_output_tokens,
                        "structured_output": config["structured_output"],
                    }
                ),
            )
        )
    await db.flush()
