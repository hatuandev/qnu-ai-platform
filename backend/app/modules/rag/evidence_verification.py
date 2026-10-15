"""Bounded semantic auditing shared by direct RAG and workflow answers."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.rag.evidence_audit import SemanticAudit, audit_coverage
from app.modules.rag.evidence_bm25 import tokens
from app.modules.rag.evidence_constraints import location_pointer_gap
from app.modules.rag.evidence_hierarchy import scope_error
from app.modules.rag.evidence_indexed_audit import (
    INDEXED_AUDIT_INSTRUCTION,
    audit_contract,
    audit_payload,
    resolve_audit,
)
from app.modules.rag.evidence_lists import uncovered_list_members
from app.modules.rag.evidence_model import VERIFY_INSTRUCTION, structured_call
from app.modules.rag.evidence_precedence import apply_precedence, validate_superseding_quotes
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan, VerificationResult
from app.modules.rag.evidence_validation import (
    formula_legend_gap,
    group_single_row_gap,
    temporal_references_supported,
)
from app.modules.rag.schemas import AskRequest


@dataclass
class VerifiedAnswer:
    claims: list[dict]
    complete: bool
    missing: list[str]
    errors: list[dict]
    verifier: VerificationResult
    audit: SemanticAudit | None
    uncovered: list[str]


def row_scope_entity(plan: QueryPlan, claims: list[dict]) -> str | None:
    """Resolve a whole row name inside a decorated individual attribute request.

    Do not normalize group/list-of-entities requests or merely partial name matches.
    Entailment/relevance/scope still require independent verification above this gate.
    """
    entity = plan.entity or ""
    subject = plan.enumeration_subject or ""
    words = lambda text: [term for term in tokens(text) if ' ' not in term]
    if plan.coverage == 'comparison' or not subject or set(words(subject)).intersection(words(entity)):
        return plan.entity
    names = {ref.get('entity_name') for claim in claims for ref in claim.get('references', [])
             if ref.get('origin') == 'reviewed_fact' and ref.get('entity_name')}
    if len(names) != 1:
        return plan.entity
    name = next(iter(names))
    requested, row = words(entity), words(name)
    return name if len(row) >= 2 and len(requested) - len(row) in (0, 1) and requested[-len(row):] == row else plan.entity


async def verify_bound_answer(db: AsyncSession, req: AskRequest, payload: dict,
                              claims: list[dict], blocks: list[EvidenceBlock], plan: QueryPlan,
                              rules: list) -> VerifiedAnswer:
    scope_errors = [{"claim_id": c["id"], "reason": reason} for c in claims
                    if (reason := scope_error(c, blocks, plan))]
    rejected_ids = {error["claim_id"] for error in scope_errors}
    claims = [claim for claim in claims if claim["id"] not in rejected_ids]
    if not claims:
        return VerifiedAnswer([], False, plan.requested_topics or [plan.attribute or req.question],
                              scope_errors, VerificationResult(complete=False), None, [])
    verifier = await structured_call(db, req, VerificationResult, VERIFY_INSTRUCTION,
                                    {**payload, "claims": claims}, max_tokens=2400)
    verdicts = {v.claim_id: v for v in verifier.verdicts}
    if len(verdicts) != len(verifier.verdicts) or set(verdicts) != {c["id"] for c in claims}:
        raise AppException("Kiểm chứng mệnh đề không đầy đủ.", code="EVIDENCE_VERIFICATION_INVALID", status_code=502)
    # A model may mistake a preferred source for a blanket replacement. Give it
    # one bounded repair when its supersession quote is not valid same-tuple proof;
    # unique information from another official source must remain eligible.
    by_block = {b.id: b for b in blocks}
    invalid_supersession = []
    for claim in claims:
        verdict = verdicts[claim["id"]]
        if not verdict.superseded_by:
            continue
        source_id = claim["references"][0]["source_revision_id"]
        try:
            valid = validate_superseding_quotes(source_id, verdict.superseded_by, rules, by_block)
        except ValueError:
            valid = False
        if not valid:
            invalid_supersession.append(claim["id"])
    if invalid_supersession:
        verifier = await structured_call(db, req, VerificationResult, VERIFY_INSTRUCTION +
            "\nThe previous audit proposed invalid superseded_by references for claim IDs "
            + ", ".join(invalid_supersession) + ". Re-evaluate those claims from their own attached quotes. "
            "Leave superseded_by empty unless one exact preferred-source quote proves the same applicability tuple.",
            {**payload, "claims": claims, "invalid_supersession_claims": invalid_supersession}, max_tokens=2400)
        verdicts = {v.claim_id: v for v in verifier.verdicts}
        if len(verdicts) != len(verifier.verdicts) or set(verdicts) != {c["id"] for c in claims}:
            raise AppException("Kiểm chứng mệnh đề sau sửa chữa không đầy đủ.", code="EVIDENCE_VERIFICATION_INVALID", status_code=502)
    errors = [*scope_errors, *apply_precedence(verifier, claims, rules, {b.id: b for b in blocks})]
    accepted = [{**c, "verified": True} for c in claims if all((verdicts[c["id"]].entailed,
        verdicts[c["id"]].relevant, verdicts[c["id"]].scope_compatible)) and temporal_references_supported(c, plan.years)]
    errors.extend({"claim_id": c["id"], "reason": verdicts[c["id"]].reason} for c in claims
                  if c["id"] not in {a["id"] for a in accepted})
    audit = None
    complete = False
    missing = verifier.missing_constraints
    if accepted and not verifier.conflict:
        indexed_payload, catalog = audit_payload({**payload, "claims": accepted}, blocks)
        indexed = await structured_call(db, req, audit_contract(accepted, catalog), INDEXED_AUDIT_INSTRUCTION,
                                        indexed_payload, max_tokens=2400)
        audit = resolve_audit(indexed, accepted, catalog)
        accepted, audit_errors, missing, complete = audit_coverage(audit, accepted, blocks,
            sorted(set(plan.years + plan.document_years + plan.event_years)), question=req.question)
        errors += audit_errors
        row_gap = group_single_row_gap(accepted, row_scope_entity(plan, accepted))
        if row_gap:
            missing = [*missing, "chỉ mới có bằng chứng cho " + ", ".join(row_gap)
                       + "; chưa đủ căn cứ cho phạm vi " + (plan.entity or "được hỏi")]
            complete = False
        if location_pointer_gap(accepted, plan.intent, plan.attribute):
            missing = [*missing, "chưa có đường dẫn hoặc địa chỉ cụ thể được trích dẫn"]
            complete = False
        if formula_legend_gap(accepted, blocks, plan.intent, plan.attribute):
            missing = [*missing, "thiếu chú giải biến và điều kiện áp dụng của công thức"]
            complete = False
        # Final coverage is judged from retained claims, not rejected unrelated extras.
        complete = complete and not verifier.conflict
        uncovered_topics = [topic for topic in plan.requested_topics
                            if verifier.topic_coverage.get(topic) is not True]
        if uncovered_topics:
            missing = list(dict.fromkeys([*missing, *uncovered_topics]))
            complete = False
    uncovered = uncovered_list_members(blocks, accepted, plan.enumeration_subject or plan.entity) if plan.coverage == "enumeration" else []
    if uncovered:
        accepted, complete = [], False
    return VerifiedAnswer(accepted, complete, missing, errors, verifier, audit, uncovered)
