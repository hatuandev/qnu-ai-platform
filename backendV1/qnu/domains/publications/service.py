"""Admin publication view, upsert and usage stats; enabling requires a ready assistant."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.assistants.service import assistant_readiness, get_assistant
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.ocr.ids import new_id
from qnu.domains.publications.models import (
    AssistantPublication,
    AssistantPublicationQuestion,
    AssistantPublicationStat,
)
from qnu.domains.publications.public_service import budget_used_today, business_day
from qnu.domains.publications.schemas import (
    PublicationResponse,
    PublicationStatDay,
    PublicationStatsResponse,
    PublicationStatTotals,
    PublicationUnansweredQuestion,
    PublicationUpdate,
)
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict
from qnu.ports.blob_store import BlobStore

DEFAULT_TURNS = 15
TOP_QUESTIONS_LIMIT = 10


def _view(row: AssistantPublication | None, readiness: str) -> PublicationResponse:
    return PublicationResponse(
        configured=row is not None,
        enabled=bool(row and row.enabled),
        slug=row.slug if row else None,
        display_name=row.display_name if row else "",
        welcome_message=row.welcome_message if row else "",
        starter_prompts=list(row.starter_prompts) if row else [],
        max_turns_per_session=row.max_turns_per_session if row else DEFAULT_TURNS,
        daily_token_budget=row.daily_token_budget if row else None,
        revision=row.revision if row else 0,
        updated_by=row.updated_by if row else None,
        updated_at=row.updated_at if row else None,
        public_path=f"/chatbot/{row.slug}" if row else None,
        system_enabled=get_settings().PUBLIC_CHATBOTS_ENABLED,
        readiness=readiness,
    )


async def _row(
    db: AsyncSession, workspace_id: str, assistant_id: str, *, lock: bool = False
) -> AssistantPublication | None:
    stmt = (
        select(AssistantPublication)
        .where(
            AssistantPublication.assistant_id == assistant_id,
            AssistantPublication.workspace_id == workspace_id,
        )
        .execution_options(populate_existing=True)
    )
    if lock:
        stmt = stmt.with_for_update()
    return await db.scalar(stmt)


async def publication_view(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    assistant_id: str,
) -> PublicationResponse:
    await get_assistant(db, actor, workspace_id, assistant_id)
    readiness = await assistant_readiness(db, blob, actor, workspace_id, assistant_id)
    return _view(await _row(db, workspace_id, assistant_id), readiness.status)


async def save_publication(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    assistant_id: str,
    req: PublicationUpdate,
) -> PublicationResponse:
    assistant: Assistant = await get_assistant(db, actor, workspace_id, assistant_id, write=True)
    readiness = await assistant_readiness(db, blob, actor, workspace_id, assistant_id)
    existing = await _row(db, workspace_id, assistant_id, lock=True)
    turning_on = req.enabled and (existing is None or not existing.enabled)
    if turning_on and readiness.status != "ready":
        raise Conflict(
            "Trợ lý chưa sẵn sàng phục vụ nên chưa thể công khai."
            " Hãy xuất bản nguồn và đợi đánh chỉ mục hoàn tất.",
            code="publication_not_ready",
        )
    holder = await db.scalar(
        select(AssistantPublication.id)
        .where(
            AssistantPublication.slug == req.slug,
            AssistantPublication.assistant_id != assistant_id,
        )
        .execution_options(populate_existing=True)
    )
    if holder is not None:
        raise Conflict(
            "Đường dẫn công khai đã được dùng cho trợ lý khác.", code="publication_slug_taken"
        )
    if existing is None:
        if req.expected_revision is not None:
            raise Conflict(
                "Cấu hình công khai đã thay đổi ở nơi khác; hãy tải lại.",
                code="publication_revision_conflict",
            )
        row = AssistantPublication(
            id=new_id("pub"),
            assistant_id=assistant_id,
            workspace_id=workspace_id,
            slug=req.slug,
            display_name=req.display_name,
            welcome_message=req.welcome_message,
            starter_prompts=req.starter_prompts,
            max_turns_per_session=req.max_turns_per_session,
            daily_token_budget=req.daily_token_budget,
            enabled=req.enabled,
            revision=1,
            updated_by=actor_ref(actor),
        )
        db.add(row)
        action = "assistant_publication.created"
    else:
        if req.expected_revision != existing.revision:
            raise Conflict(
                "Cấu hình công khai đã thay đổi ở nơi khác; hãy tải lại.",
                code="publication_revision_conflict",
            )
        row = existing
        turning_off = row.enabled and not req.enabled
        row.slug = req.slug
        row.display_name = req.display_name
        row.welcome_message = req.welcome_message
        row.starter_prompts = req.starter_prompts
        row.max_turns_per_session = req.max_turns_per_session
        row.daily_token_budget = req.daily_token_budget
        row.enabled = req.enabled
        row.revision += 1
        row.updated_by = actor_ref(actor)
        row.updated_at = utcnow()
        if turning_on:
            action = "assistant_publication.enabled"
        elif turning_off:
            action = "assistant_publication.disabled"
        else:
            action = "assistant_publication.updated"
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action=action,
        detail={
            "assistant_id": assistant.id,
            "publication_id": row.id,
            "slug": row.slug,
            "enabled": row.enabled,
            "revision": row.revision,
        },
    )
    await db.commit()
    return _view(row, readiness.status)


async def publication_stats(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    assistant_id: str,
    days: int,
) -> PublicationStatsResponse:
    await get_assistant(db, actor, workspace_id, assistant_id)
    row = await _row(db, workspace_id, assistant_id)
    if row is None:
        return PublicationStatsResponse(
            configured=False,
            days=days,
            totals=PublicationStatTotals(
                sessions=0, turns=0, insufficient_turns=0, error_turns=0, tokens=0
            ),
            daily=[],
            budget_limit=None,
            budget_used_today=0,
            top_questions=[],
        )
    start = business_day() - timedelta(days=days - 1)
    stored = (
        await db.scalars(
            select(AssistantPublicationStat)
            .where(
                AssistantPublicationStat.publication_id == row.id,
                AssistantPublicationStat.day >= start,
            )
            .order_by(AssistantPublicationStat.day)
        )
    ).all()
    by_day = {entry.day: entry for entry in stored}
    totals = PublicationStatTotals(
        sessions=0, turns=0, insufficient_turns=0, error_turns=0, tokens=0
    )
    daily: list[PublicationStatDay] = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        entry = by_day.get(day)
        values = PublicationStatDay(
            day=day,
            sessions=entry.sessions if entry else 0,
            turns=entry.turns if entry else 0,
            insufficient_turns=entry.insufficient_turns if entry else 0,
            error_turns=entry.error_turns if entry else 0,
            tokens=entry.tokens if entry else 0,
        )
        daily.append(values)
        totals.sessions += values.sessions
        totals.turns += values.turns
        totals.insufficient_turns += values.insufficient_turns
        totals.error_turns += values.error_turns
        totals.tokens += values.tokens
    questions = (
        await db.scalars(
            select(AssistantPublicationQuestion)
            .where(AssistantPublicationQuestion.publication_id == row.id)
            .order_by(
                AssistantPublicationQuestion.times_asked.desc(),
                AssistantPublicationQuestion.last_asked_at.desc(),
            )
            .limit(TOP_QUESTIONS_LIMIT)
        )
    ).all()
    return PublicationStatsResponse(
        configured=True,
        days=days,
        totals=totals,
        daily=daily,
        budget_limit=row.daily_token_budget,
        budget_used_today=await budget_used_today(row.id),
        top_questions=[
            PublicationUnansweredQuestion(
                question=question.question,
                times_asked=question.times_asked,
                last_asked_at=question.last_asked_at,
            )
            for question in questions
        ],
    )
