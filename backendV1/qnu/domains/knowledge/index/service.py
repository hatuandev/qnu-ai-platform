"""Durable index requests and deterministic source-bound chunk preparation."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import read
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.compilation.service import get_run as get_compilation_run
from qnu.domains.knowledge.index.chunking import CHUNKER_VERSION, build_chunks
from qnu.domains.knowledge.index.contextual import VERSION, contextual_size, enrich
from qnu.domains.knowledge.index.models import IndexChunk, IndexInput, IndexRun
from qnu.domains.knowledge.index.schemas import IndexRequest
from qnu.domains.knowledge.index.snapshots import current_snapshot, publication_identity
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.embedding.runtime import resolve_embedding_runtime
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue
from qnu.ports.vector_store import VectorStore

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RequestedIndex:
    run: IndexRun
    created: bool
    dispatched: bool


async def dispatch(db: AsyncSession, run: IndexRun, queue: JobQueue | None) -> bool:
    if queue is None:
        return False
    try:
        await queue.enqueue(
            "index_run", run.id, job_id=f"qnu:v1:index:{run.id}:{run.attempt_count + 1}"
        )
    except Exception:
        logger.warning("index_dispatch_pending", run_id=run.id)
        return False
    await db.execute(
        update(IndexRun)
        .where(IndexRun.id == run.id, IndexRun.status == "queued")
        .values(dispatched_at=utcnow())
    )
    await db.commit()
    await db.refresh(run)
    return True


async def request_index(
    db: AsyncSession,
    blob: BlobStore,
    vector_store: VectorStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    req: IndexRequest,
    key: str,
    queue: JobQueue | None,
    *,
    prepared_publications=None,
    replacement_action_id: str | None = None,
    replacement_plan_sha256: str | None = None,
    commit: bool = True,
) -> RequestedIndex:
    await authorize(db, actor, workspace_id, collection_id, write=True)
    options = req.model_dump()
    if not req.contextual_search:
        options.pop("contextual_search")  # Existing idempotency receipts remain replayable.
    request_hash = digest({"collection_id": collection_id, **options})
    if replacement_action_id:
        request_hash = digest(
            {
                "request": request_hash,
                "replacement_action_id": replacement_action_id,
                "plan_sha256": replacement_plan_sha256,
            }
        )
    old = await db.scalar(
        select(IndexRun).where(
            IndexRun.workspace_id == workspace_id,
            IndexRun.requested_by == actor_ref(actor),
            IndexRun.idempotency_key == key,
        )
    )
    if old is not None:
        if old.request_hash != request_hash:
            raise Conflict("Idempotency-Key đã dùng cho yêu cầu khác.", code="idempotency_conflict")
        await db.commit()
        return RequestedIndex(old, False, old.dispatched_at is not None)
    if await db.scalar(
        select(IndexRun.id).where(
            IndexRun.collection_id == collection_id, IndexRun.status.in_(("queued", "running"))
        )
    ):
        raise Conflict("Collection đã có indexing đang chạy.", code="index_run_active")
    runtime = await resolve_embedding_runtime(db, workspace_id, req.provider_id)
    runtime.budget(["preflight"])
    published = (
        prepared_publications
        if prepared_publications is not None
        else await current_snapshot(db, blob, actor, workspace_id, collection_id)
    )
    settings = get_settings()
    limits = runtime.token_limits
    maximum = min(
        n - 32 for n in (limits.max_input_tokens, limits.context_window_tokens) if n is not None
    )
    if settings.INDEX_CHUNK_MAX_BYTES is not None:
        maximum = min(maximum, settings.INDEX_CHUNK_MAX_BYTES)
    if maximum < 64:
        raise Conflict("Capacity embedding quá nhỏ cho chunk.", code="embedding_capacity_required")
    latest = await db.scalar(
        select(func.max(IndexRun.generation)).where(IndexRun.collection_id == collection_id)
    )
    run = IndexRun(
        id=new_id("idx"),
        workspace_id=workspace_id,
        collection_id=collection_id,
        generation=int(latest or 0) + 1,
        status="queued",
        is_active=False,
        dimension=runtime.dimension,
        provider_id=runtime.provider_id,
        vector_collection="qnu_v1_idx_" + uuid.uuid4().hex,
        config={
            "provider": runtime.public_dict(),
            "chunker_version": CHUNKER_VERSION,
            "chunk_max_bytes": maximum,
            "embedding_batch_size": settings.INDEX_EMBED_BATCH_SIZE,
            "vector_target_hash": vector_store.target_hash,
            **({"search_context_version": VERSION} if req.contextual_search else {}),
        },
        input_sha256=digest([publication_identity(p) for p in published]),
        requested_by=actor_ref(actor),
        idempotency_key=key,
        request_hash=request_hash,
        attempt_count=0,
        chunks_total=0,
        batch_receipts=[],
    )
    db.add(run)
    if replacement_action_id:
        run.config = {
            **run.config,
            "replacement_action_id": replacement_action_id,
            "replacement_plan_sha256": replacement_plan_sha256,
        }
    await db.flush()
    for publication in published:
        binding = IndexInput(
            id=new_id("iin"),
            run_id=run.id,
            workspace_id=workspace_id,
            collection_id=collection_id,
            **publication_identity(publication),
        )
        db.add(binding)
        await db.flush()
        compilation = await get_compilation_run(
            db, actor, workspace_id, collection_id, publication.version.compilation_run_id
        )
        _, payload = await read(db, blob, compilation, "input_snapshot")
        documents = json.loads(payload)["documents"]
        sizing = (
            {"size": contextual_size(publication.content, documents)}
            if req.contextual_search
            else {}
        )
        chunks = build_chunks(
            publication.content,
            documents,
            maximum,
            [
                a.model_dump(mode="json", exclude_none=True)
                for a in publication.version.retrieval_metadata
            ],
            **sizing,
        )
        if req.contextual_search:
            chunks = enrich(chunks, publication.content, documents, maximum)
        reports = [
            c.structure["reading_quality"]
            for c in chunks
            if c.structure and "reading_quality" in c.structure
        ]
        run.config = {
            **run.config,
            "reading_quality": [
                *run.config.get("reading_quality", []),
                {
                    "input_id": binding.id,
                    "table_fragments": len(reports),
                    "review_required": sum(r["status"] == "review_required" for r in reports),
                },
            ],
        }
        for chunk in chunks:
            ordinal = run.chunks_total
            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{run.id}:{publication.version.id}:{ordinal}:{chunk.sha256}",
                )
            )
            db.add(
                IndexChunk(
                    id=new_id("ich"),
                    input_id=binding.id,
                    run_id=run.id,
                    workspace_id=workspace_id,
                    collection_id=collection_id,
                    ordinal=ordinal,
                    point_id=point_id,
                    kind=chunk.kind,
                    text=chunk.text,
                    text_sha256=chunk.sha256,
                    citations=chunk.citations,
                    structure=chunk.structure,
                    vector=None,
                )
            )
            run.chunks_total += 1
            if run.chunks_total > settings.INDEX_MAX_CHUNKS:
                raise Conflict("Generation vượt số chunk cho phép.", code="index_too_many_chunks")
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="index.requested",
        detail={
            "run_id": run.id,
            "input_sha256": run.input_sha256,
            "provider_id": runtime.provider_id,
        },
    )
    if not commit:
        await db.flush()
        return RequestedIndex(run, True, False)
    await db.commit()
    return RequestedIndex(run, True, await dispatch(db, run, queue))


async def get_run(
    db: AsyncSession, actor: AuthActor, workspace_id: str, collection_id: str, run_id: str
) -> IndexRun:
    await authorize(db, actor, workspace_id, collection_id)
    row = await db.scalar(
        select(IndexRun).where(
            IndexRun.id == run_id,
            IndexRun.workspace_id == workspace_id,
            IndexRun.collection_id == collection_id,
        )
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy indexing run.", code="index_not_found")
    return row
