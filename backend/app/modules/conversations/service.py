"""Business logic and database service for QNU Conversations & Staff Handoff."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import EntityNotFoundError
from app.modules.conversations.models import ConversationMessageModel, ConversationThreadModel
from app.modules.conversations.schemas import (
    ConversationCreateMessageRequest,
    ConversationMessageResponse,
    ConversationThreadDetailResponse,
    ConversationThreadItemResponse,
)

logger = logging.getLogger(__name__)

HANDOFF_KEYWORDS: Sequence[str] = (
    "gặp người thật",
    "gặp tư vấn viên",
    "chuyên viên tư vấn",
    "liên hệ cán bộ",
    "gặp trực tiếp",
    "người hỗ trợ",
    "hotline",
)


def _detect_handoff_intent(text: str) -> bool:
    lower = text.casefold()
    return any(k in lower for k in HANDOFF_KEYWORDS)


def _to_message_dto(m: ConversationMessageModel) -> ConversationMessageResponse:
    return ConversationMessageResponse(
        id=m.id,
        thread_id=m.thread_id,
        sender=m.sender,  # type: ignore[arg-type]
        text=m.text,
        created_at=m.created_at,
    )


def _to_thread_dto(t: ConversationThreadModel) -> ConversationThreadItemResponse:
    return ConversationThreadItemResponse(
        id=t.id,
        assistant_code=t.assistant_code,
        assistant_name=t.assistant_name,
        user_name=t.user_name,
        user_email=t.user_email,
        last_message=t.last_message,
        status=t.status,  # type: ignore[arg-type]
        assigned_to=t.assigned_to,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


class ConversationService:
    """Service handling conversations, student questions, and staff handoff transfers."""

    async def list_threads(
        self,
        db: AsyncSession,
        *,
        assistant_code: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationThreadItemResponse]:
        query = select(ConversationThreadModel).order_by(ConversationThreadModel.updated_at.desc())

        if assistant_code:
            query = query.where(ConversationThreadModel.assistant_code == assistant_code)
        if status and status != "all":
            query = query.where(ConversationThreadModel.status == status)
        if search and search.strip():
            pat = f"%{search.strip().casefold()}%"
            query = query.where(
                or_(
                    func.lower(ConversationThreadModel.user_name).like(pat),
                    func.lower(ConversationThreadModel.user_email).like(pat),
                    func.lower(ConversationThreadModel.last_message).like(pat),
                )
            )

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        threads = list(result.scalars().all())
        return [_to_thread_dto(t) for t in threads]

    async def get_thread_detail(
        self, db: AsyncSession, thread_id: str
    ) -> ConversationThreadDetailResponse:
        query = (
            select(ConversationThreadModel)
            .options(selectinload(ConversationThreadModel.messages))
            .where(ConversationThreadModel.id == thread_id)
        )
        res = await db.execute(query)
        thread = res.scalar_one_or_none()
        if not thread:
            raise EntityNotFoundError(
                f"Phiên hội thoại '{thread_id}' không tồn tại.",
                details={"thread_id": thread_id},
            )

        return ConversationThreadDetailResponse(
            id=thread.id,
            assistant_code=thread.assistant_code,
            assistant_name=thread.assistant_name,
            user_name=thread.user_name,
            user_email=thread.user_email,
            last_message=thread.last_message,
            status=thread.status,  # type: ignore[arg-type]
            assigned_to=thread.assigned_to,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            messages=[_to_message_dto(m) for m in thread.messages],
        )

    async def record_message(
        self, db: AsyncSession, req: ConversationCreateMessageRequest
    ) -> ConversationMessageResponse:
        now_ts = datetime.now(UTC).replace(tzinfo=None)
        thread: ConversationThreadModel | None = None

        if req.thread_id:
            t_res = await db.execute(
                select(ConversationThreadModel).where(
                    ConversationThreadModel.id == req.thread_id
                )
            )
            thread = t_res.scalar_one_or_none()

        should_handoff = req.request_handoff or _detect_handoff_intent(req.text)

        if not thread:
            thread_id = req.thread_id or f"conv_{uuid.uuid4().hex[:12]}"
            thread = ConversationThreadModel(
                id=thread_id,
                assistant_code=req.assistant_code,
                assistant_name=req.assistant_name or f"Trợ lý {req.assistant_code}",
                user_name=req.user_name or "Thí sinh / Sinh viên",
                user_email=req.user_email,
                last_message=req.text,
                status="handoff_requested" if should_handoff else "ai_active",
                assigned_to=None,
                created_at=now_ts,
                updated_at=now_ts,
            )
            db.add(thread)
        else:
            thread.last_message = req.text
            thread.updated_at = now_ts
            if should_handoff and thread.status == "ai_active":
                thread.status = "handoff_requested"
            if req.user_name and thread.user_name == "Thí sinh / Sinh viên":
                thread.user_name = req.user_name
            if req.user_email and not thread.user_email:
                thread.user_email = req.user_email

        msg = ConversationMessageModel(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            thread_id=thread.id,
            sender=req.sender,
            text=req.text,
            created_at=now_ts,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        logger.info("Recorded message sender=%s in thread=%s", req.sender, thread.id)
        return _to_message_dto(msg)

    async def reply_from_staff(
        self, db: AsyncSession, thread_id: str, text: str, staff_name: str | None = None
    ) -> ConversationMessageResponse:
        res = await db.execute(
            select(ConversationThreadModel).where(ConversationThreadModel.id == thread_id)
        )
        thread = res.scalar_one_or_none()
        if not thread:
            raise EntityNotFoundError(
                f"Phiên hội thoại '{thread_id}' không tồn tại.",
                details={"thread_id": thread_id},
            )

        now_ts = datetime.now(UTC).replace(tzinfo=None)
        staff_display = staff_name or "Chuyên viên QNU"

        msg = ConversationMessageModel(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            thread_id=thread.id,
            sender="agent",
            text=text,
            created_at=now_ts,
        )
        db.add(msg)

        thread.status = "staff_claimed"
        thread.assigned_to = staff_display
        thread.last_message = text
        thread.updated_at = now_ts

        await db.commit()
        await db.refresh(msg)
        logger.info("Staff %s replied to thread %s", staff_display, thread.id)
        return _to_message_dto(msg)

    async def update_thread_status(
        self,
        db: AsyncSession,
        thread_id: str,
        status: str,
        assigned_to: str | None = None,
    ) -> ConversationThreadItemResponse:
        res = await db.execute(
            select(ConversationThreadModel).where(ConversationThreadModel.id == thread_id)
        )
        thread = res.scalar_one_or_none()
        if not thread:
            raise EntityNotFoundError(
                f"Phiên hội thoại '{thread_id}' không tồn tại.",
                details={"thread_id": thread_id},
            )

        thread.status = status
        if assigned_to is not None:
            thread.assigned_to = assigned_to
        thread.updated_at = datetime.now(UTC).replace(tzinfo=None)

        await db.commit()
        await db.refresh(thread)
        logger.info("Updated thread %s status to %s", thread.id, status)
        return _to_thread_dto(thread)


conversation_service = ConversationService()
