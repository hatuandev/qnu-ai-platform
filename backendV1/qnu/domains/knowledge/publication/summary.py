"""Read-only document summary: paginated versions, exact origins, reused readiness.

Origins come from persisted ``CompilationInput`` rows, so a version can never
claim a source it did not compile. Serving truth reuses ``document_readiness``
instead of a second index algorithm.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.contracts.pagination import Page, PageMeta
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import CompilationInput
from qnu.domains.knowledge.index.readiness import document_readiness
from qnu.domains.knowledge.models import KBSource, KBSourceRevision
from qnu.domains.knowledge.policies.capabilities import summary_capabilities
from qnu.domains.knowledge.publication import access, service
from qnu.domains.knowledge.publication.models import CompiledVersion, PublicationDecision
from qnu.domains.knowledge.publication.schemas import (
    DocumentResponse,
    DocumentSummaryResponse,
    VersionOrigin,
    VersionResponse,
    VersionSummary,
)
from qnu.domains.lifecycle.guards import visible
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.review.models import TextVersion
from qnu.domains.workspaces.access import caller_workspace_role
from qnu.ports.blob_store import BlobStore


async def _origins(
    db: AsyncSession,
    workspace_id: str,
    collection_id: str,
    versions: list[CompiledVersion],
) -> dict[str, list[VersionOrigin]]:
    run_ids = [version.compilation_run_id for version in versions]
    if not run_ids:
        return {}
    rows = (
        await db.execute(
            select(CompilationInput, OcrProcessingRun, TextVersion, KBSourceRevision, KBSource)
            .join(OcrProcessingRun, OcrProcessingRun.id == CompilationInput.ocr_run_id)
            .outerjoin(TextVersion, TextVersion.id == CompilationInput.text_version_id)
            .join(KBSourceRevision, KBSourceRevision.id == OcrProcessingRun.revision_id)
            .join(KBSource, KBSource.id == KBSourceRevision.source_id)
            .where(
                CompilationInput.run_id.in_(run_ids),
                CompilationInput.workspace_id == workspace_id,
                CompilationInput.collection_id == collection_id,
                KBSource.workspace_id == workspace_id,
                KBSource.collection_id == collection_id,
                visible("source", KBSource.id),
            )
            .order_by(CompilationInput.run_id, KBSource.title, KBSource.id)
        )
    ).all()
    grouped: dict[str, list[VersionOrigin]] = {}
    for item, ocr_run, text, revision, source in rows:
        grouped.setdefault(item.run_id, []).append(
            VersionOrigin(
                source_id=source.id,
                source_title=source.title,
                revision_id=revision.id,
                revision_no=revision.revision_no,
                file_name=revision.file_name,
                sha256=revision.sha256,
                ocr_run_id=ocr_run.id,
                ocr_generation=ocr_run.generation,
                text_version_id=text.id if text is not None else None,
                text_version_no=text.version if text is not None else None,
            )
        )
    return grouped


async def _published_decision_id(db: AsyncSession, document_id: str, version_id: str) -> str | None:
    return await db.scalar(
        select(PublicationDecision.id)
        .where(
            PublicationDecision.document_id == document_id,
            PublicationDecision.version_id == version_id,
            PublicationDecision.action == "publish",
        )
        .order_by(PublicationDecision.document_sequence.desc())
        .limit(1)
    )


async def read_document_summary(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    document_id: str,
    *,
    page: int,
    page_size: int,
) -> DocumentSummaryResponse:
    await access.authorize(db, actor, workspace_id, collection_id)
    doc = await access.document(db, workspace_id, collection_id, document_id)
    total = await db.scalar(
        select(func.count(CompiledVersion.id)).where(CompiledVersion.document_id == doc.id)
    )
    versions = await service.versions(db, doc, page_size, (page - 1) * page_size)
    origins = await _origins(db, workspace_id, collection_id, versions)
    published = await access.active_version(db, doc)
    published_decision_id = (
        await _published_decision_id(db, doc.id, published.id) if published is not None else None
    )
    readiness = await document_readiness(db, blob, actor, workspace_id, collection_id, document_id)
    prepared = await db.scalar(
        select(CompiledVersion)
        .where(
            CompiledVersion.document_id == doc.id,
            CompiledVersion.status.in_(("draft", "approved")),
        )
        .order_by(CompiledVersion.version_no.desc())
        .limit(1)
    )
    served = None
    if readiness.status == "ready" and readiness.version_id:
        served = await db.scalar(
            select(CompiledVersion).where(
                CompiledVersion.id == readiness.version_id,
                CompiledVersion.document_id == doc.id,
                CompiledVersion.workspace_id == workspace_id,
                CompiledVersion.collection_id == collection_id,
            )
        )
    serving_matches_published = bool(
        published is not None
        and published_decision_id is not None
        and readiness.status == "ready"
        and readiness.version_id == published.id
        and readiness.version_state == published.state_version
        and readiness.bundle_sha256 == published.bundle_sha256
        and readiness.publication_decision_id == published_decision_id
    )
    role = await caller_workspace_role(db, actor, workspace_id)
    items = [
        VersionSummary(
            **VersionResponse.model_validate(version).model_dump(
                exclude={"retrieval_metadata_sha256"}
            ),
            origins=origins.get(version.compilation_run_id, []),
        )
        for version in versions
    ]
    return DocumentSummaryResponse(
        observed_at=datetime.now(UTC),
        document=DocumentResponse.model_validate(doc),
        prepared_version=(
            VersionResponse.model_validate(prepared) if prepared is not None else None
        ),
        published_version=(
            VersionResponse.model_validate(published) if published is not None else None
        ),
        served_version=VersionResponse.model_validate(served) if served is not None else None,
        published_decision_id=published_decision_id,
        readiness=readiness,
        serving_matches_published=serving_matches_published,
        versions=Page[VersionSummary](
            items=items, meta=PageMeta(page=page, page_size=page_size, total=total or 0)
        ),
        capabilities=summary_capabilities(role),
    )
