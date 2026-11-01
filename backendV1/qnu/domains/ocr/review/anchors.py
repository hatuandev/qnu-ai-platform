"""Resolve literal source anchors; never fuzzy-match or rewrite the recognised text."""

import re
from collections import defaultdict

from qnu.domains.ocr.review.schemas import Suggestion, TextUnit


def anchor_suggestions(items: list[Suggestion], units: dict[str, TextUnit]) -> list[Suggestion]:
    groups: dict[tuple[str, str], list[Suggestion]] = defaultdict(list)
    for item in items:
        # Even an incorrectly counted position must be a proper forward span.
        if item.start >= item.end:
            raise ValueError("span")
        groups[item.evidence_id, item.original].append(item)
    output = []
    for (evidence_id, original), group in groups.items():
        text = units[evidence_id].text
        if all(text[s.start : s.end] == original for s in group):
            output.extend(group)
            continue
        matches = [m.start() for m in re.finditer(re.escape(original), text)]
        if len(matches) != len(group) or not matches:
            raise ValueError("ambiguous source anchor")
        if len({s.replacement for s in group}) != 1:
            raise ValueError("conflicting repeated anchors")
        if len({(s.start, s.end) for s in group}) != len(group):
            raise ValueError("duplicate proposal")
        # One exact occurrence is unique. Repeated occurrences are resolvable only
        # if every occurrence was proposed once with the same replacement.
        for item, start in zip(sorted(group, key=lambda s: s.start), matches, strict=True):
            output.append(item.model_copy(update={"start": start, "end": start + len(original)}))
    return output
