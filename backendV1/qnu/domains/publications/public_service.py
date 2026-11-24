"""Anonymous public turns: own sessions and limits, then the existing pipeline.

The public surface accepts no identity and no scope from the request. A fixed
server-built service actor is admitted for read roles only after an enabled
publication row is resolved; each turn runs without conversation memory and the
reply is reduced to presentation fields before it leaves the server.
"""

import asyncio
import hashlib
import ipaddress
import json
import os
import re
import secrets
import time
import unicodedata
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import Request
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant, AssistantCollection
from qnu.domains.assistants.schemas import AssistantRagPolicy
from qnu.domains.assistants.service import assistant_readiness, get_assistant
from qnu.domains.conversations.document_export import (
    EXPORT_MEDIA_TYPES,
    NO_KNOWLEDGE_GROUNDING_POLICY,
    DirectHistoryEntry,
    DocumentDraft,
    ExportFormat,
    active_draft_prompt_context,
    dialogue_turn_policy,
    disabled_format_refusal_message,
    disabled_requested_format,
    enabled_export_formats,
    export_policy_prompt_addon,
    extract_document_draft,
    is_abnormally_truncated_reply,
    render_docx,
    render_pdf,
    render_xlsx,
    requested_export_format,
    resolve_preferred_format,
    safe_download_filename,
    strip_document_markers,
    trim_direct_history,
    vietnam_time_context,
)
from qnu.domains.identity.service_actor import public_chatbot_actor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.directory import directory_ready
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.lifecycle.guards import visible
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.providers.service import provider_service
from qnu.domains.modelops.usage.scope import use_account
from qnu.domains.modelops.usage.service import usage_service
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
    PublicDocumentDraft,
    PublicModelOption,
    PublicSessionRequest,
    PublicSessionResponse,
    PublicTurnRequest,
    PublicTurnResponse,
)
from qnu.domains.rag.answer.schemas import AnswerRequest, AnswerResponse
from qnu.domains.rag.answer.service import answer
from qnu.domains.workspaces.models import Workspace
from qnu.platform.cache import get_json, get_redis, namespaced, set_json
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict, EntityNotFound, Forbidden
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatMessage, ChatModel, ChatResponseError
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.provider_execution import bind_usage
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


_DEFAULT_TRUSTED_PROXIES = (
    "127.0.0.1",
    "::1",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
)


def _is_trusted_proxy(host: str) -> bool:
    """Check whether the direct peer IP belongs to configured trusted reverse proxies."""
    raw_allow = os.environ.get("FORWARDED_ALLOW_IPS", "").strip()
    entries = (
        [item.strip() for item in raw_allow.split(",") if item.strip()]
        if raw_allow
        else list(_DEFAULT_TRUSTED_PROXIES)
    )
    if "*" in entries:
        return True
    try:
        peer = ipaddress.ip_address(host)
    except ValueError:
        return False
    for entry in entries:
        try:
            if "/" in entry:
                if peer in ipaddress.ip_network(entry, strict=False):
                    return True
            elif peer == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def extract_client_ip(request: Request) -> str:
    """Extract client IP, honoring proxy headers only when received from a trusted proxy."""
    direct_host = request.client.host.strip() if request.client and request.client.host else ""
    if direct_host and _is_trusted_proxy(direct_host):
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip and cf_ip.strip():
            return cf_ip.strip()
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded and forwarded.strip():
            hops = [part.strip() for part in forwarded.split(",") if part.strip()]
            # Pick the rightmost non-proxy hop to resist client-injected leading XFF values.
            for hop in reversed(hops):
                if not _is_trusted_proxy(hop):
                    return hop
            if hops:
                return hops[0]
    if direct_host:
        return direct_host
    return "unknown"


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


def _public_model_label(model_name: str) -> str:
    text = (model_name or "").strip()
    if "/" in text:
        short = text.rsplit("/", 1)[-1].strip()
        if short:
            return short
    return text


