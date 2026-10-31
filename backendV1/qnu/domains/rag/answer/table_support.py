"""Attach sealed source dependencies without editing the retrieved chunks."""

from sqlalchemy import select

from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.index.search import _eligible, _hits, manifest
from qnu.domains.knowledge.metadata import matches_metadata
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.rag.answer.table_context import bound_dependencies
from qnu.platform.errors import Conflict
from qnu.ports.vector_store import VectorHit


def supports(primary, rows, relationships, metadata_filter):
    selected, links = {}, []
    by_id = {r.id: r for r in rows}
    for hit in primary:
        table = (hit.structure or {}).get("source_table_citation")
        source = by_id[hit.chunk_id]
        link = relationships.get((source.input_id, table))
        if not link:
            continue
        siblings = [r for r in rows if r.input_id == source.input_id]
        previous = link["previous"] if 0 in hit.structure.get("row_indices", []) else None
        refs = [(link["header"], True)] + ([(previous, False)] if previous else [])
        needed = []
        for ref, is_header in refs:
            options = [
                r for r in siblings if (r.structure or {}).get("source_table_citation") == ref
            ]
            if not options:
                break
            if is_header:
                row = min(options, key=lambda r: min(r.structure["row_indices"]))
                if 0 not in row.structure["row_indices"]:
                    break
            else:
                row = max(options, key=lambda r: max(r.structure["row_indices"]))
            if not matches_metadata(row.structure, metadata_filter):
                break
            needed.append(row)
        else:
            selected.update({r.id: r for r in needed})
            links.append(
                {
                    "chunk_id": hit.chunk_id,
                    **link,
                    "previous": previous,
                    "support_ids": [r.id for r in needed],
                }
            )
    return selected, links


async def attach_table_support(db, blob, actor, workspace_id, collection_id, result, req):
    if not any((h.structure or {}).get("source_table_citation") for h in result.hits):
        return result, {}
    await authorize(db, actor, workspace_id, collection_id)
    run = await db.get(IndexRun, result.index_run_id)
    if run is None or not run.is_active or run.status != "completed":
        raise Conflict("Index context đã thay đổi.", code="answer_evidence_changed")
    allowed, _ = await _eligible(db, blob, actor, run, req.document_ids)
    rows = list(
        await db.scalars(
            select(IndexChunk).where(
                IndexChunk.run_id == run.id, IndexChunk.input_id.in_([b.id for b in allowed])
            )
        )
    )
    relationships = await bound_dependencies(db, blob, allowed, rows)
    needed, links = supports(result.hits, rows, relationships, req.metadata_filter)
    known = {h.chunk_id for h in result.hits}
    additions = [r for key, r in needed.items() if key not in known]
    # Do not silently discard a primary result to make dependencies fit.
    # Four additional dependencies are a separate, bounded allowance. Top-k
    # remains unchanged; every item still consumes the shared byte/token budget.
    room = 4
    if len(additions) > room:
        return result, {
            "table_support": "no_room",
            "unresolved_support_ids": [r.id for r in additions],
        }
    raw = [
        VectorHit(
            r.point_id,
            0,
            {
                "run_id": run.id,
                "workspace_id": workspace_id,
                "collection_id": collection_id,
                "version_id": next(b.version_id for b in allowed if b.id == r.input_id),
                "chunk_id": r.id,
                "text_sha256": r.text_sha256,
            },
        )
        for r in additions
    ]
    added = await _hits(db, run, allowed, raw, await manifest(db, blob, run)) if raw else []
    return result.model_copy(update={"hits": [*result.hits, *added]}), {
        "table_support": "resolved",
        "table_links": links,
        "support_ids": [r.id for r in additions],
    }
