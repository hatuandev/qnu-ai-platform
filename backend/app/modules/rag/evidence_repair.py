"""Bounded corrective search feedback and safe partial-answer preservation."""

from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.evidence_validation import number_values


def coverage_feedback(question: str, missing: list[str], uncovered: list[str],
                      allowed_years: list[int] | None = None) -> list[str]:
    allowed = number_values(question) | number_values(" ".join(map(str, allowed_years or [])))
    feedback = []
    for item in missing:
        # Model feedback can identify a gap, not introduce expected answers or years.
        if not (number_values(item) - allowed) and item not in feedback:
            feedback.append(item[:200])
    return feedback[:3] or ([question] if uncovered else [])


def new_evidence(previous: list[EvidenceBlock], corrected: list[EvidenceBlock]) -> list[str]:
    before = {(b.binding_id, b.index_revision_id, b.source_revision_id, b.canonical_hash, b.id, b.text) for b in previous}
    return [b.id for b in corrected if
        (b.binding_id, b.index_revision_id, b.source_revision_id, b.canonical_hash, b.id, b.text) not in before]


def retain_safe_claims(claims: list[dict], previous: list[dict], blocks: list[EvidenceBlock]) -> list[dict]:
    """Reverify retained claims together with the new draft; never auto-approve them."""
    result = list(claims)
    by_id = {block.id: block for block in blocks}
    for old in previous:
        if not all(ref["block_id"] in by_id and ref["quote"] in by_id[ref["block_id"]].text and
            all(ref.get(key) == getattr(by_id[ref["block_id"]], key) for key in
                ("binding_id", "index_revision_id", "source_revision_id", "canonical_hash")) for ref in old["references"]):
            continue
        primary = old["references"][0]
        same = lambda ref, primary=primary: all(ref.get(key) == primary.get(key) for key in
            ("binding_id", "index_revision_id", "source_revision_id", "canonical_hash", "origin", "fact_id"))
        if any(same(claim["references"][0]) and old["text"] in claim["text"] for claim in result):
            continue
        result.append({**old, "id": f"retained.{len(result)}.{old['id']}"})
    return result
