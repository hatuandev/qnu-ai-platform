"""One verified, explicitly labeled historical reference after current-year search."""

import logging
import time
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.evidence_policy import EvidencePolicy
from app.core.guardrails import output_guardrail
from app.modules.rag import evidence_blocks, evidence_claims, evidence_facts, evidence_verification
from app.modules.rag.evidence_constraints import data_year_values, retained_condition
from app.modules.rag.evidence_context import model_context
from app.modules.rag.evidence_precedence import active_preferences
from app.modules.rag.evidence_runtime import assistant_scope
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.evidence_validation import YEAR, temporal_references_supported
from app.modules.rag.schemas import AskRequest, AskResponse, RetrievalSnapshot

logger = logging.getLogger(__name__)


def historical_notice(requested_year: int, reference_year: int) -> str:
    return (f"Bạn đang hỏi năm {requested_year}. Mình chưa tìm thấy căn cứ đã kiểm chứng đủ rõ "
            f"để trả lời nội dung này cho năm {requested_year} trong kho tài liệu đang dùng.\n\n"
            f"Thông tin năm {reference_year} dưới đây chỉ để tham khảo; "
            f"không xác nhận áp dụng cho năm {requested_year}.")


def reference_plan(response: AskResponse, policy: EvidencePolicy) -> QueryPlan | None:
    decision = response.answer_decision or {}
    if (not policy.historical_reference_enabled or decision.get("status") not in {"missing", "partial"}
            or decision.get("claim_bindings") or not decision.get("requested")):
        return None
    plan = QueryPlan.model_validate(decision["requested"])
    if (not plan.historical_reference_allowed or len(plan.years) != 1 or plan.document_years
            or plan.event_years or plan.coverage == "comparison"):
        return None
    return plan


def candidate_years(block: EvidenceBlock) -> set[int]:
    scope = block.temporal_scope
    if scope.status == "ambiguous":
        return set()
    if scope.status == "verified" and scope.role == "data" and scope.data_years:
        return set(scope.data_years)
    # Actual content hints only; never the filename, issue date or title metadata.
    # They nominate a search year, NOT proof: every selected claim is audited below.
    return data_year_values(block.text) or data_year_values(block.header_context)


def historical_claim_supported(claim: dict, year: int) -> bool:
    if data_year_values(claim["text"]) - {year} or not temporal_references_supported(claim, [year]):
        return False
    return retained_condition("data_year", {"quote": str(year)}, [claim], [year])


def validate_historical_label(decision: dict, answer: str) -> int | None:
    reference = decision.get("historical_reference") or {}
    requested, year = reference.get("requested_year"), reference.get("reference_year")
    if (type(requested) is not int or type(year) is not int or not 1900 <= year < requested <= 2099
            or decision.get("status") != "partial" or decision.get("reason") != "HISTORICAL_REFERENCE_ONLY"
            or (decision.get("requested") or {}).get("years") != [requested]
            or (decision.get("requested") or {}).get("document_years")
            or (decision.get("requested") or {}).get("event_years")
            or (decision.get("requested") or {}).get("coverage") == "comparison"
            or (decision.get("requested") or {}).get("historical_reference_allowed") is False
            or not answer.startswith(historical_notice(requested, year))):
        return None
    return year


async def discover_reference_year(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot,
                                  plan: QueryPlan, policy: EvidencePolicy, candidate_mode: bool) -> int | None:
    blocks = await evidence_blocks.load_published_blocks(db, snapshot, candidate_mode=candidate_mode)
    neutral = plan.model_copy(update={"years": [], "query": YEAR.sub("", plan.query),
                                      "search_queries": []})
    neutral_req = req.model_copy(update={"question": YEAR.sub("", req.original_question or req.question),
                                         "original_question": None})
    blocks += await evidence_facts.reviewed_fact_blocks(db, neutral_req, snapshot, neutral, blocks)
    from app.modules.rag.evidence_hierarchy import scope_candidates

    blocks = scope_candidates(blocks, neutral)
    ranked = evidence_blocks.rank_blocks(blocks, [neutral_req.question, neutral.query,
        plan.entity or "", plan.attribute or ""], policy.candidate_limit)
    earlier = set()
    for block in ranked:
        observed = candidate_years(block)
        if not observed and block.temporal_scope.status != "ambiguous":
            same_source = [b for b in blocks if (b.binding_id, b.index_revision_id, b.source_revision_id)
                           == (block.binding_id, block.index_revision_id, block.source_revision_id)]
            observed = set(evidence_blocks.source_heading_years(same_source))
        earlier.update(year for year in observed if 1900 <= year < plan.years[0])
    return max(earlier, default=None)


