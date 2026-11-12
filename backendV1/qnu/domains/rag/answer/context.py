"""Bounded section windows from the same published input; never use global ordinal adjacency."""

import json
from collections import Counter

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
from qnu.domains.rag.answer.selection import question_needs
from qnu.domains.rag.answer.source_text import pinned_bundles
from qnu.domains.rag.answer.structure_context import (
    VERSION,
    continuation_groups,
    enumeration_requested,
    needs_structure,
    numbered_groups,
    select_groups,
    unresolved_references,
)
from qnu.domains.rag.answer.table_support import attach_table_support
from qnu.platform.errors import AppException, Conflict
from qnu.ports.blob_store import BlobStore
from qnu.ports.vector_store import VectorHit

# One document may not spend the whole expansion budget when other documents
# also produced primaries; the share follows primary coverage, not rank.
MIN_DOCUMENT_SHARE = 4096


def evidence_size(hit: SearchHit) -> int:
    # Two-digit IDs cover top20 plus at most four structural table dependencies.
    return len(json.dumps(evidence_item(hit, "E20"), ensure_ascii=False).encode("utf-8")) + 2


def _bounded_single_value(groups: list[dict], anchors: set[str], window: int = 1) -> list[dict]:
    """A single-value question opens around its anchor, not a whole enumeration scope."""
    bounded = []
    for group in groups:
        if group["kind"] == "bullet_list":
            continue
        ids = group["required_ids"]
        positions = [index for index, key in enumerate(ids) if key in anchors]
        if not positions:
            bounded.append(group)
            continue
        lo = max(0, min(positions) - window)
        hi = min(len(ids), max(positions) + window + 1)
        bounded.append({**group, "required_ids": ids[lo:hi], "units": [], "bounded": True})
    return bounded


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
    resolved_question: str | None = None,
) -> tuple[SearchResponse, dict]:
    needs = question_needs(req.question, resolved_question)
    # A single-value question reads its own neighbourhood; enumeration keeps
    # the structural scope. The caller's explicit window always wins.
    window = req.context_window
    if not window and needs["kind"] == "single_value":
        window = 1
    trace = {
        "window": req.context_window,
        "effective_window": window,
        "question_kind": needs["kind"],
        "primary_ids": [h.chunk_id for h in result.hits],
        "added": [],
        "budget_bytes": req.context_max_bytes,
    }
    consumed = 2 + sum(evidence_size(h) for h in result.hits)
    trace["bytes_used"] = consumed
    # Table JSON is a retrieval representation; the model receives either a
    # narrowed cell catalog or reading text. Packing measures that envelope, so
    # only narrative evidence is a reliable early failure here.
    narrative = 2 + sum(evidence_size(h) for h in result.hits if h.kind != "table")
    trace["narrative_bytes"] = narrative
    if narrative > req.context_max_bytes:
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
    narrative = 2 + sum(evidence_size(h) for h in result.hits if h.kind != "table")
    trace["narrative_bytes"] = narrative
    if narrative > req.context_max_bytes:
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
    skipped_share = []
    counts = Counter(hit.document_id for hit in result.hits)
    remaining = max(0, req.context_max_bytes - consumed)
    total_primaries = sum(counts.values())
    shares = {
        document_id: max(MIN_DOCUMENT_SHARE, remaining * count // total_primaries)
        for document_id, count in counts.items()
    }
    used: dict[str, int] = {}

    def claim(document_id: str, size: int, *, protected: bool = False) -> str:
        nonlocal consumed
        if consumed + size > req.context_max_bytes:
            return "budget"
        spent = used.get(document_id, 0)
        if spent + size > shares.get(document_id, 0) and not (protected and spent == 0):
            return "share"
        used[document_id] = spent + size
        consumed += size
        return "ok"

    structural = []
    question = resolved_question or req.question
    bundles = await pinned_bundles(db, blob, workspace_id, collection_id, result.hits, bundles)
    if needs_structure(question):
        structural = select_groups(rows, result.hits, bundles, question)
    if needs["kind"] == "single_value":
        structural = _bounded_single_value(structural, set(anchors))
    structural.extend(continuation_groups(rows, result.hits, bundles))
    if needs["kind"] == "condition":
        structural.extend(numbered_groups(rows, result.hits, bundles))
    if structural or needs_structure(question):
        trace["structure"] = {
            "version": VERSION,
            "groups": structural,
            "enumeration_requested": enumeration_requested(question),
            "unresolved_references": unresolved_references(question, structural),
            "compressed_refs": sum(len(group.get("compressed_refs") or []) for group in structural),
        }
    primary_rank = {chunk_id: rank for rank, chunk_id in enumerate(trace["primary_ids"])}

    def rank_of(chunk_id: str) -> int:
        return primary_rank.get(chunk_id, len(primary_rank))

    # Claim in relevance order so a budget cut drops the least relevant group;
    # append accepted groups in source order so evidence IDs keep reading order.
    accepted_groups = []
    for position, group in sorted(
        enumerate(structural),
        key=lambda item: (rank_of(item[1]["primary_chunk_id"]), item[0]),
    ):
        eligible = [
            by_id[key]
            for key in group["required_ids"]
            if any(matches_metadata(by_id[key].structure, scope) for scope in scopes)
        ]
        group["scope_excluded_ids"] = [
            key for key in group["required_ids"] if key not in {row.id for row in eligible}
        ]
        primary = anchors[group["primary_chunk_id"]]
        candidates = [
            candidate
            for candidate in await _hits(
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
            if candidate.chunk_id not in known
        ]
        if not candidates:
            continue
        size = sum(evidence_size(candidate) for candidate in candidates)
        outcome = claim(primary.document_id, size, protected=group["kind"] != "continuation")
        if outcome != "ok":
            if outcome == "budget":
                truncated += 1
            else:
                skipped_share.append(
                    {"primary_chunk_id": primary.chunk_id, "kind": group["kind"], "bytes": size}
                )
            continue
        known.update(candidate.chunk_id for candidate in candidates)
        accepted_groups.append((position, group, primary, candidates))
    for _, group, primary, candidates in sorted(accepted_groups, key=lambda item: item[0]):
        additions.extend(candidates)
        trace["added"].extend(
            {
                "chunk_id": candidate.chunk_id,
                "primary_chunk_id": primary.chunk_id,
                "kind": group["kind"],
            }
            for candidate in candidates
        )

    def clause_primary(group: list[IndexChunk]) -> SearchHit:
        return next(anchors[row.id] for row in group if row.id in anchors)

    bounded_scope = any(group["kind"] != "continuation" for group in structural)
    accepted_clauses = []
    for position, group in sorted(
        enumerate([] if bounded_scope else clause_groups(rows, set(anchors))),
        key=lambda item: (rank_of(clause_primary(item[1]).chunk_id), item[0]),
    ):
        if not any(
            all(matches_metadata(row.structure, scope) for row in group) for scope in scopes
        ):
            continue
        missing = [row for row in group if row.id not in known]
        if not missing:
            continue
        primary = clause_primary(group)
        candidates = await _hits(
            db,
            run,
            allowed,
            [_neighbor_hit(row, run, primary.version_id) for row in missing],
            sealed,
        )
        size = sum(evidence_size(hit) for hit in candidates)
        # Keeping a partial clause would misrepresent the source; drop the
        # whole group and let coverage report the missing units.
        if claim(primary.document_id, size, protected=True) != "ok":
            trace["clause_skipped_budget"] = trace.get("clause_skipped_budget", 0) + 1
            continue
        known.update(row.id for row in missing)
        accepted_clauses.append((position, primary, missing, candidates))
    for _, primary, missing, candidates in sorted(accepted_clauses, key=lambda item: item[0]):
        additions.extend(candidates)
        trace["added"].extend(
            {"chunk_id": row.id, "primary_chunk_id": primary.chunk_id, "kind": "clause"}
            for row in missing
        )
    if not req.context_window:
        parts, entries, consumed, part_truncated = await _join_paragraph_parts(
            db, run, allowed, sealed, result.hits, by_id, groups, scopes, known, consumed, req
        )
        additions.extend(parts)
        trace["added"].extend(entries)
        trace["parts_joined"] = len(parts)
        truncated += part_truncated
    if not window:
        trace.update(status="expanded" if additions else "disabled", bytes_used=consumed)
        trace["expansion"] = {
            "primary_counts": dict(counts),
            "per_document_bytes": shares,
            "used": dict(used),
            "skipped_share_count": len(skipped_share),
            "skipped_share": skipped_share[:20],
            "skipped_budget": truncated,
        }
        return result.model_copy(update={"hits": [*result.hits, *additions]}), trace

    pending = {}
    for hit in result.hits:
        primary = by_id[hit.chunk_id]
        parent = (primary.structure or {}).get("context", {}).get("parent")
        siblings = groups.get((primary.input_id, parent), [])
        if not siblings:
            continue  # Old generations remain readable without guessed relationships.
        if primary.kind == "table" and str(parent).startswith("table:"):
            # Fragments of one table are not independent neighbors: a bounded
            # window can strand the answer rows away from their header.
            neighbors = siblings
        else:
            position = next(i for i, c in enumerate(siblings) if c.id == primary.id)
            neighbors = siblings[max(0, position - window) : position + window + 1]
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
        _, _, primary_id, parent = pending[candidate.chunk_id]
        if claim(anchors[primary_id].document_id, evidence_size(candidate)) != "ok":
            truncated += 1
            continue
        additions.append(candidate)
        trace["added"].append(
            {"chunk_id": candidate.chunk_id, "primary_chunk_id": primary_id, "parent": parent}
        )
    trace.update(status="expanded", bytes_used=consumed, skipped_budget=truncated)
    trace["expansion"] = {
        "primary_counts": dict(counts),
        "per_document_bytes": shares,
        "used": dict(used),
        "skipped_share_count": len(skipped_share),
        "skipped_share": skipped_share[:20],
        "skipped_budget": truncated,
    }
    return result.model_copy(update={"hits": [*result.hits, *additions]}), trace


MAX_PARAGRAPH_PARTS = 4


async def _join_paragraph_parts(
    db, run, allowed, sealed, hits, by_id, groups, scopes, known, consumed, req
):
    """Rejoin parts of one paragraph that chunking split; window 0 skips the rest."""
    pending: dict[str, tuple[IndexChunk, str, str]] = {}
    for hit in hits:
        primary = by_id[hit.chunk_id]
        context = (primary.structure or {}).get("context", {})
        parent, position = context.get("parent"), context.get("position")
        if primary.kind != "paragraph" or parent is None or position is None:
            continue
        shared = [scope for scope in scopes if matches_metadata(primary.structure, scope)]
        for row in groups.get((primary.input_id, parent), []):
            row_context = (row.structure or {}).get("context", {})
            if (
                row.id in known
                or row.id in pending
                or row_context.get("position") != position
                or not any(matches_metadata(row.structure, scope) for scope in shared)
            ):
                continue
            pending[row.id] = (row, hit.version_id, primary.id)
    rows = list(pending.values())[:MAX_PARAGRAPH_PARTS]
    candidates = (
        await _hits(
            db,
            run,
            allowed,
            [_neighbor_hit(row, run, version) for row, version, _ in rows],
            sealed,
        )
        if rows
        else []
    )
    additions, entries, truncated = [], [], 0
    for candidate in candidates:
        size = evidence_size(candidate)
        if consumed + size > req.context_max_bytes:
            truncated += 1
            continue
        additions.append(candidate)
        known.add(candidate.chunk_id)
        consumed += size
        _, _, primary_id = pending[candidate.chunk_id]
        entries.append(
            {"chunk_id": candidate.chunk_id, "primary_chunk_id": primary_id, "kind": "part"}
        )
    return additions, entries, consumed, truncated


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
