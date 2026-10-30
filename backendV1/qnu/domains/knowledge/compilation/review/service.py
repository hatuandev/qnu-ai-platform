"""Authorize and pin review targets, persist request before quota can commit."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review import artifacts
from qnu.domains.knowledge.compilation.review.material import ReviewMaterial, load_material
from qnu.domains.knowledge.compilation.review.models import CompilationReview, ReviewArtifact
from qnu.domains.knowledge.compilation.review.report import (
    PROMPT_VERSION,
    SYSTEM,
    VERSION,
    messages_for,
    output_schema,
)
from qnu.domains.knowledge.compilation.review.schemas import ReviewRequest
from qnu.domains.knowledge.compilation.service import get_run
from qnu.domains.knowledge.policies.access import READ_ROLES, load_collection
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.public_api import ChatRuntime
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatMessage, ChatRequest

REVIEW_ROLES = ("admin", "editor", "reviewer")


async def authorize(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    *,
    write: bool = False,
) -> None:
    await resolve_workspace_access(
        db,
        actor,
        workspace_id,
        required_roles=REVIEW_ROLES if write else READ_ROLES,
        for_update=write,
    )
    await load_collection(db, workspace_id, collection_id)


async def expire(db: AsyncSession, row: CompilationReview) -> None:
    if row.status == "running" and row.expires_at <= utcnow():
        await db.refresh(row, with_for_update=True)
        if row.status != "running" or row.expires_at > utcnow():
            return
        row.status, row.error_code, row.finished_at = (
            "uncertain",
            "compilation_review_interrupted",
            utcnow(),
        )
        await db.commit()


async def get_review(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
) -> CompilationReview:
    await get_run(db, actor, workspace_id, collection_id, run_id)
    row = await db.scalar(
        select(CompilationReview).where(
            CompilationReview.id == review_id,
            CompilationReview.compilation_run_id == run_id,
            CompilationReview.workspace_id == workspace_id,
            CompilationReview.collection_id == collection_id,
        )
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy lượt review.", code="compilation_review_not_found")
    await expire(db, row)
    return row


async def list_reviews(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    limit: int,
    offset: int,
) -> list[CompilationReview]:
    await get_run(db, actor, workspace_id, collection_id, run_id)
    rows = list(
        (
            await db.scalars(
                select(CompilationReview)
                .where(
                    CompilationReview.compilation_run_id == run_id,
                    CompilationReview.workspace_id == workspace_id,
                    CompilationReview.collection_id == collection_id,
                )
                .order_by(CompilationReview.created_at.desc(), CompilationReview.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    for row in rows:
        await expire(db, row)
    return rows


async def target_matches(
    db: AsyncSession, blob: BlobStore, row: CompilationReview, run: CompilationRun
) -> ReviewMaterial:
    material = await load_material(db, blob, run)
    if (row.input_sha256, row.draft_sha256, row.bundle_sha256) != (
        material.bundle.input_sha256,
        material.bundle.draft_sha256,
        material.bundle.bundle_sha256,
    ):
        raise Conflict(
            "Nguồn hoặc bản nháp đã khác đối tượng review.",
            code="compilation_review_target_changed",
        )
    return material


async def checkpoint(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, row: CompilationReview, run: CompilationRun
) -> None:
    await authorize(db, actor, row.workspace_id, row.collection_id, write=True)
    await db.refresh(row, with_for_update=True)
    if row.status != "running" or row.expires_at <= utcnow():
        raise Conflict("Lượt review đã hết thời gian chờ.", code="compilation_review_expired")
    await target_matches(db, blob, row, run)


async def prepare(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    req: ReviewRequest,
    key: str,
) -> tuple[
    CompilationRun,
    CompilationReview,
    ReviewMaterial | None,
    ChatRuntime | None,
    tuple[ChatRequest, list[ChatMessage]] | None,
]:
    await authorize(db, actor, workspace_id, collection_id, write=True)
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
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
        if previous.request_hash != request_hash:
            raise Conflict("Idempotency-Key đã dùng cho review khác.", code="idempotency_conflict")
        await expire(db, previous)
        return run, previous, None, None, None
    material = await load_material(db, blob, run)
    messages = messages_for(material.payload, structured=req.structured_output)
    schema = output_schema(material.payload) if req.structured_output else None
    runtime, request, budget = await prepare_chat_request(
        db,
        actor,
        workspace_id,
        messages,
        provider_id=req.provider_id,
        task="compiler_review",
        max_output_tokens=req.max_output_tokens,
        output_schema=schema,
    )
    row = CompilationReview(
        id=new_id("rvw"),
        compilation_run_id=run_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        created_by=actor_ref(actor),
        idempotency_key=key,
        request_hash=request_hash,
        status="running",
        provider_id=runtime.provider_id,
        input_sha256=material.bundle.input_sha256,
        draft_sha256=material.bundle.draft_sha256,
        bundle_sha256=material.bundle.bundle_sha256,
        expires_at=utcnow() + timedelta(seconds=max(900, runtime.timeout_seconds + 60)),
        trace={
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": digest(SYSTEM),
            "provider_id": runtime.provider_id,
            "model_name": runtime.model_name,
            "configuration_hash": runtime.configuration_hash,
            "routing": list(runtime.routing_trace),
            "compiler_provider_id": run.provider_id,
            "source_unit_count": len(material.payload["source_units"]),
            "draft_unit_count": len(material.payload["draft_units"]),
            "max_output_tokens": budget.max_output_tokens,
            "total_reserved_tokens": budget.total_reserved_tokens,
            "structured_output": req.structured_output,
            "output_schema_sha256": digest(schema) if schema is not None else None,
        },
    )
    db.add(row)
    await db.flush()
    await artifacts.store(db, blob, row, "input_snapshot", artifacts_payload(material))
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
        },
    )
    await db.commit()
    return run, row, material, runtime, (request, messages)


def artifacts_payload(material: ReviewMaterial) -> bytes:
    return json_bytes(
        {
            "schema_version": VERSION,
            "bundle_sha256": material.bundle.bundle_sha256,
            **material.payload,
        }
    )


async def read_output(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    kind: str,
) -> tuple[ReviewArtifact, bytes]:
    row = await get_review(db, actor, workspace_id, collection_id, run_id, review_id)
    if kind in {"report_json", "markdown"}:
        if row.status != "completed":
            raise Conflict(
                "Review chưa có báo cáo hoàn tất.", code="compilation_review_not_completed"
            )
        run = await get_run(db, actor, workspace_id, collection_id, run_id)
        await target_matches(db, blob, row, run)
    return await artifacts.read(db, blob, row, kind)
