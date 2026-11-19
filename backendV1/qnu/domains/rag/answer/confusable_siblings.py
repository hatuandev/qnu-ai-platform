"""Confusable siblings detection and disambiguation for QNU RAG (Slice 5).

Prevents Vector / Reranker drift between similar identifiers (e.g. '0012' vs '0120',
'AM-0007' vs 'AM-0070', '7480201' vs '7480202') or programs sharing names across
different study modes.
Operates via pure Python algorithmic distance (0 LLM tokens, < 1ms).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qnu.domains.rag.answer.schemas import EvidenceSource

_CODE_PATTERN = re.compile(r"\b([A-Z]{2,4}-?\d{4,7}|\d{7}|\b0\d{3}\b)\b")


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1] * (len(s2) + 1)
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row[j + 1] = min(insertions, deletions, substitutions)
        prev_row = curr_row
    return prev_row[-1]


def are_digit_permutations(s1: str, s2: str) -> bool:
    """Check if two strings are digit/character permutations (e.g. '0012' and '0120')."""
    if len(s1) != len(s2) or len(s1) < 2 or s1 == s2:
        return False
    return sorted(s1) == sorted(s2)


def find_confusable_siblings(
    target: str,
    candidates: list[str],
    *,
    max_distance: int = 2,
) -> list[str]:
    """Find candidate codes that are dangerously similar to the target code.

    Matches:
    - Distance <= max_distance (e.g. 'AM-0007' vs 'AM-0070', dist=2; '7480201' vs '7480202', dist=1).
    - Digit permutations / transpositions (e.g. '0012' vs '0120').
    """
    clean_target = target.strip()
    if not clean_target:
        return []

    confusables: list[str] = []
    seen = {clean_target}

    for cand in candidates:
        clean_cand = cand.strip()
        if not clean_cand or clean_cand in seen:
            continue

        # Permutation check (e.g. '0012' vs '0120')
        if are_digit_permutations(clean_target, clean_cand):
            confusables.append(clean_cand)
            seen.add(clean_cand)
            continue

        # Edit distance check
        dist = levenshtein_distance(clean_target, clean_cand)
        if 0 < dist <= max_distance:
            # For short codes (<= 4 chars like '0012'), only allow dist <= 1 or same length dist <= 2
            if len(clean_target) <= 4 and dist > 1 and len(clean_target) != len(clean_cand):
                continue
            confusables.append(clean_cand)
            seen.add(clean_cand)

    return sorted(confusables)


def build_confusable_warning(target: str, siblings: list[str]) -> str:
    """Build a deterministic warning string to pin exact anchors and avoid entity mixing."""
    if not siblings:
        return ""
    joined = ", ".join(f"'{s}'" for s in siblings)
    return (
        f"[CẢNH BÁO ĐỊNH DANH]: Mã/thực thể '{target}' rất dễ nhầm với các thực thể anh em: {joined}. "
        "Tuyệt đối KHÔNG trộn lẫn dữ liệu hoặc điều kiện giữa các thực thể này."
    )


def extract_codes_from_text(text: str) -> list[str]:
    """Extract code identifiers preserving zero prefixes and hyphenated prefixes."""
    return [match.strip() for match in _CODE_PATTERN.findall(text or "")]


def scan_for_confusables(
    query: str,
    sources: list[EvidenceSource],
) -> list[dict[str, Any]]:
    """Scan query and evidence sources for confusable codes and return warning metadata."""
    query_codes = extract_codes_from_text(query)
    source_codes: set[str] = set()
    for s in sources:
        source_codes.update(extract_codes_from_text(s.text))
        if s.structure:
            for v in s.structure.values():
                if isinstance(v, str):
                    source_codes.update(extract_codes_from_text(v))

    results: list[dict[str, Any]] = []
    pool = sorted(source_codes)

    for code in query_codes:
        siblings = find_confusable_siblings(code, pool)
        if siblings:
            results.append(
                {
                    "target_code": code,
                    "siblings": siblings,
                    "warning": build_confusable_warning(code, siblings),
                }
            )

    return results