def compose_reference(req: AskRequest, snapshot: RetrievalSnapshot, original: AskResponse,
                      plan: QueryPlan, year: int, verified: evidence_verification.VerifiedAnswer,
                      blocks: list[EvidenceBlock], started: float, compose: Callable[..., AskResponse]) -> AskResponse:
    missing = list(dict.fromkeys([*(original.answer_decision.get("missing_constraints") or []),
                                 f"chưa đủ căn cứ cho năm {plan.years[0]}"]))
    historical = plan.model_copy(update={"years": [year]})
    response = compose(req, snapshot, "partial", "HISTORICAL_REFERENCE_ONLY", historical,
        bindings=verified.claims, missing=missing, started=started)
    response.answer = output_guardrail.check(
        historical_notice(plan.years[0], year) + "\n\n" + response.answer).sanitized_text
    response.answer_decision.update(answer=response.answer, requested=plan.model_dump(),
        historical_reference={"requested_year": plan.years[0], "reference_year": year},
        verification=verified.verifier.model_dump(),
        semantic_audit=verified.audit.model_dump() if verified.audit else None,
        current_year_decision=original.answer_decision,
        selection=[{"id": b.id, "title": b.title, "page": b.page_number} for b in blocks])
    response.contexts = [f"{b.title} · trang {b.page_number} · {b.section}\n{b.text}" for b in blocks]
    return response


async def verify_reference_year(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot,
                                policy: EvidencePolicy, plan: QueryPlan, year: int, candidate_mode: bool,
                                progress: dict, select: Callable[..., Awaitable[list[EvidenceBlock]]]
                                ) -> tuple[evidence_verification.VerifiedAnswer, list[EvidenceBlock]] | None:
    def replace_year(text: str) -> str:
        return YEAR.sub(str(year), text)

    historical = plan.model_copy(update={"years": [year], "query": replace_year(plan.query),
        "search_queries": [replace_year(query) for query in plan.search_queries]})
    reference_req = req.model_copy(update={"question": replace_year(req.original_question or req.question),
                                          "original_question": None})
    blocks = await select(db, reference_req, snapshot, historical, policy, candidate_mode=candidate_mode)
    progress["historical_blocks"] = len(blocks)
    if not blocks:
        progress["historical_outcome"] = "no_reference_evidence"
        return None
    rules = active_preferences(policy, historical, blocks)
    payload = {"question": reference_req.question, "requested": historical.model_dump(), **model_context(blocks),
        "source_preferences": [rule.model_dump() for rule in rules], "assistant_scope": assistant_scope(req),
        "historical_reference": {"original_question": req.original_question or req.question,
            "requested_year": plan.years[0], "reference_year": year}}
    progress["stage"] = "historical_verification"
    proposal, claims, _, _ = await evidence_claims.propose_bound_claims(db, reference_req, payload, blocks)
    if not claims or proposal.status in {"conflict", "clarify"}:
        progress["historical_outcome"] = "unbound_or_conflicting_reference"
        return None
    verified = await evidence_verification.verify_bound_answer(db, reference_req, payload, claims, blocks, historical, rules)
    if (not verified.claims or not verified.complete or not verified.verifier.complete or verified.verifier.conflict
            or verified.audit is not None and not verified.audit.complete
            or not all(historical_claim_supported(claim, year) for claim in verified.claims)):
        progress["historical_outcome"] = "reference_not_fully_verified"
        progress["historical_missing"] = verified.missing
        return None
    progress["historical_outcome"] = "verified_reference"
    return verified, blocks


async def try_historical_reference(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot,
                                   policy: EvidencePolicy, original: AskResponse, started: float,
                                   candidate_mode: bool, progress: dict,
                                   select: Callable[..., Awaitable[list[EvidenceBlock]]],
                                   compose: Callable[..., AskResponse]) -> AskResponse:
    plan = reference_plan(original, policy)
    if plan is None:
        progress["historical_outcome"] = "not_eligible"
        return original
    stage_started = time.perf_counter()
    progress["stage"] = "historical_retrieval"
    year = await discover_reference_year(db, req, snapshot, plan, policy, candidate_mode)
    if year is None:
        progress["historical_outcome"] = "no_earlier_data_year"
        progress["historical_reference_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
        return original
    progress["historical_requested_year"] = plan.years[0]
    progress["historical_reference_year"] = year
    result = await verify_reference_year(db, req, snapshot, policy, plan, year, candidate_mode, progress, select)
    progress["historical_reference_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
    if result is None:
        return original
    verified, blocks = result
    progress["historical_reference_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
    logger.info("evidence_historical_reference snapshot=%s requested=%s reference=%s claims=%d",
                snapshot.snapshot_id, plan.years, year, len(verified.claims))
    return compose_reference(req, snapshot, original, plan, year, verified, blocks, started, compose)
