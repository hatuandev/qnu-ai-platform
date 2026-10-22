"""Bind proposals to their own source spans, with one bounded quote repair."""

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.evidence_blocks import scope_headers
from app.modules.rag.evidence_lists import uncovered_list_members
from app.modules.rag.evidence_model import PROPOSE_INSTRUCTION, structured_call
from app.modules.rag.evidence_passages import (
    compact_passage_payload,
    passage_catalog,
    passage_payload,
    proposal_contract,
    resolve_proposal,
    source_grounded_claims,
)
from app.modules.rag.evidence_schemas import AnswerProposal, EvidenceBlock, QuoteReference
from app.modules.rag.evidence_validation import (
    YEAR,
    bind_quote,
    numbers_supported,
    row_entities_supported,
    same_source,
)
from app.modules.rag.schemas import AskRequest
from app.modules.rag.source_claim_context import supporting_scope_blocks

logger = logging.getLogger(__name__)


def restore_condition_claims(conditions: dict[str, str], blocks: list[EvidenceBlock],
                             qualifiers: list[QuoteReference] | None = None) -> list[dict]:
    """Copy missing server-owned clauses; they still require independent verification."""
    catalog, by_id = passage_catalog(blocks), {b.id: b for b in blocks}
    restored = []
    for index, (key, quote) in enumerate(conditions.items()):
        if not re.fullmatch(r'e\d+\.c\d+', key) or key.split('.c')[0] not in catalog:
            raise ValueError('Unknown source condition passage')
        body = catalog[key.split('.c')[0]]
        reference = bind_quote(QuoteReference(block_id=body.block_id, quote=quote), by_id)
        restored.append({'id': f'__source_condition_{index}', 'text': quote, 'references': [reference]})
    for index, qualifier in enumerate(qualifiers or []):
        reference = bind_quote(qualifier, by_id)
        restored.append({'id': f'__source_qualifier_{index}', 'text': reference['quote'], 'references': [reference]})
    return source_grounded_claims(restored, blocks, primary_only=True)


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
    catalog = passage_catalog(blocks)
    contract = proposal_contract(catalog)
    instruction = PROPOSE_INSTRUCTION + (
        "\nSelect evidence_ids from passages. Do NOT generate quotes or source/block IDs. "
        "Each ID is a server-owned exact passage. Select all SAME-SOURCE passages needed "
        "to prove the claim, its numbers and conditions. "
        "The public answer will use selected source sentences verbatim, not your paraphrase. "
        "Select complete relevant sentences including mandatory conditions and distinctions; "
        "avoid redundant whole-block IDs when shorter sentences cover the question. "
        "Your text field is only a relevance label and is not published. "
        "An explicit source denial, undefined symbol or rule saying an operation cannot be performed "
        "IS a supported answer, not missing evidence. Select that exact source rule and its restrictions; "
        "do not invent a number or perform arithmetic when required inputs are absent. "
        "For questions about a document's own status, its same-source introduction establishes which "
        "document is speaking; the status sentence need not repeat the full institution name. "
        "A declarative source disclaimer can be styled as a heading. For source_content questions "
        "select that exact declaration as primary evidence when it directly answers the question; "
        "do not treat a bare title/date as proof of a value or applicability. Supporting headings stay context. "
        "Conditions outside the user's "
        "question are optional ONLY when they cannot change applicability. Before selecting a permission, "
        "retain its prerequisites, exceptions and negated scopes from the SAME rule, including "
        "sentences before and after the permission. Do not split a numbered conditional rule "
        "into an unconditional allowance. Select the whole relevant rule when its clauses jointly "
        "define eligibility. Counts of different "
        "rounds are not additive. Do not infer conflicts across different years."
    )
    compact = payload.get("compact_passages", False)
    payload = {key: value for key, value in payload.items() if key not in {"evidence", "compact_passages"}}
    if compact:
        # Same catalog/IDs/quotes, metadata once per block rather than once per
        # sentence. No evidence loss and no guessed character-to-token ratio.
        payload["passages"] = compact_passage_payload(blocks, catalog)
        instruction += "\nWithin each group, whole_passage_id selects whole_text if present, otherwise ALL its passage texts in source order."
        instruction += (" evidence_ids selects ONLY sentences that directly answer the question and will be public. "
            "Put supporting season/subject headings in context_ids instead: those are proof only, NOT displayed. "
            "Essential conditions must remain in public evidence_ids, not merely in context_ids. "
            "Do not select fees/dates/other rounds unless asked or essential to the answer. "
            "Choose a complete sentence, not a lowercase continuation without its preceding sentence. "
            "The total number of selected public sentences across all claims must not exceed twelve.")
    else:
        payload["passages"] = passage_payload(blocks, catalog)
    draft = await structured_call(db, req, contract, instruction, payload, max_tokens=4000)
    proposal = resolve_proposal(draft, catalog, blocks, separate_context=compact)
    claims, rejected = bind_claims(proposal, blocks)
    repaired = False
    requested = payload.get("requested", {})
    coverage_missing = uncovered_list_members(blocks, claims,
        requested.get("enumeration_subject") or requested.get("entity")) if requested.get("coverage") == "enumeration" else []
    if proposal.claims and (rejected or coverage_missing):
        repaired = True
        draft = await structured_call(db, req, contract, instruction +
            "\nThe previous proposal failed deterministic source binding. Repair ONCE using exact "
            "passage IDs and same-source scope. Do not add facts or infer "
            "expected answers from validation errors. If unsupported, return missing/partial.",
            {**payload, "previous_proposal": draft.model_dump(), "binding_errors": rejected,
             "uncovered_list_block_ids": coverage_missing}, max_tokens=4000)
        proposal = resolve_proposal(draft, catalog, blocks, separate_context=compact)
        claims, rejected = bind_claims(proposal, blocks)
    projected = source_grounded_claims(claims, blocks, primary_only=compact,
        allow_primary_heading=requested.get('question_scope') == 'source_content')
    by_block = {block.id: block for block in blocks}
    for claim in projected:
        body = by_block[claim["references"][0]["block_id"]]
        same_revision = [block for block in blocks if
            (block.binding_id, block.index_revision_id, block.source_revision_id, block.canonical_hash) ==
            (body.binding_id, body.index_revision_id, body.source_revision_id, body.canonical_hash)]
        heading = by_block.get(body.record_heading_id or "")
        if heading and heading in same_revision:
            reference = bind_quote(QuoteReference(block_id=heading.id, quote=heading.text), by_block)
            if not any(ref["block_id"] == heading.id for ref in claim["references"]):
                claim["references"].append(reference)
        for context in supporting_scope_blocks(body, same_revision, req.original_question or req.question):
            if len(claim['references']) >= 4:
                break
            if not any(ref['block_id'] == context.id for ref in claim['references']):
                claim['references'].append(bind_quote(QuoteReference(block_id=context.id, quote=context.text), by_block))
        for header in scope_headers(same_revision, [body], requested.get("years") or []):
            reference = bind_quote(QuoteReference(block_id=header.id, quote=header.text), by_block)
            if not any(ref["block_id"] == reference["block_id"] and ref["quote"] == reference["quote"] for ref in claim["references"]):
                claim["references"].append(reference)
    return proposal, projected, rejected, repaired
