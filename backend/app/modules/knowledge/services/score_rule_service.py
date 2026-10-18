"""Collection-owned immutable drafts, approval, activation and append-only audit.

Registry is stored in existing collection JSONB, not a second independent rule store.
All writes lock and refresh the collection, check OCC and persist audit atomically.
"""

import hashlib
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.knowledge.score_rule_schemas import (
    RuleAction,
    RuleAudit,
    RuleDraft,
    RuleImport,
    RulePreview,
    RuleRecord,
    RuleRegistry,
)
from app.modules.rag.score_conversion_schemas import (
    ConversionDefinition,
    ConversionRule,
    ScoreConversionRequest,
    ScoreConversionResult,
)

REGISTRY_KEY = "score_conversion_registry"
PROTECTED_KEYS = {REGISTRY_KEY, "score_conversion_rules"}


def require(actor: AuthActor, permission: str) -> None:
    if not actor or not actor.has_permission(permission) or not actor.actor_id:
        raise AppException("Bạn không có quyền quản lý quy tắc này.", code="forbidden", status_code=403)


def registry(metadata: dict) -> RuleRegistry:
    try:
        return RuleRegistry.model_validate(metadata.get(REGISTRY_KEY, {}))
    except (ValidationError, TypeError) as exc:
        raise AppException("Dữ liệu quản trị quy tắc không hợp lệ.", code="SCORE_RULE_INVALID", status_code=422) from exc


def active_rules(metadata: dict) -> list[dict]:
    if REGISTRY_KEY not in metadata:
        # Legacy JSON has no separate activation approval. Keep it stored but
        # never silently authorize it for the new managed tool lifecycle.
        return []
    return [verified_rule(item).model_dump(mode="json") for item in registry(metadata).items if item.status == "active"]


def verified_rule(item: RuleRecord) -> ConversionRule:
    if not item.reviewed_by or not item.reviewed_at:
        raise AppException("Quy tắc chưa có xác nhận của người duyệt.", code="SCORE_RULE_NOT_APPROVED", status_code=409)
    return ConversionRule(**item.definition.model_dump(), status="verified",
                          reviewed_by=item.reviewed_by, reviewed_at=item.reviewed_at)


async def load_collection(db: AsyncSession, collection_id: str, *, lock: bool = False) -> KnowledgeCollection:
    query = select(KnowledgeCollection).where(KnowledgeCollection.id == collection_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    try:
        col = (await db.execute(query)).scalar_one_or_none()
    except Exception as exc:
        raise AppException("Không thể tải quy tắc.", code="SCORE_RULE_UNAVAILABLE", status_code=503) from exc
    if col is None:
        raise EntityNotFoundError("Không tìm thấy kho tri thức.")
    return col


async def list_rules(db: AsyncSession, actor: AuthActor, collection_id: str) -> RuleRegistry:
    require(actor, "ai.knowledge.view")
    col = await load_collection(db, collection_id)
    return registry(col.collection_metadata or {})


def check_command(state: RuleRegistry, command: RuleDraft | RuleAction, actor: AuthActor, rule_id: str) -> bool:
    digest = hashlib.sha256(command.model_dump_json().encode()).hexdigest()
    repeated = [entry for entry in state.audit if entry.request_id == command.request_id]
    if repeated:
        if any(entry.command_hash != digest or entry.actor_id != actor.actor_id or entry.rule_id != rule_id for entry in repeated):
            raise AppException("Mã thao tác đã được sử dụng cho yêu cầu khác.", code="SCORE_RULE_IDEMPOTENCY_CONFLICT", status_code=409)
        return True
    if state.version != command.expected_version:
        raise AppException("Dữ liệu đã thay đổi; hãy tải lại.", code="SCORE_RULE_VERSION_CONFLICT", status_code=409)
    return False


async def persist(db: AsyncSession, col: KnowledgeCollection, state: RuleRegistry,
                  actor: AuthActor, rule_id: str, command: RuleDraft | RuleAction) -> RuleRegistry:
    state.version += 1
    state.audit.append(RuleAudit(rule_id=rule_id, action=command.action if isinstance(command, RuleAction) else "create",
        actor_id=actor.actor_id, at=datetime.now(UTC).isoformat(), reason=getattr(command, "reason", "Tạo bản nháp"),
        request_id=command.request_id, command_hash=hashlib.sha256(command.model_dump_json().encode()).hexdigest()))
    col.collection_metadata = {**(col.collection_metadata or {}), REGISTRY_KEY: state.model_dump(mode="json")}
    try:
        await db.flush()
    except Exception as exc:
        raise AppException("Không thể lưu quy tắc và lịch sử.", code="SCORE_RULE_UNAVAILABLE", status_code=503) from exc
    return state


async def create_draft(db: AsyncSession, actor: AuthActor, collection_id: str, command: RuleDraft) -> RuleRegistry:
    require(actor, "ai.knowledge.update")
    col = await load_collection(db, collection_id, lock=True)
    state = registry(col.collection_metadata or {})
    if check_command(state, command, actor, command.definition.id):
        return state
    if any(item.definition.id == command.definition.id for item in state.items):
        raise AppException("Mã quy tắc đã tồn tại; hãy tạo mã phiên bản mới.", code="SCORE_RULE_EXISTS", status_code=409)
    state.items.append(RuleRecord(definition=command.definition, created_by=actor.actor_id, created_at=datetime.now(UTC).isoformat()))
    return await persist(db, col, state, actor, command.definition.id, command)


def find_rule(state: RuleRegistry, rule_id: str) -> RuleRecord:
    for item in state.items:
        if item.definition.id == rule_id:
            return item
    raise EntityNotFoundError("Không tìm thấy quy tắc trong kho này.")


async def import_drafts(db: AsyncSession, actor: AuthActor, collection_id: str, body: RuleImport) -> RuleRegistry:
    """One request/transaction: later failures roll back earlier drafts as well."""
    state = None
    batch_key = hashlib.sha256(body.request_id.encode()).hexdigest()
    for index, definition in enumerate(body.definitions):
        state = await create_draft(db, actor, collection_id, RuleDraft(definition=definition,
            expected_version=body.expected_version + index, request_id=f"{batch_key}:{index}"))
    assert state is not None  # Validated nonempty by RuleImport.
    return state


async def validate_definition(db: AsyncSession, collection_id: str, definition: ConversionDefinition,
                              actor: AuthActor, *, score: str | None = None,
                              combination: str | None = None) -> ScoreConversionResult:
    from app.modules.rag.retriever import hybrid_retriever
    from app.modules.rag.score_conversion import (
        calculate_verified_score,
        load_rule_blocks,
        normalized,
        reviewed_row_code,
        verified_cell,
    )

    snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, collection_id)
    # Ephemeral wrapper only, never persisted as a human approval by preview.
    rule = ConversionRule(**definition.model_dump(), status="verified",
                          reviewed_by=actor.actor_id, reviewed_at=datetime.now(UTC))
    blocks = await load_rule_blocks(db, collection_id, rule, snapshot)
    try:
        for mapping in rule.mappings:
            if (verified_cell(mapping.proof, blocks, rule) != rule.base_combination
                    or mapping.base_combination != rule.base_combination
                    or normalized(reviewed_row_code(blocks[mapping.proof.block_id], rule.combination_context_attribute)) != normalized(mapping.combination)):
                raise ValueError("Invalid mapping proof")
        request = ScoreConversionRequest(collection_id=collection_id, year=rule.year,
            source_method=rule.source_method, combination=combination or rule.mappings[0].combination,
            score=score if score is not None else rule.points[0].source.value)
        result = calculate_verified_score(request, rule, blocks, snapshot)
    except (ValueError, KeyError) as exc:
        raise AppException("Bảng, ánh xạ hoặc bằng chứng không khớp nguồn đang xuất bản.", code="SCORE_EVIDENCE_INVALID", status_code=422) from exc
    return result.model_copy(update={"is_preview": True,
        "message": "Kết quả tính thử; không đồng nghĩa quy tắc đã được duyệt hoặc kích hoạt."})


