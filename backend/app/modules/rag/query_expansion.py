"""Provenance-aware query weights; expansion never defines authorization or scope."""

import math
import re
import unicodedata
from collections.abc import Callable, Sequence
from typing import Literal, Self

QueryRole = Literal["original", "variant", "feedback", "glossary"]
VERSION = "weighted-expansion-v1"
ORIGINAL_SHARE = 0.65
EXPANSION_SHARE = 1 - ORIGINAL_SHARE
# Initial lexical weight for glossary terms: below variant queries, sharing the
# single expansion budget. Not a tuned optimum, only a conservative starting point.
GLOSSARY_LEXICAL_WEIGHT = 0.3


def normalized_query(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip().casefold()


class SearchQuery(str):
    """String-compatible transport so dense/rerank APIs still receive natural text."""

    original: str
    role: QueryRole

    def __new__(cls, text: str, original: str, role: QueryRole) -> Self:
        value = super().__new__(cls, text)
        value.original, value.role = original, role
        return value


def query_shares(queries: Sequence[str]) -> list[float]:
    """Duplicate query texts receive zero extra votes; role does not depend on order."""
    unique: dict[str, int] = {}
    for index, query in enumerate(queries):
        key = normalized_query(query)
        previous = unique.get(key)
        if previous is None or getattr(query, "role", None) == "original":
            unique[key] = index
    originals = [index for index in unique.values() if getattr(queries[index], "role", None) == "original"]
    # Backwards-compatible plain callers have their first query as authority.
    if not originals and not any(isinstance(query, SearchQuery) for query in queries) and unique:
        originals = [next(iter(unique.values()))]
    expanded = [index for index in unique.values() if index not in originals]
    shares = [0.0] * len(queries)
    if not originals:
        raise ValueError("Expanded queries require their original query")
    for index in originals:
        shares[index] = (ORIGINAL_SHARE if expanded else 1.0) / len(originals)
    for index in expanded:
        shares[index] = EXPANSION_SHARE / len(expanded)
    return shares


def lexical_weights(queries: Sequence[str], tokenize: Callable[[str], list[str]]) -> dict[str, float]:
    """Keep legacy plain scoring; cap total expansion mass, not just each term."""
    tagged = next((query for query in queries if isinstance(query, SearchQuery)), None)
    if tagged is None:
        return dict.fromkeys((term for query in queries for term in tokenize(query)), 1.0)
    originals = set(tokenize(tagged.original))
    weights = dict.fromkeys(originals, 1.0)
    expanded: dict[str, float] = {}
    for query in queries:
        role = getattr(query, "role", None)
        if role == "glossary":
            base = GLOSSARY_LEXICAL_WEIGHT
        else:
            base = 0.3 if role == "feedback" else 0.5
        for term in set(tokenize(query)) - originals:
            expanded[term] = max(expanded.get(term, 0), base)
    mass = sum(expanded.values())
    scale = min(1.0, len(originals) * EXPANSION_SHARE / ORIGINAL_SHARE / mass) if mass else 1.0
    weights.update({term: weight * scale for term, weight in expanded.items()})
    if not all(math.isfinite(weight) and weight >= 0 for weight in weights.values()):
        raise ValueError("Invalid query term weights")
    return weights
