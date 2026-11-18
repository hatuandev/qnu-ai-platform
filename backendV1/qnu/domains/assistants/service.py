from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.answer_review.models import AnswerReview
from qnu.domains.assistants.models import Assistant, AssistantCollection
from qnu.domains.assistants.schemas import (
    AssistantCollectionReadiness,
    AssistantConfig,
    AssistantRagPolicy,
    AssistantReadiness,
    AssistantUpdate,
)
from qnu.domains.conversations.models import Conversation, ConversationTurn
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexInput, IndexRun, IndexSync
from qnu.domains.knowledge.index.snapshots import current_snapshot, publication_identity
from qnu.domains.knowledge.policies.access import load_collection
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.lifecycle.effects import cancel_related_jobs
from qnu.domains.lifecycle.guards import require_available, visible
from qnu.domains.lifecycle.models import ResourceState
from qnu.domains.modelops.public_api import assert_provider_allowed
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


async def collection_bindings(
    db: AsyncSession, workspace_id: str, assistant_ids: list[str]
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    if not assistant_ids:
        return grouped
    rows = (
        await db.execute(
            select(AssistantCollection.assistant_id, AssistantCollection.collection_id)
            .where(
                AssistantCollection.workspace_id == workspace_id,
                AssistantCollection.assistant_id.in_(assistant_ids),
            )
            .order_by(AssistantCollection.position)
        )
    ).all()
    for assistant_id, collection_id in rows:
        grouped.setdefault(assistant_id, []).append(collection_id)
    return grouped


async def _attach_bindings(
    db: AsyncSession, workspace_id: str, rows: list[Assistant]
) -> list[Assistant]:
    grouped = await collection_bindings(db, workspace_id, [row.id for row in rows])
    for row in rows:
        bound = grouped.get(row.id)
        row.collection_ids = (
            bound if bound is not None else ([row.collection_id] if row.collection_id else [])
        )
    return rows


async def _replace_bindings(
    db: AsyncSession,
    row: Assistant,
    workspace_id: str,
    collection_ids: list[str],
    stored_ids: list[str],
) -> None:
    if collection_ids == stored_ids:
        return
    existing = {
        item.collection_id: item
        for item in (
            await db.scalars(
                select(AssistantCollection).where(
                    AssistantCollection.workspace_id == workspace_id,
                    AssistantCollection.assistant_id == row.id,
                )
            )
        ).all()
    }
    for collection_id, item in existing.items():
        if collection_id not in collection_ids:
            await db.delete(item)
    for position, collection_id in enumerate(collection_ids):
        item = existing.get(collection_id)
        if item is None:
            db.add(
                AssistantCollection(
                    assistant_id=row.id,
                    workspace_id=workspace_id,
                    collection_id=collection_id,
                    position=position,
                )
            )
        else:
            item.position = position


async def get_assistant(
    db: AsyncSession, actor: AuthActor, workspace_id: str, assistant_id: str, *, write: bool = False
) -> Assistant:
    await resolve_workspace_access(
        db, actor, workspace_id, required_roles=("admin",) if write else None, for_update=True
    )
    row = await db.scalar(
        select(Assistant)
        .where(Assistant.id == assistant_id, Assistant.workspace_id == workspace_id)
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy trợ lý.", code="assistant_not_found")
    await require_available(db, workspace_id, "assistant", assistant_id)
    if row.collection_id:
        await load_collection(db, workspace_id, row.collection_id)
    await _attach_bindings(db, workspace_id, [row])
    return row


def _usable_binding():
    state = (
        select(ResourceState.resource_id)
        .where(
            ResourceState.kind == "collection",
            ResourceState.resource_id == AssistantCollection.collection_id,
            ResourceState.status != "active",
        )
        .correlate(AssistantCollection)
        .exists()
    )
    usable = (
        select(AssistantCollection.collection_id)
        .where(AssistantCollection.assistant_id == Assistant.id, ~state)
        .correlate(Assistant)
        .exists()
    )
    bound = (
        select(AssistantCollection.collection_id)
        .where(AssistantCollection.assistant_id == Assistant.id)
        .correlate(Assistant)
        .exists()
    )
    # An assistant saved before any collection is attached stays listed; it is
    # hidden only when every binding it has is unavailable.
    return or_(~bound, usable)


async def list_assistants(
    db: AsyncSession, actor: AuthActor, workspace_id: str, limit: int, offset: int
) -> list[Assistant]:
    await resolve_workspace_access(db, actor, workspace_id)
    rows = list(
        (
            await db.scalars(
                select(Assistant)
                .where(Assistant.workspace_id == workspace_id)
                .where(
                    visible("assistant", Assistant.id),
                    _usable_binding(),
                )
                .order_by(Assistant.created_at, Assistant.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
    return await _attach_bindings(db, workspace_id, rows)


async def save_assistant(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    req: AssistantConfig,
    assistant_id: str | None = None,
) -> Assistant:
    await resolve_workspace_access(
        db, actor, workspace_id, required_roles=("admin",), for_update=True
    )
    if "collection_ids" in req.model_fields_set:
        # An explicit empty list unbinds every collection; the assistant still
        # saves but cannot serve turns until one is attached again.
        collection_ids = list(getattr(req, "collection_ids", None) or [])
    elif req.collection_id:
        collection_ids = [req.collection_id]
    else:
        collection_ids = []
    for collection_id in collection_ids:
        await load_collection(db, workspace_id, collection_id)
    # The scalar column mirrors the first binding so older readers keep working.
    req = req.model_copy(
        update={"collection_id": collection_ids[0] if collection_ids else None}
    )
    if assistant_id:
        existing = await get_assistant(db, actor, workspace_id, assistant_id, write=True)
        if "max_output_tokens" not in req.model_fields_set:
            req = req.model_copy(update={"max_output_tokens": existing.max_output_tokens})
        if (
            "rag_policy" in req.model_fields_set
            and "guardrail_policy" not in req.rag_policy.model_fields_set
        ):
            # Older FE clients cannot accidentally reset a guardrail they do not expose.
            stored = AssistantRagPolicy.model_validate(existing.rag_policy)
            req = req.model_copy(
                update={
                    "rag_policy": req.rag_policy.model_copy(
                        update={"guardrail_policy": stored.guardrail_policy}
                    )
                }
            )
        if "rag_policy" not in req.model_fields_set:
            # Older FE clients cannot accidentally reset a policy they do not expose.
            try:
                req = type(req).model_validate(
                    {**req.model_dump(mode="json"), "rag_policy": existing.rag_policy}
                )
            except ValidationError as exc:
                raise AppException(
                    "Ngân sách mới không tương thích RAG policy đang lưu; cần cập nhật policy cùng lúc.",
                    code="assistant_rag_policy_invalid",
                    status_code=422,
                ) from exc
    await assert_provider_allowed(db, actor, workspace_id, "chat", req.chat_provider_id)
    if req.rag_policy.retrieval_mode == "hybrid_rerank":
        try:
            await assert_provider_allowed(
                db, actor, workspace_id, "rerank", req.rag_policy.rerank_provider_id
            )
        except Conflict as exc:
            # No rerank model configured: retrieval degrades to hybrid with a
            # trace at query time; a pinned or ungranted provider still fails.
            if exc.code != "model_not_configured":
                raise
    if req.rag_policy.verification_mode != "off":
        await assert_provider_allowed(
            db,
            actor,
            workspace_id,
            "chat",
            req.rag_policy.verification_provider_id or req.chat_provider_id,
        )
    cancelled_turns = 0
    previous_collection_id: str | None = None
    previous_collection_ids: list[str] | None = None
    stored_ids: list[str] = []
    if assistant_id:
        row = await get_assistant(db, actor, workspace_id, assistant_id, write=True)
        if not isinstance(req, AssistantUpdate) or row.revision != req.expected_revision:
            raise Conflict("Cấu hình trợ lý đã thay đổi.", code="assistant_revision_conflict")
        stored_ids = row.collection_ids
        if collection_ids != stored_ids:
            previous_collection_ids = stored_ids
        if (collection_ids[0] if collection_ids else None) != row.collection_id:
            previous_collection_id = row.collection_id
        if not req.is_active:
            cancelled_turns = await cancel_related_jobs(db, workspace_id, "assistant", row)
        # Pausing and resuming the same configuration must not strand its conversations.
        if collection_ids != stored_ids or any(
            (
                AssistantRagPolicy.model_validate(row.rag_policy).model_dump(mode="json")
                if key == "rag_policy"
                else getattr(row, key)
            )
            != value
            for key, value in req.model_dump(
                mode="json", exclude={"expected_revision", "is_active", "collection_ids"}
            ).items()
        ):
            row.revision += 1
    else:
        row = Assistant(
            id=new_id("ast"), workspace_id=workspace_id, created_by=actor_ref(actor), revision=1
        )
        db.add(row)
    for key, value in req.model_dump(
        mode="json", exclude={"expected_revision", "collection_ids"}
    ).items():
        setattr(row, key, value)
    await _replace_bindings(db, row, workspace_id, collection_ids, stored_ids)
    row.updated_at = utcnow()
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="assistant.updated" if assistant_id else "assistant.created",
        detail={
            "assistant_id": row.id,
            "revision": row.revision,
            "collection_id": row.collection_id,
            "collection_ids": collection_ids,
            "previous_collection_id": previous_collection_id,
            "previous_collection_ids": previous_collection_ids,
            "provider_id": row.chat_provider_id,
            "cancelled_turns": cancelled_turns,
        },
    )
    await db.commit()
    await db.refresh(row)
    await _attach_bindings(db, workspace_id, [row])
    return row


async def delete_assistant(
    db: AsyncSession, actor: AuthActor, workspace_id: str, assistant_id: str
) -> dict[str, int]:
    """Permanently removes an assistant, including its trash state and dependent chats.

    Collection purge checks every ``chat_assistants`` row, so a soft-deleted row would
    keep the collection locked forever; this is the only path that frees it. Chat turns,
    conversations and answer reviews reference the assistant with RESTRICT, so they are
    deleted in dependency order inside the same transaction.
    """
    await resolve_workspace_access(
        db, actor, workspace_id, required_roles=("admin",), for_update=True
    )
    row = await db.scalar(
        select(Assistant)
        .where(Assistant.id == assistant_id, Assistant.workspace_id == workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy trợ lý.", code="assistant_not_found")
    cancelled_turns = await cancel_related_jobs(db, workspace_id, "assistant", row)
    conversation_ids = list(
        (
            await db.scalars(
                select(Conversation.id).where(
                    Conversation.workspace_id == workspace_id,
                    Conversation.assistant_id == assistant_id,
                )
            )
        ).all()
    )
    turns_deleted = (
        await db.execute(
            delete(ConversationTurn).where(
                ConversationTurn.workspace_id == workspace_id,
                ConversationTurn.conversation_id.in_(conversation_ids),
            )
        )
    ).rowcount
    reviews_deleted = (
        await db.execute(
            delete(AnswerReview).where(
                AnswerReview.workspace_id == workspace_id,
                AnswerReview.assistant_id == assistant_id,
            )
        )
    ).rowcount
    conversations_deleted = (
        await db.execute(
            delete(Conversation).where(
                Conversation.workspace_id == workspace_id,
                Conversation.assistant_id == assistant_id,
            )
        )
    ).rowcount
    # Lifecycle rows carry no foreign key; remove them explicitly so a restore
    # cannot resurrect a state for an identifier that no longer exists.
    await db.execute(
        delete(ResourceState).where(
            ResourceState.workspace_id == workspace_id,
            ResourceState.kind == "conversation",
            ResourceState.resource_id.in_(conversation_ids),
        )
    )
    await db.execute(
        delete(ResourceState).where(
            ResourceState.workspace_id == workspace_id,
            ResourceState.kind == "assistant",
            ResourceState.resource_id == assistant_id,
        )
    )
    await db.delete(row)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="assistant.deleted",
        detail={
            "assistant_id": assistant_id,
            "revision": row.revision,
            "collection_id": row.collection_id,
            "cancelled_turns": cancelled_turns,
            "conversations_deleted": conversations_deleted,
            "turns_deleted": turns_deleted,
            "answer_reviews_deleted": reviews_deleted,
        },
    )
    await db.commit()
    return {
        "conversations_deleted": conversations_deleted,
        "turns_deleted": turns_deleted,
        "answer_reviews_deleted": reviews_deleted,
        "cancelled_turns": cancelled_turns,
    }


async def _collection_readiness(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, workspace_id: str, collection_id: str
) -> AssistantCollectionReadiness:
    collection = await load_collection(db, workspace_id, collection_id)
    published = []
    try:
        published = await current_snapshot(db, blob, actor, workspace_id, collection_id)
    except AppException as exc:
        if exc.code != "index_no_published_documents":
            raise
    active = await db.scalar(
        select(IndexRun).where(
            IndexRun.workspace_id == workspace_id,
            IndexRun.collection_id == collection_id,
            IndexRun.is_active.is_(True),
            IndexRun.status == "completed",
        )
    )
    served = 0
    matches = False
    if active is not None and published:
        bindings = {
            tuple(row)
            for row in (
                await db.execute(
                    select(
                        IndexInput.document_id,
                        IndexInput.version_id,
                        IndexInput.publication_decision_id,
                        IndexInput.bundle_sha256,
                        IndexInput.version_state,
                    ).where(IndexInput.run_id == active.id)
                )
            ).all()
        }
        identities = [publication_identity(item) for item in published]
        served = sum(
            1
            for item in identities
            if (
                item["document_id"],
                item["version_id"],
                item["publication_decision_id"],
                item["bundle_sha256"],
                item["version_state"],
            )
            in bindings
        )
        matches = active.input_sha256 == digest(identities)
    sync = await db.get(IndexSync, collection_id)
    sync_status = sync.status if sync is not None else "not_requested"
    sync_error = sync.error_code if sync is not None else None
    published_count = len(published)

    if published_count == 0:
        status = "empty"
    elif active is not None and matches:
        # The active generation already carries the exact current publication;
        # a lagging outbox row cannot make that content stale.
        status = "ready"
    elif sync_status in {"pending", "building"}:
        status = "syncing"
    elif sync_status in {"failed", "uncertain"}:
        status = sync_status
    elif active is None:
        status = "not_indexed"
    else:
        status = "outdated"

    return AssistantCollectionReadiness(
        collection_id=collection_id,
        collection_name=collection.name,
        status=status,
        published_document_count=published_count,
        served_document_count=served,
        index_run_id=active.id if active is not None else None,
        index_generation=active.generation if active is not None else None,
        sync_status=sync_status,
        sync_error_code=sync_error,
    )


async def assistant_readiness(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    assistant_id: str,
) -> AssistantReadiness:
    assistant = await get_assistant(db, actor, workspace_id, assistant_id)
    if not assistant.collection_ids:
        return AssistantReadiness(
            assistant_id=assistant.id,
            status="empty",
            published_document_count=0,
            served_document_count=0,
            sync_status="not_requested",
            collections=[],
            checked_at=datetime.now(UTC),
        )
    entries = [
        await _collection_readiness(db, blob, actor, workspace_id, collection_id)
        for collection_id in assistant.collection_ids
    ]
    first = entries[0]
    return AssistantReadiness(
        assistant_id=assistant.id,
        collection_id=first.collection_id,
        collection_name=first.collection_name,
        status=first.status,
        published_document_count=first.published_document_count,
        served_document_count=first.served_document_count,
        index_run_id=first.index_run_id,
        index_generation=first.index_generation,
        sync_status=first.sync_status,
        sync_error_code=first.sync_error_code,
        collections=entries,
        checked_at=datetime.now(UTC),
    )
