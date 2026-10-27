"""Register immutable Compiler outputs as versions of explicit document identities."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.publication.access import authorize, document
from qnu.domains.knowledge.publication.evidence import digest, load_bundle, registered_bundle_hash
from qnu.domains.knowledge.publication.models import (
    CompiledDocument,
    CompiledVersion,
    PublicationDecision,
)
from qnu.domains.knowledge.publication.schemas import CreateDocumentRequest, RegisterVersionRequest
from qnu.domains.lifecycle.guards import visible
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import Conflict
from qnu.ports.blob_store import BlobStore


@dataclass(frozen=True, slots=True)
class Registration:
    document: CompiledDocument
    version: CompiledVersion
    created: bool


async def _replay(
    db: AsyncSession, workspace_id: str, actor: AuthActor, key: str, request_hash: str
) -> Registration | None:
    row = await db.scalar(
        select(CompiledVersion).where(
            CompiledVersion.workspace_id == workspace_id,
            CompiledVersion.created_by == actor_ref(actor),
            CompiledVersion.idempotency_key == key,
        )
    )
    if row is None:
        return None
    if row.request_hash != request_hash:
        raise Conflict("Idempotency-Key đã dùng cho yêu cầu khác.", code="idempotency_conflict")
    doc = await document(db, row.workspace_id, row.collection_id, row.document_id)
    await db.commit()
    return Registration(doc, row, False)


async def create_document(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    req: CreateDocumentRequest,
    key: str,
) -> Registration:
    await authorize(db, actor, workspace_id, collection_id, write=True)
    request_hash = digest(
        {
            "operation": "create_document",
            "collection_id": collection_id,
            **req.model_dump(
                mode="json", exclude={"retrieval_metadata"} if not req.retrieval_metadata else set()
            ),
        }
    )
    old = await _replay(db, workspace_id, actor, key, request_hash)
    if old:
        return old
    existing = await db.scalar(
        select(CompiledDocument.id).where(
            CompiledDocument.workspace_id == workspace_id,
            CompiledDocument.collection_id == collection_id,
            CompiledDocument.document_key == req.document_key,
        )
    )
    if existing is not None:
        raise Conflict(
            "Document key đã tồn tại; thêm phiên bản vào tài liệu đó.",
            code="compiled_document_key_exists",
        )
    doc = CompiledDocument(
        id=new_id("cdoc"),
        workspace_id=workspace_id,
        collection_id=collection_id,
        document_key=req.document_key,
        title=req.title,
        change_sequence=1,
        created_by=actor_ref(actor),
    )
    db.add(doc)
    await db.flush()
    return await _register(db, blob, actor, doc, req, key, request_hash)


async def register_version(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    document_id: str,
    req: RegisterVersionRequest,
    key: str,
) -> Registration:
    await authorize(db, actor, workspace_id, collection_id, write=True)
    doc = await document(db, workspace_id, collection_id, document_id, lock=True)
    request_hash = digest(
        {
            "operation": "register_version",
            "document_id": document_id,
            "collection_id": collection_id,
            **req.model_dump(
                mode="json", exclude={"retrieval_metadata"} if not req.retrieval_metadata else set()
            ),
        }
    )
    old = await _replay(db, workspace_id, actor, key, request_hash)
    if old:
        return old
    return await _register(db, blob, actor, doc, req, key, request_hash)


async def _register(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    doc: CompiledDocument,
    req: RegisterVersionRequest,
    key: str,
    request_hash: str,
) -> Registration:
    run_id = req.compilation_run_id
    bundle = await load_bundle(db, blob, doc.workspace_id, doc.collection_id, run_id)
    annotations = [a.model_dump(mode="json", exclude_none=True) for a in req.retrieval_metadata]
    bundle_hash = registered_bundle_hash(bundle, annotations)
    if await db.scalar(
        select(CompiledVersion.id).where(CompiledVersion.compilation_run_id == run_id)
    ):
        raise Conflict("Compiler run đã đăng ký thành phiên bản.", code="compiled_run_registered")
    latest = await db.scalar(
        select(func.max(CompiledVersion.version_no)).where(CompiledVersion.document_id == doc.id)
    )
    row = CompiledVersion(
        id=new_id("cver"),
        document_id=doc.id,
        workspace_id=doc.workspace_id,
        collection_id=doc.collection_id,
        compilation_run_id=run_id,
        version_no=int(latest or 0) + 1,
        status="draft",
        state_version=1,
        input_sha256=bundle.input_sha256,
        draft_sha256=bundle.draft_sha256,
        markdown_sha256=bundle.markdown_sha256,
        bundle_sha256=bundle_hash,
        retrieval_metadata=annotations,
        provenance=bundle.provenance,
        created_by=actor_ref(actor),
        idempotency_key=key,
        request_hash=request_hash,
    )
    db.add(row)
    doc.change_sequence += 1
    await record_workspace_event(
        db,
        workspace_id=doc.workspace_id,
        actor=actor,
        action="compiled_version.registered",
        detail={
            "document_id": doc.id,
            "version_id": row.id,
            "run_id": run_id,
            "bundle_sha256": bundle_hash,
        },
    )
    await db.commit()
    return Registration(doc, row, True)


async def list_documents(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    limit: int,
    offset: int,
) -> list[CompiledDocument]:
    await authorize(db, actor, workspace_id, collection_id)
    return list(
        (
            await db.scalars(
                select(CompiledDocument)
                .where(
                    CompiledDocument.workspace_id == workspace_id,
                    CompiledDocument.collection_id == collection_id,
                    visible("document", CompiledDocument.id),
                )
                .order_by(CompiledDocument.created_at, CompiledDocument.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )


async def versions(
    db: AsyncSession, doc: CompiledDocument, limit: int, offset: int
) -> list[CompiledVersion]:
    return list(
        (
            await db.scalars(
                select(CompiledVersion)
                .where(CompiledVersion.document_id == doc.id)
                .order_by(CompiledVersion.version_no.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )


async def history(
    db: AsyncSession, doc: CompiledDocument, limit: int, offset: int
) -> list[PublicationDecision]:
    return list(
        (
            await db.scalars(
                select(PublicationDecision)
                .where(PublicationDecision.document_id == doc.id)
                .order_by(PublicationDecision.document_sequence)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
