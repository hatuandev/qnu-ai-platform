"""Read-only record-template context; raw spans and published manifests stay intact."""

import re
from collections import Counter, defaultdict

from app.modules.rag.evidence_bm25 import rank_blocks, tokens
from app.modules.rag.evidence_dependencies import source_identity
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan

HEADING = re.compile(r"\s*(#{1,6})\s+([^\n]+)\s*")
FIELD = re.compile(r"(?m)^\s*(?:[-+*]\s+)?(?:\*\*)?([^:\n*]{1,80}):\s*\S")


def label_key(text: str) -> str:
    return " ".join(term for term in tokens(text) if " " not in term)


def _record_headings(source: list[EvidenceBlock]) -> dict[str, EvidenceBlock]:
    candidates = []
    for position, block in enumerate(source):
        heading = HEADING.fullmatch(block.text)
        if not heading:
            continue
        fields = set()
        for following in source[position + 1:position + 5]:
            if HEADING.fullmatch(following.text) or not FIELD.search(following.text):
                break
            fields.update(label_key(match[1]) for match in FIELD.finditer(following.text))
        if len(fields) >= 2:
            candidates.append((block, len(heading[1]), fields))
    # A repeated field schema establishes a record-template hint, not a fact.
    return {block.id: block for block, depth, fields in candidates if any(
        other.id != block.id and depth == other_depth and len(fields & other_fields) >= 2
        for other, other_depth, other_fields in candidates)}


def _page_label(text: str) -> bool:
    heading = HEADING.fullmatch(text)
    if not heading:
        return False
    match = re.fullmatch(r"(?:Trang|Page)\s+(\d{1,4})(?:\s*[—–-].*)?", heading[2], re.IGNORECASE)
    return bool(match and int(match[1]) < 1900)


def enrich_hierarchy(blocks: list[EvidenceBlock]) -> list[EvidenceBlock]:
    sources = defaultdict(list)
    for block in blocks:
        if block.origin == "canonical":
            sources[source_identity(block)].append(block)
    updates = {}
    for source in sources.values():
        ordered = sorted(source, key=lambda b: (b.start, b.end))
        records = _record_headings(ordered)
        labels = Counter(label_key(match[2]) for b in ordered if (match := HEADING.fullmatch(b.text)))
        record = None
        path = []
        for block in ordered:
            heading = HEADING.fullmatch(block.text)
            if block.id in records:
                record, path = block, [heading[2]]
            elif record and heading and not _page_label(block.text):
                if (len(heading[1]) < len(HEADING.fullmatch(record.text)[1])
                        or len(heading[1]) == len(HEADING.fullmatch(record.text)[1])
                        and labels[label_key(heading[2])] < 2):
                    record, path = None, []
                else:
                    path = [HEADING.fullmatch(record.text)[2], heading[2]]
            if record:
                updates[block.id] = block.model_copy(update={
                    "record_label": HEADING.fullmatch(record.text)[2],
                    "record_heading_id": record.id, "record_path": path.copy(),
                    "header_context": "\n".join(dict.fromkeys([block.header_context, *path]))})
    return [updates.get(block.id, block) for block in blocks]


def requested_records(blocks: list[EvidenceBlock], entity: str | None) -> set[str]:
    if not entity:
        return set()
    entity = " " + label_key(entity) + " "
    return {label_key(b.record_label) for b in blocks if b.record_label
            and " " + label_key(b.record_label) + " " in entity}


def scope_error(claim: dict, blocks: list[EvidenceBlock], plan: QueryPlan) -> str | None:
    wanted = requested_records(blocks, plan.entity)
    if not wanted or not claim.get("references"):
        return None
    primary = next((b for b in blocks if b.id == claim["references"][0]["block_id"]), None)
    if primary and primary.record_label and label_key(primary.record_label) not in wanted:
        return "EVIDENCE_RECORD_SCOPE_MISMATCH"
    return None


def scope_candidates(blocks: list[EvidenceBlock], plan: QueryPlan) -> list[EvidenceBlock]:
    wanted = requested_records(blocks, plan.entity)
    if not wanted:
        return blocks
    # Generic group policy and unclassified material remain available for verification.
    return [b for b in blocks if not b.record_label or label_key(b.record_label) in wanted]


def record_candidates(blocks: list[EvidenceBlock], plan: QueryPlan, limit: int) -> list[EvidenceBlock]:
    wanted = requested_records(blocks, plan.entity)
    pool = [b for b in blocks if b.record_label and label_key(b.record_label) in wanted]
    if not pool:
        return []
    groups = defaultdict(list)
    for block in pool:
        if not block.is_container and not HEADING.fullmatch(block.text):
            groups[(block.record_heading_id, tuple(block.record_path))].append(block)
    # Rank source-backed subsection summaries as retrieval hints. Return ORIGINAL
    # members, never the generated concatenation as a citable source block.
    summaries = [members[0].model_copy(update={'text': '\n'.join([
        *members[0].record_path, *(b.text for b in members)])}) for members in groups.values()]
    members_by_id = {members[0].id: members for members in groups.values()}
    goals = plan.requested_topics or [plan.attribute or plan.enumeration_subject or plan.query, *plan.search_queries]
    per_goal = 1 if plan.requested_topics else 2
    result = [member for goal in goals for summary in rank_blocks(
        [summary for summary in summaries if _facet_hit(summary, goal)], [goal], per_goal, plan.years)
              for member in members_by_id[summary.id][:6]]
    return list({b.id: b for b in result}.values())[:limit]


def _facet_hit(summary: EvidenceBlock, goal: str) -> bool:
    words = set(tokens(goal))
    label = ' '.join([*summary.record_path[1:], *(m[1] for m in FIELD.finditer(summary.text))])
    if words.intersection(tokens(label)):
        return True
    phrases = {term for term in words if ' ' in term}
    return bool(phrases.intersection(tokens(summary.text)))
