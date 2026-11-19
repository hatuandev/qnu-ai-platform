"""Bounded section windows from the same published input; never use global ordinal adjacency."""

import json
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.index.multi import pinned_by_collection
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
    table_family_groups,
    unresolved_references,
)
from qnu.domains.rag.answer.table_support import attach_table_support
from qnu.platform.errors import AppException, Conflict
from qnu.ports.blob_store import BlobStore
from qnu.ports.vector_store import VectorHit

# One document may not spend the whole expansion budget when other documents
# also produced primaries; the share follows primary coverage, not rank.
MIN_DOCUMENT_SHARE = 4096

# Reranked runners-up stay trimmable reading context: retrieval already found
# them relevant, but they must not displace a primary or a structural group.
RANK_BAND = 5

# Items of one source enumeration are one reading unit; a fixed window can strand
# item 5 of 6 away from the list it belongs to.
MAX_NUMBERED_RUN = 8
NUMBERED_LABEL = re.compile(r"^(\d{1,2})[.)]\s+\S")

# A wrapped source line is its own paragraph chunk; the model reads the whole
# sentence only when the line neighbours ride along as trimmable reading.
MAX_STITCH_LINES = 4
SENTENCE_END = ".!?…"
TRAILING_CLOSERS = "\"'”’)]}» \t"


def _numbered_item(chunk: IndexChunk) -> int | None:
    numbers = set()
    for annotation in (chunk.structure or {}).get("retrieval_metadata", []):
        for label in annotation["values"].get("attributes") or {}:
            match = NUMBERED_LABEL.match(str(label).strip())
            if match:
                numbers.add(int(match.group(1)))
    return numbers.pop() if len(numbers) == 1 else None


def _numbered_run(siblings: list[IndexChunk], position: int) -> tuple[int, int] | None:
    number = _numbered_item(siblings[position])
    if number is None:
        return None
    start = end = position
    while start > 0 and position - start < MAX_NUMBERED_RUN:
        if _numbered_item(siblings[start - 1]) != number - (position - start + 1):
            break
        start -= 1
    while end + 1 < len(siblings) and end - position < MAX_NUMBERED_RUN:
        if _numbered_item(siblings[end + 1]) != number + (end + 1 - position):
            break
        end += 1
    return (start, end) if (start, end) != (position, position) else None


def _visible_text(text: str) -> str:
    """Chunk body without its own header line and repeated title/heading lines."""
    lines = text.split("\n")
    title = heading = None
    if lines[0].startswith("{"):
        try:
            header = json.loads(lines.pop(0))
        except json.JSONDecodeError:
            header = {}
        title, heading = header.get("title"), header.get("heading")
    for expected in (title, heading):
        if expected is not None and lines and lines[0].strip() == expected.strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def _ends_sentence(text: str) -> bool:
    visible = _visible_text(text)
    while visible and visible[-1] in TRAILING_CLOSERS:
        visible = visible[:-1].rstrip()
    return bool(visible) and visible[-1] in SENTENCE_END


def _starts_continued(text: str) -> bool:
    for char in _visible_text(text):
        if char.isdigit():
            return False
        if char.isalpha():
            return char.islower()
    return False


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


LIST_TRACE_KEYS = (
    "added",
    "support_ids",
    "unresolved_support_ids",
    "table_links",
    "section_siblings",
    "rank_band",
    "stitch",
)
SUM_TRACE_KEYS = (
    "bytes_used",
    "narrative_bytes",
    "skipped_budget",
    "rank_band_skipped",
    "clause_skipped_budget",
    "parts_joined",
)


