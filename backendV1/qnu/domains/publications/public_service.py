"""Anonymous public turns: own sessions and limits, then the existing pipeline.

The public surface accepts no identity and no scope from the request. A fixed
server-built service actor is admitted for read roles only after an enabled
publication row is resolved; each turn runs without conversation memory and the
reply is reduced to presentation fields before it leaves the server.
"""

import asyncio
import hashlib
import json
import secrets
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.assistants.schemas import AssistantRagPolicy
from qnu.domains.assistants.service import assistant_readiness, get_assistant
from qnu.domains.identity.service_actor import public_chatbot_actor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.directory import directory_ready
from qnu.domains.lifecycle.guards import visible
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.usage.scope import use_account
from qnu.domains.ocr.ids import new_id
from qnu.domains.publications.limits import DailyBudget
from qnu.domains.publications.models import (
    AssistantPublication,
    AssistantPublicationQuestion,
    AssistantPublicationStat,
)
from qnu.domains.publications.schemas import (
    PublicChatbotInfo,
    PublicChatbotListResponse,
    PublicChatbotSummary,
    PublicCitation,
    PublicSessionResponse,
    PublicTurnRequest,
    PublicTurnResponse,
)
from qnu.domains.rag.answer.schemas import AnswerRequest, AnswerResponse
from qnu.domains.rag.answer.service import answer
from qnu.domains.workspaces.models import Workspace
from qnu.platform.cache import get_json, get_redis, namespaced, set_json
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatMessage, ChatModel
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.reranker import Reranker
from qnu.ports.vector_store import VectorStore

UNAVAILABLE_TEXT = "Trợ lý đang tạm ngưng phục vụ. Vui lòng quay lại sau."
SESSIONS_PER_HOUR = 12
TURNS_PER_HOUR = 60
INFO_CACHE_SECONDS = 30
# Short-lived readiness reuse so a busy public bot does not re-audit the whole
# collection on every turn; the answer pipeline still re-checks the snapshot.
READINESS_CACHE_SECONDS = 5
MAX_PUBLIC_CHATBOTS = 50
MAX_UNANSWERED_ROWS = 500
BUSINESS_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
logger = get_logger(__name__)


def business_day() -> date:
    """Calendar day in the unit's local time; stats and the budget reset together."""
    return datetime.now(BUSINESS_TZ).date()


def client_key(host: str | None) -> str:
    """Stable anonymous bucket; the raw address is never stored or logged."""
    return hashlib.sha256((host or "unknown").encode("utf-8")).hexdigest()[:16]


def _session_key(session_id: str) -> str:
    return f"pubchat:session:{session_id}"


def _day_key(publication_id: str, day: date | None = None) -> str:
    return f"pubchat:tokens:{publication_id}:{day or business_day():%Y%m%d}"


def _question_hash(text: str) -> str:
    normalized = " ".join(text.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def _bump_stats(
    db: AsyncSession,
    publication_id: str,
    *,
    sessions: int = 0,
    turns: int = 0,
    insufficient_turns: int = 0,
    error_turns: int = 0,
    tokens: int = 0,
    day: date | None = None,
) -> None:
    stmt = insert(AssistantPublicationStat).values(
        publication_id=publication_id,
        day=day or business_day(),
        sessions=sessions,
        turns=turns,
        insufficient_turns=insufficient_turns,
        error_turns=error_turns,
        tokens=tokens,
    )
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=["publication_id", "day"],
            set_={
                "sessions": AssistantPublicationStat.sessions + sessions,
                "turns": AssistantPublicationStat.turns + turns,
                "insufficient_turns": (
                    AssistantPublicationStat.insufficient_turns + insufficient_turns
                ),
                "error_turns": AssistantPublicationStat.error_turns + error_turns,
                "tokens": AssistantPublicationStat.tokens + tokens,
            },
        )
    )


async def _record_unanswered(db: AsyncSession, publication_id: str, question: str) -> None:
    await db.execute(
        insert(AssistantPublicationQuestion)
        .values(
            id=new_id("puq"),
            publication_id=publication_id,
            question_hash=_question_hash(question),
            question=question,
            times_asked=1,
            last_asked_at=utcnow(),
        )
        .on_conflict_do_update(
            constraint="uq_publication_question_hash",
            set_={
                "question": question,
                "times_asked": AssistantPublicationQuestion.times_asked + 1,
                "last_asked_at": utcnow(),
            },
        )
    )
    keep = (
        select(AssistantPublicationQuestion.id)
        .where(AssistantPublicationQuestion.publication_id == publication_id)
        .order_by(AssistantPublicationQuestion.last_asked_at.desc())
        .limit(MAX_UNANSWERED_ROWS)
    )
    await db.execute(
        delete(AssistantPublicationQuestion).where(
            AssistantPublicationQuestion.publication_id == publication_id,
            AssistantPublicationQuestion.id.not_in(keep),
        )
    )


