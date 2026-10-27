from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.assistants.schemas import AssistantConfig, AssistantUpdate
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.policies.access import load_collection
from qnu.domains.lifecycle.effects import cancel_related_jobs
from qnu.domains.lifecycle.guards import require_available, visible
from qnu.domains.modelops.public_api import assert_provider_allowed
from qnu.domains.ocr.ids import new_id
from qnu.domains.rag.policy import RagPolicy
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound


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
