"""Attach sealed source dependencies without editing the retrieved chunks."""

from sqlalchemy import select

from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.index.query_scope import result_scopes
from qnu.domains.knowledge.index.search import _eligible, _hits, manifest
from qnu.domains.knowledge.metadata import matches_metadata
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.rag.answer.selection import question_needs
from qnu.domains.rag.answer.table_context import bound_dependencies
from qnu.platform.errors import Conflict
from qnu.ports.vector_store import VectorHit


def _support_link(source, tables, relationships, scopes):
    table = (source.structure or {}).get("source_table_citation")
    link = relationships.get((source.input_id, table))
    if not link:
        return None
    shared = [scope for scope in scopes if matches_metadata(source.structure, scope)]
    previous = link["previous"] if 0 in source.structure.get("row_indices", []) else None
    refs = [(link["header"], True)] + ([(previous, False)] if previous else [])
    needed = []
    for ref, is_header in refs:
        options = tables.get((source.input_id, ref), [])
        if not options:
            return None
        if is_header:
            row = min(options, key=lambda r: min(r.structure["row_indices"]))
            if 0 not in row.structure["row_indices"]:
                return None
        else:
            row = max(options, key=lambda r: max(r.structure["row_indices"]))
        shared = [scope for scope in shared if matches_metadata(row.structure, scope)]
        if not shared:
            return None
        needed.append(row)
    return needed, {
        "chunk_id": source.id,
        **link,
        "previous": previous,
        "support_ids": [r.id for r in needed],
    }


def supports(primary, rows, relationships, metadata_filter, scopes=None, *, enumerate_rows=False):
    selected, links, tables = {}, {}, {}
    by_id = {r.id: r for r in rows}
    for row in rows:
        if not row.structure or "row_indices" not in row.structure:
            continue
        if table := row.structure.get("source_table_citation"):
            tables.setdefault((row.input_id, table), []).append(row)
    continuations = {
        (binding, link["previous"]): ref
        for (binding, ref), link in relationships.items()
        if link["previous"]
    }
    scopes = scopes or [metadata_filter]
    for hit in primary:
        source = by_id[hit.chunk_id]
        if not source.structure or "row_indices" not in source.structure:
            continue
        matched = _support_link(source, tables, relationships, scopes)
        if not matched:
            continue
        needed, link = matched
        selected.update({row.id: row for row in needed})
        links[source.id] = link

        structure = source.structure
        next_table = continuations.get((source.input_id, structure["source_table_citation"]))
        last_row = structure.get("original_row_count", 0) - 1
        if not next_table or (last_row not in structure["row_indices"] and not enumerate_rows):
            continue
        head = next(
            (
                row
                for row in tables.get((source.input_id, next_table), [])
                if 0 in row.structure["row_indices"]
            ),
            None,
        )
        if head is None or head.id in links:
            continue
        matched = _support_link(head, tables, relationships, scopes)
        if matched:
            needed, link = matched
            selected.update({row.id: row for row in (*needed, head)})
            links[head.id] = link
    return selected, list(links.values())


MAX_SECTION_SIBLINGS = 2


def section_siblings(primary, rows, relationships, scopes, excluded):
    """Complete self-describing tables under the anchor's verified section heading.

    Weaker than a continuation proof: a sibling is optional reading evidence,
    never a header dependency, and stays bounded per request.
    """
    by_id = {r.id: r for r in rows}
    selected, links = {}, []
    for hit in primary:
        anchor = by_id.get(hit.chunk_id)
        if anchor is None or anchor.kind != "table":
            continue
        structure = anchor.structure or {}
        heading = (structure.get("context") or {}).get("source_heading_citation")
        citation = structure.get("source_table_citation")
        if not heading or not citation:
            continue
        shared = [scope for scope in scopes if matches_metadata(structure, scope)]
        if not shared:
            continue
        candidates = []
        for row in rows:
            if row.kind != "table" or row.input_id != anchor.input_id:
                continue
            if row.id in excluded or row.id in selected:
                continue
            sibling = row.structure or {}
            ref = sibling.get("source_table_citation")
            if not ref or ref == citation:
                continue
            if (sibling.get("context") or {}).get("source_heading_citation") != heading:
                continue
            if sibling.get("row_indices") != list(range(sibling.get("original_row_count", 0))):
                continue
            link = relationships.get((row.input_id, ref))
            if not link or link["header"] != ref:
                continue
            if not any(matches_metadata(sibling, scope) for scope in shared):
                continue
            candidates.append(row)
        candidates.sort(key=lambda r: (abs(r.ordinal - anchor.ordinal), r.ordinal))
        for row in candidates:
            if len(selected) >= MAX_SECTION_SIBLINGS:
                return selected, links
            selected[row.id] = row
            links.append(
                {
                    **relationships[(row.input_id, row.structure["source_table_citation"])],
                    "chunk_id": row.id,
                    "support_ids": [row.id],
                    "sibling_of": anchor.id,
                    "heading_citation": heading,
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
    scopes = result_scopes(result, req.metadata_filter)
    needs = question_needs(req.question)
    needed, links = supports(
        result.hits,
        rows,
        relationships,
        req.metadata_filter,
        scopes,
        enumerate_rows=needs["enumeration"] or needs["count"],
    )
    known = {h.chunk_id for h in result.hits}
    # Header and continuation rows are the conditions under which a table cell
    # may be cited at all; they cannot compete with an optional allowance, or
    # the catalog loses its header and every numeric statement is rejected.
    # The shared byte budget and packing still bound what reaches the model.
    selected, resolved, unresolved = {}, [], []
    for link in links:
        extra = list(
            dict.fromkeys(
                key
                for key in (link["chunk_id"], *link["support_ids"])
                if key not in known and key not in selected
            )
        )
        selected.update({key: needed[key] for key in extra})
        resolved.append(link)
    siblings, sibling_links = section_siblings(
        result.hits, rows, relationships, scopes, excluded=set(known) | set(needed)
    )
    resolved.extend(sibling_links)
    additions = list(selected.values()) + list(siblings.values())
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
    trace = {
        "table_support": "partial" if unresolved else "resolved",
        "unresolved_support_ids": list(dict.fromkeys(unresolved)),
        "table_links": resolved,
        "support_ids": [r.id for r in additions],
    }
    if sibling_links:
        trace["section_siblings"] = [link["chunk_id"] for link in sibling_links]
        # Unlike header dependencies, a sibling is expendable reading evidence:
        # packing may trim it when the envelope exceeds the byte budget.
        trace["added"] = [
            {
                "chunk_id": link["chunk_id"],
                "primary_chunk_id": link["sibling_of"],
                "kind": "sibling_table",
            }
            for link in sibling_links
        ]
    return result.model_copy(update={"hits": [*result.hits, *added]}), trace