async def _rate_limit(bucket: str, limit: int) -> None:
    client = get_redis()
    key = namespaced(f"pubchat:rate:{bucket}")
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, 3600)
    if count > limit:
        raise AppException(
            "Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút.",
            code="public_chat_rate_limited",
            status_code=429,
        )


_RESERVE_TURN_LUA = """
local raw = redis.call('GET', KEYS[1])
if not raw then return cjson.encode({status='expired'}) end
local session = cjson.decode(raw)
if session.publication_id ~= ARGV[1] then return cjson.encode({status='expired'}) end
local used = tonumber(session.turns or 0)
local max_turns = tonumber(ARGV[2])
if used >= max_turns then return cjson.encode({status='limit'}) end
session.turns = used + 1
redis.call('SET', KEYS[1], cjson.encode(session), 'EX', tonumber(ARGV[3]))
return cjson.encode({status='ok', remaining=max_turns - used - 1})
"""

_REFUND_TURN_LUA = """
local raw = redis.call('GET', KEYS[1])
if not raw then return 0 end
local session = cjson.decode(raw)
if session.publication_id ~= ARGV[1] then return 0 end
local used = tonumber(session.turns or 0)
if used <= 0 then return 0 end
session.turns = used - 1
redis.call('SET', KEYS[1], cjson.encode(session), 'EX', tonumber(ARGV[2]))
return 1
"""


async def _reserve_turn(session_id: str, publication_id: str, max_turns: int, ttl: int) -> int:
    """Atomically claim one turn before any model cost; return turns remaining.

    Check-and-increment runs inside Redis so parallel turns on the same session
    cannot both pass the cap. A failed answer refunds the claim so server errors
    stay free for the visitor.
    """
    raw = await get_redis().eval(
        _RESERVE_TURN_LUA, 1, namespaced(_session_key(session_id)), publication_id, max_turns, ttl
    )
    result = json.loads(raw)
    if result["status"] == "expired":
        raise AppException(
            "Phiên trò chuyện đã hết hạn. Hãy bắt đầu phiên mới.",
            code="public_chat_session_expired",
            status_code=410,
        )
    if result["status"] == "limit":
        raise AppException(
            "Phiên đã đạt giới hạn số câu hỏi. Hãy bắt đầu phiên mới.",
            code="public_chat_session_limit",
            status_code=429,
        )
    return int(result["remaining"])


async def _refund_turn(session_id: str, publication_id: str, ttl: int) -> None:
    await get_redis().eval(
        _REFUND_TURN_LUA, 1, namespaced(_session_key(session_id)), publication_id, ttl
    )


def _publication_query():
    return (
        select(AssistantPublication, Assistant.is_active)
        .join(
            Assistant,
            and_(
                Assistant.id == AssistantPublication.assistant_id,
                Assistant.workspace_id == AssistantPublication.workspace_id,
            ),
        )
        .where(AssistantPublication.enabled.is_(True))
    )


async def _publication(db: AsyncSession, slug: str) -> tuple[AssistantPublication, bool]:
    if not get_settings().PUBLIC_CHATBOTS_ENABLED:
        raise EntityNotFound("Không tìm thấy chatbot công khai.", code="public_chatbot_not_found")
    result = (
        await db.execute(
            _publication_query()
            .where(AssistantPublication.slug == slug.strip().lower())
            .execution_options(populate_existing=True)
        )
    ).one_or_none()
    if result is None:
        raise EntityNotFound("Không tìm thấy chatbot công khai.", code="public_chatbot_not_found")
    return result._tuple()


async def _readiness(db: AsyncSession, blob: BlobStore, row: AssistantPublication) -> str:
    cache_key = f"pubchat:ready:{row.id}:{row.revision}"
    cached = await get_json(cache_key)
    if cached is not None:
        return str(cached)
    report = await assistant_readiness(
        db, blob, public_chatbot_actor(), row.workspace_id, row.assistant_id
    )
    await set_json(cache_key, report.status, READINESS_CACHE_SECONDS)
    return report.status


async def info(db: AsyncSession, blob: BlobStore, slug: str) -> PublicChatbotInfo:
    row, active = await _publication(db, slug)
    cache_key = f"pubchat:info:{row.id}:{row.revision}:{int(active)}"
    cached = await get_json(cache_key)
    if cached is not None:
        return PublicChatbotInfo.model_validate(cached)
    available = active and await _readiness(db, blob, row) == "ready"
    value = PublicChatbotInfo(
        display_name=row.display_name,
        welcome_message=row.welcome_message,
        starter_prompts=list(row.starter_prompts),
        max_turns_per_session=row.max_turns_per_session,
        available=available,
        unavailable_reason=None if available else UNAVAILABLE_TEXT,
    )
    await set_json(cache_key, value.model_dump(mode="json"), INFO_CACHE_SECONDS)
    return value


