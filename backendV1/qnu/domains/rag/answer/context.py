"""Bounded section windows from the same published input; never use global ordinal adjacency."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
from qnu.domains.knowledge.index.search import _eligible, _hits, manifest
from qnu.domains.knowledge.metadata import matches_metadata
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.platform.errors import AppException, Conflict
from qnu.ports.blob_store import BlobStore
from qnu.ports.vector_store import VectorHit


def evidence_size(hit: SearchHit) -> int:
    # Match the JSON sent to the model. SQL/source locator DTOs are not prompt context.
    return (
        len(
            json.dumps(
                {"evidence_id": "E20", **hit.model_dump(include={"kind", "text", "structure"})},
                ensure_ascii=False,
            ).encode("utf-8")
        )
        + 2
    )


async def expand_context(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    result: SearchResponse,
    req: AnswerRequest,
) -> tuple[SearchResponse, dict]:
    trace = {
        "window": req.context_window,
        "primary_ids": [h.chunk_id for h in result.hits],
        "added": [],
        "budget_bytes": req.context_max_bytes,
    }
    if not req.context_window or not result.hits:
        trace["status"] = "disabled" if not req.context_window else "no_hits"
        return result, trace
    from qnu.domains.knowledge.publication.access import authorize

    await authorize(db, actor, workspace_id, collection_id)
    run = await db.get(IndexRun, result.index_run_id)
    if run is None or not run.is_active or run.status != "completed":
        raise Conflict("Index context đã thay đổi.", code="answer_evidence_changed")
    allowed, _ = await _eligible(db, blob, actor, run, req.document_ids)
    sealed = await manifest(db, blob, run)
    rows = list(
        (
            await db.scalars(
                select(IndexChunk)
                .where(
                    IndexChunk.run_id == run.id,
                    IndexChunk.input_id.in_([b.id for b in allowed]),
                )
                .order_by(IndexChunk.ordinal)
            )
        ).all()
    )
    by_id = {c.id: c for c in rows}
    groups = {}
    for row in rows:
        parent = (row.structure or {}).get("context", {}).get("parent")
        if parent is not None:
            groups.setdefault((row.input_id, parent), []).append(row)
    consumed = 2 + sum(evidence_size(h) for h in result.hits)
    if consumed > req.context_max_bytes:
        raise AppException(
            "Evidence chính vượt ngân sách context; giảm top_k hoặc tăng budget.",
            code="answer_context_budget_exceeded",
            status_code=422,
        )
    known = {h.chunk_id for h in result.hits}
    additions = []
    truncated = 0
    for hit in result.hits:
        primary = by_id[hit.chunk_id]
        parent = (primary.structure or {}).get("context", {}).get("parent")
        siblings = groups.get((primary.input_id, parent), [])
        if not siblings:
            continue  # Old generations remain readable without guessed relationships.
        position = next(i for i, c in enumerate(siblings) if c.id == primary.id)
        neighbors = siblings[
            max(0, position - req.context_window) : position + req.context_window + 1
        ]
        for row in neighbors:
            if row.id in known or not matches_metadata(row.structure, req.metadata_filter):
                continue
            raw = VectorHit(
                row.point_id,
                0.0,
                {
                    "run_id": run.id,
                    "workspace_id": workspace_id,
                    "collection_id": collection_id,
                    "version_id": hit.version_id,
                    "chunk_id": row.id,
                    "text_sha256": row.text_sha256,
                },
            )
            candidate = (await _hits(db, run, allowed, [raw], sealed))[0]
            size = evidence_size(candidate)
            if consumed + size > req.context_max_bytes or len(result.hits) + len(additions) >= 20:
                truncated += 1
                continue
            additions.append(candidate)
            known.add(row.id)
            consumed += size
            trace["added"].append(
                {"chunk_id": row.id, "primary_chunk_id": primary.id, "parent": parent}
            )
    trace.update(status="expanded", bytes_used=consumed, skipped_budget=truncated)
    return result.model_copy(update={"hits": [*result.hits, *additions]}), trace
