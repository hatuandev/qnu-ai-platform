"""One bounded, source-bound prose check after an inconclusive structured route."""

import asyncio
import re
import time
from typing import Literal

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.evidence_policy import EvidencePolicy
from app.core.exceptions import AppException
from app.core.retrieval_policy import configured_policy
from app.modules.rag.evidence_blocks import (
    load_published_blocks,
    pack_context,
    rank_blocks,
    section_neighbors,
)
from app.modules.rag.evidence_claims import propose_bound_claims, restore_condition_claims
from app.modules.rag.evidence_context import model_context
from app.modules.rag.evidence_model import structured_call
from app.modules.rag.evidence_pipeline import decision_response
from app.modules.rag.evidence_precedence import active_preferences
from app.modules.rag.evidence_recovery import retain_recovered_conditions
from app.modules.rag.evidence_repair import retain_safe_claims
from app.modules.rag.evidence_retrieval import bounded_rerank
from app.modules.rag.evidence_schemas import QueryPlan, StrictContract
from app.modules.rag.evidence_validation import request_years
from app.modules.rag.evidence_verification import blocking_repair_errors, verify_bound_answer
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.prose_selection import (
    answer_facets,
    distinct_candidates,
    merge_candidates,
    recovery_order,
    topic_order,
)
from app.modules.rag.schemas import AskRequest, AskResponse, RetrievalSnapshot
from app.modules.rag.source_candidates import linked_candidates, reference_priority
from app.modules.rag.source_labels import supplemental_context
from app.modules.rag.source_locators import addressed_prose, referenced_sections
from app.modules.rag.temporal_answer import is_temporal_table_question


class RecoveryIntent(StrictContract):
    topic: str = Field(min_length=1, max_length=160)
    coverage: Literal["focused", "enumeration", "comparison"]
    required_topics: list[str] = Field(min_length=1, max_length=4)
    entity: str | None
    intent: str = Field(min_length=1, max_length=160)
    event: str | None
    round: str | None
    scalar_update_lookup: bool = Field(description="True only for a current scalar quantity whose updates must be compared; false for dates, procedures, eligibility and existence questions.")


class RecoveryPlan(QueryPlan):
    scalar_update_lookup: bool = False


async def recovery_plan(db, req, question, years):
    intent = await structured_call(db, req, RecoveryIntent,
        "Identify ONLY the original question's requested metric/topic and necessary answer facets. "
        "Do not answer or add expected values, advice or extra questions. topic is a short searchable "
        "Vietnamese label excluding repeated institution/year boilerplate. coverage=enumeration for "
        "which/all/list questions, comparison for compared entities/years, focused otherwise. "
        "required_topics must preserve each explicit compared year, entity, method and event; "
        "a list request requires the list, not just one member. Never broaden scope or negate it. "
        "required_topics are requested answer facets, not separate demands to repeat each entity name. "
        "A conditional calculation with a missing input asks whether a result is determined; "
        "user-supplied input values are constraints, not separate facts for the source to restate. "
        "An explicit source restriction or undefined value can fully answer a request negatively. "
        "entity preserves the target class or individual; intent preserves the decision asked. "
        "Keep event and round separate when stated; otherwise null, never invented. "
        "A yes/no existence question asks for the supported answer and essential restrictions, "
        "not every date/fee/formula nearby. Do not turn 'is there a formula' into a request to calculate.",
        {"question": question}, max_tokens=500)
    return RecoveryPlan(query=question, years=years, historical_reference_allowed=False,
        attribute=intent.topic, coverage=intent.coverage, requested_topics=answer_facets(intent.required_topics, question),
        enumeration_subject=intent.topic if intent.coverage == "enumeration" else None,
        entity=intent.entity, intent=intent.intent, event=intent.event, round=intent.round,
        scalar_update_lookup=intent.scalar_update_lookup)


def can_check_prose(decision: dict | None) -> bool:
    """Never override a supported/partial answer, conflict or ambiguous scope."""
    return bool(decision and decision.get("status") == "missing"
        and not decision.get("claim_bindings") and not decision.get("cells")
        and (decision.get("reason") in {
            "NO_COMPATIBLE_FACT_EVIDENCE", "DATA_YEAR_UNVERIFIED",
            "ROW_METRIC_SCOPE_UNRESOLVED", "ROW_SELECTION_MISSING", "ROW_AUDIT_REJECTED",
            "ROW_RULE_REQUIRES_CONTEXT",
        } or (decision.get('reason') == 'METRIC_UNVERIFIED'
              and not (decision.get('requested') or {}).get('years'))))