async def listing(db: AsyncSession) -> PublicChatbotListResponse:
    if not get_settings().PUBLIC_CHATBOTS_ENABLED:
        return PublicChatbotListResponse(chatbots=[])
    rows = (
        await db.execute(
            _publication_query()
            .add_columns(
                Assistant.collection_id,
                and_(
                    Workspace.status == "active",
                    visible("assistant", Assistant.id),
                    or_(
                        Assistant.collection_id.is_(None),
                        visible("collection", Assistant.collection_id),
                    ),
                ).label("visible_for_serving"),
            )
            .join(Workspace, Workspace.id == AssistantPublication.workspace_id)
            .order_by(
                AssistantPublication.display_name.asc(),
                AssistantPublication.slug.asc(),
            )
            .limit(MAX_PUBLIC_CHATBOTS)
        )
    ).all()
    ready = await directory_ready(
        db,
        {
            (row.workspace_id, collection_id)
            for row, active, collection_id, visible_for_serving in rows
            if active and visible_for_serving and collection_id is not None
        },
    )
    items: list[PublicChatbotSummary] = []
    for row, active, collection_id, visible_for_serving in rows:
        available = (
            active
            and visible_for_serving
            and (collection_id is None or (row.workspace_id, collection_id) in ready)
        )
        items.append(
            PublicChatbotSummary(
                slug=row.slug,
                display_name=row.display_name,
                welcome_message=row.welcome_message,
                available=available,
                unavailable_reason=None if available else UNAVAILABLE_TEXT,
            )
        )
    return PublicChatbotListResponse(chatbots=items)


async def create_session(db: AsyncSession, slug: str, requester: str) -> PublicSessionResponse:
    row, active = await _publication(db, slug)
    if not active:
        raise Conflict(UNAVAILABLE_TEXT, code="public_chatbot_unavailable")
    await _rate_limit(f"sessions:{requester}:{row.id}", SESSIONS_PER_HOUR)
    ttl = get_settings().PUBLIC_CHATBOT_SESSION_TTL_SECONDS
    session_id = secrets.token_urlsafe(24)
    await set_json(_session_key(session_id), {"publication_id": row.id, "turns": 0}, ttl)
    await _bump_stats(db, row.id, sessions=1)
    await db.commit()
    return PublicSessionResponse(
        session_id=session_id,
        expires_in_seconds=ttl,
        max_turns=row.max_turns_per_session,
        turns_remaining=row.max_turns_per_session,
    )


def _page(citations: dict) -> int | None:
    for entry in citations.values():
        if isinstance(entry, dict) and isinstance(entry.get("page"), int):
            return entry["page"]
    return None


def _public_reply(result: AnswerResponse, remaining: int) -> PublicTurnResponse:
    citations: list[PublicCitation] = []
    labels: dict[str, int] = {}
    for source in result.sources:
        index = len(citations) + 1
        labels[source.evidence_id] = index
        citations.append(
            PublicCitation(
                index=index,
                title=source.source_title or "Tài liệu nguồn",
                page=_page(source.citations),
            )
        )
    text = result.answer
    if text:
        for evidence_id, index in labels.items():
            text = text.replace(f"[{evidence_id}]", f"[{index}]")
    return PublicTurnResponse(
        status=result.status,
        answer=text,
        message=result.message if result.status == "insufficient_evidence" else None,
        citations=citations,
        turns_remaining=remaining,
    )


async def budget_used_today(publication_id: str) -> int:
    raw = await get_redis().get(namespaced(_day_key(publication_id)))
    return int(raw or 0)


