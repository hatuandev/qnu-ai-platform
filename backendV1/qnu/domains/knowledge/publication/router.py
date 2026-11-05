"""Document/version and explicit publication-decision HTTP contracts."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db, get_job_queue
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.publication import access, decisions, reading, review_gate, service
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.knowledge.publication.models import (
    CompiledDocument,
    CompiledVersion,
    PublicationDecision,
    PublicationPreview,
)
from qnu.domains.knowledge.publication.schemas import (
    CommitRequest,
    CreateDocumentRequest,
    DecisionResponse,
    DocumentResponse,
    PreviewRequest,
    PreviewResponse,
    PublishedResponse,
    RegisterVersionRequest,
    RegistrationResponse,
    VersionResponse,
)
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}/compiled-documents",
    tags=["Knowledge · Compiled publication"],
)
Key = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"),
]
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]


def _registration(outcome: service.Registration, response: Response) -> RegistrationResponse:
    response.status_code = 201 if outcome.created else 200
    return RegistrationResponse(
        document=DocumentResponse.model_validate(outcome.document),
        version=VersionResponse.model_validate(outcome.version),
        created=outcome.created,
    )


@router.post("", response_model=RegistrationResponse, status_code=201)
async def create_document(
    workspace_id: str,
    collection_id: str,
    body: CreateDocumentRequest,
    response: Response,
    idempotency_key: Key,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> RegistrationResponse:
    return _registration(
        await service.create_document(
            db, blob, actor, workspace_id, collection_id, body, idempotency_key
        ),
        response,
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: str,
    collection_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[CompiledDocument]:
    return await service.list_documents(db, actor, workspace_id, collection_id, limit, offset)


@router.get("/{document_id}", response_model=DocumentResponse)
async def document_detail(
    workspace_id: str, collection_id: str, document_id: str, db: DB, actor: Actor
) -> CompiledDocument:
    await access.authorize(db, actor, workspace_id, collection_id)
    return await access.document(db, workspace_id, collection_id, document_id)


@router.post("/{document_id}/versions", response_model=RegistrationResponse, status_code=201)
async def register_version(
    workspace_id: str,
    collection_id: str,
    document_id: str,
    body: RegisterVersionRequest,
    response: Response,
    idempotency_key: Key,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> RegistrationResponse:
    return _registration(
        await service.register_version(
            db, blob, actor, workspace_id, collection_id, document_id, body, idempotency_key
        ),
        response,
    )


@router.get("/{document_id}/versions", response_model=list[VersionResponse])
async def list_versions(
    workspace_id: str,
    collection_id: str,
    document_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[CompiledVersion]:
    await access.authorize(db, actor, workspace_id, collection_id)
    doc = await access.document(db, workspace_id, collection_id, document_id)
    return await service.versions(db, doc, limit, offset)


@router.get("/{document_id}/versions/{version_id}", response_model=VersionResponse)
async def version_detail(
    workspace_id: str, collection_id: str, document_id: str, version_id: str, db: DB, actor: Actor
) -> CompiledVersion:
    await access.authorize(db, actor, workspace_id, collection_id)
    doc = await access.document(db, workspace_id, collection_id, document_id)
    return await access.version(db, doc, version_id)


@router.get("/{document_id}/versions/{version_id}/draft")
async def version_draft(
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
    response: Response,
    db: DB,
    actor: Actor,
    blob: Blob,
    group_by_source: bool = False,
) -> dict:
    sha, content = await reading.read_version_draft(
        db,
        blob,
        actor,
        workspace_id,
        collection_id,
        document_id,
        version_id,
        group_by_source=group_by_source,
    )
    response.headers.update({"ETag": f'"{sha}"', "Cache-Control": "private, no-store"})
    return content


@router.post(
    "/{document_id}/versions/{version_id}/decision-preview", response_model=PreviewResponse
)
async def decision_preview(
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
    body: PreviewRequest,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> PublicationPreview:
    return await decisions.create_preview(
        db, blob, actor, workspace_id, collection_id, document_id, version_id, body
    )


@router.get("/{document_id}/versions/{version_id}/review-gate")
async def publication_review_gate(
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
    db: DB,
    actor: Actor,
    blob: Blob,
    response: Response,
) -> dict:
    await access.authorize(db, actor, workspace_id, collection_id)
    doc = await access.document(db, workspace_id, collection_id, document_id)
    target = await access.version(db, doc, version_id)
    response.headers["Cache-Control"] = "private, no-store"
    return await review_gate.material(db, blob, target)


@router.post("/{document_id}/versions/{version_id}/decisions", response_model=DecisionResponse)
async def decide(
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
    body: CommitRequest,
    idempotency_key: Key,
    db: DB,
    actor: Actor,
    blob: Blob,
    queue: JobQueue | None = Depends(get_job_queue),
) -> PublicationDecision:
    result = await decisions.commit_decision(
        db, blob, actor, workspace_id, collection_id, document_id, version_id, body, idempotency_key
    )
    if result.action in {"publish", "withdraw"}:
        from qnu.domains.knowledge.index.sync import wake

        await wake(queue, collection_id)
    return result


@router.get("/{document_id}/history", response_model=list[DecisionResponse])
async def history(
    workspace_id: str,
    collection_id: str,
    document_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[PublicationDecision]:
    await access.authorize(db, actor, workspace_id, collection_id)
    doc = await access.document(db, workspace_id, collection_id, document_id)
    return await service.history(db, doc, limit, offset)


@router.get("/{document_id}/published", response_model=PublishedResponse)
async def published(
    workspace_id: str,
    collection_id: str,
    document_id: str,
    response: Response,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> PublishedResponse:
    result = await reading.read_published(db, blob, actor, workspace_id, collection_id, document_id)
    response.headers.update(
        {
            "ETag": f'"{digest({"bundle": result.version.bundle_sha256, "decision": result.decision.id, "sequence": result.document.change_sequence})}"',
            "Cache-Control": "private, no-store",
        }
    )
    return result
