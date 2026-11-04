"""Build a staged dense generation, then atomically activate only a current publication snapshot."""

from __future__ import annotations

import asyncio
import hashlib

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.chunking import READABLE_CHUNKER_VERSIONS
from qnu.domains.knowledge.index.contextual import VERSION as CONTEXT_VERSION
from qnu.domains.knowledge.index.lease import (
    ClaimLost,
    assert_claim,
    claim,
    commit_owned,
    heartbeat,
)
from qnu.domains.knowledge.index.models import IndexChunk, IndexInput, IndexRun
from qnu.domains.knowledge.index.snapshots import assert_snapshot, publication_identity
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.embedding.runtime import resolve_embedding_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict, DependencyUnavailable
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.provider_execution import bind_usage
from qnu.ports.vector_store import VectorStore

logger = get_logger(__name__)


async def validate_target(db: AsyncSession, run: IndexRun, actor: AuthActor, vectors: VectorStore):
    await authorize(db, actor, run.workspace_id, run.collection_id, write=True)
    runtime = await resolve_embedding_runtime(db, run.workspace_id, run.provider_id)
    if (
        runtime.configuration_hash != run.config["provider"]["configuration_hash"]
        or vectors.target_hash != run.config["vector_target_hash"]
        or run.config["chunker_version"] not in READABLE_CHUNKER_VERSIONS
        or run.config.get("search_context_version") not in (None, CONTEXT_VERSION)
    ):
        raise Conflict(
            "Model/vector target/chunker đã thay đổi.", code="index_configuration_changed"
        )
    return runtime


async def _embed_pending(db, blob, run, actor, model: EmbeddingModel, vectors: VectorStore) -> None:
    rows = list(
        (
            await db.scalars(
                select(IndexChunk).where(IndexChunk.run_id == run.id).order_by(IndexChunk.ordinal)
            )
        ).all()
    )
    size = run.config["embedding_batch_size"]
    for start in range(0, len(rows), size):
        batch = [row for row in rows[start : start + size] if row.vector is None]
        if not batch:
            continue
        runtime = await validate_target(db, run, actor, vectors)
        await assert_snapshot(db, blob, actor, run)
        texts = [row.text for row in batch]
        budget = runtime.budget(texts)
        await assert_claim(db, run)
        request_hash = digest(
            {
                "run_id": run.id,
                "chunk_ids": [c.id for c in batch],
                "text_hashes": [c.text_sha256 for c in batch],
                "model": runtime.configuration_hash,
            }
        )
        usage = await usage_service.reserve(
            db,
            actor,
            run.workspace_id,
            "embedding",
            f"index:{run.id}:{start}",
            request_hash,
            budget,
            run.provider_id,
        )
        await assert_claim(db, run)
        run.pending_batch = {
            "start": start,
            "usage_id": usage.id,
            "chunk_ids": [c.id for c in batch],
        }
        await commit_owned(db, run)
        try:
            result = await model.embed(texts, bind_usage(runtime.request(), usage.id))
        except AppException:
            await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
            raise
        try:
            await assert_claim(db, run)
        except ClaimLost:
            # Account for a measured upstream response even when its job was cancelled.
            await usage_service.settle(db, usage.id, total_tokens=result.total_tokens, failed=True)
            raise
        raw_sha = hashlib.sha256(result.raw_body).hexdigest()
        raw_key = f"v1/workspaces/{run.workspace_id}/index/{run.id}/batches/{start}-{raw_sha}.json"
        try:
            await blob.put_bytes(raw_key, result.raw_body, "application/json")
        except Exception as exc:
            raise DependencyUnavailable(
                "Không lưu được phản hồi embedding.", code="storage_unavailable"
            ) from exc
        if result.dimension != run.dimension or len(result.vectors) != len(batch):
            raise Conflict(
                "Embedding không khớp số chunk/dimension.", code="embedding_dimension_mismatch"
            )
        for chunk, vector in zip(batch, result.vectors, strict=True):
            chunk.vector = vector
        run.batch_receipts = [
            *run.batch_receipts,
            {
                "start": start,
                "count": len(batch),
                "raw_key": raw_key,
                "raw_sha256": raw_sha,
                "usage_id": usage.id,
                "total_tokens": result.total_tokens,
            },
        ]
        run.pending_batch = None
        await commit_owned(db, run)
        await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
        logger.info(
            "index_batch_embedded",
            run_id=run.id,
            start=start,
            count=len(batch),
            dimension=run.dimension,
        )


async def _write_vectors(db, blob, run, actor, vectors: VectorStore) -> None:
    await validate_target(db, run, actor, vectors)
    await assert_snapshot(db, blob, actor, run)
    await assert_claim(db, run)
    await vectors.ensure_collection(run.vector_collection, run.dimension)
    rows = (
        await db.execute(
            select(IndexChunk, IndexInput)
            .join(IndexInput, IndexChunk.input_id == IndexInput.id)
            .where(IndexChunk.run_id == run.id)
            .order_by(IndexChunk.ordinal)
        )
    ).all()
    for start in range(0, len(rows), 64):
        points = []
        for chunk, binding in rows[start : start + 64]:
            if chunk.vector is None or len(chunk.vector) != run.dimension:
                raise Conflict("Chunk chưa có vector hoàn chỉnh.", code="index_vectors_incomplete")
            points.append(
                {
                    "id": chunk.point_id,
                    "vector": chunk.vector,
                    "payload": {
                        "run_id": run.id,
                        "workspace_id": run.workspace_id,
                        "collection_id": run.collection_id,
                        "version_id": binding.version_id,
                        "chunk_id": chunk.id,
                        "text_sha256": chunk.text_sha256,
                    },
                }
            )
        await assert_claim(db, run)
        await vectors.upsert(run.vector_collection, points)
    await commit_owned(db, run)


