"""Rebuild conversation scope from existing messages without a second state database."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.conversations.models import ConversationMessageModel, ConversationThreadModel
from app.modules.rag.intent_rules import is_meta, social_kind


async def recent_knowledge_history(db: AsyncSession, conversation_id: str, assistant_code: str | None,
                                   limit: int = 6, scope_since: datetime | None = None) -> list[dict[str, str]]:
    if not conversation_id:
        return []
    try:
        thread = (await db.execute(select(ConversationThreadModel).where(
            ConversationThreadModel.id == conversation_id))).scalar_one_or_none()
        if thread is None:
            return []
        if assistant_code and thread.assistant_code != assistant_code:
            raise AppException('Phiên hội thoại không thuộc trợ lý hiện tại.', code='conversation_not_found', status_code=404)
        rows = []
        for page in range(8):
            stmt = select(ConversationMessageModel).where(ConversationMessageModel.thread_id == conversation_id)
            if isinstance(scope_since, datetime):
                stmt = stmt.where(ConversationMessageModel.created_at >= scope_since.replace(tzinfo=None))
            batch = list((await db.scalars(stmt.order_by(ConversationMessageModel.created_at.desc(),
                ConversationMessageModel.id.desc()).offset(page * 32).limit(32))).all())
            rows.extend(batch)
            useful = [r for r in rows if r.sender == 'user' and r.text and not social_kind(r.text) and not is_meta(r.text)]
            if len(useful) >= limit or len(batch) < 32:
                break
        history = []
        keep = False
        for row in reversed(rows):
            if row.sender == 'user':
                keep = bool(row.text) and not social_kind(row.text) and not is_meta(row.text)
            if keep and row.text:
                history.append({'role': 'user' if row.sender == 'user' else 'assistant', 'content': row.text})
        return history[-(limit * 2):]
    except AppException:
        raise
    except Exception as exc:
        raise AppException('Không đọc được ngữ cảnh hội thoại. Vui lòng thử lại.',
            code='CONVERSATION_HISTORY_UNAVAILABLE', status_code=503) from exc
