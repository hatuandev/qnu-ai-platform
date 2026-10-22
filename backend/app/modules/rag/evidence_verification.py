"""Bounded semantic auditing shared by direct RAG and workflow answers."""

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.rag.evidence_audit import SemanticAudit, audit_coverage
from app.modules.rag.evidence_bm25 import tokens
from app.modules.rag.evidence_constraints import location_pointer_gap
from app.modules.rag.evidence_context import compact_claim_context
from app.modules.rag.evidence_contracts import verification_contract
from app.modules.rag.evidence_hierarchy import scope_error
from app.modules.rag.evidence_indexed_audit import (
    INDEXED_AUDIT_INSTRUCTION,
    audit_contract,
    audit_payload,
    literal_condition_claims,
    resolve_audit,
)
from app.modules.rag.evidence_lists import uncovered_list_members
from app.modules.rag.evidence_model import VERIFY_INSTRUCTION, structured_call
from app.modules.rag.evidence_obligations import missing_conditions, remember_conditions
from app.modules.rag.evidence_precedence import apply_precedence, validate_superseding_quotes
from app.modules.rag.evidence_schemas import (
    EvidenceBlock,
    QueryPlan,
    QuoteReference,
    VerificationResult,
)
from app.modules.rag.evidence_validation import (
    formula_legend_gap,
    group_single_row_gap,
    temporal_references_supported,
)
from app.modules.rag.schemas import AskRequest
from app.modules.rag.source_dependency_agreement import reconcile_dependencies
from app.modules.rag.source_dependency_review import review_dependencies


@dataclass
class VerifiedAnswer:
    claims: list[dict]
    complete: bool
    missing: list[str]
    errors: list[dict]
    verifier: VerificationResult
    audit: SemanticAudit | None
    uncovered: list[str]
    source_condition_gaps: dict[str, str] = field(default_factory=dict)
    source_qualifier_gaps: list[QuoteReference] = field(default_factory=list)


def blocking_repair_errors(verified: VerifiedAnswer) -> bool:
    retained = {claim['id'] for claim in verified.claims}
    return any(not error.get('claim_id') or error['claim_id'] in retained for error in verified.errors)


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


async def complete_source_conditions(db: AsyncSession, req: AskRequest, payload: dict,
                                     verified: VerifiedAnswer | None, blocks: list[EvidenceBlock],
                                     plan: QueryPlan, rules: list) -> VerifiedAnswer | None:
    """Copy missing, audited source clauses and reverify within two request-wide rounds."""
    from app.modules.rag.evidence_claims import restore_condition_claims

    trace = req._retrieval_diagnostics.setdefault('source_condition_completion', [])
    while verified and not verified.complete and len(trace) < 2:
        gaps = getattr(verified, 'source_condition_gaps', {})
        qualifiers = getattr(verified, 'source_qualifier_gaps', [])
        if (not (gaps or qualifiers) or not verified.claims or blocking_repair_errors(verified) or verified.verifier.conflict
                or any(verified.verifier.topic_coverage.get(t) is not True for t in plan.requested_topics)):
            break
        signature = {'clause_ids': sorted(gaps), 'qualifier_blocks': sorted(q.block_id for q in qualifiers)}
        if signature in trace:
            break
        try:
            restored = restore_condition_claims(gaps, blocks, qualifiers)
        except ValueError as exc:
            raise AppException('Không đối chiếu được điều kiện nguồn cần phục hồi.',
                code='SOURCE_CONDITION_REPAIR_INVALID', status_code=503) from exc
        public = {(ref['block_id'], ref['quote']) for c in verified.claims for ref in c['references']
                  if ref['quote'] in c['text']}
        restored = [c for c in restored if (c['references'][0]['block_id'],c['text']) not in public]
        if not restored or len(verified.claims) + len(restored) > 48:
            break
        used = {c['id'] for c in verified.claims}
        for c in restored:
            while c['id'] in used:
                c['id'] = '_' + c['id']
            used.add(c['id'])
        trace.append(signature)
        verified = await verify_bound_answer(db, req, payload, [*verified.claims,*restored], blocks, plan, rules)
    return verified


