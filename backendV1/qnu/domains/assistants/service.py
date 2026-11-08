from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.assistants.schemas import AssistantConfig, AssistantReadiness, AssistantUpdate
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexInput, IndexRun, IndexSync
from qnu.domains.knowledge.index.snapshots import current_snapshot, publication_identity
from qnu.domains.knowledge.policies.access import load_collection
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.lifecycle.effects import cancel_related_jobs
from qnu.domains.lifecycle.guards import require_available, visible
from qnu.domains.modelops.public_api import assert_provider_allowed
from qnu.domains.ocr.ids import new_id
from qnu.domains.rag.policy import RagPolicy
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


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
    await load_collection(db, workspace_id, row.collection_id)
    return row


async def list_assistants(
    db: AsyncSession, actor: AuthActor, workspace_id: str, limit: int, offset: int
) -> list[Assistant]:
    await resolve_workspace_access(db, actor, workspace_id)
    return list(
        (
            await db.scalars(
                select(Assistant)
                .where(Assistant.workspace_id == workspace_id)
                .where(
                    visible("assistant", Assistant.id),
                    visible("collection", Assistant.collection_id),
                )
                .order_by(Assistant.created_at, Assistant.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )


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
    await load_collection(db, workspace_id, req.collection_id)
    if assistant_id:
        existing = await get_assistant(db, actor, workspace_id, assistant_id, write=True)
        if "max_output_tokens" not in req.model_fields_set:
            req = req.model_copy(update={"max_output_tokens": existing.max_output_tokens})
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
        await assert_provider_allowed(
            db, actor, workspace_id, "rerank", req.rag_policy.rerank_provider_id
        )
    if req.rag_policy.verification_mode != "off":
        await assert_provider_allowed(
            db,
            actor,
            workspace_id,
            "chat",
            req.rag_policy.verification_provider_id or req.chat_provider_id,
        )
    cancelled_turns = 0
    if assistant_id:
        row = await get_assistant(db, actor, workspace_id, assistant_id, write=True)
        if not isinstance(req, AssistantUpdate) or row.revision != req.expected_revision:
            raise Conflict("Cấu hình trợ lý đã thay đổi.", code="assistant_revision_conflict")
        if req.collection_id != row.collection_id:
            raise Conflict(
                "Tạo trợ lý mới khi đổi kho tri thức.", code="assistant_collection_immutable"
            )
        if not req.is_active:
            cancelled_turns = await cancel_related_jobs(db, workspace_id, "assistant", row)
        # Pausing and resuming the same configuration must not strand its conversations.
        if any(
            (
                RagPolicy.model_validate(row.rag_policy).model_dump(mode="json")
                if key == "rag_policy"
                else getattr(row, key)
            )
            != value
            for key, value in req.model_dump(
                mode="json", exclude={"expected_revision", "is_active"}
            ).items()
        ):
            row.revision += 1
    else:
        row = Assistant(
            id=new_id("ast"), workspace_id=workspace_id, created_by=actor_ref(actor), revision=1
        )
        db.add(row)
    for key, value in req.model_dump(mode="json", exclude={"expected_revision"}).items():
        setattr(row, key, value)
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
            "provider_id": row.chat_provider_id,
            "cancelled_turns": cancelled_turns,
        },
    )
    await db.commit()
    await db.refresh(row)
    return row


async def assistant_readiness(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    assistant_id: str,
) -> AssistantReadiness:
    assistant = await get_assistant(db, actor, workspace_id, assistant_id)
    collection = await load_collection(db, workspace_id, assistant.collection_id)
    published = []
    try:
        published = await current_snapshot(db, blob, actor, workspace_id, assistant.collection_id)
    except AppException as exc:
        if exc.code != "index_no_published_documents":
            raise
    active = await db.scalar(
        select(IndexRun).where(
            IndexRun.workspace_id == workspace_id,
            IndexRun.collection_id == assistant.collection_id,
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
    sync = await db.get(IndexSync, assistant.collection_id)
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

    return AssistantReadiness(
        assistant_id=assistant.id,
        collection_id=assistant.collection_id,
        collection_name=collection.name,
        status=status,
        published_document_count=published_count,
        served_document_count=served,
        index_run_id=active.id if active is not None else None,
        index_generation=active.generation if active is not None else None,
        sync_status=sync_status,
        sync_error_code=sync_error,
        checked_at=datetime.now(UTC),
    )
