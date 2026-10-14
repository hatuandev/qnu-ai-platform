"""Bounded source-span answering shared by direct RAG and assistant workflows."""

import asyncio
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.evidence_policy import EvidencePolicy
from app.core.exceptions import AppException
from app.core.guardrails import output_guardrail
from app.modules.rag.evidence_blocks import (
    enumeration_neighbors,
    load_published_blocks,
    pack_context,
    rank_blocks,
)
from app.modules.rag.evidence_claims import propose_bound_claims
from app.modules.rag.evidence_context import model_context
from app.modules.rag.evidence_facts import reviewed_fact_blocks
from app.modules.rag.evidence_lists import list_tail_context
from app.modules.rag.evidence_lists import list_groups, matches_subject
from app.modules.rag.evidence_model import (
    PLAN_INSTRUCTION,
    structured_call,
)
from app.modules.rag.evidence_precedence import (
    active_preferences,
    preference_candidates,
)
from app.modules.rag.evidence_retrieval import bounded_rerank, retrieve_anchors
from app.modules.rag.evidence_runtime import assistant_scope, no_answer_message
from app.modules.rag.evidence_schemas import (
    EvidenceBlock,
    QueryPlan,
)
from app.modules.rag.evidence_scope import resolve_institution_scope
from app.modules.rag.evidence_validation import (
    VERSION,
    YEAR,
    evidence_digest,
    validate_plan_years,
)
from app.modules.rag.evidence_verification import verify_bound_answer
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.schemas import AskRequest, AskResponse, Citation, RetrievalSnapshot

logger = logging.getLogger(__name__)


def reference_year(policy: EvidencePolicy, now: datetime | None = None) -> int | None:
    if policy.reference_year_mode == "current_year":
        return (now.astimezone(ZoneInfo(policy.timezone)) if now else datetime.now(ZoneInfo(policy.timezone))).year
    return policy.default_reference_year if policy.reference_year_mode == "fixed" else None


def decision_response(req: AskRequest, snapshot: RetrievalSnapshot, status: str, reason: str,
                      plan: QueryPlan | None = None, bindings: list[dict] | None = None,
                      missing: list[str] | None = None, started: float = 0,
                      blocks: list[EvidenceBlock] | None = None) -> AskResponse:
    bindings = bindings or []
    lines = list(dict.fromkeys(c["text"] for c in bindings))
    if plan and plan.years:
        lines.insert(0, "Đối chiếu năm " + ", ".join(map(str, plan.years)) + ":")
    if status == "clarify":
        lines.append("Bạn muốn tra cứu cho năm hoặc đợt tuyển sinh nào? Hãy bổ sung ngữ cảnh cần đối chiếu.")
    elif status == "conflict":
        lines.append("Các nguồn có thông tin không thống nhất cho ngữ cảnh được hỏi; cần đối soát trước khi kết luận.")
    elif status in {"missing", "partial"}:
        if missing:
            lines.append("Chưa đủ căn cứ để trả lời đầy đủ yêu cầu của bạn.")
        if status == "partial" and bindings:
            lines.append("Mình chỉ xác nhận được các thông tin có trích dẫn ở trên; phần còn lại cần đối soát thêm.")
        else:
            lines.append(no_answer_message(req))
    answer = output_guardrail.check("\n\n".join(lines)).sanitized_text
    refs = [ref for claim in bindings for ref in claim["references"]]
    unique = { (r["block_id"], r["quote"]): r for r in refs }
    citations = [Citation(source_id=r["binding_id"], binding_id=r["binding_id"],
        index_revision_id=r["index_revision_id"], source_revision_id=r["source_revision_id"],
        title=r["title"], section=r["section"], page_number=r["page_number"], quote=r["quote"],
        source_pages=[r["page_number"]] if r["page_number"] is not None else None,
        evidence_origin=r["origin"], fact_id=r["fact_id"],
        span_start=r["start"], span_end=r["end"], canonical_hash=r["canonical_hash"])
        for r in unique.values()]
    decision = {"version": VERSION, "status": status, "reason": reason, "answer": answer,
        "requested": plan.model_dump() if plan else {}, "claim_bindings": bindings,
        "evidence_digest": evidence_digest(bindings), "missing_constraints": missing or []}
    if blocks is not None:
        decision["selection"] = [{"id": b.id, "title": b.title, "page": b.page_number} for b in blocks]
    return AskResponse(answer_decision=decision, status="answered" if status == "supported" else "insufficient_context",
        answer=answer, citations=citations,
        contexts=[f"{b.title} · trang {b.page_number} · {b.section}\n{b.text}" for b in blocks] if blocks is not None else [r["quote"] for r in unique.values()],
        retrieval_snapshot=snapshot, snapshot=snapshot, latency_ms=round((time.perf_counter() - started) * 1000, 2))


