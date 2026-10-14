"""Read-time structural closure for numbered parents and subordinate branches."""

import re
from collections import defaultdict

from app.modules.rag.evidence_lists import MARKER
from app.modules.rag.evidence_schemas import EvidenceBlock


def source_identity(block: EvidenceBlock) -> tuple[str, str, str, str]:
    return block.binding_id, block.index_revision_id, block.source_revision_id, block.canonical_hash


def _level(block: EvidenceBlock) -> int | None:
    marker = MARKER.match(block.text)
    if not marker:
        return None
    return 1 if marker.group("number") else 2


def _numbered_groups(source: list[EvidenceBlock]) -> list[list[EvidenceBlock]]:
    groups = []
    for position, parent in enumerate(source):
        if _level(parent) != 1:
            continue
        children = []
        for child in source[position + 1:]:
            if _level(child) == 1 or child.text.lstrip().startswith("#") or child.section != parent.section:
                break
            if not children and _level(child) != 2:
                break
            children.append(child)
        if children:
            groups.extend(_branch_groups(parent, children))
    return groups


def _branch_groups(parent: EvidenceBlock, children: list[EvidenceBlock]) -> list[list[EvidenceBlock]]:
    # Lettered rule branches share conditions/exceptions. Bullet options are
    # independent members unless the query explicitly asks for the entire list.
    first = MARKER.match(children[0].text)
    if first and first.group("bullet"):
        return [[parent, child] for child in children]
    return [[parent, *children]]


def dependency_groups(blocks: list[EvidenceBlock]) -> dict[str, list[EvidenceBlock]]:
    """Never cross binding/index/hash; all members retain their original raw spans."""
    sources = defaultdict(list)
    for block in blocks:
        if block.origin == "canonical" and not block.is_container:
            sources[source_identity(block)].append(block)
    groups = []
    for source in sources.values():
        ordered = sorted(source, key=lambda block: (block.start, block.end))
        groups.extend(_numbered_groups(ordered))
        by_unit = {block.unit_id: block for block in ordered if block.unit_id}
        children = defaultdict(list)
        for block in ordered:
            if block.parent_id in by_unit:
                children[block.parent_id].append(block)
        for parent_id, members in children.items():
            parent = by_unit[parent_id]
            # Heading ancestry is attached separately. Do not expand an entire
            # book chapter merely because it has a heading parent.
            if _level(parent) is not None or re.search(r":\s*$", parent.text):
                groups.extend(_branch_groups(parent, members))
    result = {}
    for group in groups:
        for member in group:
            existing = result.get(member.id, [])
            result[member.id] = sorted({b.id: b for b in [*existing, *group]}.values(), key=lambda b: b.start)
    return result


def coverage_order(blocks: list[EvidenceBlock], goals: list[str], groups: dict,
                   years: list[int]) -> list[EvidenceBlock]:
    """Greedy discounted coverage of query facets, with dependency costs intact.

    Lexical coverage is a packing hint, NEVER proof of semantic completeness.
    """
    from app.modules.rag.evidence_bm25 import rank_blocks

    if not goals:
        return blocks
    facets = list(dict.fromkeys(goal for goal in goals if goal))
    scores = [{block.id: 1 / rank for rank, block in enumerate(
        rank_blocks(blocks, [goal], len(blocks), years), 1)} for goal in facets]
    achieved = [0.0] * len(scores)
    pending = list(enumerate(blocks))
    result = []
    while pending:
        def gain(item, previous_coverage=achieved):
            rank, block = item
            members = groups.get(block.id, [block])
            incremental = sum(max(0, max((facet.get(b.id, 0) for b in members), default=0) - previous)
                              for facet, previous in zip(scores, previous_coverage, strict=True))
            cost = max(1, sum(len(b.text) for b in members))
            return (incremental / cost ** 0.25 + 0.1 / (rank + 1), -rank)
        chosen = max(pending, key=gain)
        pending.remove(chosen)
        block = chosen[1]
        result.append(block)
        members = groups.get(block.id, [block])
        achieved = [max(previous, max((facet.get(b.id, 0) for b in members), default=0))
                    for facet, previous in zip(scores, achieved, strict=True)]
    return result


def dependency_intros(blocks: list[EvidenceBlock]) -> dict[str, list[EvidenceBlock]]:
    return {member: [group[0]] for member, group in dependency_groups(blocks).items()
            if group and group[0].id != member and _level(group[0]) == 1 and len(group[0].text) <= 4000}
