"""Scoped, data-driven precedence; never discard a source's unique information."""

from app.core.evidence_policy import EvidencePolicy, EvidenceSourcePreference
from app.modules.rag.evidence_blocks import rank_blocks
from app.modules.rag.evidence_schemas import (
    EvidenceBlock,
    QueryPlan,
    QuoteReference,
    VerificationResult,
)
from app.modules.rag.evidence_validation import bind_quote


def active_preferences(policy: EvidencePolicy, plan: QueryPlan,
                       blocks: list[EvidenceBlock]) -> list[EvidenceSourcePreference]:
    sources = {b.source_revision_id for b in blocks}
    # Unknown applicability cannot activate a precedence rule.
    return [r for r in policy.source_preferences if plan.years and
            set(plan.years).issubset(r.years) and r.preferred_source_revision_id in sources]


def preference_candidates(rules: list[EvidenceSourcePreference], plan: QueryPlan,
                          blocks: list[EvidenceBlock]) -> list[EvidenceBlock]:
    selected = []
    for rule in rules:
        # Table rows have a separate ranked/reranked lane. Their repeated field
        # labels must not drown short authoritative prose fields in this lane.
        source_blocks = [b for b in blocks if b.source_revision_id == rule.preferred_source_revision_id
                         and b.origin == "canonical"]
        for query in [plan.attribute, plan.query, *plan.search_queries]:
            if not query:
                continue
            selected.extend(rank_blocks(source_blocks, [query], 12, plan.years))
    return list({b.id: b for b in selected}.values())[:24]


def validate_superseding_quotes(source_id: str, references: list[QuoteReference],
                               rules: list[EvidenceSourcePreference],
                               blocks: dict[str, EvidenceBlock]) -> bool:
    """A verifier must attach exact preferred-source proof to disqualify an old claim."""
    if not references:
        return False
    bound = [bind_quote(reference, blocks) for reference in references]
    return any(source_id in rule.superseded_source_revision_ids and
               all(r["source_revision_id"] == rule.preferred_source_revision_id for r in bound)
               for rule in rules)


def apply_precedence(verifier: VerificationResult, claims: list[dict],
                     rules: list[EvidenceSourcePreference], blocks: dict[str, EvidenceBlock]) -> list[dict]:
    """Invalid override rejects its claim, never causes a false source switch."""
    rejected = []
    verdicts = {verdict.claim_id: verdict for verdict in verifier.verdicts}
    for claim in claims:
        verdict = verdicts[claim["id"]]
        if not verdict.superseded_by:
            continue
        source = claim["references"][0]["source_revision_id"]
        try:
            proofs = [bind_quote(ref, blocks) for ref in verdict.superseded_by]
            original = {(ref["block_id"], ref["quote"]) for ref in claim["references"]}
            if all((ref["block_id"], ref["quote"]) in original for ref in proofs):
                # Repeating the claim's own quotes is not a replacement by a
                # different source. Preserve the independent semantic verdict.
                verdict.superseded_by = []
                continue
            valid = validate_superseding_quotes(source, verdict.superseded_by, rules, blocks)
        except ValueError:
            valid = False
        verdict.scope_compatible = False
        if not valid:
            rejected.append({"claim_id": claim["id"], "reason": "INVALID_PRECEDENCE_PROOF"})
    return rejected
