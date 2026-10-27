"""Owner checks precede conversation or turn reads, including platform administrators."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.conversations.models import Conversation, ConversationTurn
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.policies.access import load_collection
from qnu.domains.lifecycle.guards import require_available
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.platform.errors import Conflict, EntityNotFound


async def owned(
    db: AsyncSession, actor: AuthActor, workspace_id: str, conversation_id: str
) -> Conversation:
    await resolve_workspace_access(db, actor, workspace_id, for_update=True)
    row = await db.scalar(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
            Conversation.owner_ref == actor_ref(actor),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy hội thoại.", code="conversation_not_found")
    await require_available(db, workspace_id, "conversation", conversation_id)
    await require_available(db, workspace_id, "assistant", row.assistant_id)
    await load_collection(db, workspace_id, row.collection_id)
    return row


async def current_assistant(db: AsyncSession, conversation: Conversation) -> Assistant:
    await require_available(db, conversation.workspace_id, "assistant", conversation.assistant_id)
    row = await db.scalar(
        select(Assistant)
        .where(
            Assistant.id == conversation.assistant_id,
            Assistant.workspace_id == conversation.workspace_id,
        )
        .execution_options(populate_existing=True)
    )
    if row is None or not row.is_active:
        raise Conflict("Trợ lý đã tạm dừng.", code="assistant_inactive")
    if row.revision != conversation.assistant_revision:
        raise Conflict(
            "Cấu hình trợ lý đã thay đổi; cần hội thoại mới.", code="conversation_assistant_changed"
        )
    if conversation.status != "active":
        raise Conflict("Hội thoại đã lưu trữ.", code="conversation_archived")
    return row


async def checkpoint(db: AsyncSession, actor: AuthActor, turn: ConversationTurn) -> None:
    conversation = await owned(db, actor, turn.workspace_id, turn.conversation_id)
    await current_assistant(db, conversation)
    row = await db.scalar(
        select(ConversationTurn)
        .where(
            ConversationTurn.id == turn.id,
            ConversationTurn.status == "running",
            ConversationTurn.lease_expires_at > utcnow(),
        )
        .with_for_update()
    )
    if row is None:
        raise Conflict("Lượt hỏi đã hết quyền thực thi.", code="conversation_turn_expired")
