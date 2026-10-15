"""Collection glossary service — approval-gated search aliases.

Only approved, in-scope, non-revoked entries ever reach retrieval. Every
retrieval-affecting change (approve, edit of an approved entry, revoke,
feature toggle) bumps the collection glossary version inside the same
transaction as the data and audit rows, and invalidates the semantic cache.
"""

from __future__ import annotations

import inspect
import logging
import re
import unicodedata
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.glossary_schemas import (
    GlossaryReview,
    GlossarySettingsUpdate,
    GlossaryTermCreate,
    GlossaryTermUpdate,
)
from app.modules.knowledge.models import (
    KnowledgeGlossaryAudit,
    KnowledgeGlossarySetting,
    KnowledgeGlossaryTerm,
)
from app.modules.knowledge.services.scope_helper import get_scoped_collection

logger = logging.getLogger(__name__)

PERMISSION_MANAGE = "ai.knowledge.update"
PERMISSION_REVIEW = "ai.knowledge.review"
PERMISSION_VIEW = "ai.knowledge.view"

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_REVOKED = "revoked"

_REVIEW_TRANSITIONS = {
    "approve": {"pending", "rejected"},
    "reject": {"pending"},
    "revoke": {"approved"},
}
_REVIEW_TARGETS = {"approve": STATUS_APPROVED, "reject": STATUS_REJECTED, "revoke": STATUS_REVOKED}


@asynccontextmanager
async def _read_savepoint(db: AsyncSession) -> AsyncIterator[None]:
    transaction = db.begin_nested()
    if inspect.iscoroutine(transaction):
        transaction = await transaction
    async with transaction:
        yield