def merge_context_traces(
    entries: list[tuple[str, dict]], primary_ids: list[str], budget_bytes: int
) -> dict:
    """One reading context from several collections; counts add, ids keep order."""
    traces = [trace for _, trace in entries]
    first = traces[0]
    merged = {
        "window": first.get("window"),
        "effective_window": first.get("effective_window"),
        "question_kind": first.get("question_kind"),
        "budget_bytes": budget_bytes,
        "primary_ids": primary_ids,
        "collections": [{"collection_id": key, **trace} for key, trace in entries],
    }
    for key in LIST_TRACE_KEYS:
        merged[key] = [item for trace in traces for item in trace.get(key) or []]
    for key in SUM_TRACE_KEYS:
        merged[key] = sum(trace.get(key) or 0 for trace in traces)
    merged["status"] = (
        "expanded"
        if any(trace.get("status") == "expanded" for trace in traces)
        else "no_hits"
        if all(trace.get("status") == "no_hits" for trace in traces)
        else "disabled"
    )
    support = [trace["table_support"] for trace in traces if trace.get("table_support")]
    if support:
        merged["table_support"] = "partial" if "partial" in support else support[0]
    structures = [trace["structure"] for trace in traces if trace.get("structure")]
    if structures:
        merged["structure"] = {
            "version": structures[0]["version"],
            "groups": [group for item in structures for group in item.get("groups") or []],
            "enumeration_requested": any(item.get("enumeration_requested") for item in structures),
            "unresolved_references": [
                ref for item in structures for ref in item.get("unresolved_references") or []
            ],
            "compressed_refs": sum(item.get("compressed_refs") or 0 for item in structures),
        }
    expansions = [trace["expansion"] for trace in traces if trace.get("expansion")]
    if expansions:
        merged["expansion"] = {
            "primary_counts": {
                document_id: count
                for item in expansions
                for document_id, count in item.get("primary_counts", {}).items()
            },
            "per_document_bytes": {
                document_id: size
                for item in expansions
                for document_id, size in item.get("per_document_bytes", {}).items()
            },
            "used": {
                document_id: size
                for item in expansions
                for document_id, size in item.get("used", {}).items()
            },
            "skipped_share_count": sum(item.get("skipped_share_count") or 0 for item in expansions),
            "skipped_share": [
                entry for item in expansions for entry in item.get("skipped_share") or []
            ][:20],
            "skipped_budget": sum(item.get("skipped_budget") or 0 for item in expansions),
        }
    return merged


