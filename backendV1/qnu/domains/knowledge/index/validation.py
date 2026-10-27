"""Revalidate already retrieved evidence without another query embedding or vector search."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.index.schemas import SearchResponse
from qnu.domains.knowledge.index.search import _eligible, _hits, manifest
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.embedding.runtime import resolve_embedding_runtime
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import Conflict
from qnu.ports.blob_store import BlobStore
from qnu.ports.vector_store import VectorHit, VectorStore


async def validate_results(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    result: SearchResponse,
    document_ids: list[str] | None,
) -> str:
    await resolve_workspace_access(db, actor, workspace_id, for_update=True)
    await authorize(db, actor, workspace_id, collection_id)
    run = await db.scalar(
        select(IndexRun)
        .where(
            IndexRun.id == result.index_run_id,
            IndexRun.workspace_id == workspace_id,
            IndexRun.collection_id == collection_id,
            IndexRun.is_active.is_(True),
            IndexRun.status == "completed",
        )
        .execution_options(populate_existing=True)
    )
    if run is None or vectors.target_hash != run.config["vector_target_hash"]:
        raise Conflict("Index đã thay đổi khi trả lời.", code="answer_evidence_changed")
    runtime = await resolve_embedding_runtime(db, workspace_id, run.provider_id)
    if runtime.configuration_hash != run.config["provider"]["configuration_hash"]:
        raise Conflict("Model embedding đã thay đổi.", code="index_configuration_changed")
    allowed, _ = await _eligible(db, blob, actor, run, document_ids)
    eligible = {(b.document_id, b.version_id, b.publication_decision_id) for b in allowed}
    if any(
        (h.document_id, h.version_id, h.publication_decision_id) not in eligible
        for h in result.hits
    ):
        raise Conflict(
            "Nguồn đã thu hồi hoặc thay đổi khi trả lời.", code="answer_evidence_changed"
        )
    sealed = await manifest(db, blob, run)
    chunks = list(
        (
            await db.scalars(
                select(IndexChunk)
                .where(
                    IndexChunk.run_id == run.id,
                    IndexChunk.id.in_([h.chunk_id for h in result.hits]),
                )
                .execution_options(populate_existing=True)
            )
        ).all()
    )
    by_id = {c.id: c for c in chunks}
    if len(by_id) != len(result.hits):
        raise Conflict("Chunk nguồn đã thay đổi.", code="answer_evidence_changed")
    raw = [
        VectorHit(
            by_id[h.chunk_id].point_id,
            h.score,
            {
                "run_id": run.id,
                "workspace_id": workspace_id,
                "collection_id": collection_id,
                "version_id": h.version_id,
                "chunk_id": h.chunk_id,
                "text_sha256": by_id[h.chunk_id].text_sha256,
            },
        )
        for h in result.hits
    ]
    current = await _hits(db, run, allowed, raw, sealed)
    if current != result.hits:
        raise Conflict("Nội dung evidence đã thay đổi.", code="answer_evidence_changed")
    return digest(
        {
            "workspace_id": workspace_id,
            "collection_id": collection_id,
            "document_ids": document_ids,
            "manifest_sha256": run.manifest_sha256,
            "hits": [h.model_dump() for h in current],
        }
    )
