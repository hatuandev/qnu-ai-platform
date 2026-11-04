"""Bounded section windows from the same published input; never use global ordinal adjacency."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.index.query_scope import result_scopes
from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
from qnu.domains.knowledge.index.search import _eligible, _hits, manifest
from qnu.domains.knowledge.metadata import matches_metadata
from qnu.domains.rag.answer.clause_context import clause_groups
from qnu.domains.rag.answer.projection import evidence_item
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.source_text import pinned_bundles
from qnu.domains.rag.answer.structure_context import (
    VERSION,
    enumeration_requested,
    needs_structure,
    select_groups,
    unresolved_references,
)
from qnu.domains.rag.answer.table_support import attach_table_support
from qnu.platform.errors import AppException, Conflict
from qnu.ports.blob_store import BlobStore
from qnu.ports.vector_store import VectorHit


def evidence_size(hit: SearchHit) -> int:
    # Two-digit IDs cover top20 plus at most four structural table dependencies.
    return len(json.dumps(evidence_item(hit, "E20"), ensure_ascii=False).encode("utf-8")) + 2


async def expand_context(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    result: SearchResponse,
    req: AnswerRequest,
    *,
    bundles: dict | None = None,
) -> tuple[SearchResponse, dict]:
    trace = {
        "window": req.context_window,
        "primary_ids": [h.chunk_id for h in result.hits],
        "added": [],
        "budget_bytes": req.context_max_bytes,
    }
    consumed = 2 + sum(evidence_size(h) for h in result.hits)
    trace["bytes_used"] = consumed
    if consumed > req.context_max_bytes:
        raise AppException(
            "Evidence chính vượt ngân sách context; giảm top_k hoặc tăng budget.",
            code="answer_context_budget_exceeded",
            status_code=422,
        )
    result, support_trace = await attach_table_support(
        db, blob, actor, workspace_id, collection_id, result, req
    )
    trace.update(support_trace)
    consumed = 2 + sum(evidence_size(h) for h in result.hits)
    trace["bytes_used"] = consumed
    if consumed > req.context_max_bytes:
        raise AppException(
            "Evidence cùng context bảng vượt ngân sách.",
            code="answer_context_budget_exceeded",
            status_code=422,
        )
    if not result.hits:
        trace["status"] = "no_hits"
        return result, trace
    if not req.context_window and not any(hit.kind == "paragraph" for hit in result.hits):
        trace["status"] = "disabled"
        return result, trace
    from qnu.domains.knowledge.publication.access import authorize

    await authorize(db, actor, workspace_id, collection_id)
    run = await db.get(IndexRun, result.index_run_id)
    if run is None or not run.is_active or run.status != "completed":
        raise Conflict("Index context đã thay đổi.", code="answer_evidence_changed")
    allowed, _ = await _eligible(db, blob, actor, run, req.document_ids)
    sealed = await manifest(db, blob, run)
    hit_inputs = select(IndexChunk.input_id).where(
        IndexChunk.run_id == run.id,
        IndexChunk.id.in_([hit.chunk_id for hit in result.hits]),
    )
    rows = list(
        (
            await db.scalars(
                select(IndexChunk)
                .where(
                    IndexChunk.run_id == run.id,
                    IndexChunk.input_id.in_([b.id for b in allowed]),
                    IndexChunk.input_id.in_(hit_inputs),
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
    known = {h.chunk_id for h in result.hits}
    anchors = {hit.chunk_id: hit for hit in result.hits}
    scopes = result_scopes(result, req.metadata_filter)
    additions = []
    truncated = 0
    structural = []
    if needs_structure(req.question):
        bundles = await pinned_bundles(db, blob, workspace_id, collection_id, result.hits, bundles)
        structural = select_groups(rows, result.hits, bundles, req.question)
        trace["structure"] = {
            "version": VERSION,
            "groups": structural,
            "enumeration_requested": enumeration_requested(req.question),
            "unresolved_references": unresolved_references(req.question, structural),
        }
    for group in structural:
        eligible = [
            by_id[key]
            for key in group["required_ids"]
            if any(matches_metadata(by_id[key].structure, scope) for scope in scopes)
        ]
        group["scope_excluded_ids"] = [
            key for key in group["required_ids"] if key not in {row.id for row in eligible}
        ]
        primary = anchors[group["primary_chunk_id"]]
        candidates = await _hits(
            db,
            run,
            allowed,
            [
                _neighbor_hit(row, run, primary.version_id)
                for row in eligible
                if row.id not in known
            ],
            sealed,
        )
        for candidate in candidates:
            size = evidence_size(candidate)
            if consumed + size > req.context_max_bytes or len(known) >= 20:
                truncated += 1
                continue
            additions.append(candidate)
            known.add(candidate.chunk_id)
            consumed += size
            trace["added"].append(
                {
                    "chunk_id": candidate.chunk_id,
                    "primary_chunk_id": primary.chunk_id,
                    "kind": "structure",
                }
            )
    for group in [] if structural else clause_groups(rows, set(anchors)):
        if not any(
            all(matches_metadata(row.structure, scope) for row in group) for scope in scopes
        ):
            continue
        missing = [row for row in group if row.id not in known]
        if not missing:
            continue
        primary = next(anchors[row.id] for row in group if row.id in anchors)
        candidates = await _hits(
            db,
            run,
            allowed,
            [_neighbor_hit(row, run, primary.version_id) for row in missing],
            sealed,
        )
        size = sum(evidence_size(hit) for hit in candidates)
        if consumed + size > req.context_max_bytes or len(known) + len(candidates) > 20:
            raise AppException(
                "Các điểm cùng khoản vượt ngân sách context.",
                code="answer_context_budget_exceeded",
                status_code=422,
            )
        additions.extend(candidates)
        known.update(row.id for row in missing)
        consumed += size
        trace["added"].extend(
            {"chunk_id": row.id, "primary_chunk_id": primary.chunk_id, "kind": "clause"}
            for row in missing
        )
    if not req.context_window:
        trace.update(status="expanded" if additions else "disabled", bytes_used=consumed)
        return result.model_copy(update={"hits": [*result.hits, *additions]}), trace

    pending = {}
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
        shared_scopes = [scope for scope in scopes if matches_metadata(primary.structure, scope)]
        for row in neighbors:
            if row.id in known or not any(
                matches_metadata(row.structure, scope) for scope in shared_scopes
            ):
                continue
            pending.setdefault(row.id, (row, hit.version_id, primary.id, parent))
    candidates = (
        await _hits(
            db,
            run,
            allowed,
            [_neighbor_hit(row, run, version) for row, version, _, _ in pending.values()],
            sealed,
        )
        if pending
        else []
    )
    for candidate in candidates:
        size = evidence_size(candidate)
        if consumed + size > req.context_max_bytes or len(result.hits) + len(additions) >= 20:
            truncated += 1
            continue
        additions.append(candidate)
        consumed += size
        _, _, primary_id, parent = pending[candidate.chunk_id]
        trace["added"].append(
            {"chunk_id": candidate.chunk_id, "primary_chunk_id": primary_id, "parent": parent}
        )
    trace.update(status="expanded", bytes_used=consumed, skipped_budget=truncated)
    return result.model_copy(update={"hits": [*result.hits, *additions]}), trace


def _neighbor_hit(row: IndexChunk, run: IndexRun, version_id: str) -> VectorHit:
    return VectorHit(
        row.point_id,
        0.0,
        {
            "run_id": run.id,
            "workspace_id": run.workspace_id,
            "collection_id": run.collection_id,
            "version_id": version_id,
            "chunk_id": row.id,
            "text_sha256": row.text_sha256,
        },
    )