async def recover_empty_source_read(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot,
                                    policy: EvidencePolicy, response: AskResponse, *,
                                    started: float, candidate_mode: bool) -> AskResponse:
    """Reuse the existing independent canonical check after an empty wiki proposal.

    Never override explicit evidence policy, a partial answer, conflict, binding
    rejection or provider failure. The original request's deadline remains hard.
    """
    decision = response.answer_decision or {}
    if (policy.enabled or not snapshot.knowledge_wiki_enabled or decision.get('status') != 'missing'
            or decision.get('reason') != 'INVALID_OR_EMPTY_CLAIMS'
            or (decision.get('requested') or {}).get('question_scope') != 'source_content'
            or decision.get('claim_bindings') or decision.get('binding_rejections')):
        return response
    remaining = policy.timeout_seconds - (time.perf_counter() - started)
    if remaining <= 0:
        return response
    try:
        async with asyncio.timeout(remaining):
            verified = await answer_from_prose(db, req, snapshot, policy, 'EMPTY_SOURCE_READ', candidate_mode=candidate_mode)
    except TimeoutError as exc:
        raise AppException('Đối soát nguồn vượt ngân sách thời gian còn lại.', code='EVIDENCE_TIMEOUT', status_code=504) from exc
    return verified or response


async def answer_from_prose(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot,
                            policy: EvidencePolicy, reason: str, *, candidate_mode: bool = False) -> AskResponse | None:
    if req.collection_id != snapshot.collection_id:
        raise AppException("Phạm vi chứng cứ không khớp kho tri thức.", code="PROSE_SCOPE_MISMATCH", status_code=403)
    trace = {"trigger": reason, "verified": False}
    req._retrieval_diagnostics["prose_fallback"] = trace
    started = time.perf_counter()
    try:
        async with asyncio.timeout(policy.timeout_seconds):
            response = await _answer(db, req, snapshot, policy, trace, started, candidate_mode)
    except TimeoutError as exc:
        raise AppException("Đối soát đoạn văn vượt thời gian xử lý.", code="PROSE_EVIDENCE_TIMEOUT", status_code=504) from exc
    trace["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return response


async def _answer(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot,
                  policy: EvidencePolicy, trace: dict, started: float,
                  candidate_mode: bool) -> AskResponse | None:
    question = req.original_question or req.question
    years = sorted(request_years(question))
    blocks = await load_published_blocks(db, snapshot, candidate_mode=candidate_mode)
    # A table row rejected for metric/year must not be laundered through synthesis.
    prose = [block for block in blocks if not block.is_container and block.origin == "canonical"
             and block.fact_context.get("source_kind") not in {"heading", "image", "table"}
             and not re.search(r"(?m)^\s*\||<table\b", block.text, re.IGNORECASE)]
    if not prose:
        trace["reason"] = "NO_PROSE_CANDIDATES"
        return None
    plan = await recovery_plan(db, req, question, years)
    supplemental = supplemental_context(blocks, question,
        allow_tables=(trace['trigger'] == 'ROW_RULE_REQUIRES_CONTEXT'
        or not is_temporal_table_question(question, req.module_code))
        and trace['trigger'] not in {'ROW_AUDIT_REJECTED', 'ROW_AUDIT_SCOPE_MISSING'},
        allow_descriptive_unresolved=trace['trigger'] == 'ROW_RULE_REQUIRES_CONTEXT')
    candidates_pool = list({b.id: b for b in [*prose, *supplemental]}.values())
    retrieval = configured_policy(req.runtime_policy)
    # Honor configured context policy, not a hidden 6000-character/3-body cap.
    # Whole evidence groups still must fit; provider checks its actual window.
    limit = retrieval.context_top_k if retrieval else policy.context_limit
    budget = retrieval.max_context_chars if retrieval else policy.max_context_chars
    ranked = rank_blocks(candidates_pool, [plan.attribute or question, *plan.requested_topics,
        *[b.text for b in supplemental]], policy.candidate_limit, years)
    prose_ids = {block.id for block in candidates_pool}
    section_hits = [block for block in section_neighbors(blocks, plan.attribute or question, years, policy.candidate_limit)
                    if block.id in prose_ids]
    allowed_section_ids = {b.id for b in rank_blocks(section_hits,
        [plan.attribute or question, *plan.requested_topics], len(section_hits), years)}
    section_hits = [b for b in section_hits if b.id in allowed_section_ids]
    # Reserve both retrieval channels within the same candidate ceiling. Heading
    # children retain their original IDs and body spans; headings are not facts.
    ranked = merge_candidates(section_hits, ranked, policy.candidate_limit)
    topics = list(dict.fromkeys([plan.attribute or question, *plan.requested_topics, plan.entity or ""]))
    ranked = distinct_candidates(topic_order(ranked, topics))
    linked = linked_candidates(candidates_pool, ranked, years, max_links=1)
    # Reserve the direct lexical hit and its reference-linked counterpart BEFORE
    # reranking. A semantically similar boilerplate must not crowd an update out.
    priority = (reference_priority(linked) if getattr(plan, "scalar_update_lookup", False)
        and plan.coverage == "focused" and not (plan.event or plan.round) else [])
    priority = list({b.id: b for b in [*priority, *referenced_sections(blocks, question)]}.values())
    ranked = linked
    if ranked and (req.reranker_policy or {}).get("enabled", True):
        # School/year boilerplate can dominate lexical matches. Resolve semantic
        # relevance with the configured reranker, never by a filename/year boost.
        candidates = [FusionCandidate(block.id, block.binding_id, f"{block.section}\n{block.text}", 1 / (60 + i),
            binding_id=block.binding_id, index_revision_id=block.index_revision_id)
            for i, block in enumerate(ranked, 1)]
        rerank_query = "\n".join(dict.fromkeys([plan.attribute or question, question]))
        reranked = await bounded_rerank(rerank_query, candidates, len(ranked), req, policy)
        if plan.coverage == "focused" and reranked and all(hit.relevance_score is not None for hit in reranked):
            # Hybrid RRF has already established recall. For this bounded prose
            # shortlist, a second RRF must not overrule the actual cross-encoder
            # on event/intent relevance. No score is fabricated when unavailable.
            reranked = sorted(reranked, key=lambda hit: hit.relevance_score, reverse=True)
        trace["rerank_candidates"] = [{"id": hit.chunk_id, "score": hit.relevance_score} for hit in reranked]
        by_id = {block.id: block for block in ranked}
        if reranked:
            ranked = [by_id[hit.chunk_id] for hit in reranked]
        else:
            # CE relevance is a retrieval signal, not a verdict that the source
            # has no answer. Keep bounded lexical candidates for binding and
            # independent verification; do not invent a score or accept a fact.
            trace["rerank_empty"] = True
    # For a focused question the cross-encoder has seen the ORIGINAL decision,
    # event and subject. Do not undo that ranking with generic topic word counts
    # (an unrelated round can contain every word of a short topic label).
    ranked = recovery_order(topic_order(ranked, topics) if plan.coverage == 'enumeration' else ranked,
                            supplemental, priority, question=question)
    if trace['trigger'] == 'ROW_RULE_REQUIRES_CONTEXT':
        # The exact row can contain a restriction absent from prose; the prose
        # can contain prerequisites absent from that row. Retain both proofs.
        anchors = [b for b in supplemental if b.fact_context.get('source_kind') == 'table']
        ranked = list({b.id: b for b in [*anchors, *ranked]}.values())
        priority = list({b.id: b for b in [*anchors, *priority]}.values())
    addressed = addressed_prose(ranked, question)
    ranked = list({b.id: b for b in [*addressed, *ranked]}.values())
    priority = list({b.id: b for b in [*addressed, *priority]}.values())
    packing = {}
    selected = pack_context(blocks, ranked, years, limit, budget, atomic_lists=True,
        enumeration_subject=plan.enumeration_subject if plan.coverage == 'enumeration' else None, diagnostics=packing,
        coverage_goals=[], priority_ids={b.id for b in priority}, allow_first_whole_group=True)
    trace.update(candidate_count=len(ranked), section_candidates=len(section_hits), context_count=len(selected), lexical_engine="evidence_bm25",
                 max_context_chars=budget, context_limit=limit, max_output_tokens=req.max_tokens)
    trace.update(coverage=plan.coverage, context_ids=[b.id for b in selected], packing=packing)
    trace["requested_scope"] = {"entity": plan.entity, "intent": plan.intent,
        "event": plan.event, "round": plan.round}
    if not selected:
        trace["reason"] = "NO_PROSE_CANDIDATES"
        return None
    trace['table_recovery'] = any(b.fact_context.get('source_kind') == 'table' for b in selected)
    # No history facts, no model-authored numerical values. Existing passage IDs,
    # span binding, year checks and independent semantic audit remain authoritative.
    rules = active_preferences(policy, plan, selected)
    payload = _prose_payload(question, plan, selected, rules)
    bounded = req.model_copy()
    trace["stage"] = "proposal"
    try:
        proposal, claims, rejected, repaired = await propose_bound_claims(db, bounded, payload, selected)
    except AppException as exc:
        if exc.code != "MODEL_CONTEXT_EXCEEDED":
            raise
        # ONE source-aware repack after an explicit provider window rejection.
        # No guessed token ratio, new model, partial list or extra semantic retry.
        fit_packing = {}
        selected_ids = {b.id for b in selected}
        anchor = next((b for b in ranked if b.id in selected_ids), None)
        # Retry the highest-priority WHOLE proof group, not half a syntactic list
        # or an arbitrary smaller character cap. Completeness is still audited.
        fit_seeds = list({b.id: b for b in [*priority, *([anchor] if anchor else [])]}.values())
        fitted = pack_context(blocks, fit_seeds, years, limit, budget,
            atomic_lists=True,
            enumeration_subject=plan.enumeration_subject if plan.coverage == 'enumeration' else None, diagnostics=fit_packing,
            coverage_goals=[], priority_ids={b.id for b in priority}, allow_first_whole_group=True)
        fitted_ids = {b.id for b in fitted}
        if not fitted or fitted_ids == selected_ids or not anchor or anchor.id not in fitted_ids:
            raise
        trace["window_repack"] = {"reason": exc.code, "previous_context_ids": [b.id for b in selected],
                                  "strategy": "highest_priority_whole_group", "packing": fit_packing}
        selected = fitted
        rules = active_preferences(policy, plan, selected)
        payload = _prose_payload(question, plan, selected, rules)
        trace.update(context_count=len(selected), context_ids=[b.id for b in selected])
        proposal, claims, rejected, repaired = await propose_bound_claims(db, bounded, payload, selected)
    trace.update(binding_rejections=rejected, quote_repair_attempted=repaired)
    if not claims or proposal.status in {"conflict", "clarify"}:
        trace["reason"] = "NO_UNAMBIGUOUS_BOUND_PROSE"
        return None
    trace["stage"] = "verification"
    verified = await verify_bound_answer(db, bounded, payload, claims, selected, plan, rules)
    trace['semantic_repair_attempted'] = False
    trace['repair_stop_reason'] = 'budget_exhausted'
    seen_repairs = set()
    for repair_round in range(2):
        if verified.complete or verified.verifier.conflict:
            trace['repair_stop_reason'] = 'complete' if verified.complete else 'conflict'
            break
        gaps = getattr(verified, 'source_condition_gaps', {})
        qualifiers = getattr(verified, 'source_qualifier_gaps', [])
        facets = tuple(t for t in plan.requested_topics if verified.verifier.topic_coverage.get(t) is not True)
        if repair_round and not (gaps or qualifiers or facets or verified.missing):
            trace['repair_stop_reason'] = 'unresolved_verdict'
            break  # No actionable source/facet gap: do not replay an unverified answer.
        signature = (tuple(sorted(gaps.items())), tuple((q.block_id, q.quote) for q in qualifiers),
                     facets, tuple(verified.missing))
        if signature in seen_repairs:
            trace['repair_stop_reason'] = 'no_progress'
            break
        seen_repairs.add(signature)
        trace.setdefault('condition_repair_rounds', []).append({'round': repair_round + 1,
            'condition_ids': sorted(gaps), 'qualifier_blocks': [q.block_id for q in qualifiers],
            'missing_topics': list(facets)})
        # Two rounds on the SAME source, for changed condition OR answer-facet gaps.
        # Restoring a prerequisite may expose a discarded facet that needs reselection.
        trace['semantic_repair_attempted'] = True
        current_feedback = {'missing_constraints': verified.missing,
            'verification_errors': verified.errors, 'topic_coverage': verified.verifier.topic_coverage,
            'source_condition_gaps': getattr(verified, 'source_condition_gaps', {}),
            'audit_complete': verified.audit.complete if verified.audit else None}
        trace.setdefault('initial_verification', current_feedback)
        repaired_payload = {**payload, 'coverage_repair': current_feedback,
            'instruction': payload['instruction'] + ' Repair missing answer facets/conditions using ONLY supplied source IDs. '
            'A source-declared unknown can answer a numerical premise negatively; never invent a value. '
            'Keep exact prerequisites, exceptions and preservation instructions in public evidence IDs. '
            'When one short source rule jointly defines permission, prerequisites and exclusions, '
            'prefer its whole_passage_id over selecting only its permission sentence.'}
        gaps = getattr(verified, 'source_condition_gaps', {})
        qualifiers = getattr(verified, 'source_qualifier_gaps', [])
        same_owner_progress = bool(qualifiers and repair_round and
            {q.block_id for q in qualifiers}.issubset(
                trace['condition_repair_rounds'][0]['qualifier_blocks']))
        if ((gaps or qualifiers) and verified.claims and not blocking_repair_errors(verified)
                and (not repair_round or gaps or same_owner_progress)
                and all(verified.verifier.topic_coverage.get(t) is True for t in plan.requested_topics)):
            try:
                restored = restore_condition_claims(gaps, selected, qualifiers)
            except ValueError as exc:
                raise AppException('Không đối chiếu được điều kiện nguồn cần phục hồi.',
                    code='SOURCE_CONDITION_REPAIR_INVALID', status_code=503) from exc
            # Restored claims are exact source text, never a model's replacement
            # for an entity/value. A new verification and audit remain mandatory.
            used = {c['id'] for c in verified.claims}
            for claim in restored:
                while claim['id'] in used:
                    claim['id'] = '_' + claim['id']
                used.add(claim['id'])
            claims = [*verified.claims, *restored]
            trace['repair_strategy'] = 'source_condition_completion'
            if len(claims) > 48:
                trace.update(reason='SOURCE_CONDITION_REPAIR_BUDGET', stage='complete')
                return None
        else:
            proposal, claims, rejected, repaired = await propose_bound_claims(db, bounded, repaired_payload, selected)
            trace.update(repair_binding_rejections=rejected, repair_quote_repair_attempted=repaired,
                         repair_strategy='source_passage_selection')
            if not claims or proposal.status in {'conflict', 'clarify'}:
                trace.update(reason='SEMANTIC_REPAIR_NO_BOUND_CLAIMS', stage='complete')
                return None
            claims = retain_safe_claims(claims, verified.claims, selected)
            if ((gaps or qualifiers) and verified.claims and not blocking_repair_errors(verified)
                    and all(verified.verifier.topic_coverage.get(t) is True for t in plan.requested_topics)):
                try:
                    restored = restore_condition_claims(gaps, selected, qualifiers)
                except ValueError as exc:
                    raise AppException('Không đối chiếu được điều kiện nguồn sau chọn lại.',
                        code='SOURCE_CONDITION_REPAIR_INVALID', status_code=503) from exc
                claims = retain_recovered_conditions(claims, restored)
                trace['retained_reselection_conditions'] = len(restored)
            if len(claims) > 48:
                trace.update(reason='SOURCE_CONDITION_REPAIR_BUDGET', stage='complete')
                return None
        verified = await verify_bound_answer(db, bounded, repaired_payload, claims, selected, plan, rules)
    trace["stage"] = "complete"
    if verified.complete:
        trace['repair_stop_reason'] = 'complete'
    trace.update(reason="VERIFIED_PROSE" if verified.complete else "PROSE_NOT_FULLY_VERIFIED",
                 accepted_claims=len(verified.claims), missing_constraints=verified.missing,
                 verification_errors=verified.errors, verifier_complete=verified.verifier.complete,
                 topic_coverage=verified.verifier.topic_coverage,
                 audit_complete=verified.audit.complete if verified.audit else None)
    # Final complete is computed from retained claims by the independent whole-
    # answer audit plus topic, scope, formula, qualifier and list-coverage gates.
    # The initial proposal's summary can include an unrelated claim later rejected;
    # it must not overrule the final audited set (same contract as evidence_pipeline).
    if not verified.complete or not verified.claims or verified.verifier.conflict:
        return None
    response = decision_response(req, snapshot, "supported", "VERIFIED_PROSE_FALLBACK", plan,
                                 bindings=verified.claims, started=started)
    response.answer_decision.update(fallback_trigger=trace["trigger"], verification=verified.verifier.model_dump())
    trace["verified"] = True
    req._retrieval_diagnostics.update(branch="canonical_prose", canonical_search_executed=True)
    return response


def _prose_payload(question, plan, selected, rules):
    requested = plan.model_dump(exclude_none=True, exclude_defaults=True)
    requested["years"] = plan.years
    # No explicit year restriction is different from a refused cross-year lookup.
    # Do not let the recovery-only 'no extra historical lookup' flag suggest that
    # all source-dated evidence is inapplicable to a seasonless question.
    if not plan.years:
        requested.pop("historical_reference_allowed", None)
    instruction = "Answer only the original question. Keep its entity, metric, year and exceptions; do not add adjacent facts."
    if not plan.years:
        instruction += (" The user specified NO data-year restriction. Do not demand an unspecified current season, "
            "uniqueness or applicability to all years. Answer within the quoted source's own scope, "
            "without claiming that it applies to an unrequested year.")
    return {"question": question, "requested": requested,
            **model_context(selected, compact=True), "compact_passages": True,
            "source_preferences": [rule.model_dump() for rule in rules],
            "instruction": instruction}