async def _activate(db, blob, run, actor, vectors: VectorStore) -> str:
    await validate_target(db, run, actor, vectors)
    published = await assert_snapshot(db, blob, actor, run)
    if digest([publication_identity(p) for p in published]) != run.input_sha256:
        raise Conflict("Snapshot index không khớp publication.", code="index_publication_changed")
    if run.config.get("replacement_action_id"):
        from qnu.domains.lifecycle.replacement import activate_replacement

        published = await activate_replacement(db, blob, actor, run)
    chunks = list(
        (
            await db.scalars(
                select(IndexChunk).where(IndexChunk.run_id == run.id).order_by(IndexChunk.ordinal)
            )
        ).all()
    )
    manifest = {
        "schema_version": "qnu.index.manifest/v1",
        "run_id": run.id,
        "generation": run.generation,
        "inputs": [publication_identity(p) for p in published],
        "input_sha256": run.input_sha256,
        "config": run.config,
        "dimension": run.dimension,
        "vector_collection": run.vector_collection,
        "chunks": [
            {
                "id": c.id,
                "point_id": c.point_id,
                "text_sha256": c.text_sha256,
                "vector_sha256": digest(c.vector),
                "citations_sha256": digest(c.citations),
                "structure_sha256": digest(c.structure),
            }
            for c in chunks
        ],
        "batch_receipts": run.batch_receipts,
    }
    payload = json_bytes(manifest)
    sha = hashlib.sha256(payload).hexdigest()
    key = f"v1/workspaces/{run.workspace_id}/index/{run.id}/manifest/{sha}.json"
    try:
        await blob.put_bytes(key, payload, "application/json")
    except Exception as exc:
        raise DependencyUnavailable(
            "Không lưu được index manifest.", code="storage_unavailable"
        ) from exc
    await assert_claim(db, run)
    await db.execute(
        update(IndexRun)
        .where(
            IndexRun.collection_id == run.collection_id,
            IndexRun.id != run.id,
            IndexRun.is_active.is_(True),
        )
        .values(is_active=False)
    )
    run.manifest_key, run.manifest_sha256 = key, sha
    run.status, run.is_active, run.finished_at = "completed", True, utcnow()
    run.lease_expires_at = None
    run.error_code = None
    await record_workspace_event(
        db,
        workspace_id=run.workspace_id,
        actor=actor,
        action="index.activated",
        detail={"run_id": run.id, "manifest_sha256": sha, "chunks": run.chunks_total},
    )
    await commit_owned(db, run)
    return "completed"


async def execute_run(
    db: AsyncSession,
    blob: BlobStore,
    run_id: str,
    *,
    worker_id: str,
    model: EmbeddingModel,
    vectors: VectorStore,
) -> str:
    seconds = get_settings().INDEX_LEASE_SECONDS
    run = await claim(db, run_id, worker_id, seconds)
    if run is None:
        return "not_claimed"
    token = run.worker_id
    actor = background_actor(run.requested_by)
    async with heartbeat(run, seconds):
        try:
            if run.pending_batch is not None:
                await usage_service.settle(
                    db, run.pending_batch["usage_id"], total_tokens=None, failed=True
                )
                raise AppException("Worker bị ngắt khi embedding.", code="embedding_uncertain")
            if run.attempt_count > get_settings().INDEX_MAX_ATTEMPTS:
                raise Conflict("Đã hết số lần chạy index.", code="index_attempts_exhausted")
            for receipt in run.batch_receipts:
                await usage_service.settle(
                    db, receipt["usage_id"], total_tokens=receipt["total_tokens"]
                )
            await _embed_pending(db, blob, run, actor, model, vectors)
            await _write_vectors(db, blob, run, actor, vectors)
            status = await _activate(db, blob, run, actor, vectors)
            logger.info(
                "index_completed", run_id=run.id, generation=run.generation, chunks=run.chunks_total
            )
            return status
        except asyncio.CancelledError:
            await db.rollback()
            raise
        except ClaimLost:
            await db.rollback()
            logger.warning("index_claim_lost", run_id=run_id)
            return "not_claimed"
        except Exception as exc:
            await db.rollback()
            run = await db.get(IndexRun, run_id, populate_existing=True)
            if run is None or run.worker_id != token:
                return "not_claimed"
            code = exc.code if isinstance(exc, AppException) else "index_failed"
            try:
                await assert_claim(db, run)
                uncertain = code == "embedding_uncertain" or (
                    run.pending_batch is not None
                    and code
                    not in {
                        "embedding_unreachable",
                        "embedding_auth_failed",
                        "embedding_rate_limited",
                        "embedding_unavailable",
                        "embedding_rejected",
                        "embedding_response_invalid",
                        "embedding_dimension_mismatch",
                        "embedding_vector_invalid",
                        "embedding_count_mismatch",
                        "embedding_model_mismatch",
                    }
                )
                retry = (
                    code in {"vector_unavailable", "storage_unavailable"}
                    and not uncertain
                    and run.attempt_count < get_settings().INDEX_MAX_ATTEMPTS
                )
                run.status = "uncertain" if uncertain else "queued" if retry else "failed"
                run.error_code = code
                if not retry:
                    from qnu.domains.lifecycle.replacement import fail_replacement

                    await fail_replacement(db, run, code)
                run.lease_expires_at = None
                run.finished_at = None if retry else utcnow()
                if retry:
                    run.dispatched_at = None
                await commit_owned(db, run)
                logger.warning("index_stopped", run_id=run.id, status=run.status, error_code=code)
                return run.status
            except ClaimLost:
                await db.rollback()
                return "not_claimed"
