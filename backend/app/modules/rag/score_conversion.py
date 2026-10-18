"""Read-only, source-bound piecewise interpolation; no eval, LLM arithmetic or defaults."""

import unicodedata
from decimal import Decimal, localcontext
from itertools import pairwise

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_facts import reviewed_fact_blocks
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.evidence_validation import bind_quote
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.score_conversion_schemas import (
    ConversionRule,
    ScoreConversionRequest,
    ScoreConversionResult,
    SourceCell,
    parse_score,
)


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split()).casefold()


def verified_cell(cell: SourceCell, blocks: dict[str, EvidenceBlock], rule: ConversionRule) -> str:
    block = blocks.get(cell.block_id)
    if block is None or (block.binding_id, block.index_revision_id, block.source_revision_id, block.canonical_hash) != (
            rule.binding_id, rule.index_revision_id, rule.source_revision_id, rule.canonical_hash):
        raise ValueError("Cell is outside the reviewed source revision")
    matches = [entry for entry in block.fact_context.get("cells", [])
               if entry["fact_id"] == cell.fact_id and entry["attribute"] == cell.attribute and entry["value"] == cell.value]
    if block.origin != "reviewed_fact" or len(matches) != 1:
        raise ValueError("Conversion cell is missing or has changed")
    return cell.value


def reviewed_row_code(block: EvidenceBlock, label: str) -> str:
    """Read the row's own identifier cell; a row may be named by subject list, not by code."""
    entries = block.fact_context.get("row_context") or []
    if any(not isinstance(entry, list) or len(entry) != 2 for entry in entries):
        raise ValueError("Mapping row context is malformed")
    codes = [str(value) for key, value in entries if normalized(str(key)) == normalized(label)]
    if len(codes) != 1:
        raise ValueError("Mapping row does not carry exactly one reviewed combination code")
    return codes[0]


def calculate_verified_score(request: ScoreConversionRequest, rule: ConversionRule,
                             blocks: dict[str, EvidenceBlock], snapshot: RetrievalSnapshot) -> ScoreConversionResult:
    """All data and policies come from reviewed server configuration and current facts."""
    if snapshot.binding_revisions.get(rule.binding_id) != rule.index_revision_id or request.year != rule.year:
        raise ValueError("Conversion rule is stale or applies to another year")
    if normalized(request.source_method) not in {normalized(value) for value in [rule.source_method, *rule.source_aliases]}:
        raise ValueError("Source method does not match the reviewed rule")
    mappings = [mapping for mapping in rule.mappings if normalized(mapping.combination) == normalized(request.combination)]
    if len(mappings) != 1 or mappings[0].base_combination != rule.base_combination:
        raise ValueError("No unambiguous source-backed combination mapping")
    if verified_cell(mappings[0].proof, blocks, rule) != rule.base_combination:
        raise ValueError("Combination mapping differs from reviewed fact")
    mapping_block = blocks[mappings[0].proof.block_id]
    if normalized(reviewed_row_code(mapping_block, rule.combination_context_attribute)) != normalized(request.combination):
        raise ValueError("Mapping proof belongs to another combination")
    for proof in rule.rule_proofs:
        block = blocks.get(proof.block_id)
        if block is None or (block.binding_id, block.index_revision_id, block.source_revision_id, block.canonical_hash) != (
                rule.binding_id, rule.index_revision_id, rule.source_revision_id, rule.canonical_hash):
            raise ValueError("Formula/rounding proof belongs to another source")
        bind_quote(proof, blocks)
    if any(point.source.attribute != rule.source_attribute or point.target.attribute != rule.target_attribute
           or point.source.block_id != point.target.block_id for point in rule.points):
        raise ValueError("Source and target must be the reviewed columns in the same percentile row")
    points = [(parse_score(verified_cell(point.source, blocks, rule)),
               parse_score(verified_cell(point.target, blocks, rule))) for point in rule.points]
    # Preserve the reviewed percentile order; never sort away corrupt/mixed columns.
    differences = [right[0] - left[0] for left, right in pairwise(points)]
    if not (all(step > 0 for step in differences) or all(step < 0 for step in differences)):
        raise ValueError("Source points must be strictly monotonic without duplicate boundaries")
    points = points if differences[0] > 0 else list(reversed(points))
    if any(right[1] < left[1] for left, right in pairwise(points)):
        raise ValueError("Target points are inconsistent with source order")
    score = parse_score(request.score)
    brackets = [(left, right) for left, right in pairwise(points) if left[0] <= score <= right[0]]
    if not brackets:
        return ScoreConversionResult(status="missing", reason="SCORE_OUTSIDE_VERIFIED_RANGE",
            message="Điểm nằm ngoài khoảng đã được kiểm chứng; mình không tự ngoại suy kết quả.")
    (x1, y1), (x2, y2) = brackets[0]
    with localcontext() as decimal_context:
        decimal_context.prec = 40
        result = (y1 + (score - x1) * (y2 - y1) / (x2 - x1)).quantize(
            Decimal(1).scaleb(-rule.decimal_places), rounding=rule.rounding)
    used = {proof.block_id for proof in rule.rule_proofs} | {mappings[0].proof.block_id}
    used.update(point.source.block_id for point, values in zip(rule.points, [
        (parse_score(point.source.value), parse_score(point.target.value)) for point in rule.points], strict=True)
        if values in ((x1, y1), (x2, y2)))
    from app.modules.rag.combination_enumeration import _citation

    return ScoreConversionResult(status="calculated", reason="VERIFIED_PIECEWISE_LINEAR",
        message="Kết quả được tính từ bảng và quy tắc đã duyệt, làm tròn một lần ở bước cuối.",
        rule_id=rule.id, year=rule.year, source_method=rule.source_method, target_method=rule.target_method,
        combination=request.combination, base_combination=rule.base_combination, input_score=str(score),
        x1=str(x1), x2=str(x2), y1=str(y1), y2=str(y2), result=str(result),
        formula="Y = Y1 + ((X - X1) / (X2 - X1)) * (Y2 - Y1)", rounding=rule.rounding,
        source_revision_id=rule.source_revision_id, index_revision_id=rule.index_revision_id,
        snapshot_id=snapshot.snapshot_id, evidence_block_ids=sorted(used),
        citations=[_citation(blocks[block_id]) for block_id in sorted(used)])


