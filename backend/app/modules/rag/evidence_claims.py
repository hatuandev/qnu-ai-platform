"""Bind proposals to their own source spans, with one bounded quote repair."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.evidence_blocks import scope_headers
from app.modules.rag.evidence_lists import uncovered_list_members
from app.modules.rag.evidence_model import PROPOSE_INSTRUCTION, structured_call
from app.modules.rag.evidence_schemas import AnswerProposal, EvidenceBlock, QuoteReference
from app.modules.rag.evidence_validation import (
    YEAR,
    bind_quote,
    numbers_supported,
    row_entities_supported,
    same_source,
)
from app.modules.rag.schemas import AskRequest

logger = logging.getLogger(__name__)


def bind_claims(proposal: AnswerProposal, blocks: list[EvidenceBlock]) -> tuple[list[dict], list[dict]]:
    by_id = {b.id: b for b in blocks}
    claims, rejected, seen = [], [], set()
    for claim in proposal.claims:
        try:
            if claim.id in seen:
                raise ValueError("Duplicate claim ID")
            seen.add(claim.id)
            refs = [bind_quote(r, by_id) for r in claim.references]
            if not numbers_supported(claim.text, [r["quote"] for r in refs]):
                # Attach real same-source season headings, never a filename or
                # an unrelated number. Verifier still checks applicability.
                missing_years = {int(y) for y in YEAR.findall(claim.text)}
                source = by_id[refs[0]["block_id"]]
                same_revision = [b for b in blocks if
                    (b.binding_id, b.index_revision_id, b.source_revision_id) ==
                    (source.binding_id, source.index_revision_id, source.source_revision_id)]
                for header in scope_headers(same_revision, [source], list(missing_years)):
                    if len(refs) < 4:
                        refs.append(bind_quote(QuoteReference(block_id=header.id, quote=header.text), by_id))
            if not numbers_supported(claim.text, [r["quote"] for r in refs]):
                raise ValueError("Numbers are not bound to their own quote")
            # A reviewed row is atomic evidence. Expand only an already valid
            # substring of that exact row, retaining its authoritative identity.
            for ref in refs:
                if ref["origin"] == "reviewed_fact":
                    ref["quote"] = by_id[ref["block_id"]].text
            if not same_source(refs):
                raise ValueError("One claim cannot borrow scope from another source")
            if not numbers_supported(claim.text, [r["quote"] for r in refs]):
                raise ValueError("Numbers are not bound to their own quote")
            if not row_entities_supported(claim.text, refs):
                raise ValueError("Reviewed row quote and claim must preserve its exact entity name, not a broader group")
            claims.append({"id": claim.id, "text": claim.text, "references": refs})
        except ValueError as exc:
            logger.info("evidence_claim_rejected claim=%s reason=%s", claim.id, exc)
            rejected.append({"claim_id": claim.id, "reason": str(exc)})
    return claims, rejected


async def propose_bound_claims(db: AsyncSession, req: AskRequest, payload: dict,
                               blocks: list[EvidenceBlock]) -> tuple[AnswerProposal, list[dict], list[dict], bool]:
    proposal = await structured_call(db, req, AnswerProposal, PROPOSE_INSTRUCTION, payload, max_tokens=4000)
    claims, rejected = bind_claims(proposal, blocks)
    repaired = False
    requested = payload.get("requested", {})
    coverage_missing = uncovered_list_members(blocks, claims,
        requested.get("enumeration_subject") or requested.get("entity")) if requested.get("coverage") == "enumeration" else []
    if proposal.claims and (rejected or coverage_missing):
        repaired = True
        proposal = await structured_call(db, req, AnswerProposal, PROPOSE_INSTRUCTION +
            "\nThe previous proposal failed deterministic source binding. Repair ONCE using exact "
            "quotes from the supplied block.text and same-source scope. Do not add facts or infer "
            "expected answers from validation errors. If unsupported, return missing/partial.",
            {**payload, "previous_proposal": proposal.model_dump(), "binding_errors": rejected,
             "uncovered_list_block_ids": coverage_missing}, max_tokens=4000)
        claims, rejected = bind_claims(proposal, blocks)
    return proposal, claims, rejected, repaired