async def select_context(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot, plan: QueryPlan,
                         policy: EvidencePolicy, *, candidate_mode: bool) -> list[EvidenceBlock]:
    # First retrieval establishes semantic page anchors. Supplement is read-only and bounded.
    candidates = await retrieve_anchors(req, snapshot, plan.query, policy, candidate_mode, data_years=plan.years)
    blocks = await load_published_blocks(db, snapshot, candidate_mode=candidate_mode)
    blocks += await reviewed_fact_blocks(db, req, snapshot, plan, blocks)
    rules = active_preferences(policy, plan, blocks)
    preferred = preference_candidates(rules, plan, blocks)
    preferred_lexical = preferred[:3]
    rp = req.reranker_policy or {}
    if preferred and rp.get("enabled", True):
        preferred_hits = [FusionCandidate(b.id, b.binding_id, f"{b.title}\n{b.text}", 1 / (60 + i),
            page_number=b.page_number, binding_id=b.binding_id, index_revision_id=b.index_revision_id)
            for i, b in enumerate(preferred, 1)]
        reranked_preferred = await bounded_rerank(req.question, preferred_hits, 2, req, policy)
        preferred_by_id = {b.id: b for b in preferred}
        preferred = list({b.id: b for b in [*preferred_lexical,
            *[preferred_by_id[c.chunk_id] for c in reranked_preferred]]}.values())
    queries = list(dict.fromkeys([req.question, plan.query, *plan.search_queries,
                                 *([plan.attribute] if plan.attribute else [])]))
    variants = [rank_blocks(blocks, [query], max(6, policy.candidate_limit // len(queries)), plan.years) for query in queries]
    variant_scores = {}
    by_id = {b.id: b for b in blocks}
    for hits in variants:
        for rank, block in enumerate(hits, 1):
            variant_scores[block.id] = variant_scores.get(block.id, 0) + 1 / (60 + rank)
    ranked = [by_id[bid] for bid in sorted(variant_scores, key=variant_scores.get, reverse=True)]
    anchors = {(c.binding_id, c.index_revision_id, c.page_number) for c in candidates}
    anchored = rank_blocks([b for b in blocks if (b.binding_id, b.index_revision_id, b.page_number) in anchors], queries, 3, plan.years)
    shortlist = list({b.id: b for b in [*ranked[:4], *preferred, *anchored, *ranked]}.values())[:policy.candidate_limit]
    # Preserve a direct lexical attribute hit alongside semantic winners. It is
    # only a candidate, never a verified answer or a source-authority override.
    direct = rank_blocks(blocks, [plan.attribute or plan.query], 2, plan.years)
    if rp.get("enabled", True) and shortlist:
        fused = [FusionCandidate(b.id, b.binding_id, f"{b.title}\n{b.section}\n{b.text}\n{b.header_context[:900]}", 1 / (60 + i),
            page_number=b.page_number, binding_id=b.binding_id, index_revision_id=b.index_revision_id)
            for i, b in enumerate(shortlist, 1)]
        reranked = await bounded_rerank(plan.query, fused, min(policy.context_limit, rp.get("top_k", 5)), req, policy)
        by_id = {b.id: b for b in shortlist}
        shortlist = [by_id[c.chunk_id] for c in reranked]
    # Cover one authoritative table row even when the paragraph shortlist dominates.
    fact_pool = [b for b in blocks if b.origin == "reviewed_fact"]
    table_rows = rank_blocks(fact_pool, [req.question, *queries], policy.candidate_limit, plan.years)
    if rp.get("enabled", True) and table_rows:
        fact_candidates = [FusionCandidate(b.id, b.binding_id, f"{b.title}\n{b.text}\n{b.header_context[:900]}", 1 / (60 + i),
            page_number=b.page_number, binding_id=b.binding_id, index_revision_id=b.index_revision_id)
            for i, b in enumerate(table_rows, 1)]
        fact_ranked = await bounded_rerank(plan.query, fact_candidates, 2, req, policy)
        fact_by_id = {b.id: b for b in table_rows}
        table_rows = [fact_by_id[c.chunk_id] for c in fact_ranked]
    else:
        table_rows = table_rows[:2]
    shortlist = list({b.id: b for b in [*direct, *shortlist, *preferred[:2]]}.values())
    neighbors = enumeration_neighbors(blocks, shortlist, 6, subject=plan.enumeration_subject or plan.entity) if plan.coverage == "enumeration" else []
    tails = list_tail_context(blocks, neighbors) if neighbors else []
    shortlist = list({b.id: b for b in [*direct, *table_rows, *shortlist, *neighbors, *tails]}.values())
    if plan.coverage == "enumeration":
        subject = plan.enumeration_subject or plan.entity
        groups = [group for group in list_groups(blocks) if matches_subject(group, subject)]
        summaries = [group[0].model_copy(update={"text": "\n".join(b.text for b in group)}) for group in groups]
        best = rank_blocks(summaries, [subject or plan.query], 1, plan.years)
        if best:
            group = next(group for group in groups if group[0].id == best[0].id)
            shortlist = list({b.id: b for b in [*group, *list_tail_context(blocks, group), *shortlist]}.values())
    packing = {}
    selected = pack_context(blocks, shortlist, plan.years, policy.context_limit, policy.max_context_chars,
                            atomic_lists=plan.coverage == "enumeration", enumeration_subject=plan.enumeration_subject or plan.entity,
                            diagnostics=packing)
    logger.info("evidence_selection conversation=%s snapshot=%s corpus=%d candidates=%d packed=%d chars=%d dropped=%s ids=%s",
                req.conversation_id, snapshot.snapshot_id, len(blocks), len(shortlist), len(selected), packing["packed_characters"],
                packing["dropped"], [b.id for b in selected])
    return selected


async def _answer(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot, policy: EvidencePolicy,
                  started: float, candidate_mode: bool, progress: dict | None = None) -> AskResponse:
    progress = progress if progress is not None else {}
    if req.original_question:
        req = req.model_copy(update={"question": req.original_question})
    progress["stage"] = "planning"
    stage_started = time.perf_counter()
    default_year = reference_year(policy)
    scope = assistant_scope(req)
    roles = await resolve_institution_scope(db, req, scope)
    plan = await structured_call(db, req, QueryPlan, PLAN_INSTRUCTION,
        {"question": req.question, "history": req.history or [], "configured_reference_year": default_year,
         "assistant_scope": scope, "resolved_institution_roles": roles}, max_tokens=1000)
    if roles:
        plan.target_institution = roles["target_institution"]
        plan.exam_organizer = roles["exam_organizer"]
        if plan.target_institution:
            plan.query = f"{plan.target_institution}: {plan.query}"[:2000]
            plan.search_queries = [f"{plan.target_institution}: {query}" for query in plan.search_queries]
    progress["planning_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
    if not plan.years and not plan.document_years and not plan.event_years and default_year:
        plan.years = [default_year]
    try:
        validate_plan_years(plan, req.question, req.history or [], default_year)
    except ValueError as exc:
        raise AppException("Bộ lập kế hoạch thay đổi ngữ cảnh năm được hỏi.", code="EVIDENCE_PLAN_SCOPE_INVALID", status_code=502) from exc
    requested_years = sorted(set(plan.years + plan.document_years + plan.event_years))
    if plan.requires_year and not requested_years:
        return decision_response(req, snapshot, "clarify", "YEAR_REQUIRED", plan, started=started)
    if plan.requires_year and not YEAR.search(plan.query):
        plan.query += " năm " + ", ".join(map(str, requested_years))
    progress["stage"] = "retrieval"
    stage_started = time.perf_counter()
    blocks = await select_context(db, req, snapshot, plan, policy, candidate_mode=candidate_mode)
    progress["retrieval_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
    if not blocks:
        return decision_response(req, snapshot, "missing", "NO_COMPATIBLE_EVIDENCE", plan, started=started)
    evidence = model_context(blocks)
    rules = active_preferences(policy, plan, blocks)
    preferences = [rule.model_dump() for rule in rules]
    progress["stage"] = "proposal"
    stage_started = time.perf_counter()
    payload = {"question": req.question, "requested": plan.model_dump(), **evidence,
               "source_preferences": preferences, "assistant_scope": scope}
    proposal, claims, rejected, repaired = await propose_bound_claims(db, req, payload, blocks)
    progress["proposal_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
    if proposal.status in {"missing", "conflict", "clarify"} and not proposal.claims:
        return decision_response(req, snapshot, proposal.status, "EVIDENCE_NOT_SUPPORTED", plan,
                                 missing=proposal.missing_constraints, started=started, blocks=blocks)
    if not claims:
        response = decision_response(req, snapshot, "missing", "INVALID_OR_EMPTY_CLAIMS", plan, started=started, blocks=blocks)
        response.answer_decision.update(binding_rejections=rejected, quote_repair_attempted=repaired)
        return response
    progress["stage"] = "verification"
    stage_started = time.perf_counter()
    verified = await verify_bound_answer(db, req, payload, claims, blocks, plan, rules)
    repair_history = []
    if not verified.complete and not verified.verifier.conflict and proposal.status != "conflict":
        previous_verified = verified
        repair_history = [{"errors": rejected + verified.errors, "missing_constraints": verified.missing,
                           "audit": verified.audit.model_dump() if verified.audit else None,
                           "uncovered_list_members": verified.uncovered}]
        proposal, claims, rejected, quote_repaired = await propose_bound_claims(db, req,
            {**payload, "previous_proposal": proposal.model_dump(), "coverage_feedback": repair_history,
             "repair_instruction": "Repair the answer ONCE from exact supplied evidence. Retain essential qualifiers, "
             "split unsupported compound relations, omit unrelated extras. Never invent missing evidence or expected answers."}, blocks)
        repaired = repaired or quote_repaired
        if claims:
            repaired_verified = await verify_bound_answer(db, req, payload, claims, blocks, plan, rules)
            # A bounded repair must not erase a previously verified safe partial
            # answer when its new proposal is rejected as a whole.
            if repaired_verified.claims or not previous_verified.claims:
                verified = repaired_verified
        else:
            verified = previous_verified
            verified.missing = list(dict.fromkeys([*verified.missing, *proposal.missing_constraints]))
    progress["verification_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
    if verified.verifier.conflict or proposal.status == "conflict":
        return decision_response(req, snapshot, "conflict", "CONFLICTING_EVIDENCE", plan, started=started, blocks=blocks)
    accepted, complete = verified.claims, verified.complete
    status = "supported" if complete else "partial" if accepted else "missing"
    logger.info("evidence_answer_decision status=%s accepted=%d rejected=%d snapshot=%s years=%s",
                status, len(accepted), len(proposal.claims) - len(accepted), snapshot.snapshot_id, plan.years)
    response = decision_response(req, snapshot, status, "VERIFIED_CLAIM_COVERAGE" if complete else "PARTIAL_OR_MISSING_COVERAGE",
        plan, bindings=accepted, missing=verified.missing, started=started)
    response.contexts = [f"{b.title} · trang {b.page_number} · {b.section}\n{b.text}" for b in blocks]
    response.answer_decision["verification"] = verified.verifier.model_dump()
    response.answer_decision.update(binding_rejections=rejected + verified.errors, quote_repair_attempted=repaired,
        semantic_audit=verified.audit.model_dump() if verified.audit else None,
        semantic_repair_attempted=bool(repair_history), repair_history=repair_history)
    response.answer_decision["source_preferences"] = preferences
    response.answer_decision["uncovered_list_members"] = verified.uncovered
    response.answer_decision["selection"] = [{"id": b.id, "title": b.title, "page": b.page_number} for b in blocks]
    return response


async def answer_with_evidence(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot, policy: EvidencePolicy,
                              *, candidate_mode: bool = False) -> AskResponse:
    started = time.perf_counter()
    progress = {}
    try:
        async with asyncio.timeout(policy.timeout_seconds):
            response = await _answer(db, req, snapshot, policy, started, candidate_mode, progress)
            response.answer_decision["stage_timings_ms"] = {k: v for k, v in progress.items() if k.endswith("_ms")}
            return response
    except TimeoutError as exc:
        stage = progress.get("stage", "initialization")
        logger.warning("evidence_timeout stage=%s conversation=%s snapshot=%s", stage, req.conversation_id, snapshot.snapshot_id)
        raise AppException(f"Đối soát chứng cứ vượt thời gian xử lý (bước: {stage}).",
            code="EVIDENCE_TIMEOUT", status_code=504) from exc
