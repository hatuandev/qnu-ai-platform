"""One-hop numeric/reference closure, for verification, never source precedence."""

import re
from collections import Counter
from decimal import Decimal

from app.modules.rag.evidence_bm25 import tokens
from app.modules.rag.evidence_validation import number_values


def anchors(text: str) -> set[str]:
    # Long quantities/reference identifiers, excluding standalone years.
    return {str(value) for value in number_values(text) if isinstance(value, Decimal) and value >= 100
            and not re.fullmatch(r"(?:19|20)\d{2}", str(value))}


def linked_candidates(blocks, ranked, years, *, max_links=2):
    """Expose an update/comparison mentioning an earlier figure to the verifier.

    Equal numbers are only search anchors. Neither dates nor this ordering assert
    replacement. The source-bound semantic audit must verify the actual relation.
    """
    if not ranked:
        return []
    seed = ranked[0]
    own = anchors(seed.text)
    if not own:
        return ranked
    frequencies = Counter(anchor for block in blocks for anchor in anchors(block.text))
    seed_words = set(tokens(seed.text))
    links = []
    for block in blocks:
        shared = own.intersection(anchors(block.text))
        if (block.id == seed.id or block.is_container or not shared
                or not any(frequencies[a] <= 12 for a in shared)
                or len(seed_words.intersection(tokens(block.text))) < 4):
            continue
        # A verified other-year block must not enter an explicitly scoped lookup.
        if years and block.scope_years and not set(years).intersection(block.scope_years):
            continue
        links.append(block)
    links.sort(key=lambda b: (-len(own.intersection(anchors(b.text))), b.id))
    return list({b.id: b for b in [seed, *links[:max_links], *ranked[1:]]}.values())


def reference_priority(ranked):
    """Prefer a reference-linked passage carrying the earlier anchors plus context.

    This is packing informativeness, not a newer-source/supersession decision.
    Both passages remain candidates; the semantic verifier owns applicability.
    """
    if len(ranked) < 2:
        return []
    first, second = anchors(ranked[0].text), anchors(ranked[1].text)
    if not first.intersection(second):
        return []
    return [ranked[1], ranked[0]] if first < second else ranked[:2]