async def list_public_chat_models(
    db: AsyncSession, assistant_chat_provider_id: str | None
) -> tuple[list[PublicModelOption], str | None, dict[str, str]]:
    """Return active chat models safe for public display (no provider IDs or endpoints)."""
    providers = await provider_service.list(db, active_only=True)
    chat_providers = [p for p in providers if "chat" in (p.capabilities or []) and p.model_name]

    default_provider_id = assistant_chat_provider_id or await catalog_service.system_default_for(
        db, "chat"
    )
    default_model_name = next(
        (p.model_name for p in chat_providers if p.id == default_provider_id), None
    )

    model_to_provider: dict[str, str] = {}
    for p in chat_providers:
        if p.id == default_provider_id:
            model_to_provider[p.model_name] = p.id
        else:
            model_to_provider.setdefault(p.model_name, p.id)
    options = [
        PublicModelOption(
            model_name=name,
            label=_public_model_label(name),
            is_default=name == default_model_name,
        )
        for name in model_to_provider
    ]
    return options, default_model_name, model_to_provider


async def resolve_public_chat_provider(
    db: AsyncSession,
    assistant: Assistant,
    requested_model_name: str | None,
) -> tuple[str | None, str | None]:
    """Validate an optional visitor-selected model against active chat providers."""
    _, default_model_name, model_to_provider = await list_public_chat_models(
        db, assistant.chat_provider_id
    )
    if not requested_model_name:
        return assistant.chat_provider_id, default_model_name
    matched_provider_id = model_to_provider.get(requested_model_name)
    if matched_provider_id is None:
        raise AppException(
            "Mô hình AI đã chọn hiện không khả dụng.",
            code="public_chat_model_unavailable",
            status_code=422,
        )
    return matched_provider_id, requested_model_name


