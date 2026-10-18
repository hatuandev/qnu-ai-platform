"""Read-only structural evidence from the pinned published source revisions."""

import hashlib
import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.normalization.retrieval_units import (
    manifest_digest,
    manifest_hash_matches,
    resolve_unit_manifest,
)
from app.modules.knowledge.services.source_artifact import (
    get_source_artifact,
    get_structured_review_state,
)
from app.modules.rag.evidence_bm25 import rank_blocks, tokens  # noqa: F401
from app.modules.rag.evidence_context import model_block
from app.modules.rag.evidence_dependencies import (
    coverage_order,
    dependency_groups,
    sentence_continuations,
    source_identity,
)
from app.modules.rag.evidence_hierarchy import enrich_hierarchy
from app.modules.rag.evidence_lists import family, list_groups, matches_subject
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.schemas import RetrievalSnapshot

PAGE = re.compile(r"<!--\s*(?:Trang|Page)\s+(\d+)\s*-->", re.IGNORECASE)
PARAGRAPH = re.compile(r"\S[\s\S]*?(?=\n\s*\n|\Z)")
LIST_ITEM = re.compile(r"^\s*(?:[-+*]|\d+[.)]|[a-z][.)])\s")


def enumeration_neighbors(blocks: list[EvidenceBlock], selected: list[EvidenceBlock], limit: int,
                          subject: str | None = None) -> list[EvidenceBlock]:
    """Complete adjacent syntactic lists, not a hand-authored domain keyword expansion."""
    ids = {block.id for block in selected}
    result = []
    for group in list_groups(blocks):
        if matches_subject(group, subject) and len(group) <= limit and any(block.id in ids for block in group):
            result.extend(group)
    return list({b.id: b for b in result}.values())


def section_neighbors(blocks: list[EvidenceBlock], subject: str, years: list[int],
                       limit: int) -> list[EvidenceBlock]:
    """Expand matched headings to bounded prose children, never another section."""
    headings = [block for block in blocks if re.fullmatch(r"\s*#{1,6}\s+[^\n]+\s*", block.text)]
    labels = [heading.model_copy(update={"text": heading.text.lstrip("# "),
        "title": "", "section": "", "is_container": False}) for heading in headings]
    matched = rank_blocks(labels, [subject], 2, years)
    by_id = {heading.id: heading for heading in headings}
    result = []
    for label in matched:
        heading = by_id[label.id]
        identity = (heading.binding_id, heading.index_revision_id, heading.source_revision_id)
        same = [block for block in blocks if (block.binding_id, block.index_revision_id,
            block.source_revision_id) == identity]
        boundary = min((block.start for block in same if block.start > heading.start
            and block.id in by_id), default=float("inf"))
        children = sorted((block for block in same if heading.end <= block.start < boundary
            and not block.is_container), key=lambda block: block.start)
        result.extend(children[:limit])
    return list({block.id: block for block in result}.values())[:limit]


def split_source_blocks(markdown: str, *, binding_id: str, index_id: str,
                        source_id: str, title: str, canonical_hash: str = "") -> list[EvidenceBlock]:
    markers = list(PAGE.finditer(markdown))
    ranges = [(0, markers[0].start(), None)] if markers and markers[0].start() else []
    ranges += [(m.end(), markers[i + 1].start() if i + 1 < len(markers) else len(markdown), int(m[1]))
               for i, m in enumerate(markers)]
    if not markers:
        ranges = [(0, len(markdown), None)]
    headers: list[str] = []
    header_context = markdown[:1200]
    blocks = []
    for begin, end, page in ranges:
        for paragraph in PARAGRAPH.finditer(markdown, begin, end):
            text = paragraph.group().rstrip()
            heading = re.fullmatch(r"(#{1,6})\s+([^\n]+)", text)
            if heading:
                depth = len(heading[1])
                headers = headers[:depth - 1] + [heading[2]]
            for offset in range(0, len(text), 6000):
                start = paragraph.start() + offset
                finish = min(paragraph.start() + len(text), start + 6000)
                blocks.append(EvidenceBlock(id=f"{source_id}:{start}:{finish}",
                    binding_id=binding_id, index_revision_id=index_id, source_revision_id=source_id,
                    title=title, page_number=page, section=" / ".join(headers[-3:]),
                    header_context=header_context, text=markdown[start:finish], start=start, end=finish,
                    canonical_hash=canonical_hash))
    return enrich_hierarchy(blocks)


