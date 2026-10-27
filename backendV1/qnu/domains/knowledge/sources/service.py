"""Source and revision use cases: store bytes, append a version, read the original file.

Ordering rule for uploads: validate → authorize (router) → write the content-addressed
blob → commit the database rows. Object storage is never assumed to be inside the
database transaction; the compensation is that the key is derived from the checksum,
so a retry rewrites exactly the same object instead of creating a second copy.

After a rollback every ORM instance is expired, so the conflict path only works with
plain identifiers captured before the transaction failed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.artifacts.files import (
    StoredFile,
    build_storage_key,
    detect_stored_file,
)
from qnu.domains.knowledge.ids import new_id
from qnu.domains.knowledge.models import (
    KBSource,
    KBSourceRevision,
    KBUploadRequest,
)
from qnu.domains.knowledge.policies.access import load_collection, load_revision, load_source
from qnu.domains.lifecycle.guards import visible
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.models import Workspace
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, DependencyUnavailable
from qnu.ports.blob_store import BlobStore


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    source: KBSource
    revision: KBSourceRevision
    replayed: bool = False


def _legacy_request_hash(
    workspace_id: str, collection_id: str, source_id: str | None, stored: StoredFile
) -> str:
    material = "|".join(
        (
            workspace_id,
            collection_id,
            source_id or "",
            stored.file_name,
            stored.sha256,
            str(stored.size_bytes),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _request_hash(
    workspace_id: str,
    collection_id: str,
    source_id: str | None,
    stored: StoredFile,
    title: str | None,
) -> str:
    material = {
        "version": 2,
        "workspace_id": workspace_id,
        "collection_id": collection_id,
        "source_id": source_id,
        "file_name": stored.file_name,
        "sha256": stored.sha256,
        "size_bytes": stored.size_bytes,
        "title": title,
    }
    return hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


class SourceService:
    """Callers resolve workspace access first; every lookup here is workspace-scoped."""

    async def upload(
        self,
        db: AsyncSession,
        blob_store: BlobStore,
        workspace: Workspace,
        collection_id: str,
        *,
        file_name: str,
        title: str | None,
        payload: bytes,
        max_bytes: int,
        actor: AuthActor,
        idempotency_key: str | None = None,
        source_id: str | None = None,
        staged: bool = False,
    ) -> UploadOutcome:
        ref = actor_ref(actor)
        workspace_id = workspace.id
        if source_id is not None and title is not None:
            raise AppException(
                "API thêm phiên bản không hỗ trợ thay tiêu đề nguồn.",
                code="revision_title_not_supported",
                status_code=422,
            )
        stored = detect_stored_file(file_name, payload, max_bytes)
        effective_title = (
            ((title or "").strip() or stored.file_name)[:255] if source_id is None else None
        )
        request_hash = _request_hash(
            workspace_id, collection_id, source_id, stored, effective_title
        )
        if staged:
            request_hash = hashlib.sha256((request_hash + ":staged").encode()).hexdigest()

        if idempotency_key:
            ledger = await self._find_idempotent(db, workspace_id, ref, idempotency_key)
            if ledger is not None:
                return await self._replay(
                    db,
                    workspace_id,
                    ledger,
                    request_hash,
                    legacy_hash=_legacy_request_hash(
                        workspace_id, collection_id, source_id, stored
                    ),
                    title=effective_title,
                )

        collection = await load_collection(db, workspace_id, collection_id)
        scoped_collection_id = collection.id
        if source_id is not None:
            await load_source(db, workspace_id, scoped_collection_id, source_id)
        owner = await self._content_owner(db, scoped_collection_id, stored.sha256)
        if owner is not None:
            raise self._duplicate_content(owner, source_id)

        storage_key = build_storage_key(workspace_id, scoped_collection_id, stored.sha256)
        try:
            await blob_store.put_bytes(storage_key, payload, stored.content_type)
        except Exception as exc:
            raise DependencyUnavailable(
                "Không ghi được tệp vào kho lưu trữ; chưa tạo nguồn tài liệu.",
                code="storage_unavailable",
            ) from exc

        try:
            if source_id is None:
                source, revision = await self._create_source(
                    db,
                    workspace_id=workspace_id,
                    collection_id=scoped_collection_id,
                    stored=stored,
                    storage_key=storage_key,
                    title=effective_title,
                    actor=actor,
                    ref=ref,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                )
            else:
                source, revision = await self._append_revision(
                    db,
                    workspace_id=workspace_id,
                    collection_id=scoped_collection_id,
                    source_id=source_id,
                    stored=stored,
                    storage_key=storage_key,
                    actor=actor,
                    ref=ref,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    staged=staged,
                )
            await db.flush()
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return await self._resolve_conflict(
                db,
                workspace_id=workspace_id,
                collection_id=scoped_collection_id,
                source_id=source_id,
                stored=stored,
                request_hash=request_hash,
                ref=ref,
                idempotency_key=idempotency_key,
                title=effective_title,
            )
        except Exception:
            await db.rollback()
            raise

        await db.refresh(source)
        await db.refresh(revision)
        return UploadOutcome(source=source, revision=revision)

    async def list_page(
        self,
        db: AsyncSession,
        workspace: Workspace,
        collection_id: str,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[KBSource, KBSourceRevision]], int]:
        collection = await load_collection(db, workspace.id, collection_id)
        condition = and_(
            KBSource.collection_id == collection.id,
            KBSource.workspace_id == workspace.id,
            visible("source", KBSource.id),
        )
        total = int(
            (await db.execute(select(func.count(KBSource.id)).where(condition))).scalar_one()
        )
        stmt = (
            select(KBSource, KBSourceRevision)
            .join(
                KBSourceRevision,
                and_(
                    KBSourceRevision.source_id == KBSource.id,
                    KBSourceRevision.revision_no == KBSource.latest_revision_no,
                ),
            )
            .where(condition)
            .order_by(KBSource.created_at.desc(), KBSource.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await db.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows], total

    async def get(
        self, db: AsyncSession, workspace: Workspace, collection_id: str, source_id: str
    ) -> tuple[KBSource, KBSourceRevision]:
        source = await load_source(db, workspace.id, collection_id, source_id)
        return source, await self._current_revision(db, source)

    async def list_revisions(
        self, db: AsyncSession, workspace: Workspace, collection_id: str, source_id: str
    ) -> list[KBSourceRevision]:
        source = await load_source(db, workspace.id, collection_id, source_id)
        stmt = (
            select(KBSourceRevision)
            .where(
                KBSourceRevision.source_id == source.id,
                KBSourceRevision.workspace_id == workspace.id,
            )
            .order_by(KBSourceRevision.revision_no.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def read_content(
        self,
        db: AsyncSession,
        blob_store: BlobStore,
        workspace: Workspace,
        collection_id: str,
        source_id: str,
        revision_id: str,
    ) -> tuple[KBSourceRevision, bytes]:
        await load_source(db, workspace.id, collection_id, source_id)
        revision = await load_revision(db, workspace.id, source_id, revision_id)
        try:
            payload = await blob_store.get_bytes(revision.storage_key)
        except FileNotFoundError as exc:
            raise AppException(
                "Tệp gốc không còn trong kho lưu trữ.",
                code="blob_missing",
                status_code=502,
                title="Thiếu tệp gốc",
            ) from exc
        except Exception as exc:
            raise DependencyUnavailable(
                "Không đọc được kho lưu trữ.", code="storage_unavailable"
            ) from exc

        if len(payload) != revision.size_bytes or (
            hashlib.sha256(payload).hexdigest() != revision.sha256
        ):
            raise AppException(
                "Tệp trả về không khớp checksum đã lưu.",
                code="blob_integrity_failed",
                status_code=502,
                title="Tệp gốc không toàn vẹn",
            )
        return revision, payload

    # ------------------------------------------------------------------ internals
    async def _create_source(
        self,
        db: AsyncSession,
        *,
        workspace_id: str,
        collection_id: str,
        stored: StoredFile,
        storage_key: str,
        title: str,
        actor: AuthActor,
        ref: str,
        idempotency_key: str | None,
        request_hash: str,
    ) -> tuple[KBSource, KBSourceRevision]:
        source = KBSource(
            id=new_id("src"),
            workspace_id=workspace_id,
            collection_id=collection_id,
            title=title[:255],
            status="stored",
            latest_revision_no=1,
            created_by=ref,
        )
        revision = KBSourceRevision(
            id=new_id("rev"),
            workspace_id=workspace_id,
            collection_id=collection_id,
            source_id=source.id,
            revision_no=1,
            file_name=stored.file_name,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            storage_key=storage_key,
            created_by=ref,
        )
        db.add(source)
        db.add(revision)
        await self._record_upload(
            db,
            workspace_id=workspace_id,
            collection_id=collection_id,
            source=source,
            revision=revision,
            actor=actor,
            ref=ref,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action="source.stored",
        )
        return source, revision

    async def _append_revision(
        self,
        db: AsyncSession,
        *,
        workspace_id: str,
        collection_id: str,
        source_id: str,
        stored: StoredFile,
        storage_key: str,
        actor: AuthActor,
        ref: str,
        idempotency_key: str | None,
        request_hash: str,
        staged: bool = False,
    ) -> tuple[KBSource, KBSourceRevision]:
        source = await load_source(db, workspace_id, collection_id, source_id, for_update=True)
        revision_no = source.latest_revision_no + 1
        source.latest_revision_no = revision_no
        if not staged:
            source.serving_revision_no = revision_no
        revision = KBSourceRevision(
            id=new_id("rev"),
            workspace_id=workspace_id,
            collection_id=collection_id,
            source_id=source.id,
            revision_no=revision_no,
            file_name=stored.file_name,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            storage_key=storage_key,
            created_by=ref,
        )
        db.add(revision)
        await self._record_upload(
            db,
            workspace_id=workspace_id,
            collection_id=collection_id,
            source=source,
            revision=revision,
            actor=actor,
            ref=ref,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action="source.revision_added",
        )
        return source, revision

    async def _record_upload(
        self,
        db: AsyncSession,
        *,
        workspace_id: str,
        collection_id: str,
        source: KBSource,
        revision: KBSourceRevision,
        actor: AuthActor,
        ref: str,
        idempotency_key: str | None,
        request_hash: str,
        action: str,
    ) -> None:
        if idempotency_key:
            db.add(
                KBUploadRequest(
                    id=new_id("upl"),
                    workspace_id=workspace_id,
                    collection_id=collection_id,
                    actor_ref=ref,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    source_id=source.id,
                    revision_id=revision.id,
                )
            )
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action=action,
            detail={
                "collection_id": collection_id,
                "source_id": source.id,
                "revision_no": revision.revision_no,
                "file_name": revision.file_name,
                "size_bytes": revision.size_bytes,
                "sha256": revision.sha256,
            },
        )

    async def _resolve_conflict(
        self,
        db: AsyncSession,
        *,
        workspace_id: str,
        collection_id: str,
        source_id: str | None,
        stored: StoredFile,
        request_hash: str,
        ref: str,
        idempotency_key: str | None,
        title: str | None,
    ) -> UploadOutcome:
        if idempotency_key:
            ledger = await self._find_idempotent(db, workspace_id, ref, idempotency_key)
            if ledger is not None:
                return await self._replay(
                    db,
                    workspace_id,
                    ledger,
                    request_hash,
                    legacy_hash=_legacy_request_hash(
                        workspace_id, collection_id, source_id, stored
                    ),
                    title=title,
                )
        owner = await self._content_owner(db, collection_id, stored.sha256)
        if owner is not None:
            raise self._duplicate_content(owner, source_id)
        raise Conflict(
            "Không ghi được nguồn tài liệu do dữ liệu thay đổi đồng thời.",
            code="source_write_conflict",
        )

    async def _replay(
        self,
        db: AsyncSession,
        workspace_id: str,
        ledger: KBUploadRequest,
        request_hash: str,
        *,
        legacy_hash: str,
        title: str | None,
    ) -> UploadOutcome:
        if ledger.request_hash not in {request_hash, legacy_hash}:
            raise Conflict(
                "Idempotency-Key đã được dùng cho một yêu cầu khác.",
                code="idempotency_conflict",
            )
        source = await load_source(db, workspace_id, ledger.collection_id, ledger.source_id)
        # Old ledgers omitted title. Require the persisted title as extra evidence;
        # never rewrite a ledger or accept changed metadata as an old replay.
        if ledger.request_hash != request_hash and title is not None and source.title != title:
            raise Conflict(
                "Idempotency-Key đã được dùng cho một yêu cầu khác.", code="idempotency_conflict"
            )
        revision = await load_revision(db, workspace_id, source.id, ledger.revision_id)
        return UploadOutcome(source=source, revision=revision, replayed=True)

    async def _find_idempotent(
        self, db: AsyncSession, workspace_id: str, ref: str, key: str
    ) -> KBUploadRequest | None:
        stmt = select(KBUploadRequest).where(
            KBUploadRequest.workspace_id == workspace_id,
            KBUploadRequest.actor_ref == ref,
            KBUploadRequest.idempotency_key == key,
        )
        return (await db.execute(stmt)).scalars().first()

    async def _content_owner(self, db: AsyncSession, collection_id: str, sha256: str) -> str | None:
        stmt = (
            select(KBSourceRevision.source_id)
            .where(
                KBSourceRevision.collection_id == collection_id,
                KBSourceRevision.sha256 == sha256,
            )
            .limit(1)
        )
        return (await db.execute(stmt)).scalars().first()

    async def _current_revision(self, db: AsyncSession, source: KBSource) -> KBSourceRevision:
        stmt = select(KBSourceRevision).where(
            KBSourceRevision.source_id == source.id,
            KBSourceRevision.revision_no == source.latest_revision_no,
        )
        revision = (await db.execute(stmt)).scalars().first()
        if revision is None:
            raise AppException(
                "Nguồn tài liệu không có phiên bản hiện tại.",
                code="revision_missing",
                status_code=500,
                title="Dữ liệu nguồn không nhất quán",
            )
        return revision

    def _duplicate_content(self, owner_source_id: str, target_source_id: str | None) -> Conflict:
        if target_source_id is not None and owner_source_id == target_source_id:
            return Conflict(
                "Nội dung tệp không thay đổi so với phiên bản hiện tại của nguồn.",
                code="revision_unchanged",
            )
        return Conflict(
            f"Nội dung tệp đã tồn tại trong kho tri thức (nguồn {owner_source_id}).",
            code="duplicate_content",
        )


source_service = SourceService()
