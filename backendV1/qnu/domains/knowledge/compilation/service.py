"""Compiler use cases: authorize, pin evidence/model, persist, dispatch and read."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation import outputs as compilation_outputs
from qnu.domains.knowledge.compilation import refinement
from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation.artifacts import (
    artifact,
    json_bytes,
    read,
    read_segment,
    store,
)
from qnu.domains.knowledge.compilation.drafting import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    messages_for,
    output_schema,
)
from qnu.domains.knowledge.compilation.evidence import load_documents
from qnu.domains.knowledge.compilation.models import (
    CompilationArtifact,
    CompilationInput,
    CompilationRun,
    CompilationSegment,
    CompilationSegmentArtifact,
    utcnow,
)
from qnu.domains.knowledge.compilation.scheduler import effective_concurrency
from qnu.domains.knowledge.compilation.schemas import (
    CompilationProgress,
    CompilationRequest,
    CompilationSegmentProgress,
)
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES, load_collection
from qnu.domains.knowledge.source_sections import reading_groups
from qnu.domains.lifecycle.guards import require_compilation_sources
from qnu.domains.modelops.inference.service import (
    available_input_tokens,
    prepare_chat_limits,
    prepare_chat_request,
)
from qnu.domains.modelops.public_api import assert_provider_allowed
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict, EntityNotFound
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


@dataclass(frozen=True, slots=True)
class CompilationOutcome:
    run: CompilationRun
    created: bool
    dispatched: bool


async def authorize_collection(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    *,
    write: bool = False,
    lock: bool = False,
) -> None:
    await resolve_workspace_access(
        db,
        actor,
        workspace_id,
        required_roles=WRITE_ROLES if write else READ_ROLES,
        for_update=lock,
    )
    await load_collection(db, workspace_id, collection_id)


async def get_run(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
) -> CompilationRun:
    await authorize_collection(db, actor, workspace_id, collection_id)
    run = await db.scalar(
        select(CompilationRun).where(
            CompilationRun.id == run_id,
            CompilationRun.workspace_id == workspace_id,
            CompilationRun.collection_id == collection_id,
        )
    )
    if run is None:
        raise EntityNotFound("Không tìm thấy lượt biên soạn.", code="compilation_not_found")
    await require_compilation_sources(db, workspace_id, run.id)
    return run


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
    if req.source_first:
        provider = await assert_provider_allowed(db, actor, workspace_id, "chat", req.provider_id)
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
            provider_id=provider.id,
            config={
                "source_first": True,
                "workflow_version": "qnu.compiler.source-first/v1",
                "auto_review": False,
                "review": {"provider_id": provider.id},
            },
        )
        db.add(run)
        await db.flush()
        return await _persist_inputs(db, blob, actor, run, documents, payload, queue)
    schema = output_schema(documents) if req.structured_output and not req.ai_supplement else None
    requested_output = req.max_output_tokens
    provider_id = req.provider_id
    planned_runtime = None
    if req.max_output_tokens is None and not req.ai_supplement:
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
    if req.ai_supplement:
        runtime, budget = await prepare_chat_limits(
            db,
            actor,
            workspace_id,
            provider_id=provider_id,
            task="compiler",
            max_output_tokens=requested_output,
        )
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
            raise AppException(
                "Chưa xác định được ngân sách biên soạn.", code="model_capacity_required"
            )
        plans = await asyncio.to_thread(
            split.plan_segments,
            documents,
            req.topic,
            capacity=capacity,
            structured=req.structured_output,
            projection=projection,
            output_tokens=budget.max_output_tokens,
        )
        plans = await asyncio.to_thread(
            split.finalize_plans,
            plans,
            documents,
            req.topic,
            capacity=capacity,
            structured=req.structured_output,
            projection=projection,
        )
    reasoning_directive = runtime.reasoning_directive("compiler")
    config = {
        **({"ai_supplement": True} if req.ai_supplement else {}),
        "refinement": {
            "version": 1,
            "max_depth": 4,
            "max_nodes": len(plans) * 31,
            "max_seconds": 1500,
        },
        "workflow_version": "qnu.compiler.workflow/v2" if plans else "qnu.compiler.workflow/v1",
        "auto_review": req.auto_review,
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
        if req.ai_supplement
        else PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(
            (
                split.segment_system(1, len(plans), projection=projection)
                if req.ai_supplement
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
            "auto_review": req.auto_review,
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


async def read_result(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    kind: str,
) -> tuple[CompilationArtifact | CompilationSegmentArtifact, bytes]:
    if run.status != "completed" and kind in {"draft_json", "markdown"}:
        raise Conflict(
            "Lượt biên soạn chưa có bản nháp hoàn tất.", code="compilation_not_completed"
        )
    if kind == "raw_response" and await artifact(db, run.id, kind) is None:
        # Preserve the single-source raw API; multi-root runs use per-node artifacts.
        roots = list(
            (
                await db.scalars(
                    select(CompilationSegment)
                    .where(
                        CompilationSegment.run_id == run.id,
                        CompilationSegment.parent_segment_id.is_(None),
                    )
                    .limit(2)
                )
            ).all()
        )
        if len(roots) == 1:
            return await read_segment(db, blob, roots[0], kind)
    return await read(db, blob, run, kind)


async def read_draft_view(
    db: AsyncSession, blob: BlobStore, run: CompilationRun
) -> tuple[str, dict]:
    _, payload = await read_result(db, blob, run, "draft_json")
    snapshot, raw_input = await read(db, blob, run, "input_snapshot")
    if snapshot.sha256 != run.input_sha256:
        raise Conflict("Snapshot Compiler khác nguồn đã ghim.", code="compilation_source_mismatch")
    content = json.loads(payload)
    content["reading_groups"] = reading_groups(content, json.loads(raw_input)["documents"])
    return hashlib.sha256(json_bytes(content)).hexdigest(), content


async def progress(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
) -> CompilationProgress:
    """Report only durable part states and provider-observed token counts."""
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    segments = list(
        (
            await db.scalars(
                select(CompilationSegment)
                .where(CompilationSegment.run_id == run.id)
                .where(CompilationSegment.parent_segment_id.is_(None))
                .order_by(CompilationSegment.segment_index)
            )
        ).all()
    )
    latest = await compilation_outputs.latest(db, run.id)
    nodes = list(
        (
            await db.scalars(
                select(CompilationSegment)
                .where(
                    CompilationSegment.run_id == run.id,
                )
                .order_by(CompilationSegment.segment_index)
            )
        ).all()
    )
    counts: dict[str, int] = {}
    for segment in segments:
        counts[segment.status] = counts.get(segment.status, 0) + 1
    segmented = bool(run.config.get("segmentation")) or bool(segments)
    if segmented:
        completed = counts.get("completed", 0)
        pending = counts.get("pending", 0)
        # A received part already has provider bytes but is still being validated.
        running = counts.get("running", 0) + counts.get("received", 0)
        failed = counts.get("failed", 0)
        uncertain = counts.get("uncertain", 0)
        cancelled = counts.get("cancelled", 0)
        observed = [
            segment.usage_tokens for segment in segments if segment.usage_tokens is not None
        ]
        active = [
            segment.segment_index
            for segment in segments
            if segment.status in {"running", "received"}
        ]
        concurrency = effective_concurrency(run.config)
    else:
        # A single-call run is one durable request; map its status without inventing parts.
        completed = int(run.status == "completed")
        pending = int(run.status == "queued")
        running = int(run.status == "running")
        failed = int(run.status == "failed")
        uncertain = int(run.status == "uncertain")
        cancelled = int(run.status == "cancelled")
        observed = []
        active = []
        concurrency = 1
    usage_tokens = sum(observed) if observed else run.usage_tokens
    if run.config.get("refinement"):
        usage_tokens = refinement.total_usage(nodes)
    elapsed_seconds = (
        round(((run.finished_at or utcnow()) - run.started_at).total_seconds(), 1)
        if run.started_at is not None
        else None
    )
    return CompilationProgress(
        refinement_timeout_seconds=(run.config.get("refinement") or {}).get("max_seconds", 0),
        nodes=[
            {
                "id": node.id,
                "parent_id": node.parent_segment_id,
                "index": node.segment_index,
                "status": node.status,
                "error_code": node.error_code,
                "request_usage_tokens": refinement.request_usage(node),
            }
            for node in nodes
        ],
        run_id=run.id,
        status=run.status,
        workflow_version=str(run.config.get("workflow_version", "qnu.compiler.workflow/v1")),
        segmented=segmented,
        total=len(segments) if segmented else 1,
        completed=completed,
        pending=pending,
        running=running,
        failed=failed,
        uncertain=uncertain,
        cancelled=cancelled,
        usage_tokens=usage_tokens,
        started_at=run.started_at,
        finished_at=run.finished_at,
        latest_output_generation=latest.generation if latest is not None else None,
        latest_output_partial=latest.partial if latest is not None else None,
        segments=[
            CompilationSegmentProgress(
                index=segment.segment_index,
                status=segment.status,
                attempt_count=segment.attempt_count,
                usage_tokens=segment.usage_tokens,
                error_code=segment.error_code,
                started_at=segment.started_at,
                finished_at=segment.finished_at,
                duration_seconds=(
                    round((segment.finished_at - segment.started_at).total_seconds(), 1)
                    if segment.started_at is not None and segment.finished_at is not None
                    else None
                ),
            )
            for segment in segments
        ],
        received=counts.get("received", 0) if segmented else 0,
        concurrency=concurrency,
        active_segments=active,
        elapsed_seconds=elapsed_seconds,
        planner_version=(run.config.get("segmentation") or {}).get("planner_version"),
        queue_timeout_seconds=get_settings().MODEL_CHAT_QUEUE_TIMEOUT_SECONDS,
    )


async def read_partial_draft(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
) -> tuple[str, bytes]:
    """Latest partial JSON generation; never the final publication pointer."""
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    row = await compilation_outputs.latest(db, run.id, partial=True)
    if row is None:
        raise EntityNotFound("Chưa có bản nháp từng phần.", code="compilation_partial_not_found")
    draft, _ = await compilation_outputs.read_output(db, blob, row)
    return row.draft_sha256, draft


async def read_segment_raw(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    segment_index: int,
    kind: str = "raw_response",
) -> tuple[str, str, bytes]:
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    segment = await db.scalar(
        select(CompilationSegment).where(
            CompilationSegment.run_id == run.id,
            CompilationSegment.segment_index == segment_index,
        )
    )
    if segment is None:
        raise EntityNotFound("Không tìm thấy phần biên soạn.", code="compilation_segment_not_found")
    if kind not in {"raw_response", "draft_json", "markdown"}:
        raise EntityNotFound("Không có loại artifact này.", code="compilation_artifact_not_found")
    artifact, payload = await read_segment(db, blob, segment, kind)
    return artifact.content_type, artifact.sha256, payload