async def turn(
    db: AsyncSession,
    blob: BlobStore,
    embedding: EmbeddingModel,
    vectors: VectorStore,
    chat: ChatModel,
    reranker: Reranker | None,
    slug: str,
    req: PublicTurnRequest,
    requester: str,
) -> PublicTurnResponse:
    row, active = await _publication(db, slug)
    if not active:
        raise Conflict(UNAVAILABLE_TEXT, code="public_chatbot_unavailable")
    ttl = get_settings().PUBLIC_CHATBOT_SESSION_TTL_SECONDS
    session = await get_json(_session_key(req.session_id))
    if not session or session.get("publication_id") != row.id:
        raise AppException(
            "Phiên trò chuyện đã hết hạn. Hãy bắt đầu phiên mới.",
            code="public_chat_session_expired",
            status_code=410,
        )
    if int(session.get("turns", 0)) >= row.max_turns_per_session:
        raise AppException(
            "Phiên đã đạt giới hạn số câu hỏi. Hãy bắt đầu phiên mới.",
            code="public_chat_session_limit",
            status_code=429,
        )
    publication_id = row.id
    day = business_day()
    budget = DailyBudget(namespaced(_day_key(publication_id, day)), row.daily_token_budget)
    await _rate_limit(f"turns:{requester}:{publication_id}", TURNS_PER_HOUR)
    await budget.check()
    if await _readiness(db, blob, row) != "ready":
        raise Conflict(UNAVAILABLE_TEXT, code="public_chatbot_unavailable")
    # Claim the turn atomically before spending model tokens; concurrent turns on
    # the same session serialize here instead of both passing the cap.
    remaining = await _reserve_turn(req.session_id, publication_id, row.max_turns_per_session, ttl)
    try:
        actor = public_chatbot_actor()
        assistant: Assistant = await get_assistant(db, actor, row.workspace_id, row.assistant_id)
        if not assistant.is_active:
            raise Conflict(UNAVAILABLE_TEXT, code="public_chatbot_unavailable")
        collection_ids = list(
            dict.fromkeys(
                item
                for item in [assistant.collection_id, *(assistant.collection_ids or [])]
                if item
            )
        )
        if not collection_ids:
            messages = [
                ChatMessage(
                    role="system",
                    content=assistant.persona
                    or "Bạn là trợ lý AI của Trường Đại học Quy Nhơn (QNU). Hãy hỗ trợ người dùng chu đáo, thân thiện và chuẩn mực sư phạm.",
                ),
                ChatMessage(role="user", content=req.question),
            ]
            with use_account(budget):
                _runtime, chat_req, _b = await prepare_chat_request(
                    db,
                    actor,
                    row.workspace_id,
                    messages,
                    provider_id=assistant.chat_provider_id,
                    task="chat",
                    max_output_tokens=assistant.max_output_tokens,
                )
                chat_res = await chat.complete(messages, chat_req)
            pub_raw = chat_res.content.strip()
            pub_ans = pub_raw
            if pub_raw.startswith("{") and pub_raw.endswith("}"):
                try:
                    p = json.loads(pub_raw)
                    if isinstance(p, dict):
                        extracted = (
                            p.get("answer")
                            or p.get("message")
                            or p.get("content")
                            or p.get("text")
                        )
                        if extracted and isinstance(extracted, str):
                            pub_ans = extracted.strip()
                except Exception:
                    pass
            if not pub_ans or pub_ans == "{}":
                pub_ans = (
                    "Tôi đã ghi nhận câu hỏi của bạn. Về nội dung này, bạn có thể diễn đạt cụ thể hơn "
                    "hoặc cung cấp thêm chi tiết để mình hỗ trợ chính xác nhất nhé."
                )
            return PublicTurnResponse(
                session_id=req.session_id,
                status="answered",
                answer=pub_ans,
                message=None,
                citations=[],
                remaining_turns=remaining,
            )
        policy = AssistantRagPolicy.model_validate(assistant.rag_policy or {}).model_dump(
            mode="json", exclude={"guardrail_policy", "suggested_prompts"}
        )
        policy["metadata_filter"] = {}
        with use_account(budget):
            result = await answer(
                db,
                blob,
                embedding,
                vectors,
                chat,
                actor,
                row.workspace_id,
                collection_ids[0],
                AnswerRequest(
                    question=req.question,
                    top_k=assistant.top_k,
                    provider_id=assistant.chat_provider_id,
                    max_output_tokens=assistant.max_output_tokens,
                    **policy,
                ),
                persona=assistant.persona,
                reranker=reranker,
                compose_insufficient_message=True,
                collection_ids=collection_ids,
            )
    except (Exception, asyncio.CancelledError):
        try:
            await _refund_turn(req.session_id, publication_id, ttl)
        except Exception:
            logger.warning("public_chat_session_refund_failed", publication_id=publication_id)
        try:
            await db.rollback()
            await _bump_stats(
                db, publication_id, error_turns=1, tokens=budget.observed_tokens, day=day
            )
            await db.commit()
        except Exception:
            logger.warning("public_chat_error_stats_failed", publication_id=publication_id)
        raise
    insufficient = result.status == "insufficient_evidence"
    await _bump_stats(
        db,
        row.id,
        turns=1,
        insufficient_turns=1 if insufficient else 0,
        tokens=budget.observed_tokens,
        day=day,
    )
    if insufficient:
        await _record_unanswered(db, row.id, req.question)
    await db.commit()
    return _public_reply(result, remaining)
