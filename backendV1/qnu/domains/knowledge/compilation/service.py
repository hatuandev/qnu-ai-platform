"""Compiler use cases: authorize, pin evidence/model, persist, dispatch and read."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation import supplement
from qnu.domains.knowledge.compilation.access import authorize_collection, get_run
from qnu.domains.knowledge.compilation.artifacts import json_bytes, store
from qnu.domains.knowledge.compilation.drafting import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    messages_for,
    output_schema,
)
from qnu.domains.knowledge.compilation.evidence import load_documents
from qnu.domains.knowledge.compilation.models import (
    CompilationInput,
    CompilationRun,
    CompilationSegment,
    utcnow,
)
from qnu.domains.knowledge.compilation.reads import (
    progress,
    progress_summary,
    read_draft_view,
    read_partial_draft,
    read_result,
    read_segment_raw,
)
from qnu.domains.knowledge.compilation.schemas import CompilationRequest
from qnu.domains.modelops.inference.service import (
    available_input_tokens,
    prepare_chat_limits,
    prepare_chat_request,
)
from qnu.domains.modelops.public_api import assert_provider_allowed
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

logger = get_logger(__name__)
TASK_NAME = "compile_run"
SEGMENTED_CODES = {
    "compilation_output_requires_segments",
    "model_context_limit_exceeded",
    "model_input_limit_exceeded",
    "model_output_limit_exceeded",
}
OPTIONAL_PLANNING_ERRORS = SEGMENTED_CODES | {
    "model_capacity_required",
    "compilation_segment_too_large",
    "compilation_segment_output_too_large",
}

__all__ = [
    "CompilationOutcome",
    "authorize_collection",
    "dispatch",
    "get_run",
    "list_runs",
    "progress",
    "progress_summary",
    "read_draft_view",
    "read_partial_draft",
    "read_result",
    "read_segment_raw",
    "request_run",
]


@dataclass(frozen=True, slots=True)
class CompilationOutcome:
    run: CompilationRun
    created: bool
    dispatched: bool


async def dispatch(db: AsyncSession, run: CompilationRun, queue: JobQueue | None) -> bool:
    if queue is None:
        return False
    try:
        await queue.enqueue(
            TASK_NAME, run.id, job_id=f"qnu:v1:compile:{run.id}:{run.attempt_count + 1}"
        )
    except Exception:
        logger.warning("compilation_dispatch_pending", run_id=run.id)
        return False
    now = utcnow()
    await db.execute(
        update(CompilationRun)
        .where(
            CompilationRun.id == run.id,
            CompilationRun.status == "queued",
        )
        .values(dispatched_at=now)
    )
    await db.commit()
    await db.refresh(run)
    return True


async def request_run(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    req: CompilationRequest,
    idempotency_key: str,
    queue: JobQueue | None,
    *,
    reuse_key: str | None = None,
) -> CompilationOutcome:
    await authorize_collection(db, actor, workspace_id, collection_id, write=True, lock=True)
    ref = actor_ref(actor)
    requested = {
        **req.model_dump(
            exclude={
                key
                for key in (
                    "structured_output",
                    "review_structured_output",
                    "source_first",
                    "ai_supplement",
                    "selective_supplement",
                )
                if not getattr(req, key)
            }
        ),
        "ocr_run_ids": sorted(req.ocr_run_ids),
        "collection_id": collection_id,
    }
    request_hash = hashlib.sha256(json_bytes(requested)).hexdigest()
    old = await db.scalar(
        select(CompilationRun).where(
            CompilationRun.workspace_id == workspace_id,
            CompilationRun.requested_by == ref,
            CompilationRun.idempotency_key == idempotency_key,
        )
    )
    if old is not None:
        legacy = {
            k: v
            for k, v in requested.items()
            if k
            not in {
                "text_versions",
                "auto_review",
                "review_provider_id",
                "review_max_output_tokens",
            }
        }
        legacy_replay = (
            "workflow_version" not in old.config
            and not (
                req.model_fields_set
                & {"text_versions", "auto_review", "review_provider_id", "review_max_output_tokens"}
            )
            and old.request_hash == hashlib.sha256(json_bytes(legacy)).hexdigest()
        )
        if old.request_hash != request_hash and not legacy_replay:
            raise Conflict("Idempotency-Key đã dùng cho yêu cầu khác.", code="idempotency_conflict")
        await db.commit()
        return CompilationOutcome(old, False, old.dispatched_at is not None)
    if idempotency_key.startswith("edit:"):
        raise Conflict("Khóa lưu bản sửa được dành riêng.", code="idempotency_conflict")
    documents = await load_documents(
        db, blob, workspace_id, collection_id, req.ocr_run_ids, req.text_versions
    )
    snapshot = {
        "schema_version": "qnu.compiler.input/v1",
        "topic": req.topic,
        "documents": documents,
    }
    payload = json_bytes(snapshot)
    generation = 1 + int(
        await db.scalar(
            select(func.max(CompilationRun.generation)).where(
                CompilationRun.collection_id == collection_id,
            )
        )
        or 0
    )
    selected_units = (
        await asyncio.to_thread(supplement.select_units, documents)
        if req.selective_supplement
        else None
    )

    async def persist_source_draft(error_code: str | None = None) -> CompilationOutcome:
        # Source-only work never calls a chat model. An explicitly pinned target is
        # still validated and recorded; otherwise the run truthfully has none.
        provider = (
            await assert_provider_allowed(db, actor, workspace_id, "chat", req.provider_id)
            if req.provider_id is not None
            else None
        )
        run = CompilationRun(
            id=new_id("cmp"),
            workspace_id=workspace_id,
            collection_id=collection_id,
            generation=generation,
            topic=req.topic,
            status="queued",
            requested_by=ref,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            input_sha256=hashlib.sha256(payload).hexdigest(),
            provider_id=provider.id if provider is not None else None,
            config={
                "source_first": True,
                **({"selective_supplement": True} if req.selective_supplement else {}),
                **({"supplement_plan_error": error_code} if error_code else {}),
                **({"reuse_key": reuse_key} if reuse_key else {}),
                "workflow_version": "qnu.compiler.source-first/v1",
                "auto_review": False,
                **({"review": {"provider_id": provider.id}} if provider is not None else {}),
            },
        )
        db.add(run)
        await db.flush()
        return await _persist_inputs(db, blob, actor, run, documents, payload, queue)

    if req.source_first or selected_units == []:
        return await persist_source_draft()
    has_supplement = req.ai_supplement or req.selective_supplement
    auto_review = req.auto_review and not req.selective_supplement
    schema = output_schema(documents) if req.structured_output and not has_supplement else None
    requested_output = req.max_output_tokens
    provider_id = req.provider_id
    planned_runtime = None
    if req.max_output_tokens is None and not has_supplement:
        planned_runtime, _ = await prepare_chat_limits(
            db,
            actor,
            workspace_id,
            provider_id=provider_id,
            task="compiler",
            max_output_tokens=None,
        )
        provider_id = planned_runtime.provider_id
    plans: list[split.SegmentPlan] = []
    projection = split.PROJECTION_SUPPLEMENT if req.ai_supplement else split.PROJECTION_V4
    if req.selective_supplement:
        projection = split.PROJECTION_SELECTIVE
    if has_supplement:
        try:
            runtime, budget = await prepare_chat_limits(
                db,
                actor,
                workspace_id,
                provider_id=provider_id,
                task="compiler",
                max_output_tokens=requested_output,
            )
        except AppException as exc:
            if req.selective_supplement and exc.code in OPTIONAL_PLANNING_ERRORS:
                return await persist_source_draft(exc.code)
            raise
    else:
        try:
            runtime, _, budget = await prepare_chat_request(
                db,
                actor,
                workspace_id,
                messages_for(req.topic, documents),
                provider_id=provider_id,
                task="compiler",
                reasoning_task="compiler",
                max_output_tokens=requested_output,
                output_schema=schema,
            )
            owned_size = await asyncio.to_thread(
                split.estimate_output_size, documents, split.build_units(documents)
            )
            content_budget = split.output_content_bytes(budget.max_output_tokens)
            if content_budget is not None and owned_size > content_budget:
                raise AppException(
                    "Nguồn cần chia phần theo ngân sách đầu ra.",
                    code="compilation_output_requires_segments",
                    status_code=422,
                )
        except AppException as exc:
            if exc.code not in SEGMENTED_CODES:
                raise
            runtime, budget = await prepare_chat_limits(
                db,
                actor,
                workspace_id,
                provider_id=provider_id,
                task="compiler",
                max_output_tokens=requested_output,
            )
            capacity = available_input_tokens(runtime.token_limits, budget.max_output_tokens)
            if capacity is None:
                raise AppException(
                    "Chưa xác định được ngân sách biên soạn.",
                    code="model_capacity_required",
                    status_code=422,
                ) from exc
            plans = await asyncio.to_thread(
                split.plan_segments,
                documents,
                req.topic,
                capacity=capacity,
                structured=req.structured_output,
                output_tokens=budget.max_output_tokens,
            )
            plans = await asyncio.to_thread(
                split.finalize_plans,
                plans,
                documents,
                req.topic,
                capacity=capacity,
                structured=req.structured_output,
            )
    if (
        planned_runtime is not None
        and runtime.configuration_hash != planned_runtime.configuration_hash
    ):
        raise Conflict("Model thay đổi trong lúc lập kế hoạch.", code="chat_provider_changed")
    if not plans:
        capacity = available_input_tokens(runtime.token_limits, budget.max_output_tokens)
        if capacity is None:
            if req.selective_supplement:
                return await persist_source_draft("model_capacity_required")
            raise AppException(
                "Chưa xác định được ngân sách biên soạn.", code="model_capacity_required"
            )
        try:
            plans = await asyncio.to_thread(
                split.plan_segments,
                documents,
                req.topic,
                capacity=capacity,
                structured=req.structured_output,
                projection=projection,
                output_tokens=budget.max_output_tokens,
                selected_units=selected_units,
            )
            plans = await asyncio.to_thread(
                split.finalize_plans,
                plans,
                documents,
                req.topic,
                capacity=capacity,
                structured=req.structured_output,
                projection=projection,
                selected_units=selected_units,
            )
        except AppException as exc:
            if req.selective_supplement and exc.code in OPTIONAL_PLANNING_ERRORS:
                return await persist_source_draft(exc.code)
            raise
    reasoning_directive = runtime.reasoning_directive("compiler")
    config = {
        **({"ai_supplement": True} if has_supplement else {}),
        **({"selective_supplement": True} if req.selective_supplement else {}),
        **({"reuse_key": reuse_key} if reuse_key else {}),
        "refinement": {
            "version": 1,
            "max_depth": 4,
            "max_nodes": len(plans) * 31,
        },
        "workflow_version": "qnu.compiler.workflow/v2" if plans else "qnu.compiler.workflow/v1",
        "auto_review": auto_review,
        "review": {
            "provider_id": req.review_provider_id or runtime.provider_id,
            "max_output_tokens": req.review_max_output_tokens,
            **({"structured_output": True} if req.review_structured_output else {}),
        },
        "provider": {
            **runtime.public_dict(),
            "reasoning": runtime.reasoning_trace("compiler"),
        },
        "max_output_tokens": budget.max_output_tokens,
        "automatic_output_budget": req.max_output_tokens is None,
        "reasoning_directive": (
            reasoning_directive.public_dict() if reasoning_directive is not None else None
        ),
        "prompt_version": split.prompt_version_for(projection)
        if has_supplement
        else PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(
            (
                split.segment_system(1, len(plans), projection=projection)
                if has_supplement
                else SYSTEM_PROMPT
            ).encode()
        ).hexdigest(),
        **(
            {
                "structured_output": True,
                "output_schema_sha256": hashlib.sha256(json_bytes(schema)).hexdigest(),
            }
            if schema is not None
            else {}
        ),
    }
    if plans:
        config["segmentation"] = {
            "planner_version": split.PLANNER_VERSION,
            "prompt_version": split.prompt_version_for(projection),
            "projection_version": projection,
            "segment_count": len(plans),
            "concurrency": get_settings().COMPILER_SEGMENT_CONCURRENCY,
            "input_capacity_tokens": available_input_tokens(
                runtime.token_limits, budget.max_output_tokens
            ),
            "output_tokens": budget.max_output_tokens,
            "output_content_bytes": split.output_content_bytes(budget.max_output_tokens),
            "manifest_sha256": None,
        }
    run = CompilationRun(
        id=new_id("cmp"),
        workspace_id=workspace_id,
        collection_id=collection_id,
        generation=generation,
        topic=req.topic,
        status="queued",
        requested_by=ref,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        input_sha256=hashlib.sha256(payload).hexdigest(),
        provider_id=runtime.provider_id,
        config=config,
    )
    db.add(run)
    await db.flush()
    if plans:
        manifest = split.manifest_for(
            run,
            plans,
            documents,
            capacity=available_input_tokens(runtime.token_limits, budget.max_output_tokens) or 0,
            output_tokens=budget.max_output_tokens,
        )
        manifest_payload = json_bytes(manifest)
        await store(db, blob, run, "segment_manifest", manifest_payload)
        run.config = {
            **run.config,
            "segmentation": {
                **run.config["segmentation"],
                "manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
            },
        }
        reasoning_public = (
            reasoning_directive.public_dict() if reasoning_directive is not None else None
        )
        segment_config = {
            "provider_id": runtime.provider_id,
            "configuration_hash": runtime.configuration_hash,
            "max_output_tokens": budget.max_output_tokens,
            "structured_output": bool(req.structured_output),
            "auto_review": auto_review,
            "projection_version": projection,
            # Stored verbatim so a resume sends the same reasoning contract or fails.
            "reasoning": reasoning_public,
        }
        for plan in plans:
            db.add(
                CompilationSegment(
                    id=new_id("cseg"),
                    run_id=run.id,
                    segment_index=plan.index,
                    status="pending",
                    scope=plan.scope_dict(),
                    input_sha256=plan.input_sha256,
                    prompt_version=split.prompt_version_for(projection),
                    schema_sha256=plan.schema_sha256,
                    config=segment_config,
                    request_hash=hashlib.sha256(
                        json_bytes(
                            {
                                "run_id": run.id,
                                "segment_index": plan.index,
                                "input_sha256": plan.input_sha256,
                                "schema_sha256": plan.schema_sha256,
                                "configuration_hash": runtime.configuration_hash,
                                "max_output_tokens": budget.max_output_tokens,
                                "structured_output": bool(req.structured_output),
                                "projection_version": plan.projection,
                                "reasoning": reasoning_public,
                            }
                        )
                    ).hexdigest(),
                )
            )
        await db.flush()
    return await _persist_inputs(db, blob, actor, run, documents, payload, queue)


async def _persist_inputs(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    run: CompilationRun,
    documents: list[dict],
    payload: bytes,
    queue: JobQueue | None,
) -> CompilationOutcome:
    for document in documents:
        db.add(
            CompilationInput(
                id=new_id("cin"),
                run_id=run.id,
                workspace_id=run.workspace_id,
                collection_id=run.collection_id,
                ocr_run_id=document["ocr_run_id"],
                canonical_sha256=document["canonical_sha256"],
                manifest_sha256=document["manifest_sha256"],
                text_version_id=document.get("text_version", {}).get("id"),
                original_canonical_sha256=document.get("original_canonical_sha256"),
            )
        )
    await store(db, blob, run, "input_snapshot", payload)
    await record_workspace_event(
        db,
        workspace_id=run.workspace_id,
        actor=actor,
        action="compilation.requested",
        detail={
            "run_id": run.id,
            "collection_id": run.collection_id,
            "input_sha256": run.input_sha256,
            "provider_id": run.provider_id,
        },
    )
    await db.commit()
    dispatched = await dispatch(db, run, queue)
    return CompilationOutcome(run, True, dispatched)


async def list_runs(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    limit: int,
    offset: int = 0,
) -> list[CompilationRun]:
    await authorize_collection(db, actor, workspace_id, collection_id)
    return list(
        (
            await db.scalars(
                select(CompilationRun)
                .where(
                    CompilationRun.workspace_id == workspace_id,
                    CompilationRun.collection_id == collection_id,
                )
                .order_by(CompilationRun.generation.desc(), CompilationRun.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
