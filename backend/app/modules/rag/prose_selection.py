"""Topic-first recovery ordering without changing source text or scope."""

from itertools import zip_longest

from app.modules.rag.evidence_bm25 import tokens
from app.modules.rag.evidence_schemas import EvidenceBlock


def merge_candidates(left: list[EvidenceBlock], right: list[EvidenceBlock], limit: int) -> list[EvidenceBlock]:
    """Reserve both retrieval channels under one ceiling, retaining raw IDs."""
    result = {}
    for pair in zip_longest(left, right):
        for block in pair:
            if block is not None and len(result) < limit:
                result.setdefault(block.id, block)
    return list(result.values())


def topic_order(blocks: list[EvidenceBlock], topics: list[str]) -> list[EvidenceBlock]:
    """Keep complete lexical topic matches ahead of short partial boilerplate.

    This is only candidate priority; entailment and applicability still require
    independent audit. Use body terms, not filename/heading as answer evidence.
    Stable ordering preserves reranker order within equivalent coverage tiers.
    """
    facets = [set(tokens(topic)) for topic in topics if topic.strip()]
    if not facets:
        return blocks

    def coverage(block: EvidenceBlock) -> tuple[int, float]:
        body = set(tokens(block.text))
        shares = [len(body & facet) / max(1, len(facet)) for facet in facets]
        return sum(share == 1 for share in shares), sum(shares) / len(shares)

    return sorted(blocks, key=coverage, reverse=True)


def distinct_candidates(blocks: list[EvidenceBlock]) -> list[EvidenceBlock]:
    """Deduplicate identical candidate bodies only within identical source/scope.

    Keep the corpus intact for list/dependency expansion and quote offsets. Never
    merge sources, different years, headings, records, or merely similar prose.
    """
    seen, result = set(), []
    for block in blocks:
        key = (block.binding_id, block.index_revision_id, block.source_revision_id,
               block.canonical_hash, block.section, block.header_context, block.parent_id,
               tuple(block.record_path), tuple(block.scope_years),
               block.temporal_scope.model_dump_json(), block.text)
        if key not in seen:
            seen.add(key)
            result.append(block)
    return result