async def expand_collections(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    retrieval: SearchResponse,
    req: AnswerRequest,
    *,
    bundles: dict | None = None,
    resolved_question: str | None = None,
) -> tuple[SearchResponse, dict]:
    """Expand each source collection inside its own index, then merge in rank order."""
    if not retrieval.hits:
        return retrieval, {
            "window": req.context_window,
            "primary_ids": [],
            "budget_bytes": req.context_max_bytes,
            "added": [],
            "status": "no_hits",
        }
    hit_scope = dict(retrieval.trace.get("hit_scope") or {})
    traces = retrieval.trace.get("collection_traces") or {}
    ranked_ids = retrieval.trace.get("rerank_ranked_ids") or []
    served_ids = [
        record["collection_id"]
        for record in retrieval.trace.get("collections") or []
        if record.get("status") == "served"
    ]
    pinned = await pinned_by_collection(db, workspace_id, served_ids, req.document_ids)
    entries, owners, additions = [], {}, []
    for record in retrieval.trace.get("collections") or []:
        if record.get("status") != "served":
            continue
        owner = record["collection_id"]
        group = [hit for hit in retrieval.hits if hit_scope.get(hit.chunk_id) == owner]
        if not group:
            continue
        trace = dict(traces.get(owner) or {})
        ranked = [key for key in ranked_ids if hit_scope.get(key) == owner]
        if ranked:
            trace["rerank_ranked_ids"] = ranked
        sub = SearchResponse(
            index_run_id=record["index_run_id"],
            generation=record["generation"],
            status="results",
            hits=group,
            eligible_documents=record["eligible_documents"],
            skipped_documents=[],
            trace=trace,
        )
        # A pinned document only narrows the collection that owns it.
        scoped = (
            req.model_copy(update={"document_ids": pinned[owner]}) if pinned is not None else req
        )
        expanded, entry = await expand_context(
            db,
            blob,
            actor,
            workspace_id,
            owner,
            sub,
            scoped,
            bundles=bundles,
            resolved_question=resolved_question,
        )
        entries.append((owner, entry))
        for hit in expanded.hits:
            owners[hit.chunk_id] = owner
        additions.extend(expanded.hits[len(group) :])
    primary_ids = [hit.chunk_id for hit in retrieval.hits]
    merged = (
        merge_context_traces(entries, primary_ids, req.context_max_bytes)
        if entries
        else {
            "window": req.context_window,
            "primary_ids": primary_ids,
            "budget_bytes": req.context_max_bytes,
            "added": [],
            "status": "no_hits",
        }
    )
    retrieval = retrieval.model_copy(
        update={
            "hits": [*retrieval.hits, *additions],
            "trace": {**retrieval.trace, "hit_scope": {**hit_scope, **owners}},
        }
    )
    return retrieval, merged


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
    # A table-only question still needs its family when it enumerates or counts
    # rows; otherwise a retrieved fragment is read as the whole table.
    family_needed = (needs["enumeration"] or needs["count"]) and any(
        hit.kind == "table" for hit in result.hits
    )
    if (
        not req.context_window
        and not any(hit.kind == "paragraph" for hit in result.hits)
        and not family_needed
    ):
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

    async def append_rank_band(additions: list[SearchHit]) -> None:
        """Reranked runners-up become trimmable reading, never mandatory evidence."""
        ordered = result.trace.get("rerank_ranked_ids") or []
        if not ordered or result.trace.get("facets"):
            return
        tail = [key for key in ordered[len(trace["primary_ids"]) :] if key not in known]
        if not tail:
            return
        rows = {
            row.id: row
            for row in await db.scalars(
                select(IndexChunk).where(
                    IndexChunk.run_id == run.id,
                    IndexChunk.id.in_(tail),
                    IndexChunk.input_id.in_([b.id for b in allowed]),
                )
            )
        }
        # Tables already arrive through table_support links; dumping whole tables as
        # reading evidence only inflates the prompt.
        band = [key for key in tail if key in rows and rows[key].kind != "table"][:RANK_BAND]
        skipped_tables = sum(1 for key in tail if key in rows and rows[key].kind == "table")
        if skipped_tables:
            trace["rank_band_tables_skipped"] = skipped_tables
        if not band:
            return
        version = {b.id: getattr(b, "version_id", None) or getattr(b, "id", "") for b in allowed}
        candidates = await _hits(
            db,
            run,
            allowed,
            [
                _neighbor_hit(rows[key], run, version.get(rows[key].input_id, ""))
                for key in band
                if key in rows
                and any(matches_metadata(rows[key].structure, scope) for scope in scopes)
            ],
            sealed,
        )
        taken = []
        for candidate in candidates:
            if candidate.chunk_id in known:
                continue
            if claim(candidate.document_id, evidence_size(candidate)) != "ok":
                trace["rank_band_skipped"] = trace.get("rank_band_skipped", 0) + 1
                continue
            known.add(candidate.chunk_id)
            taken.append(candidate)
        if not taken:
            return
        additions.extend(taken)
        trace["added"].extend(
            {"chunk_id": candidate.chunk_id, "primary_chunk_id": None, "kind": "rank"}
            for candidate in taken
        )
        trace["rank_band"] = [candidate.chunk_id for candidate in taken]

    async def stitch_sentence_fragments() -> None:
        """Line neighbours of a split sentence ride along as trimmable reading."""
        by_ordinal: dict[str, dict[int, IndexChunk]] = {}
        for row in rows:
            by_ordinal.setdefault(row.input_id, {})[row.ordinal] = row
        owners = {hit.chunk_id: hit.document_id for hit in result.hits}
        owners.update({hit.chunk_id: hit.document_id for hit in additions})
        version = {b.id: getattr(b, "version_id", None) or getattr(b, "id", "") for b in allowed}
        pending: dict[str, tuple[IndexChunk, str]] = {}
        per_anchor: Counter = Counter()

        def queue(row: IndexChunk | None, anchor: IndexChunk) -> bool:
            if row is None or row.kind != "paragraph" or row.id in known or row.id in pending:
                return False
            if per_anchor[anchor.id] >= MAX_STITCH_LINES:
                return False
            shared = [scope for scope in scopes if matches_metadata(anchor.structure, scope)]
            if not any(matches_metadata(row.structure, scope) for scope in shared):
                return False
            pending[row.id] = (row, anchor.id)
            per_anchor[anchor.id] += 1
            return True

        for anchor_id in list(owners):
            anchor = by_id.get(anchor_id)
            if anchor is None or anchor.kind != "paragraph" or not _visible_text(anchor.text):
                continue
            table = by_ordinal.get(anchor.input_id, {})
            if not _ends_sentence(anchor.text):
                row = table.get(anchor.ordinal + 1)
                while queue(row, anchor):
                    if _ends_sentence(row.text):
                        break
                    row = table.get(row.ordinal + 1)
            if _starts_continued(anchor.text):
                row = table.get(anchor.ordinal - 1)
                while queue(row, anchor):
                    if not _starts_continued(row.text):
                        break
                    row = table.get(row.ordinal - 1)
        if not pending:
            return
        candidates = await _hits(
            db,
            run,
            allowed,
            [_neighbor_hit(row, run, version.get(row.input_id, "")) for row, _ in pending.values()],
            sealed,
        )
        taken = []
        for candidate in candidates:
            anchor_id = pending[candidate.chunk_id][1]
            if candidate.chunk_id in known:
                continue
            if claim(owners[anchor_id], evidence_size(candidate)) != "ok":
                trace["stitch_skipped"] = trace.get("stitch_skipped", 0) + 1
                continue
            known.add(candidate.chunk_id)
            owners[candidate.chunk_id] = candidate.document_id
            taken.append((candidate, anchor_id))
        if not taken:
            return
        additions.extend(candidate for candidate, _ in taken)
        trace["added"].extend(
            {"chunk_id": candidate.chunk_id, "primary_chunk_id": anchor_id, "kind": "stitch"}
            for candidate, anchor_id in taken
        )
        trace["stitch"] = [candidate.chunk_id for candidate, _ in taken]

    structural = []
    question = resolved_question or req.question
    bundles = await pinned_bundles(db, blob, workspace_id, collection_id, result.hits, bundles)
    if needs_structure(question):
        structural = select_groups(rows, result.hits, bundles, question)
    if needs["kind"] == "single_value":
        structural = _bounded_single_value(structural, set(anchors))
    if needs["enumeration"] or needs["count"]:
        structural.extend(table_family_groups(rows, result.hits, scopes))
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
        if group["kind"] == "table_family":
            # A table family is a reading sequence, not one clause: take the
            # fragments that fit in source order and let coverage report the rest.
            taken = []
            for candidate in candidates:
                outcome = claim(primary.document_id, evidence_size(candidate), protected=True)
                if outcome != "ok":
                    if outcome == "budget":
                        truncated += 1
                    else:
                        skipped_share.append(
                            {
                                "primary_chunk_id": primary.chunk_id,
                                "kind": group["kind"],
                                "bytes": evidence_size(candidate),
                            }
                        )
                    group["truncated"] = True
                    break
                taken.append(candidate)
                known.add(candidate.chunk_id)
            if taken:
                accepted_groups.append((position, group, primary, taken))
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
        await append_rank_band(additions)
        await stitch_sentence_fragments()
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
            start, end = max(0, position - window), min(len(siblings) - 1, position + window)
            span = _numbered_run(siblings, position)
            if span:
                start, end = min(start, span[0]), max(end, span[1])
            neighbors = siblings[start : end + 1]
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
        known.add(candidate.chunk_id)
        trace["added"].append(
            {"chunk_id": candidate.chunk_id, "primary_chunk_id": primary_id, "parent": parent}
        )
    await append_rank_band(additions)
    await stitch_sentence_fragments()
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
