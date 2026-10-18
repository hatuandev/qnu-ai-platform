"""Bounded, content/revision-keyed BM25 statistics; never caches authorization."""

import math
import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache

from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.query_expansion import lexical_weights


def tokens(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    words = re.findall(r"[^\W_]+", "".join(c for c in decomposed if not unicodedata.combining(c)))
    return words + [" ".join(words[i:i + 2]) for i in range(len(words) - 1)]


@lru_cache(maxsize=4)
def corpus_statistics(signature: tuple[tuple[str, ...], ...]):
    # Field-weighted term frequencies: body evidence dominates repeated labels.
    counts = []
    for row in signature:
        body = Counter(tokens(row[-1]))
        context = Counter(tokens(row[-2]))
        counts.append({term: body[term] + 0.15 * context[term] for term in body.keys() | context.keys()})
    lengths = [sum(count.values()) for count in counts]
    average = sum(lengths) / max(1, len(lengths))
    postings = defaultdict(list)
    for index, count in enumerate(counts):
        for term, frequency in count.items():
            postings[term].append((index, frequency))
    return lengths, average, dict(postings)


def rank_blocks(blocks: list[EvidenceBlock], queries: list[str], limit: int,
                years: list[int] | None = None) -> list[EvidenceBlock]:
    if not blocks or limit <= 0:
        return []
    # Legacy prose header_context can contain the whole source. Only typed table
    # units carry an actual column-header chain suitable for fielded scoring.
    signature = tuple((b.binding_id, b.index_revision_id, b.source_revision_id, b.id,
                       b.canonical_hash, f"{b.title}\n{b.section}\n{' / '.join(b.record_path)}\n"
                       + (b.header_context if b.fact_context.get("source_kind") == "table" else ""), b.text) for b in blocks)
    lengths, average, postings = corpus_statistics(signature)
    scores = defaultdict(float)
    for term, query_weight in sorted(lexical_weights(queries, tokens).items()):
        hits = postings.get(term, [])
        idf = math.log(1 + (len(blocks) - len(hits) + 0.5) / (len(hits) + 0.5))
        for index, frequency in hits:
            scores[index] += query_weight * idf * (frequency * 2.2) / (
                frequency + 1.2 * (0.25 + 0.75 * lengths[index] / max(1, average)))
    wanted = set(years or [])
    original = getattr(queries[0], "original", queries[0]) if queries else ""
    # Leading-zero identifiers are literal constraints, not ordinary prose words.
    # Use only the original question, never model-authored query expansion.
    literal_codes = {token for token in tokens(original) if token.isdigit() and len(token) > 1 and token.startswith("0")}
    ranked = []
    for index, score in scores.items():
        block = blocks[index]
        if block.is_container:
            continue
        if block.unit_id and block.parent_id and block.unit_id == f"{block.parent_id}:header":
            continue  # A structural header labels data; it is not a data row.
        if re.fullmatch(r"\s*#{1,6}\s+[^\n]+\s*", block.text):
            continue  # Headings supply context; they are not an answer-bearing hit.
        if literal_codes.intersection(tokens(block.text)):
            score *= 4
        fact_year = (block.fact_context.get("temporal_context") or {}).get("year")
        if wanted and ((fact_year and fact_year not in wanted)
                       or (block.scope_years and not wanted.intersection(block.scope_years))):
            continue
        observed = (set(block.temporal_scope.data_years) or set(block.temporal_scope.mentioned_years)
                    or {int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", block.text)})
        if wanted and observed and not observed.intersection(wanted):
            score *= 0.1  # Hint only; semantic verification establishes applicability.
        elif wanted and observed.intersection(wanted):
            score *= 1.1
        elif wanted:
            hints = set(block.temporal_scope.heading_years) or {int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", block.source_context)}
            if hints:
                score *= 1.05 if wanted.intersection(hints) else 0.1
        ranked.append((score, index))
    return [blocks[index] for score, index in sorted(ranked, reverse=True)[:limit] if score > 0]