async def info(db: AsyncSession, blob: BlobStore, slug: str) -> PublicChatbotInfo:
    row, active = await _publication(db, slug)
    assistant = await db.scalar(
        select(Assistant).where(
            Assistant.id == row.assistant_id,
            Assistant.workspace_id == row.workspace_id,
        )
    )
    ast_rev = assistant.revision if assistant is not None else 0
    cache_key = f"pubchat:info:v3:{row.id}:{row.revision}:{ast_rev}:{int(active)}"
    cached = await get_json(cache_key)
    assistant_provider_id = assistant.chat_provider_id if assistant is not None else None
    models, default_model_name, _ = await list_public_chat_models(db, assistant_provider_id)
    if cached is not None:
        return PublicChatbotInfo.model_validate(
            {**cached, "models": models, "default_model_name": default_model_name}
        )
    available = active and await _readiness(db, blob, row) == "ready"
    export_formats = (
        enabled_export_formats({"rag_policy": assistant.rag_policy})
        if assistant is not None
        else []
    )
    has_collection = bool(assistant is not None and assistant.collection_id)
    if not has_collection and assistant is not None:
        bound_col = await db.scalar(
            select(AssistantCollection.collection_id)
            .where(
                AssistantCollection.assistant_id == assistant.id,
                AssistantCollection.workspace_id == row.workspace_id,
            )
            .limit(1)
        )
        has_collection = bool(bound_col)
    value = PublicChatbotInfo(
        display_name=row.display_name,
        welcome_message=row.welcome_message,
        starter_prompts=list(row.starter_prompts),
        allowed_embed_origins=list(row.allowed_embed_origins) if row.allowed_embed_origins else [],
        max_turns_per_session=row.max_turns_per_session,
        available=available,
        unavailable_reason=None if available else UNAVAILABLE_TEXT,
        models=models,
        default_model_name=default_model_name,
        has_knowledge=has_collection,
        export_formats=export_formats,
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


async def create_session(
    db: AsyncSession,
    slug: str,
    requester: str,
    body: PublicSessionRequest | None = None,
) -> PublicSessionResponse:
    if body and body.website and body.website.strip():
        raise AppException(
            "Yêu cầu không hợp lệ.",
            code="public_chat_bot_detected",
            status_code=400,
        )
    row, active = await _publication(db, slug)
    if not active:
        raise Conflict(UNAVAILABLE_TEXT, code="public_chatbot_unavailable")
    await _rate_limit(f"sessions:{requester}:{row.id}", SESSIONS_PER_HOUR)
    ttl = get_settings().PUBLIC_CHATBOT_SESSION_TTL_SECONDS
    session_id = secrets.token_urlsafe(24)
    await set_json(
        _session_key(session_id),
        {"publication_id": row.id, "turns": 0, "created_at": time.time()},
        ttl,
    )
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


_SMALLTALK_MAX_CHARS = 48
_SMALLTALK_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_GREETING_RE = re.compile(
    r"^(?:"
    r"(?:xin\s+)?chào(?:\s+(?:bạn|ad|admin|bot|trợ\s+lý|thầy|cô|anh|chị|em|shop|mọi\s+người|qnu))?"
    r"|chào\s+buổi\s+(?:sáng|trưa|chiều|tối)"
    r"|alo(?:\s+alo)?"
    r"|(?:hi|hello|hey)(?:\s+(?:there|bot|admin|qnu|assistant))?"
    r"|good\s+(?:morning|afternoon|evening)"
    r")(?:\s+(?:ạ|nhé|nha|nhỉ|ơi))?$"
)
_THANKS_RE = re.compile(
    r"^(?:"
    r"(?:(?:ok|oke|okay|vâng|dạ|rồi)\s+)?(?:xin\s+)?c[ảá]m\s+ơn"
    r"(?:\s+(?:bạn|ad|admin|bot|trợ\s+lý|thầy|cô|anh|chị|em|nhiều|rất\s+nhiều|nhé|nha|ạ)){0,3}"
    r"|(?:(?:ok|oke|okay)\s+)?(?:thanks|thank\s+you|tks|ty)(?:\s+(?:so\s+much|a\s+lot))?"
    r")$"
)
_FAREWELL_RE = re.compile(
    r"^(?:tạm\s+biệt|chào\s+tạm\s+biệt|bye(?:\s+bye)?|goodbye|hẹn\s+gặp\s+lại)"
    r"(?:\s+(?:bạn|nhé|nha|ạ))?$"
)


def is_pure_smalltalk(question: str) -> bool:
    """Return True only for short pure greetings/thanks/farewells (no digits or queries).

    Used strictly to avoid heavy RAG retrieval on social turns; the reply itself
    is always generated naturally by the LLM using the assistant's Persona and
    session history rather than hardcoded canned strings.
    """
    raw = unicodedata.normalize("NFC", question or "").strip()
    if not raw or len(raw) > _SMALLTALK_MAX_CHARS or any(ch.isdigit() for ch in raw):
        return False
    if "?" in raw and len(raw.split()) > 3:
        return False
    normalized = " ".join(_SMALLTALK_PUNCT_RE.sub(" ", raw.casefold()).split())
    if not normalized:
        return False
    return bool(
        _GREETING_RE.fullmatch(normalized)
        or _THANKS_RE.fullmatch(normalized)
        or _FAREWELL_RE.fullmatch(normalized)
    )


def _history_key(session_id: str) -> str:
    return f"pubchat:history:{session_id}"


async def _load_public_history(session_id: str, limit: int) -> list[dict[str, str]]:
    cap = min(max(int(limit or 0), 0), 6)
    if cap == 0:
        return []
    raw = await get_json(_history_key(session_id))
    if not isinstance(raw, list):
        return []
    cleaned = [
        item
        for item in raw
        if isinstance(item, dict)
        and isinstance(item.get("question"), str)
        and isinstance(item.get("answer"), str)
    ]
    return cleaned[-cap:]


async def _append_public_history(
    session_id: str,
    question: str,
    answer_text: str,
    ttl: int,
) -> None:
    if not answer_text or not answer_text.strip():
        return
    existing = await _load_public_history(session_id, 6)
    existing.append(
        {
            "question": question.strip()[:1000],
            "answer": answer_text.strip()[:2000],
        }
    )
    await set_json(_history_key(session_id), existing[-6:], ttl)


def _draft_key(session_id: str, draft_id: str) -> str:
    return f"pubchat:draft:{session_id}:{draft_id}"


def _latest_draft_key(session_id: str) -> str:
    return f"pubchat:latest_draft:{session_id}"


async def _load_latest_public_draft(session_id: str) -> DocumentDraft | None:
    stored = await get_json(_latest_draft_key(session_id))
    if not isinstance(stored, dict):
        return None
    try:
        return DocumentDraft.model_validate(stored)
    except Exception:
        return None


async def _store_public_draft(
    session_id: str,
    publication_id: str,
    draft: DocumentDraft,
    ttl: int,
) -> PublicDocumentDraft:
    draft_id = "drf_" + uuid.uuid4().hex[:12]
    dumped = draft.model_dump(mode="json")
    await set_json(
        _draft_key(session_id, draft_id),
        {"publication_id": publication_id, "draft": dumped},
        ttl,
    )
    await set_json(_latest_draft_key(session_id), dumped, ttl)
    return PublicDocumentDraft(
        draft_id=draft_id,
        title=draft.title,
        layout=draft.layout,
        markdown=draft.markdown,
        has_tables=draft.has_tables,
        preferred_format=draft.preferred_format,
    )


async def export_public_draft(
    db: AsyncSession,
    slug: str,
    session_id: str,
    draft_id: str,
    fmt: ExportFormat,
) -> tuple[bytes, str, str]:
    """Authorize public session, enforce assistant export toggles, and render file."""
    row, active = await _publication(db, slug)
    if not active:
        raise Conflict(UNAVAILABLE_TEXT, code="public_chatbot_unavailable")
    session = await get_json(_session_key(session_id))
    if not session or session.get("publication_id") != row.id:
        raise AppException(
            "Phiên trò chuyện đã hết hạn. Hãy bắt đầu phiên mới.",
            code="public_chat_session_expired",
            status_code=410,
        )
    assistant = await db.scalar(
        select(Assistant).where(
            Assistant.id == row.assistant_id,
            Assistant.workspace_id == row.workspace_id,
        )
    )
    if assistant is None or not assistant.is_active:
        raise Conflict(UNAVAILABLE_TEXT, code="public_chatbot_unavailable")
    allowed_formats = enabled_export_formats({"rag_policy": assistant.rag_policy})
    if fmt not in allowed_formats:
        raise Forbidden(
            f"Trợ lý hiện không bật xuất định dạng {fmt.upper()}.",
            code="assistant_export_format_disabled",
        )
    stored = await get_json(_draft_key(session_id, draft_id))
    if not stored or stored.get("publication_id") != row.id or not isinstance(stored.get("draft"), dict):
        raise EntityNotFound(
            "Không tìm thấy bản thảo để xuất hoặc bản thảo đã hết hạn.",
            code="public_draft_not_found",
        )
    draft = DocumentDraft.model_validate(stored["draft"])
    if fmt == "docx":
        payload = await asyncio.to_thread(render_docx, draft)
    elif fmt == "xlsx":
        payload = await asyncio.to_thread(render_xlsx, draft)
    else:
        payload = await render_pdf(draft)
    return payload, EXPORT_MEDIA_TYPES[fmt], safe_download_filename(draft.title, fmt)


def _public_reply(
    result: AnswerResponse,
    remaining: int,
    *,
    model_name: str | None = None,
    document_draft: PublicDocumentDraft | None = None,
    answer_override: str | None = None,
) -> PublicTurnResponse:
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
    text = answer_override if answer_override is not None else result.answer
    if text:
        for evidence_id, index in labels.items():
            text = text.replace(f"[{evidence_id}]", f"[{index}]")
    return PublicTurnResponse(
        status=result.status,
        answer=text,
        message=result.message if result.status == "insufficient_evidence" else None,
        citations=citations,
        turns_remaining=remaining,
        model_name=model_name,
        document_draft=document_draft,
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
    if req.website and req.website.strip():
        raise AppException(
            "Yêu cầu không hợp lệ.",
            code="public_chat_bot_detected",
            status_code=400,
        )
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
    prior_turns = int(session.get("turns", 0))
    if prior_turns >= row.max_turns_per_session:
        raise AppException(
            "Phiên đã đạt giới hạn số câu hỏi. Hãy bắt đầu phiên mới.",
            code="public_chat_session_limit",
            status_code=429,
        )
    created_at = float(session.get("created_at") or 0)
    if prior_turns == 0 and created_at > 0 and (time.time() - created_at) < 0.8:
        raise AppException(
            "Thao tác quá nhanh. Vui lòng thử lại sau ít giây.",
            code="public_chat_too_fast",
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
        selected_provider_id, selected_model_name = await resolve_public_chat_provider(
            db, assistant, req.model_name
        )
        export_formats = enabled_export_formats({"rag_policy": assistant.rag_policy})
        collection_ids = list(
            dict.fromkeys(
                item
                for item in [assistant.collection_id, *(assistant.collection_ids or [])]
                if item
            )
        )
        # Release any read transaction snapshot/locks before long-running LLM inference.
        await db.commit()
        disabled_fmt = disabled_requested_format(req.question, export_formats)
        if disabled_fmt is not None:
            refusal_text = disabled_format_refusal_message(disabled_fmt)
            await _append_public_history(req.session_id, req.question, refusal_text, ttl)
            await _bump_stats(
                db,
                row.id,
                turns=1,
                insufficient_turns=0,
                tokens=0,
                day=day,
            )
            await db.commit()
            return PublicTurnResponse(
                status="answered",
                answer=refusal_text,
                message=None,
                citations=[],
                turns_remaining=remaining,
                model_name=selected_model_name,
                document_draft=None,
            )
        social_only = is_pure_smalltalk(req.question)
        latest_draft = (
            await _load_latest_public_draft(req.session_id)
            if export_formats and not social_only
            else None
        )
        if not collection_ids or social_only:
            base_persona = (
                assistant.persona
                or "Bạn là trợ lý AI của Trường Đại học Quy Nhơn (QNU). Hãy hỗ trợ người dùng chu đáo, thân thiện và chuẩn mực sư phạm."
            )
            if not collection_ids:
                system_content = (
                    base_persona
                    + NO_KNOWLEDGE_GROUNDING_POLICY
                    + export_policy_prompt_addon(export_formats)
                    + active_draft_prompt_context(latest_draft)
                )
            else:
                system_content = (
                    base_persona
                    + "\n\n[LƯU Ý GIAO TIẾP]: Người dùng đang chào hỏi hoặc trao đổi xã giao. "
                    "Hãy đáp lại ngắn gọn, tự nhiên và đúng vai trò trong Persona; không tự bịa số liệu."
                )
            history_rows = await _load_public_history(
                req.session_id, getattr(assistant, "history_turns", 3)
            )
            trimmed_history = trim_direct_history(
                [
                    DirectHistoryEntry(question=item["question"], answer=item["answer"])
                    for item in history_rows
                ],
                max_turns=getattr(assistant, "history_turns", 3),
            )
            system_content += vietnam_time_context() + dialogue_turn_policy(len(trimmed_history))
            messages = [ChatMessage(role="system", content=system_content)]
            for item in trimmed_history:
                messages.append(ChatMessage(role="user", content=item.question))
                if item.answer:
                    messages.append(ChatMessage(role="assistant", content=item.answer))
            messages.append(ChatMessage(role="user", content=req.question))

            def _parse_pub_reply(raw: str) -> str:
                pub_raw = (raw or "").strip()
                parsed_text = pub_raw
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
                                parsed_text = extracted.strip()
                    except Exception:
                        pass
                return parsed_text

            with use_account(budget):
                runtime, chat_req, chat_budget = await prepare_chat_request(
                    db,
                    actor,
                    row.workspace_id,
                    messages,
                    provider_id=selected_provider_id,
                    task="chat",
                    max_output_tokens=assistant.max_output_tokens,
                )

                async def _run_public_completion():
                    usage = await usage_service.reserve(
                        db,
                        actor,
                        row.workspace_id,
                        "chat",
                        f"pub:{row.id}:{uuid.uuid4().hex}",
                        digest(
                            {
                                "publication_id": row.id,
                                "question": req.question,
                                "config": runtime.inference_configuration_hash("chat"),
                            }
                        ),
                        chat_budget.total_reserved_tokens,
                        runtime.provider_id,
                    )
                    try:
                        await db.commit()
                    except BaseException:
                        await usage_service.settle(db, usage.id, total_tokens=0, failed=True)
                        raise
                    try:
                        res = await chat.complete(messages, bind_usage(chat_req, usage.id))
                    except ChatResponseError as exc:
                        await usage_service.settle(
                            db, usage.id, total_tokens=exc.usage_tokens, failed=True
                        )
                        raise
                    except BaseException:
                        await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
                        raise
                    await usage_service.settle(db, usage.id, total_tokens=res.total_tokens)
                    return res

                chat_res = await _run_public_completion()
                pub_ans = _parse_pub_reply(chat_res.content)
                if not social_only and is_abnormally_truncated_reply(pub_ans, req.question):
                    logger.warning(
                        "public_chat_truncated_reply_retry",
                        publication_id=row.id,
                        provider_id=runtime.provider_id,
                        raw_len=len(pub_ans.strip()),
                    )
                    retry_res = await _run_public_completion()
                    retry_ans = _parse_pub_reply(retry_res.content)
                    if retry_ans.strip():
                        pub_ans = retry_ans
            if not pub_ans or pub_ans == "{}":
                pub_ans = (
                    "Tôi đã ghi nhận câu hỏi của bạn. Về nội dung này, bạn có thể diễn đạt cụ thể hơn "
                    "hoặc cung cấp thêm chi tiết để mình hỗ trợ chính xác nhất nhé."
                )
            pub_draft: PublicDocumentDraft | None = None
            disabled_fmt = disabled_requested_format(req.question, export_formats)
            if disabled_fmt is not None:
                pub_ans = (
                    strip_document_markers(pub_ans, remove_blocks=True)
                    or disabled_format_refusal_message(disabled_fmt)
                )
            elif export_formats and not social_only:
                pub_ans, extracted_draft = extract_document_draft(
                    pub_ans,
                    req.question,
                    has_active_draft=latest_draft is not None,
                )
                if extracted_draft is None and latest_draft is not None:
                    req_fmt = requested_export_format(req.question)
                    if req_fmt is not None and req_fmt in export_formats:
                        extracted_draft = latest_draft
                if extracted_draft is not None:
                    extracted_draft = resolve_preferred_format(
                        extracted_draft, req.question, export_formats
                    )
                    pub_draft = await _store_public_draft(
                        req.session_id, row.id, extracted_draft, ttl
                    )
            else:
                pub_ans = strip_document_markers(pub_ans, remove_blocks=True)
            await _append_public_history(req.session_id, req.question, pub_ans, ttl)
            await _bump_stats(
                db,
                row.id,
                turns=1,
                insufficient_turns=0,
                tokens=budget.observed_tokens,
                day=day,
            )
            await db.commit()
            return PublicTurnResponse(
                status="answered",
                answer=pub_ans,
                message=None,
                citations=[],
                turns_remaining=remaining,
                model_name=selected_model_name,
                document_draft=pub_draft,
            )
        policy = AssistantRagPolicy.model_validate(assistant.rag_policy or {}).model_dump(
            mode="json", exclude={"guardrail_policy", "suggested_prompts"}
        )
        policy["metadata_filter"] = {}
        effective_persona = (
            (assistant.persona or "")
            + export_policy_prompt_addon(export_formats)
            + active_draft_prompt_context(latest_draft)
        )
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
                    provider_id=selected_provider_id,
                    max_output_tokens=assistant.max_output_tokens,
                    **policy,
                ),
                persona=effective_persona,
                reranker=reranker,
                compose_insufficient_message=True,
                collection_ids=collection_ids,
                public_channel=True,
                is_follow_up=prior_turns > 0,
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
    rag_draft: PublicDocumentDraft | None = None
    answer_override: str | None = None
    raw_rag_text = result.answer or ""
    disabled_rag_fmt = disabled_requested_format(req.question, export_formats)
    if disabled_rag_fmt is not None:
        if "<<<" in raw_rag_text:
            answer_override = (
                strip_document_markers(raw_rag_text, remove_blocks=True)
                or disabled_format_refusal_message(disabled_rag_fmt)
            )
    elif export_formats and not insufficient:
        display_rag_text, extracted_rag = extract_document_draft(
            raw_rag_text,
            req.question,
            has_active_draft=latest_draft is not None,
        )
        if extracted_rag is None and latest_draft is not None:
            req_fmt = requested_export_format(req.question)
            if req_fmt is not None and req_fmt in export_formats:
                extracted_rag = latest_draft
        if extracted_rag is not None:
            extracted_rag = resolve_preferred_format(
                extracted_rag, req.question, export_formats
            )
            rag_draft = await _store_public_draft(req.session_id, row.id, extracted_rag, ttl)
            if "<<<" in raw_rag_text:
                answer_override = display_rag_text
        elif "<<<" in raw_rag_text:
            answer_override = strip_document_markers(raw_rag_text)
    elif "<<<" in raw_rag_text:
        answer_override = strip_document_markers(raw_rag_text, remove_blocks=True)
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
    reply_payload = _public_reply(
        result,
        remaining,
        model_name=selected_model_name,
        document_draft=rag_draft,
        answer_override=answer_override,
    )
    if reply_payload.answer:
        await _append_public_history(req.session_id, req.question, reply_payload.answer, ttl)
    return reply_payload
