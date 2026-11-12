"""Resolve literal source anchors; never fuzzy-match or rewrite the recognised text."""

import re
from collections import defaultdict

from qnu.domains.ocr.review.schemas import RejectedSuggestion, Suggestion, TextUnit


def context_supports(item: Suggestion, text: str, start: int) -> bool:
    """Prove the quoted phrase surrounds this exact occurrence, not another one."""
    before, after = item.context_before, item.context_after
    if not before or not after:
        return False
    end = start + len(item.original)
    for match in re.finditer(re.escape(before), text):
        offset = match.start()
        local_start, local_end = start - offset, end - offset
        if (
            0 <= local_start < local_end <= len(before)
            and before[:local_start] + item.replacement + before[local_end:] == after
        ):
            # A single word is not enough proof unless it is the whole unit.
            return before == text or len(re.findall(r"\w+", before)) >= 2
    return False


def reject(item: Suggestion, reason: str) -> RejectedSuggestion:
    return RejectedSuggestion(
        evidence_id=item.evidence_id, reason=reason, start=item.start, end=item.end
    )


def anchor_suggestions(
    items: list[Suggestion], units: dict[str, TextUnit]
) -> tuple[list[Suggestion], list[RejectedSuggestion]]:
    anchored: list[Suggestion] = []
    rejected: list[RejectedSuggestion] = []
    groups: dict[tuple[str, str], list[Suggestion]] = defaultdict(list)
    for item in items:
        # Even an incorrectly counted position must be a proper forward span.
        if item.start >= item.end:
            rejected.append(reject(item, "invalid_span"))
        else:
            groups[item.evidence_id, item.original].append(item)
    for (evidence_id, original), group in groups.items():
        unit = units.get(evidence_id)
        if unit is None:
            rejected.extend(reject(item, "unknown_evidence") for item in group)
            continue
        text = unit.text
        occurrences = [match.start() for match in re.finditer(re.escape(original), text)]
        for item in group:
            if text[item.start : item.end] == original:
                anchored.append(item)
                continue
            if not occurrences:
                rejected.append(reject(item, "source_text_missing"))
                continue
            if len(occurrences) == 1:
                start = occurrences[0]
            else:
                # A repeated literal is resolvable only when the quoted context
                # selects exactly one occurrence; otherwise it stays unreviewed.
                supported = [start for start in occurrences if context_supports(item, text, start)]
                if len(supported) != 1:
                    rejected.append(reject(item, "source_anchor_ambiguous"))
                    continue
                start = supported[0]
            anchored.append(item.model_copy(update={"start": start, "end": start + len(original)}))
    return anchored, rejected