async def verify_bound_answer(db: AsyncSession, req: AskRequest, payload: dict,
                              claims: list[dict], blocks: list[EvidenceBlock], plan: QueryPlan,
                              rules: list) -> VerifiedAnswer:
    # Selection feedback is historical, not evidence for an independent verdict.
    payload = {key: value for key, value in payload.items() if key not in {
        'coverage_repair', 'previous_proposal', 'coverage_feedback', 'repair_instruction'}}
    scope_errors = [{"claim_id": c["id"], "reason": reason} for c in claims
                    if (reason := scope_error(c, blocks, plan))]
    rejected_ids = {error["claim_id"] for error in scope_errors}
    claims = [claim for claim in claims if claim["id"] not in rejected_ids]
    if not claims:
        return VerifiedAnswer([], False, plan.requested_topics or [plan.attribute or req.question],
                              scope_errors, VerificationResult(complete=False), None, [])
    contract = verification_contract(claims, plan.requested_topics)
    verification_payload = (compact_claim_context(payload, claims) if payload.get("compact_passages")
                            else {**payload, "claims": claims})
    verifier = await structured_call(db, req, contract, VERIFY_INSTRUCTION +
                                    "\nJudge only the original question and requested_topics. Do not require adjacent rows, "
                                    "ranges, comparisons or definitions not asked or essential to that answer. "
                                    "An explicit rule that missing input prevents calculation fully answers the scenario; "
                                    "do not require the source to repeat user-provided hypothetical input values. "
                                    "Resolve every reference_catalog ID. Additional same-source quotes may prove a condition "
                                    "but must not replace a primary body about another condition or subject.",
                                    verification_payload, max_tokens=2400,
                                    error_code="EVIDENCE_VERIFICATION_INVALID")
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
        verifier = await structured_call(db, req, contract, VERIFY_INSTRUCTION +
            "\nThe previous audit proposed invalid superseded_by references for claim IDs "
            + ", ".join(invalid_supersession) + ". Re-evaluate those claims from their own attached quotes. "
            "Leave superseded_by empty unless one exact preferred-source quote proves the same applicability tuple.",
            {**verification_payload, "invalid_supersession_claims": invalid_supersession}, max_tokens=2400,
            error_code="EVIDENCE_VERIFICATION_INVALID")
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
        clauses = indexed_payload.get('source_conditions', {})
        indexed = await structured_call(db, req, audit_contract(accepted, catalog, clauses), INDEXED_AUDIT_INSTRUCTION,
                                        indexed_payload, max_tokens=2400,
                                        error_code="EVIDENCE_VERIFICATION_INVALID")
        audit = resolve_audit(indexed, accepted, catalog, clauses, blocks)
        remember_conditions(req, plan, indexed, audit, clauses, catalog, blocks)
        req._retrieval_diagnostics.setdefault('source_audit_checks', []).append({
            'claim_ids': [claim['id'] for claim in accepted],
            'complete': audit.complete,
            'condition_checks': [{'clause_id': check.clause_id, 'required': check.required,
                'retained_by': check.retained_by,
                'block_id': catalog[check.clause_id.split('.c')[0]].block_id}
                for check in getattr(indexed, 'source_conditions', [])],
            'missing_condition_ids': list(audit.source_condition_gaps)})
        accepted, audit_errors, missing, complete = audit_coverage(audit, accepted, blocks,
            sorted(set(plan.years + plan.document_years + plan.event_years)), question=req.question)
        if audit.complete and accepted:
            owners = literal_condition_claims(clauses, catalog, accepted, blocks)
            pending = {key: text for key, text in clauses.items() if not owners.get(key)}
            dependencies = await review_dependencies(db, req, plan, accepted, blocks, pending, catalog, structured_call)
            if dependencies is not None:
                dependencies = await reconcile_dependencies(db, req, plan, accepted, blocks, clauses,
                    catalog, indexed, dependencies, structured_call)
                remember_conditions(req, plan, dependencies, audit, clauses, catalog, blocks)
        if not audit.complete:
            complete = False
            missing = list(dict.fromkeys([*missing, 'Kiểm chứng toàn bộ câu trả lời chưa đầy đủ.']))
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
    known_ids = {claim['id'] for claim in accepted}
    qualifier_gaps = [q.reference for q in audit.required_qualifiers
        if q.requirement in missing and set(q.retained_by).issubset(known_ids)] if audit else []
    obligations, unavailable = missing_conditions(req, plan, accepted, blocks)
    if obligations or unavailable:
        complete = False
        missing = list(dict.fromkeys([*missing, 'Chưa giữ đủ điều kiện nguồn đã xác minh cho câu hỏi này.']))
        qualifier_gaps = list({(ref.block_id, ref.quote): ref for ref in [*qualifier_gaps, *obligations]}.values())
    if unavailable:
        errors.append({'reason': 'SOURCE_CONDITION_CONTEXT_MISSING', 'block_ids': unavailable})
    return VerifiedAnswer(accepted, complete, missing, errors, verifier, audit, uncovered,
                          audit.source_condition_gaps if audit else {}, qualifier_gaps)