def source_heading_years(blocks: list[EvidenceBlock]) -> list[int]:
    for block in blocks:
        if block.page_number not in (None, 1) or len(block.text) > 300:
            continue
        years = sorted({int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", block.text)})
        first_line = block.text.splitlines()[0]
        letters = [c for c in first_line if c.isalpha()]
        uppercase = sum(c.isupper() for c in letters) / max(1, len(letters))
        if years and (uppercase == 1 or first_line.lstrip().startswith("#")):
            return years
    return []


async def load_published_blocks(db: AsyncSession, snapshot: RetrievalSnapshot, *, candidate_mode: bool = False) -> list[EvidenceBlock]:
    if not snapshot.binding_revisions or not snapshot.tenant_id or not snapshot.workspace_id:
        return []
    query = (select(KnowledgeSourceRevision, KnowledgeIndexRevision, KnowledgeBinding)
        .join(KnowledgeIndexRevision, KnowledgeIndexRevision.source_revision_v2_id == KnowledgeSourceRevision.id)
        .join(KnowledgeBinding, KnowledgeIndexRevision.binding_id == KnowledgeBinding.id)
        .join(KnowledgeCollection, KnowledgeBinding.collection_id == KnowledgeCollection.id)
        .where(KnowledgeIndexRevision.id.in_(snapshot.binding_revisions.values()),
               KnowledgeIndexRevision.status.in_(["active", "ready"] if candidate_mode else ["active"]),
               KnowledgeBinding.collection_id == snapshot.collection_id, KnowledgeBinding.status == "active",


               KnowledgeSourceRevision.status == "ready"))
    try:
        records = (await db.execute(query)).all()
    except Exception as exc:
        raise AppException("Không thể tải chứng cứ đã xuất bản.", code="EVIDENCE_SOURCE_UNAVAILABLE", status_code=503) from exc
    blocks = []
    total_chars = 0
    for source, index, binding in records:
        markdown = source.canonical_markdown or ""
        if snapshot.binding_revisions.get(binding.id) != index.id:
            continue
        valid = (index.chunk_count > 0 and (index.parity_report or {}).get("parity_passed")
                 and not get_structured_review_state(source)[1]
                 and hashlib.sha256(markdown.encode("utf-8")).hexdigest() == source.canonical_hash)
        if not valid:
            raise AppException("Chứng cứ nguồn không qua đối soát revision/hash/review.", code="EVIDENCE_SOURCE_INVALID", status_code=503)
        total_chars += len(markdown)
        if total_chars > 2_000_000:
            raise AppException("Kho vượt ngân sách đối soát; cần phân vùng nguồn.", code="EVIDENCE_SOURCE_BUDGET", status_code=422)
        try:
            source_artifact = get_source_artifact(source)
            manifest = resolve_unit_manifest(markdown, source_artifact)
            digest = manifest_digest(manifest)
            pinned_hash = (index.parity_report or {}).get("unit_manifest_hash")
            if pinned_hash and not manifest_hash_matches(pinned_hash, manifest):
                raise ValueError("Index and source have different unit manifests")
        except ValueError as exc:
            raise AppException("Đơn vị nguồn không khớp chứng cứ hoặc bản chỉ mục.",
                code="EVIDENCE_UNIT_INVALID", status_code=503) from exc
        source_blocks = [EvidenceBlock(id=f"{source.id}:{unit.start}:{unit.end}", binding_id=binding.id,
            index_revision_id=index.id, source_revision_id=source.id,
            title=(source.snapshot_metadata or {}).get("title") or binding.id,
            page_number=unit.page_number, section=" / ".join(unit.heading_path), text=unit.text,
            header_context="\n".join([*unit.heading_path, unit.header_context]), start=unit.start, end=unit.end,
            source_context=markdown[:1200],
            canonical_hash=source.canonical_hash, temporal_scope=unit.temporal,
            fact_context={"source_kind": unit.kind, **({"qnu_block_id": unit.qnu_block_id,
                "source_locations": unit.source_locations, "context_unit_ids": source_artifact.get("context_graph", {}).get("links", {}).get(unit.id, [])}
                if unit.qnu_block_id else {})},
            scope_years=unit.temporal.data_years if unit.temporal.status == "verified" and unit.temporal.role == "data" else [],
            unit_id=unit.id, parent_id=unit.parent_id, unit_manifest_hash=digest,
            is_container=unit.is_container) for unit in manifest.units]
        if (index.parity_report or {}).get("fact_set_hash") and not any(unit.qnu_block_id for unit in manifest.units):
            # Materialized reviewed facts take precedence over original table cells.
            source_blocks = [b for b in source_blocks if not (
                re.search(r"(?m)^\s*\|", b.text) or re.search(r"<table\b", b.text, re.IGNORECASE))]
        blocks.extend(source_blocks)
    return enrich_hierarchy(blocks)


def scope_headers(blocks: list[EvidenceBlock], selected: list[EvidenceBlock], years: list[int]) -> list[EvidenceBlock]:
    """Attach exact same-source heading spans, never filename-derived years."""
    sources = {source_identity(b) for b in selected}
    result = []
    for identity in sources:
        choices = []
        for block in blocks:
            if source_identity(block) != identity or len(block.text) > 300:
                continue
            found = {int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", block.text)}
            first_line = block.text.splitlines()[0]
            letters = [c for c in first_line if c.isalpha()]
            uppercase = sum(c.isupper() for c in letters) / max(1, len(letters))
            if found.intersection(years) and (uppercase == 1 or block.text.lstrip().startswith("#")):
                choices.append(block)
        if choices:
            result.append(min(choices, key=lambda b: b.start))
    return result


def pack_context(blocks: list[EvidenceBlock], ordered: list[EvidenceBlock], years: list[int],
                 limit: int, max_chars: int, *, atomic_lists: bool = True,
                 enumeration_subject: str | None = None, diagnostics: dict | None = None,
                 coverage_goals: list[str] | None = None, priority_ids: set[str] | None = None,
                 allow_first_whole_group: bool = False) -> list[EvidenceBlock]:
    """Admit whole body/same-source-heading pairs, never truncate off their proof."""
    headers = {source_identity(b): b for b in scope_headers(blocks, ordered, years)}
    groups = {member.id: group for group in list_groups(blocks) if matches_subject(group, enumeration_subject)
              for member in group} if atomic_lists else {}
    for member, dependencies in dependency_groups(blocks).items():
        groups[member] = sorted({b.id: b for b in [*groups.get(member, []), *dependencies]}.values(), key=lambda b: b.start)
    if atomic_lists:
        for group in list_groups(blocks):
            if not matches_subject(group, enumeration_subject):
                continue
            first = group[0]
            preceding = max((b for b in blocks if source_identity(b) == source_identity(first)
                             and b.end <= first.start), key=lambda b: b.end, default=None)
            if preceding and re.fullmatch(r"\s*\*\*[^\n]+\*\*\s*", preceding.text):
                groups[preceding.id] = [preceding, *group]
        for summary in ordered:
            if not re.fullmatch(r"\s*\*\*[^\n]+\*\*\s*", summary.text):
                continue
            following = min((b for b in blocks if source_identity(b) == source_identity(summary)
                             and b.start >= summary.end), key=lambda b: b.start, default=None)
            if following and family(following):
                groups[summary.id] = [summary, *groups.get(following.id, [following])]
    ordered = coverage_order(ordered, coverage_goals or [], groups, years)
    if priority_ids:
        ordered = sorted(ordered, key=lambda b: b.id not in priority_ids)
    selected, seen, used = [], set(), 40  # Payload field names and brackets.
    whole_group_admitted = False
    intro_sources = set()
    dropped = []
    for body in ordered:
        header = headers.get(source_identity(body))
        bodies = groups.get(body.id, [body])
        parents = structural_context(blocks, body)
        body_ids = {b.id for b in bodies}
        continuations = [block for member in bodies for block in sentence_continuations(blocks, member)
                         if block.id not in seen and block.id not in body_ids][:2]
        pair = list({b.id: b for b in [header, *parents, *bodies, *continuations] if b is not None and b.id not in seen}.values())
        intros = {b.source_revision_id: b.source_context for b in pair if b.source_context and b.source_revision_id not in intro_sources}
        size = sum(len(json.dumps(model_block(b), ensure_ascii=False)) + 1 for b in pair)
        size += len(json.dumps(intros, ensure_ascii=False)) if intros else 0
        body_count = sum(not re.fullmatch(r"\s*#{1,6}\s+[^\n]+\s*", b.text)
                         and b.id not in {h.id for h in headers.values()} for b in [*selected, *pair])
        # One atomic proof unit can consist of more physical blocks than K.
        # Opt-in recovery may admit that FIRST unit whole, never a partial formula
        # or list. No further unrelated body can then enter; byte budget is hard.
        oversized_first = allow_first_whole_group and not selected and len(bodies) > 1
        if (body_count > limit and not oversized_first) or used + size > max_chars:
            dropped.append({"block_id": body.id, "reason": "block_limit" if body_count > limit else "character_budget",
                            "group_size": len(pair), "characters": size})
            continue
        selected.extend(pair)
        whole_group_admitted = whole_group_admitted or (oversized_first and body_count > limit)
        seen.update(b.id for b in pair)
        used += size
        intro_sources.update(intros)
        if whole_group_admitted:
            break
    if diagnostics is not None:
        diagnostics.update(packed_characters=used, packed_blocks=len(selected), dropped=dropped)
        if whole_group_admitted:
            diagnostics["whole_group_exceeds_block_k"] = True
    return selected


def structural_context(blocks: list[EvidenceBlock], body: EvidenceBlock) -> list[EvidenceBlock]:
    """Attach evidenced ancestors/table headers, never nearby unrelated prose."""
    identity = (body.binding_id, body.index_revision_id, body.source_revision_id)
    same = [block for block in blocks if (block.binding_id, block.index_revision_id, block.source_revision_id) == identity]
    by_unit = {block.unit_id: block for block in same if block.unit_id}
    result = []
    if body.record_heading_id:
        result.extend(b for b in same if b.id == body.record_heading_id)
    parent = by_unit.get(body.parent_id)
    for _ in range(6):
        if not parent:
            break
        if not parent.is_container:
            result.append(parent)
        else:
            result.extend(block for block in same if block.parent_id == parent.unit_id
                          and block.id != body.id and block.text in body.header_context)
        parent = by_unit.get(parent.parent_id)
    return list({block.id: block for block in reversed(result)}.values())
