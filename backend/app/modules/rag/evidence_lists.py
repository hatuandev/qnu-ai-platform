"""Same-source syntactic list families and atomic coverage; no domain vocabulary."""

import re

from app.modules.rag.evidence_bm25 import tokens
from app.modules.rag.evidence_schemas import EvidenceBlock

MARKER = re.compile(r"^\s*(?:(?P<bullet>[-+*])|(?P<number>\d+)[.)]|(?P<letter>[a-z])[.)])\s")


def family(block: EvidenceBlock) -> str | None:
    marker = MARKER.match(block.text) if block.origin == "canonical" else None
    if not marker:
        return None
    return marker.group("bullet") or ("number" if marker.group("number") else "letter")


def list_groups(blocks: list[EvidenceBlock]) -> list[list[EvidenceBlock]]:
    sources = {}
    for block in blocks:
        if block.origin == "canonical":
            sources.setdefault((block.binding_id, block.index_revision_id, block.source_revision_id), []).append(block)
    result = []
    for source in sources.values():
        run = []
        previous = None
        for block in sorted(source, key=lambda b: b.start):
            marker = family(block)
            if not marker or marker != previous:
                if len(run) > 1:
                    result.append(run)
                run = []
            if marker:
                run.append(block)
            previous = marker
        if len(run) > 1:
            result.append(run)
    return result


def matches_subject(group: list[EvidenceBlock], subject: str | None) -> bool:
    if not subject:
        return True
    # A record's heterogeneous key/value fields are not an enumeration of the
    # requested topic. Individual requested fields are covered by topic verification.
    # Never apply this exception to unclassified policy lists or record subsections.
    if group and all(b.record_label and b.record_path == [b.record_label]
                     and re.match(r"^\s*[-+*]\s+[^:\n]{1,80}:\s*\S", b.text) for b in group):
        return False
    labels = [tokens(MARKER.sub("", b.text).splitlines()[0]) for b in group]
    prefix = []
    for parts in zip(*labels, strict=False):
        if len(set(parts)) != 1 or not parts[0].isalpha():
            break
        prefix.append(parts[0])
    # Without a shared syntactic label, retain conservative coverage checks.
    return len(prefix) < 2 or bool(set(tokens(" ".join(prefix))).intersection(tokens(subject)))


def uncovered_list_members(blocks: list[EvidenceBlock], claims: list[dict], subject: str | None = None) -> list[str]:
    cited = {ref["block_id"] for claim in claims for ref in claim["references"]}
    missing = []
    for group in list_groups(blocks):
        if not matches_subject(group, subject):
            continue
        ids = {block.id for block in group}
        if ids.intersection(cited):
            missing.extend(sorted(ids - cited))
    return missing


def list_tail_context(blocks: list[EvidenceBlock], selected: list[EvidenceBlock]) -> list[EvidenceBlock]:
    """Keep one unmarked trailing paragraph, but never the next marked section."""
    selected_ids = {b.id for b in selected}
    result = []
    for group in list_groups(blocks):
        if not any(b.id in selected_ids for b in group):
            continue
        last = group[-1]
        following = sorted((b for b in blocks if b.origin == "canonical"
            and (b.binding_id, b.index_revision_id, b.source_revision_id) ==
                (last.binding_id, last.index_revision_id, last.source_revision_id)
            and b.start > last.start), key=lambda b: b.start)
        if following:
            tail = following[0]
            letters = [c for c in tail.text if c.isalpha()]
            if (not family(tail) and len(tail.text) <= 800 and not tail.text.startswith("#")
                    and not (letters and all(c.isupper() for c in letters))):
                result.append(tail)
    return result
