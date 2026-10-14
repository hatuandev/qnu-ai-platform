"""Server-owned source passages: models select IDs instead of reproducing quotes."""

import re

from pydantic import Field

from app.modules.rag.evidence_schemas import AnswerProposal, EvidenceClaim, QuoteReference, StrictContract


class PassageClaim(StrictContract):
    id: str
    text: str = Field(min_length=3, max_length=2000)
    evidence_ids: list[str] = Field(min_length=1, max_length=4)


class PassageProposal(StrictContract):
    status: str = Field(pattern="^(supported|partial|missing|conflict|clarify)$")
    claims: list[PassageClaim] = Field(default_factory=list, max_length=12)
    missing_constraints: list[str] = Field(default_factory=list, max_length=10)


def passage_catalog(blocks):
    catalog = {}
    for index, block in enumerate(blocks, 1):
        # Keep punctuation, decimal values and formulas intact in every raw span.
        starts = [0, *[m.end() for m in re.finditer(r"(?<=[.!?;])\s+(?=[A-ZÀ-Ỹ])", block.text)], len(block.text)]
        for part, (start, end) in enumerate(zip(starts, starts[1:]), 1):
            quote = block.text[start:end].strip()
            if len(quote) >= 3:
                catalog[f"e{index}.{part}"] = QuoteReference(block_id=block.id, quote=quote)
    return catalog


def passage_payload(blocks, catalog):
    by_id = {block.id: block for block in blocks}
    return [{"id": pid, "block_id": ref.block_id, "text": ref.quote,
             "source_revision_id": by_id[ref.block_id].source_revision_id,
             "section": by_id[ref.block_id].section} for pid, ref in catalog.items()]


def resolve_proposal(proposal: PassageProposal, catalog) -> AnswerProposal:
    claims = []
    for claim in proposal.claims:
        if any(pid not in catalog for pid in claim.evidence_ids):
            # Never silently bind an unknown ID to arbitrary evidence.
            references = [QuoteReference(block_id="invalid", quote="unknown passage")]
        else:
            references = [catalog[pid] for pid in dict.fromkeys(claim.evidence_ids)]
        claims.append(EvidenceClaim(id=claim.id, text=claim.text, references=references))
    return AnswerProposal(status=proposal.status, claims=claims, missing_constraints=proposal.missing_constraints)
