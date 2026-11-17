"""System ModelOps defaults for AI compilation, preparation and review.

The document group is an ordered list of chat models with a per-model limit. It is
separate from the chatbot chat model: document work never changes the chat default.

``document_provider_id``/``document_concurrency`` remain the legacy single-target
contract. Rows written before the group existed keep working through the same read
path, and old clients can keep writing those two fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.audit import record_event
from qnu.domains.modelops.models import DEFAULT_ROW_ID, ModelDefaults, Provider
from qnu.domains.modelops.providers.service import provider_service
from qnu.domains.modelops.reasoning import EXTRA_CONFIG_KEY, parse_policy, trace_for
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.platform.logging import get_logger

logger = get_logger(__name__)

DEFAULT_DOCUMENT_CONCURRENCY = 1
MAX_DOCUMENT_MODELS = 8
MAX_DOCUMENT_CONCURRENCY = 64
DocumentMode = Literal["priority", "parallel"]
ThinkingLevel = Literal["server", "low", "off"]
ModelID = Annotated[str, Field(min_length=1, max_length=64)]
Concurrency = Annotated[int, Field(ge=1, le=MAX_DOCUMENT_CONCURRENCY)]


def _invalid(detail: str) -> AppException:
    return AppException(detail, code="document_models_invalid", status_code=422)


class DocumentModelInput(BaseModel):
    """One registered chat model in the document group, in priority order."""

    model_config = ConfigDict(strict=True, extra="forbid")

    provider_id: ModelID
    concurrency: Concurrency = DEFAULT_DOCUMENT_CONCURRENCY


class DocumentProcessingUpdate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    mode: DocumentMode | None = None
    models: list[DocumentModelInput] | None = None
    # Deprecated single-target fields, translated by ``update`` for old clients.
    provider_id: ModelID | None = None
    concurrency: dict[ModelID, Concurrency] = Field(default_factory=dict)


class DocumentThinking(BaseModel):
    """Declared compiler level, the level actually applied and why."""

    configured: ThinkingLevel
    effective: ThinkingLevel
    verified: bool
    status: str
    reason: str | None = None


class DocumentModel(BaseModel):
    provider_id: str
    name: str
    model_name: str
    concurrency: int
    effective_concurrency: int
    available: bool
    thinking: DocumentThinking


class DocumentProcessingSettings(BaseModel):
    mode: DocumentMode
    models: list[DocumentModel]
    max_concurrency: int
    shared_concurrency: int
    # Legacy mirror, kept while old clients still read these two fields.
    provider_id: str | None = None
    concurrency: dict[str, int] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GroupModel:
    provider_id: str
    concurrency: int


@dataclass(frozen=True, slots=True)
class DocumentGroup:
    """Ordered models a document run may use; empty means the chat default."""

    mode: str
    models: tuple[GroupModel, ...]

    @property
    def provider_id(self) -> str | None:
        return self.models[0].provider_id if self.models else None


def shared_concurrency() -> int:
    """Default admission limit for one endpoint+model, from the environment.

    Document runs pin their configured per-model limit and only use this value as
    the floor, so it never caps a limit chosen in the interface.
    """
    return get_settings().MODEL_CHAT_CONCURRENCY


def bounded_limit(requested: int | None) -> int:
    """The configured limit as saved; only the product-wide cap can lower it."""
    return max(
        1, min(requested or DEFAULT_DOCUMENT_CONCURRENCY, MAX_DOCUMENT_CONCURRENCY)
    )


def thinking_for(extra_config: dict | None) -> DocumentThinking:
    policy = parse_policy((extra_config or {}).get(EXTRA_CONFIG_KEY))
    trace = trace_for(policy, "compiler")
    level = policy.level_for("compiler") if policy is not None else None
    applied = bool(trace.get("applied"))
    return DocumentThinking(
        configured="server" if level is None else level,
        effective=str(trace.get("level")) if applied else "server",
        verified=bool(policy is not None and policy.verified and level is not None),
        status=str(
            trace.get("status")
            or ("server_default" if policy is not None else "not_configured")
        ),
        reason=trace.get("reason"),
    )


def _stored_models(row: ModelDefaults | None) -> list[DocumentModelInput]:
    if row is None:
        return []
    if row.document_models is not None:
        entries: list[DocumentModelInput] = []
        for item in row.document_models:
            try:
                entries.append(DocumentModelInput.model_validate(item))
            except Exception as exc:  # A corrupted entry must not hide the rest
                logger.warning(
                    "document_model_entry_invalid",
                    provider_id=(item or {}).get("provider_id"),
                    error_type=type(exc).__name__,
                )
                continue
        return entries[:MAX_DOCUMENT_MODELS]
    if row.document_provider_id is None:
        return []
    limits = row.document_concurrency or {}
    return [
        DocumentModelInput(
            provider_id=row.document_provider_id,
            concurrency=limits.get(
                row.document_provider_id, DEFAULT_DOCUMENT_CONCURRENCY
            ),
        )
    ]


def _stored_mode(row: ModelDefaults | None) -> DocumentMode:
    mode = row.document_mode if row is not None else None
    return mode if mode in {"priority", "parallel"} else "priority"


def _is_available(provider: Provider | None, parents: dict[str, Provider]) -> bool:
    if provider is None or not provider.is_active or provider.is_connection:
        return False
    if "chat" not in (provider.capabilities or []):
        return False
    if provider.parent_id:
        parent = parents.get(provider.parent_id)
        if parent is None or not parent.is_active:
            return False
    return True


async def _load_providers(
    db: AsyncSession, ids: list[str]
) -> tuple[dict[str, Provider], dict[str, Provider]]:
    if not ids:
        return {}, {}
    rows = list((await db.scalars(select(Provider).where(Provider.id.in_(ids)))).all())
    parents = {
        parent_id
        for row in rows
        if (parent_id := row.parent_id) is not None
    } - {row.id for row in rows}
    parent_rows = (
        list((await db.scalars(select(Provider).where(Provider.id.in_(parents)))).all())
        if parents
        else []
    )
    return {row.id: row for row in rows}, {row.id: row for row in parent_rows}


async def document_provider(db: AsyncSession) -> str | None:
    row = await db.get(ModelDefaults, DEFAULT_ROW_ID)
    return row.document_provider_id if row is not None else None


async def configured_concurrency(db: AsyncSession, provider_id: str) -> int:
    row = await db.get(ModelDefaults, DEFAULT_ROW_ID)
    for entry in _stored_models(row):
        if entry.provider_id == provider_id:
            return bounded_limit(entry.concurrency)
    return DEFAULT_DOCUMENT_CONCURRENCY


async def resolve_document_group(
    db: AsyncSession, requested_provider_id: str | None = None
) -> DocumentGroup:
    """Ordered usable models for a document run.

    An explicit request pins exactly that model. Otherwise a priority-mode group is
    truncated to its first entry, and entries that are disabled, missing or without
    the chat capability are skipped. An empty result keeps the chat default contract.
    """
    if requested_provider_id is not None:
        # An explicit request pins that model, but its saved limit still applies.
        row = await db.get(ModelDefaults, DEFAULT_ROW_ID)
        limit = next(
            (
                bounded_limit(entry.concurrency)
                for entry in _stored_models(row)
                if entry.provider_id == requested_provider_id
            ),
            DEFAULT_DOCUMENT_CONCURRENCY,
        )
        return DocumentGroup(
            "priority", (GroupModel(requested_provider_id, limit),)
        )
    row = await db.get(ModelDefaults, DEFAULT_ROW_ID)
    stored = _stored_models(row)
    mode = _stored_mode(row)
    if not stored:
        return DocumentGroup(mode, ())
    if mode == "priority":
        stored = stored[:1]
    providers, parents = await _load_providers(
        db, [entry.provider_id for entry in stored]
    )
    models = tuple(
        GroupModel(entry.provider_id, bounded_limit(entry.concurrency))
        for entry in stored
        if _is_available(providers.get(entry.provider_id), parents)
    )
    return DocumentGroup(mode, models)


async def _settings(
    db: AsyncSession, row: ModelDefaults | None
) -> DocumentProcessingSettings:
    stored = _stored_models(row)
    providers, parents = await _load_providers(
        db, [entry.provider_id for entry in stored]
    )
    models = []
    for entry in stored:
        provider = providers.get(entry.provider_id)
        models.append(
            DocumentModel(
                provider_id=entry.provider_id,
                name=provider.name if provider is not None else "Model đã xóa",
                model_name=(
                    provider.model_name if provider is not None else entry.provider_id
                ),
                concurrency=entry.concurrency,
                effective_concurrency=entry.concurrency,
                available=_is_available(provider, parents),
                thinking=thinking_for(
                    provider.extra_config if provider is not None else None
                ),
            )
        )
    return DocumentProcessingSettings(
        mode=_stored_mode(row),
        models=models,
        max_concurrency=MAX_DOCUMENT_CONCURRENCY,
        shared_concurrency=shared_concurrency(),
        provider_id=row.document_provider_id if row is not None else None,
        concurrency=(row.document_concurrency or {}) if row is not None else {},
    )


async def read(db: AsyncSession) -> DocumentProcessingSettings:
    return await _settings(db, await db.get(ModelDefaults, DEFAULT_ROW_ID))


def _validated_group(body: DocumentProcessingUpdate) -> list[DocumentModelInput]:
    entries = body.models or []
    if len(entries) > MAX_DOCUMENT_MODELS:
        raise _invalid(f"Chỉ được thêm tối đa {MAX_DOCUMENT_MODELS} model xử lý văn bản.")
    ids = [entry.provider_id for entry in entries]
    if len(ids) != len(set(ids)):
        raise _invalid("Một model chỉ được thêm một lần.")
    return entries


async def update(
    db: AsyncSession, body: DocumentProcessingUpdate, actor: AuthActor
) -> DocumentProcessingSettings:
    require_model_admin(actor)
    writes_group = "models" in body.model_fields_set
    writes_legacy = bool(body.model_fields_set & {"provider_id", "concurrency"})
    entries = _validated_group(body) if writes_group else []
    if writes_group:
        for entry in entries:
            await provider_service.require_capability(db, entry.provider_id, "chat")
    if writes_legacy:
        targets = set(body.concurrency)
        if body.provider_id is not None:
            targets.add(body.provider_id)
        for provider_id in sorted(targets):
            await provider_service.require_capability(db, provider_id, "chat")

    await db.execute(insert(ModelDefaults).values(id=DEFAULT_ROW_ID).on_conflict_do_nothing())
    row = await db.scalar(
        select(ModelDefaults).where(ModelDefaults.id == DEFAULT_ROW_ID).with_for_update()
    )
    assert row is not None
    if writes_group:
        row.document_models = [entry.model_dump() for entry in entries]
        row.document_provider_id = entries[0].provider_id if entries else None
        row.document_concurrency = {
            entry.provider_id: entry.concurrency
            for entry in entries
            if entry.concurrency != DEFAULT_DOCUMENT_CONCURRENCY
        } or None
    elif writes_legacy:
        if "provider_id" in body.model_fields_set:
            row.document_provider_id = body.provider_id
        if body.concurrency:
            limits = {**(row.document_concurrency or {}), **body.concurrency}
            row.document_concurrency = {
                provider_id: limit
                for provider_id, limit in limits.items()
                if limit != DEFAULT_DOCUMENT_CONCURRENCY
            }
        # A legacy write owns the whole contract; never mix it with a stored group.
        row.document_models = None
    if "mode" in body.model_fields_set:
        row.document_mode = body.mode or "priority"
    record_event(db, actor, "document_processing.updated", fields=list(body.model_fields_set))
    await db.commit()
    await db.refresh(row)
    return await _settings(db, row)