def overlaps(left: ConversionDefinition, right: ConversionDefinition) -> bool:
    from app.modules.rag.score_conversion import normalized

    return (left.year == right.year
        and bool({normalized(x) for x in [left.source_method, *left.source_aliases]} & {normalized(x) for x in [right.source_method, *right.source_aliases]})
        and bool({normalized(x.combination) for x in left.mappings} & {normalized(x.combination) for x in right.mappings}))


async def transition(db: AsyncSession, actor: AuthActor, collection_id: str,
                      rule_id: str, command: RuleAction) -> RuleRegistry:
    require(actor, "ai.knowledge.review")
    col = await load_collection(db, collection_id, lock=True)
    state = registry(col.collection_metadata or {})
    if check_command(state, command, actor, rule_id):
        return state
    item = find_rule(state, rule_id)
    transitions = {"approve": ({"draft"}, "approved"), "activate": ({"approved"}, "active"),
                   "deactivate": ({"active"}, "approved"), "revoke": ({"draft", "approved", "active"}, "revoked")}
    allowed, target = transitions[command.action]
    if item.status not in allowed:
        raise AppException("Trạng thái quy tắc không cho phép thao tác này.", code="SCORE_RULE_TRANSITION_INVALID", status_code=409)
    if command.action in {"approve", "activate"}:
        await validate_definition(db, collection_id, item.definition, actor)
    if command.action == "activate" and any(other.status == "active" and overlaps(item.definition, other.definition) for other in state.items):
        raise AppException("Đã có quy tắc hoạt động trùng phạm vi; cần ngừng dùng bản cũ trước.", code="SCORE_RULE_OVERLAP", status_code=409)
    if command.action == "approve":
        item.reviewed_by, item.reviewed_at = actor.actor_id, datetime.now(UTC).isoformat()
    item.status = target
    return await persist(db, col, state, actor, rule_id, command)


async def preview(db: AsyncSession, actor: AuthActor, collection_id: str,
                   rule_id: str, body: RulePreview) -> ScoreConversionResult:
    require(actor, "ai.knowledge.view")
    state = await list_rules(db, actor, collection_id)
    if body.expected_version != state.version:
        raise AppException("Quy tắc đã thay đổi; tải lại trước khi tính thử.", code="SCORE_RULE_VERSION_CONFLICT", status_code=409)
    item = find_rule(state, rule_id)
    if item.status == "revoked":
        raise AppException("Quy tắc đã thu hồi.", code="SCORE_RULE_REVOKED", status_code=409)
    return await validate_definition(db, collection_id, item.definition, actor, score=body.score, combination=body.combination)
