"""Topic-first recovery ordering without changing source text or scope."""

import re
from itertools import zip_longest

from app.modules.rag.evidence_bm25 import tokens
from app.modules.rag.evidence_schemas import EvidenceBlock


def recovery_order(ranked: list[EvidenceBlock], supplemental: list[EvidenceBlock],
                   priority: list[EvidenceBlock], *, question: str = '') -> list[EvidenceBlock]:
    """Keep ranked full conditions ahead of supplemental table summaries.

    Formula/caption bodies restore otherwise absent modalities. A table row is
    only a retrieval anchor and must not crowd out its higher-ranked full rule.
    """
    from app.modules.rag.source_locators import TABLE_LABEL

    bodies = [block for block in supplemental if block.fact_context.get('source_kind') != 'table'
              and not TABLE_LABEL.match(block.text.strip())]
    identifiers = re.findall(r'(?<!\w)[A-Za-zĐđ]+[\w]*(?:[-/][A-Za-zĐđ0-9]+)+(?!\w)', question)
    addressed = [block for block in supplemental if block.fact_context.get('source_kind') == 'table'
                 and any(re.search(r'(?<!\w)' + re.escape(label) + r'(?!\w)', block.text, re.IGNORECASE) for label in identifiers)]
    return list({block.id: block for block in [*priority, *bodies, *addressed, *ranked, *supplemental]}.values())


def answer_facets(topics: list[str], question: str) -> list[str]:
    """Locators and literal scenario inputs constrain evidence; they are not facts to repeat.

    The complete original question still reaches both independent semantic audits.
    This only prevents a scope locator/input from becoming a second public-answer demand.
    """
    scenario = bool(re.search(r'\b[^\W\d_]\w*\s*=\s*[-+]?\d', question))
    result = []
    for topic in topics:
        locator = re.fullmatch(r'(?:điều|mục|phần|chương|bảng|hình|phụ lục)\s+[\dIVXLCDM]+(?:[.\-][\dIVXLCDM]+)*', topic, re.IGNORECASE)
        given = (scenario and not re.fullmatch(r'(?:19|20)\d{2}', topic.strip())
                 and topic.casefold() in question.casefold() and bool(re.match(r'(?:[^\W\d_]\w*\s*=|\d)', topic)))
        if locator or given:
            continue
        result.append(topic)
    return result


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
