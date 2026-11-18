"""Owned conversation lifecycle and durable turn reservation, without model calls."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.schemas import AssistantConfig, AssistantRagPolicy
from qnu.domains.assistants.service import get_assistant
from qnu.domains.conversations.access import current_assistant, owned
from qnu.domains.conversations.models import Conversation, ConversationTurn
from qnu.domains.conversations.schemas import ConversationCreate, ConversationUpdate, TurnRequest
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.metadata import merge_scope, scope_conflicts
from qnu.domains.knowledge.publication.access import document
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.lifecycle.effects import cancel_related_jobs
from qnu.domains.lifecycle.guards import visible
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict, EntityNotFound


async def _require_document(
    db: AsyncSession, workspace_id: str, collection_ids: list[str], document_id: str
) -> None:
    """A pinned document only has to exist in one of the assistant's collections."""
    for collection_id in collection_ids:
        try:
            await document(db, workspace_id, collection_id, document_id)
        except EntityNotFound as exc:
            if exc.code != "compiled_document_not_found":
                raise
            continue
        return
    raise EntityNotFound("Không tìm thấy tài liệu biên soạn.", code="compiled_document_not_found")


async def create(
    db: AsyncSession, actor: AuthActor, workspace_id: str, req: ConversationCreate
) -> Conversation:
    assistant = await get_assistant(db, actor, workspace_id, req.assistant_id)
    if not assistant.is_active:
        raise Conflict("Trợ lý đã tạm dừng.", code="assistant_inactive")
    collection_ids = list(
        dict.fromkeys(
            item
            for item in [assistant.collection_id, *(assistant.collection_ids or [])]
            if item
        )
    )
    if not collection_ids:
        raise Conflict(
            "Trợ lý chưa gắn kho tri thức nên chưa thể bắt đầu hội thoại.",
            code="assistant_no_collections",
        )
    for document_id in req.document_ids or []:
        await _require_document(db, workspace_id, collection_ids, document_id)
    snapshot = AssistantConfig.model_validate(assistant, from_attributes=True).model_dump(
        mode="json"
    )
    snapshot["collection_ids"] = collection_ids
    row = Conversation(
        id=new_id("cnv"),
        workspace_id=workspace_id,
        collection_id=collection_ids[0],
        assistant_id=assistant.id,
        assistant_revision=assistant.revision,
        assistant_snapshot=snapshot,
        owner_ref=actor_ref(actor),
        title=req.title,
        document_ids=req.document_ids,
        last_turn_no=0,
    )
    db.add(row)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="conversation.created",
        detail={"conversation_id": row.id, "assistant_id": assistant.id},
    )
    await db.commit()
    await db.refresh(row)
    return row


async def listing(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    limit: int,
    offset: int,
    assistant_id: str | None = None,
) -> list[Conversation]:
    await resolve_workspace_access(db, actor, workspace_id)
    query = select(Conversation).where(
        Conversation.workspace_id == workspace_id,
        Conversation.owner_ref == actor_ref(actor),
        visible("conversation", Conversation.id),
        visible("assistant", Conversation.assistant_id),
        visible("collection", Conversation.collection_id),
    )
    if assistant_id is not None:
        query = query.where(Conversation.assistant_id == assistant_id)
    return list(
        (
            await db.scalars(
                query.order_by(Conversation.updated_at.desc(), Conversation.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )


async def update(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    conversation_id: str,
    req: ConversationUpdate,
) -> Conversation:
    row = await owned(db, actor, workspace_id, conversation_id)
    cancelled_turns = (
        await cancel_related_jobs(db, workspace_id, "conversation", row)
        if req.status == "archived"
        else 0
    )
    row.title, row.status, row.updated_at = req.title, req.status, utcnow()
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="conversation.updated",
        detail={
            "conversation_id": row.id,
            "status": row.status,
            "cancelled_turns": cancelled_turns,
        },
    )
    await db.commit()
    return row


async def expire(db: AsyncSession, conversation: Conversation) -> None:
    rows = list(
        (
            await db.scalars(
                select(ConversationTurn)
                .where(
                    ConversationTurn.conversation_id == conversation.id,
                    ConversationTurn.status == "running",
                    ConversationTurn.lease_expires_at <= utcnow(),
                )
                .with_for_update()
            )
        ).all()
    )
    for row in rows:
        row.status, row.error_code, row.finished_at = (
            "uncertain",
            "conversation_turn_interrupted",
            utcnow(),
        )
    await db.flush()


async def reserve_turn(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    conversation_id: str,
    req: TurnRequest,
    key: str,
) -> tuple[Conversation, ConversationTurn, bool]:
    conversation = await owned(db, actor, workspace_id, conversation_id)
    await current_assistant(db, conversation)
    await expire(db, conversation)
    fingerprint = digest(
        req.model_dump(
            mode="json", exclude={"metadata_filter"} if req.metadata_filter is None else set()
        )
    )
    old = await db.scalar(
        select(ConversationTurn).where(
            ConversationTurn.conversation_id == conversation.id,
            ConversationTurn.idempotency_key == key,
        )
    )
    if old is not None:
        if old.request_sha256 != fingerprint:
            raise Conflict("Key đã dùng cho câu hỏi khác.", code="idempotency_conflict")
        await db.commit()
        return conversation, old, False
    if await db.scalar(
        select(ConversationTurn.id).where(
            ConversationTurn.conversation_id == conversation.id,
            ConversationTurn.status == "running",
        )
    ):
        raise Conflict("Hội thoại đang xử lý một lượt hỏi.", code="conversation_busy")
    if req.expected_turn_no != conversation.last_turn_no:
        raise Conflict(
            "Lịch sử đã thay đổi; tải lại hội thoại.", code="conversation_sequence_conflict"
        )
    conversation.last_turn_no += 1
    conversation.updated_at = utcnow()
    policy = AssistantRagPolicy.model_validate(
        conversation.assistant_snapshot.get("rag_policy", {})
    )
    fixed_scope = policy.metadata_filter.model_dump(mode="json", exclude_none=True)
    previous = await db.scalar(
        select(ConversationTurn)
        .where(
            ConversationTurn.conversation_id == conversation.id,
            ConversationTurn.status == "completed",
        )
        .order_by(ConversationTurn.turn_no.desc())
        .limit(1)
    )
    scope = merge_scope(fixed_scope, (previous.metadata_filter or {}) if previous else {})
    if req.metadata_filter is not None:
        requested = req.metadata_filter.model_dump(mode="json", exclude_none=True)
        if scope_conflicts(fixed_scope, requested):
            raise Conflict(
                "Câu hỏi mâu thuẫn phạm vi cố định của trợ lý.", code="conversation_scope_conflict"
            )
        scope = merge_scope(scope, requested)
        if len(scope.get("attributes", {})) > 20:
            raise Conflict(
                "Phạm vi hội thoại có quá nhiều thuộc tính.", code="query_scope_too_large"
            )
    turn = ConversationTurn(
        id=new_id("trn"),
        workspace_id=workspace_id,
        collection_id=conversation.collection_id,
        conversation_id=conversation.id,
        turn_no=conversation.last_turn_no,
        idempotency_key=key,
        request_sha256=fingerprint,
        question=req.question,
        metadata_filter=scope,
        status="running",
        history_turn_ids=[],
        lease_expires_at=utcnow()
        + timedelta(seconds=get_settings().CONVERSATION_TURN_LEASE_SECONDS),
    )
    db.add(turn)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="conversation.turn_requested",
        detail={"conversation_id": conversation.id, "turn_id": turn.id, "turn_no": turn.turn_no},
    )
    await db.commit()
    return conversation, turn, True
