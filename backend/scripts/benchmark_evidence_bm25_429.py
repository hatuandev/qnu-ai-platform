"""Compare prior BM25 scoring to cached postings on frozen diagnostic evidence."""

import json
import math
import re
import statistics
import time
from collections import Counter
from pathlib import Path

from app.modules.rag.evidence_bm25 import corpus_statistics, rank_blocks, tokens
from app.modules.rag.evidence_schemas import EvidenceBlock


def reference_rank(blocks, queries, limit, years):
    counts = [Counter(tokens(f"{b.title}\n{b.section}\n{b.text}")) for b in blocks]
    frequency = Counter(term for count in counts for term in count)
    terms = {term for query in queries for term in tokens(query)}
    average = sum(sum(c.values()) for c in counts) / len(counts)
    scores = []
    for index, count in enumerate(counts):
        length = sum(count.values())
        score = 0.0
        for term in sorted(terms & count.keys()):
            idf = math.log(1 + (len(counts) - frequency[term] + 0.5) / (frequency[term] + 0.5))
            tf = count[term]
            score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * length / max(1, average)))
        wanted = set(years)
        fact_year = (blocks[index].fact_context.get("temporal_context") or {}).get("year")
        if wanted and ((fact_year and fact_year not in wanted)
                       or (blocks[index].scope_years and not wanted.intersection(blocks[index].scope_years))):
            continue
        observed = {int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", blocks[index].header_context + "\n" + blocks[index].text)}
        if wanted and observed and not observed.intersection(wanted):
            score *= 0.1
        scores.append((score, index))
    return [blocks[index] for score, index in sorted(scores, reverse=True)[:limit] if score > 0]


def main():
    fixture = json.loads(Path("storage/evidence429_before.json").read_text(encoding="utf-8"))
    corpus = list({b["id"]: EvidenceBlock.model_validate(b) for case in fixture for b in case["blocks"]}.values())
    queries = [case["plan"]["query"] for case in fixture]
    for query in queries:
        assert [b.id for b in rank_blocks(corpus, [query], 10, [2026])] == [b.id for b in reference_rank(corpus, [query], 10, [2026])]
    timings = {}
    for name, function in [("previous_rebuild", reference_rank), ("cached_postings", rank_blocks)]:
        samples = []
        for _ in range(30):
            start = time.perf_counter()
            for query in queries:
                function(corpus, [query], 10, [2026])
            samples.append((time.perf_counter() - start) * 1000 / len(queries))
        timings[name] = round(statistics.median(samples), 3)
    result = {"blocks": len(corpus), "queries": len(queries), "rankings_identical": True,
              "median_ms_per_rank": timings, "cache": corpus_statistics.cache_info()._asdict(),
              "scope": "Frozen diagnostic corpus; warm BM25 scoring only, not end-to-end chatbot latency."}
    Path("storage/bm25_429_benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