def normalize_phrase(value: str) -> str:
    """NFC + whitespace + casefold duplicate detection. Never strips diacritics."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value or "")).strip().casefold()


def _require(actor: AuthActor | Any | None, permission: str) -> AuthActor:
    if actor is None or not actor.has_permission(permission):
        raise AppException(
            f"Tài khoản không có quyền '{permission}' để thực hiện hành động này.",
            code="forbidden",
            status_code=403,
        )
    return actor


def _check_version(current: int, expected: int) -> None:
    if current != expected:
        raise AppException(
            "Dữ liệu đã thay đổi bởi người khác; hãy tải lại và thử lại.",
            code="GLOSSARY_VERSION_CONFLICT",
            status_code=409,
        )


async def _get_settings_locked(db: AsyncSession, collection_id: str) -> KnowledgeGlossarySetting:
    stmt = select(KnowledgeGlossarySetting).where(
        KnowledgeGlossarySetting.collection_id == collection_id).with_for_update().execution_options(
            populate_existing=True)
    settings = await _fetch_one(db, stmt)
    if settings is None:
        settings = KnowledgeGlossarySetting(collection_id=collection_id, is_enabled=False, version=1)
        db.add(settings)
    return settings


async def _bump_settings(db: AsyncSession, collection_id: str, actor_id: str | None) -> KnowledgeGlossarySetting:
    settings = await _get_settings_locked(db, collection_id)
    settings.version = (settings.version or 0) + 1
    settings.updated_by = actor_id
    return settings


async def _invalidate(db: AsyncSession, collection_id: str) -> None:
    from app.core.redis import semantic_cache

    await semantic_cache.invalidate_collection(collection_id=collection_id)


def _term_or_404(term: KnowledgeGlossaryTerm | None, term_id: str) -> KnowledgeGlossaryTerm:
    if term is None:
        raise EntityNotFoundError(f"Không tìm thấy thuật ngữ '{term_id}' trong phạm vi quản lý.")
    return term


async def _fetch_one(db: AsyncSession, stmt: Any) -> Any | None:
    """Await each DB layer, tolerating sync and async test doubles like scope_helper."""
    res = await db.execute(stmt)
    if inspect.isawaitable(res):
        res = await res
    row = res.scalar_one_or_none()
    if inspect.isawaitable(row):
        row = await row
    return row


async def _fetch_all(db: AsyncSession, stmt: Any) -> list[Any]:
    res = await db.execute(stmt)
    if inspect.isawaitable(res):
        res = await res
    scalars = res.scalars()
    if inspect.isawaitable(scalars):
        scalars = await scalars
    rows = scalars.all()
    if inspect.isawaitable(rows):
        rows = await rows
    return list(rows)


async def _fetch_get(db: AsyncSession, model: Any, key: Any) -> Any | None:
    row = await db.get(model, key)
    if inspect.isawaitable(row):
        row = await row
    return row


class GlossaryService:
    """Manage glossary lifecycle; retrieval reads go through load_approved_terms."""

    async def create_term(
        self, db: AsyncSession, actor: AuthActor | Any | None,
        collection_id: str, payload: GlossaryTermCreate,
    ) -> KnowledgeGlossaryTerm:
        actor = _require(actor, PERMISSION_MANAGE)
        try:
            collection = await get_scoped_collection(db, collection_id, actor)
            term = KnowledgeGlossaryTerm(
                collection_id=collection.id, user_phrase=payload.user_phrase.strip(),
                phrase_normalized=normalize_phrase(payload.user_phrase),
                target_term=payload.target_term.strip(), note=payload.note or "",
                scope=dict(payload.scope or {}), status=STATUS_PENDING,
                created_by=getattr(actor, "actor_id", None),
            )
            db.add(term)
            db.add(KnowledgeGlossaryAudit(
                collection_id=collection.id, action="create",
                actor_id=getattr(actor, "actor_id", None)))
            await db.flush()
            await db.commit()
            return term
        except AppException:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            raise AppException("Không lưu được thuật ngữ do lỗi dữ liệu.",
                               code="GLOSSARY_STORE_UNAVAILABLE", status_code=503) from exc

    async def _load_term_for_update(
        self, db: AsyncSession, actor: AuthActor, term_id: str,
    ) -> tuple[KnowledgeGlossaryTerm, Any]:
        stmt = select(KnowledgeGlossaryTerm).where(
            KnowledgeGlossaryTerm.id == term_id).with_for_update().execution_options(
                populate_existing=True)
        term = await _fetch_one(db, stmt)
        term = _term_or_404(term, term_id)
        collection = await get_scoped_collection(db, term.collection_id, actor, for_update=True)
        return term, collection

    async def update_term(
        self, db: AsyncSession, actor: AuthActor | Any | None,
        term_id: str, payload: GlossaryTermUpdate,
    ) -> KnowledgeGlossaryTerm:
        actor = _require(actor, PERMISSION_MANAGE)
        try:
            term, collection = await self._load_term_for_update(db, actor, term_id)
            _check_version(term.version, payload.expected_version)
            changed_scope = False
            if payload.user_phrase is not None and payload.user_phrase.strip() != term.user_phrase:
                term.user_phrase = payload.user_phrase.strip()
                term.phrase_normalized = normalize_phrase(payload.user_phrase)
                changed_scope = True
            if payload.target_term is not None and payload.target_term.strip() != term.target_term:
                term.target_term = payload.target_term.strip()
                changed_scope = True
            if payload.scope is not None and dict(payload.scope) != dict(term.scope or {}):
                term.scope = dict(payload.scope)
                changed_scope = True
            if payload.note is not None:
                term.note = payload.note
            reverted = False
            if term.status == STATUS_APPROVED and changed_scope:
                term.status = STATUS_PENDING
                term.reviewed_by = None
                term.review_reason = "Sửa cụm từ/phạm vi của mục đã duyệt, quay về chờ duyệt."
                reverted = True
            term.version = (term.version or 0) + 1
            term.updated_by = getattr(actor, "actor_id", None)
            db.add(KnowledgeGlossaryAudit(
                entry_id=term.id, collection_id=collection.id,
                action="revert_to_pending" if reverted else "update",
                actor_id=getattr(actor, "actor_id", None)))
            if reverted:
                await _bump_settings(db, collection.id, getattr(actor, "actor_id", None))
                await _invalidate(db, collection.id)
            await db.flush()
            await db.commit()
            return term
        except AppException:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            raise AppException("Không lưu được thuật ngữ do lỗi dữ liệu.",
                               code="GLOSSARY_STORE_UNAVAILABLE", status_code=503) from exc

    async def review_term(
        self, db: AsyncSession, actor: AuthActor | Any | None,
        term_id: str, payload: GlossaryReview,
    ) -> KnowledgeGlossaryTerm:
        actor = _require(actor, PERMISSION_REVIEW)
        try:
            term, collection = await self._load_term_for_update(db, actor, term_id)
            _check_version(term.version, payload.expected_version)
            allowed = _REVIEW_TRANSITIONS[payload.action]
            if term.status not in allowed:
                raise AppException(
                    f"Không thể '{payload.action}' mục đang ở trạng thái '{term.status}'.",
                    code="GLOSSARY_INVALID_TRANSITION", status_code=409)
            term.status = _REVIEW_TARGETS[payload.action]
            term.reviewed_by = getattr(actor, "actor_id", None)
            term.review_reason = payload.reason
            from datetime import UTC, datetime

            term.reviewed_at = datetime.now(UTC)
            term.version = (term.version or 0) + 1
            db.add(KnowledgeGlossaryAudit(
                entry_id=term.id, collection_id=collection.id, action=payload.action,
                actor_id=getattr(actor, "actor_id", None), reason=payload.reason))
            if payload.action in ("approve", "revoke"):
                await _bump_settings(db, collection.id, getattr(actor, "actor_id", None))
                await _invalidate(db, collection.id)
            await db.flush()
            await db.commit()
            return term
        except AppException:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            raise AppException("Không lưu được quyết định duyệt do lỗi dữ liệu.",
                               code="GLOSSARY_STORE_UNAVAILABLE", status_code=503) from exc

    async def get_term(
        self, db: AsyncSession, actor: AuthActor | Any | None, term_id: str,
    ) -> KnowledgeGlossaryTerm:
        actor = _require(actor, PERMISSION_VIEW)
        term = await _fetch_get(db, KnowledgeGlossaryTerm, term_id)
        term = _term_or_404(term, term_id)
        await get_scoped_collection(db, term.collection_id, actor)
        return term

    async def list_terms(
        self, db: AsyncSession, actor: AuthActor | Any | None, collection_id: str,
        *, search: str | None = None, status: str | None = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[KnowledgeGlossaryTerm], int]:
        actor = _require(actor, PERMISSION_VIEW)
        collection = await get_scoped_collection(db, collection_id, actor)
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        stmt = select(KnowledgeGlossaryTerm).where(
            KnowledgeGlossaryTerm.collection_id == collection.id)
        if status:
            stmt = stmt.where(KnowledgeGlossaryTerm.status == status)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(sa.or_(
                KnowledgeGlossaryTerm.user_phrase.ilike(pattern),
                KnowledgeGlossaryTerm.target_term.ilike(pattern)))
        total = await _fetch_one(db, select(func.count()).select_from(stmt.subquery()))
        items = await _fetch_all(db, stmt.order_by(
            KnowledgeGlossaryTerm.updated_at.desc()).offset((page - 1) * page_size).limit(page_size))
        return list(items), int(total or 0)

    async def get_settings(
        self, db: AsyncSession, actor: AuthActor | Any | None, collection_id: str,
    ) -> KnowledgeGlossarySetting:
        actor = _require(actor, PERMISSION_VIEW)
        collection = await get_scoped_collection(db, collection_id, actor)
        settings = await _fetch_get(db, KnowledgeGlossarySetting, collection.id)
        if settings is None:
            settings = KnowledgeGlossarySetting(collection_id=collection.id)
        return settings

    async def update_settings(
        self, db: AsyncSession, actor: AuthActor | Any | None,
        collection_id: str, payload: GlossarySettingsUpdate,
    ) -> KnowledgeGlossarySetting:
        actor = _require(actor, PERMISSION_REVIEW)
        try:
            collection = await get_scoped_collection(db, collection_id, actor, for_update=True)
            settings = await _get_settings_locked(db, collection.id)
            _check_version(settings.version, payload.expected_version)
            settings.is_enabled = payload.is_enabled
            settings.version = (settings.version or 0) + 1
            settings.updated_by = getattr(actor, "actor_id", None)
            db.add(KnowledgeGlossaryAudit(
                entry_id=None, collection_id=collection.id,
                action="toggle_on" if payload.is_enabled else "toggle_off",
                actor_id=getattr(actor, "actor_id", None)))
            await _invalidate(db, collection.id)
            await db.flush()
            await db.commit()
            return settings
        except AppException:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            raise AppException("Không lưu được cấu hình thuật ngữ do lỗi dữ liệu.",
                               code="GLOSSARY_STORE_UNAVAILABLE", status_code=503) from exc

    async def load_approved_terms(
        self, db: AsyncSession, collection_id: str,
    ) -> list[KnowledgeGlossaryTerm]:
        """Retrieval-side loader: approved, in-scope, non-revoked entries only."""
        try:
            stmt = select(KnowledgeGlossaryTerm).where(
                KnowledgeGlossaryTerm.collection_id == collection_id,
                KnowledgeGlossaryTerm.status == STATUS_APPROVED)
            async with _read_savepoint(db):
                rows = await _fetch_all(db, stmt)
            return list(rows)
        except ProgrammingError as exc:
            if getattr(exc.orig, "sqlstate", None) == "42P01":
                logger.info("Glossary tables unavailable; retrieval continues without aliases.")
                return []
            raise AppException("Không tải được thuật ngữ do lỗi dữ liệu.",
                               code="GLOSSARY_STORE_UNAVAILABLE", status_code=503) from exc
        except Exception as exc:
            raise AppException("Không tải được thuật ngữ do lỗi dữ liệu.",
                               code="GLOSSARY_STORE_UNAVAILABLE", status_code=503) from exc

    async def glossary_cache_version(
        self, db: AsyncSession, collection_id: str,
    ) -> int:
        """Collection glossary version for cache keys; 0 when disabled or absent."""
        try:
            stmt = select(KnowledgeGlossarySetting).where(
                KnowledgeGlossarySetting.collection_id == collection_id)
            async with _read_savepoint(db):
                settings = await _fetch_one(db, stmt)
            if settings is None or not settings.is_enabled:
                return 0
            return int(settings.version or 0)
        except ProgrammingError as exc:
            if getattr(exc.orig, "sqlstate", None) == "42P01":
                logger.info("Glossary settings unavailable; retrieval continues without aliases.")
                return 0
            raise AppException("Không tải được phiên bản thuật ngữ do lỗi dữ liệu.",
                               code="GLOSSARY_STORE_UNAVAILABLE", status_code=503) from exc
        except Exception as exc:
            raise AppException("Không tải được phiên bản thuật ngữ do lỗi dữ liệu.",
                               code="GLOSSARY_STORE_UNAVAILABLE", status_code=503) from exc


glossary_service = GlossaryService()
