"""Compiler use cases: authorize, pin evidence/model, persist, dispatch and read."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import json_bytes, read, store
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
    utcnow,
)
from qnu.domains.knowledge.compilation.schemas import CompilationRequest
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES, load_collection
from qnu.domains.lifecycle.guards import require_compilation_sources
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

logger = get_logger(__name__)
TASK_NAME = "compile_run"


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
                for key in ("structured_output", "review_structured_output")
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
    schema = output_schema(documents) if req.structured_output else None
    runtime, _, budget = await prepare_chat_request(
        db,
        actor,
        workspace_id,
        messages_for(req.topic, documents),
        provider_id=req.provider_id,
        max_output_tokens=req.max_output_tokens or get_settings().COMPILER_MAX_OUTPUT_TOKENS,
        output_schema=schema,
    )
    generation = 1 + int(
        await db.scalar(
            select(func.max(CompilationRun.generation)).where(
                CompilationRun.collection_id == collection_id,
            )
        )
        or 0
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
        provider_id=runtime.provider_id,
        config={
            "workflow_version": "qnu.compiler.workflow/v1",
            "auto_review": req.auto_review,
            "review": {
                "provider_id": req.review_provider_id or runtime.provider_id,
                "max_output_tokens": req.review_max_output_tokens,
                **({"structured_output": True} if req.review_structured_output else {}),
            },
            "provider": runtime.public_dict(),
            "max_output_tokens": budget.max_output_tokens,
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
            **(
                {
                    "structured_output": True,
                    "output_schema_sha256": hashlib.sha256(json_bytes(schema)).hexdigest(),
                }
                if schema is not None
                else {}
            ),
        },
    )
    db.add(run)
    await db.flush()
    for document in documents:
        db.add(
            CompilationInput(
                id=new_id("cin"),
                run_id=run.id,
                workspace_id=workspace_id,
                collection_id=collection_id,
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
        workspace_id=workspace_id,
        actor=actor,
        action="compilation.requested",
        detail={
            "run_id": run.id,
            "collection_id": collection_id,
            "input_sha256": run.input_sha256,
            "provider_id": runtime.provider_id,
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
) -> tuple[CompilationArtifact, bytes]:
    if run.status != "completed" and kind in {"draft_json", "markdown"}:
        raise Conflict(
            "Lượt biên soạn chưa có bản nháp hoàn tất.", code="compilation_not_completed"
        )
    return await read(db, blob, run, kind)
