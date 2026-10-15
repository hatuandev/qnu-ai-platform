"""Bounded, content/revision-keyed BM25 statistics; never caches authorization."""

import math
import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache

from app.modules.rag.evidence_schemas import EvidenceBlock


def tokens(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    words = re.findall(r"\w+", "".join(c for c in decomposed if not unicodedata.combining(c)))
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
    signature = tuple((b.binding_id, b.index_revision_id, b.source_revision_id, b.id,
                       b.canonical_hash, f"{b.title}\n{b.section}\n{' / '.join(b.record_path)}", b.text) for b in blocks)
    lengths, average, postings = corpus_statistics(signature)
    scores = defaultdict(float)
    for term in sorted({term for query in queries for term in tokens(query)}):
        hits = postings.get(term, [])
        idf = math.log(1 + (len(blocks) - len(hits) + 0.5) / (len(hits) + 0.5))
        for index, frequency in hits:
            scores[index] += idf * (frequency * 2.2) / (
                frequency + 1.2 * (0.25 + 0.75 * lengths[index] / max(1, average)))
    wanted = set(years or [])
    ranked = []
    for index, score in scores.items():
        block = blocks[index]
        if block.is_container:
            continue
        if re.fullmatch(r"\s*#{1,6}\s+[^\n]+\s*", block.text):
            continue  # Headings supply context; they are not an answer-bearing hit.
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