async def convert_admission_score(db: AsyncSession, request: ScoreConversionRequest, *, tenant_id: str,
                                  workspace_id: str) -> ScoreConversionResult:
    """Rules can only come from persisted, administrator-managed collection metadata."""
    from app.modules.rag.retriever import hybrid_retriever

    try:
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, request.collection_id,
            tenant_id=tenant_id, workspace_id=workspace_id)
    except AppException:
        raise
    except Exception as exc:
        raise AppException("Không thể tải quy tắc quy đổi điểm.", code="SCORE_RULE_UNAVAILABLE", status_code=503) from exc

    if snapshot.collection_id != request.collection_id:
        raise AppException("Snapshot không thuộc kho tri thức được yêu cầu.",
                           code="SCORE_SCOPE_FORBIDDEN", status_code=403)

    try:
        collection = await db.get(KnowledgeCollection, request.collection_id)
    except Exception as exc:
        raise AppException("Không thể tải quy tắc quy đổi điểm.", code="SCORE_RULE_UNAVAILABLE", status_code=503) from exc
    if (collection is None):
        raise AppException("Không có quyền đọc quy tắc quy đổi.", code="SCORE_SCOPE_FORBIDDEN", status_code=403)
    from app.modules.knowledge.services.score_rule_service import active_rules

    raw_rules = active_rules(collection.collection_metadata or {})
    try:
        rules = [ConversionRule.model_validate(rule) for rule in raw_rules]
    except (ValidationError, TypeError) as exc:
        raise AppException("Cấu hình quy đổi chưa qua kiểm chứng hợp lệ.", code="SCORE_RULE_INVALID", status_code=422) from exc
    matching = [rule for rule in rules if rule.year == request.year and
        normalized(request.source_method) in {normalized(value) for value in [rule.source_method, *rule.source_aliases]}
        and any(normalized(mapping.combination) == normalized(request.combination) for mapping in rule.mappings)]
    if len(matching) != 1:
        return ScoreConversionResult(status="clarify" if matching else "missing", reason="CONVERSION_RULE_AMBIGUOUS" if matching else "NO_VERIFIED_CONVERSION_RULE",
            message="Chưa có một bộ công thức, bảng điểm và ánh xạ tổ hợp đã duyệt phù hợp với năm/phương thức này; mình chưa thể tính điểm an toàn.")
    rule = matching[0]
    pinned = snapshot.model_copy(update={"binding_revisions": {rule.binding_id: rule.index_revision_id}})
    if snapshot.binding_revisions.get(rule.binding_id) != rule.index_revision_id:
        raise AppException("Bảng quy đổi không còn thuộc nguồn đang xuất bản.", code="SCORE_RULE_STALE", status_code=409)
    blocks = await load_rule_blocks(db, request.collection_id, rule, pinned)
    try:
        return calculate_verified_score(request, rule, blocks, snapshot)
    except ValueError as exc:
        raise AppException("Bảng hoặc bằng chứng quy đổi không còn khớp bản đã duyệt.", code="SCORE_EVIDENCE_INVALID", status_code=422) from exc


async def load_rule_blocks(db: AsyncSession, collection_id: str, rule: ConversionRule,
                           snapshot: RetrievalSnapshot) -> dict[str, EvidenceBlock]:
    """Same source/hash checks for administrator preview and runtime calculation."""
    pinned = snapshot.model_copy(update={"binding_revisions": {rule.binding_id: rule.index_revision_id}})
    if snapshot.binding_revisions.get(rule.binding_id) != rule.index_revision_id:
        raise AppException("Nguồn của quy tắc không còn được xuất bản.", code="SCORE_RULE_STALE", status_code=409)
    try:
        blocks = await load_published_blocks(db, pinned)
        req = AskRequest(question="Score conversion", collection_id=collection_id)
        blocks += await reviewed_fact_blocks(db, req, pinned, QueryPlan(query=req.question), blocks, exhaustive=True)
        return {block.id: block for block in blocks}
    except AppException:
        raise
    except Exception as exc:
        raise AppException("Không thể tải bằng chứng quy đổi.", code="SCORE_RULE_UNAVAILABLE", status_code=503) from exc
