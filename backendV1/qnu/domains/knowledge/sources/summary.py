"""Bounded, read-only lineage from one source revision through Compiler to serving.

The summary never infers an "in use" run from generation order: every derivation
comes from a persisted ``CompilationInput`` that pinned one OCR run and one text
version. Availability reuses ``document_readiness`` instead of a second algorithm.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import CompilationInput, CompilationRun
from qnu.domains.knowledge.index.readiness import document_readiness
from qnu.domains.knowledge.index.schemas import IndexReadiness
from qnu.domains.knowledge.policies.access import READ_ROLES, load_revision
from qnu.domains.knowledge.policies.capabilities import summary_capabilities
from qnu.domains.knowledge.preparation.models import (
    ACTIVE_PREPARATION_STATUSES,
    PreparationIntent,
)
from qnu.domains.knowledge.preparation.schemas import PREPARATION_STEPS
from qnu.domains.knowledge.publication.models import CompiledDocument, CompiledVersion
from qnu.domains.knowledge.sources.schemas import (
    RevisionResponse,
    SourceActionPermissions,
    SourceDerivation,
    SourcePreparationSummary,
    SourceProcessingRunSummary,
    SourceServingState,
    SourceSummaryResponse,
    SourceTextVersionRef,
    SourceVersionRef,
)
from qnu.domains.knowledge.sources.service import source_service
from qnu.domains.lifecycle.guards import visible
from qnu.domains.lifecycle.models import LifecycleAction, ResourceState
from qnu.domains.ocr.models import ACTIVE_RUN_STATUSES, OcrProcessingRun
from qnu.domains.ocr.review.models import TextVersion
from qnu.domains.ocr.schemas import ProcessingRunResponse
from qnu.domains.workspaces.access import caller_workspace_role, resolve_workspace_access
from qnu.ports.blob_store import BlobStore


def _text_ref(row: TextVersion | None) -> SourceTextVersionRef | None:
    if row is None:
        return None
    return SourceTextVersionRef(
        id=row.id,
        version=row.version,
        canonical_sha256=row.canonical_sha256,
        markdown_sha256=row.markdown_sha256,
        created_by=row.created_by,
        created_at=row.created_at,
    )


async def _latest_text_versions(db: AsyncSession, run_ids: list[str]) -> dict[str, TextVersion]:
    if not run_ids:
        return {}
    rows = (
        await db.scalars(
            select(TextVersion)
            .where(TextVersion.run_id.in_(run_ids))
            .order_by(TextVersion.run_id, TextVersion.version.desc())
            .distinct(TextVersion.run_id)
        )
    ).all()
    return {row.run_id: row for row in rows}


async def _derivations(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    revision_id: str,
    limit: int,
) -> tuple[list[SourceDerivation], bool]:
    rows = (
        await db.execute(
            select(CompilationInput, CompilationRun, OcrProcessingRun)
            .join(CompilationRun, CompilationRun.id == CompilationInput.run_id)
            .join(OcrProcessingRun, OcrProcessingRun.id == CompilationInput.ocr_run_id)
            .where(
                OcrProcessingRun.revision_id == revision_id,
                OcrProcessingRun.workspace_id == workspace_id,
                OcrProcessingRun.collection_id == collection_id,
                CompilationInput.workspace_id == workspace_id,
                CompilationInput.collection_id == collection_id,
                CompilationRun.workspace_id == workspace_id,
                CompilationRun.collection_id == collection_id,
            )
            .order_by(CompilationRun.generation.desc(), CompilationRun.id)
            .limit(limit + 1)
        )
    ).all()
    truncated = len(rows) > limit
    rows = rows[:limit]

    compilation_ids = list({run.id for _, run, _ in rows})
    versions_by_run: dict[str, tuple[CompiledVersion, CompiledDocument]] = {}
    if compilation_ids:
        version_rows = (
            await db.execute(
                select(CompiledVersion, CompiledDocument)
                .join(CompiledDocument, CompiledDocument.id == CompiledVersion.document_id)
                .where(
                    CompiledVersion.compilation_run_id.in_(compilation_ids),
                    CompiledVersion.workspace_id == workspace_id,
                    CompiledVersion.collection_id == collection_id,
                    visible("document", CompiledDocument.id),
                )
            )
        ).all()
        versions_by_run = {
            version.compilation_run_id: (version, doc) for version, doc in version_rows
        }

    text_ids = [item.text_version_id for item, _, _ in rows if item.text_version_id]
    text_by_id: dict[str, TextVersion] = {}
    if text_ids:
        text_rows = (
            await db.scalars(select(TextVersion).where(TextVersion.id.in_(text_ids)))
        ).all()
        text_by_id = {row.id: row for row in text_rows}

    readiness_by_document: dict[str, IndexReadiness] = {}
    for version, document in versions_by_run.values():
        if version.status != "published" or document.id in readiness_by_document:
            continue
        readiness_by_document[document.id] = await document_readiness(
            db, blob, actor, workspace_id, collection_id, document.id
        )

    derivations: list[SourceDerivation] = []
    for item, compilation, ocr_run in rows:
        version, document = versions_by_run.get(compilation.id, (None, None))
        readiness = (
            readiness_by_document.get(document.id)
            if version is not None and document is not None and version.status == "published"
            else None
        )
        is_serving = bool(
            readiness is not None
            and version is not None
            and readiness.status == "ready"
            and readiness.version_id == version.id
            and readiness.version_state == version.state_version
            and readiness.bundle_sha256 == version.bundle_sha256
        )
        derivations.append(
            SourceDerivation(
                compilation_run_id=compilation.id,
                compilation_generation=compilation.generation,
                compilation_status=compilation.status,
                origin=compilation.origin,
                ocr_run_id=item.ocr_run_id,
                ocr_generation=ocr_run.generation,
                text_version=_text_ref(text_by_id.get(item.text_version_id or "")),
                version=(
                    SourceVersionRef(
                        version_id=version.id,
                        version_no=version.version_no,
                        state_version=version.state_version,
                        status=version.status,
                        bundle_sha256=version.bundle_sha256,
                        document_id=document.id,
                        document_title=document.title,
                    )
                    if version is not None and document is not None
                    else None
                ),
                readiness=readiness,
                is_serving=is_serving,
            )
        )
    return derivations, truncated


async def read_summary(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    source_id: str,
    *,
    revision_id: str | None,
    runs_limit: int,
    derivations_limit: int,
) -> SourceSummaryResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    source, current_revision = await source_service.get(db, workspace, collection_id, source_id)
    revision = (
        current_revision
        if revision_id is None
        else await load_revision(db, workspace.id, source.id, revision_id)
    )

    run_rows = list(
        (
            await db.scalars(
                select(OcrProcessingRun)
                .where(
                    OcrProcessingRun.revision_id == revision.id,
                    OcrProcessingRun.workspace_id == workspace.id,
                    OcrProcessingRun.collection_id == collection_id,
                )
                .order_by(OcrProcessingRun.generation.desc(), OcrProcessingRun.id)
                .limit(runs_limit + 1)
            )
        ).all()
    )
    runs_truncated = len(run_rows) > runs_limit
    runs = run_rows[:runs_limit]

    active_run_id = await db.scalar(
        select(OcrProcessingRun.id)
        .where(
            OcrProcessingRun.revision_id == revision.id,
            OcrProcessingRun.workspace_id == workspace.id,
            OcrProcessingRun.collection_id == collection_id,
            OcrProcessingRun.status.in_(ACTIVE_RUN_STATUSES),
        )
        .limit(1)
    )
    latest_text = await _latest_text_versions(db, [run.id for run in runs])
    derivations, derivations_truncated = await _derivations(
        db, blob, actor, workspace.id, collection_id, revision.id, derivations_limit
    )
    role = await caller_workspace_role(db, actor, workspace.id)
    serving, actions, preparation = await _serving_and_actions(
        db,
        blob,
        actor,
        workspace.id,
        collection_id,
        source,
        role,
        revision.revision_no if active_run_id is not None else None,
    )

    return SourceSummaryResponse(
        observed_at=datetime.now(UTC),
        source_id=source.id,
        title=source.title,
        latest_revision_no=source.latest_revision_no,
        serving_revision_no=source.serving_revision_no,
        revision=RevisionResponse(
            id=revision.id,
            source_id=revision.source_id,
            revision_no=revision.revision_no,
            file_name=revision.file_name,
            content_type=revision.content_type,
            size_bytes=revision.size_bytes,
            sha256=revision.sha256,
            created_by=revision.created_by,
            created_at=revision.created_at,
        ),
        processing_runs=[
            SourceProcessingRunSummary(
                **ProcessingRunResponse.from_run(run).model_dump(),
                latest_text_version=_text_ref(latest_text.get(run.id)),
            )
            for run in runs
        ],
        runs_truncated=runs_truncated,
        active_run_id=active_run_id,
        derivations=derivations,
        derivations_truncated=derivations_truncated,
        capabilities=summary_capabilities(role),
        serving=serving,
        actions=actions,
        preparation=preparation,
    )


async def _published_version(
    db: AsyncSession,
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_no: int | None,
) -> tuple[str, str, int] | None:
    statement = (
        select(CompiledVersion.id, CompiledDocument.id, OcrProcessingRun.revision_no)
        .join(CompilationInput, CompilationInput.run_id == CompiledVersion.compilation_run_id)
        .join(OcrProcessingRun, OcrProcessingRun.id == CompilationInput.ocr_run_id)
        .join(CompiledDocument, CompiledDocument.id == CompiledVersion.document_id)
        .where(
            CompiledVersion.workspace_id == workspace_id,
            CompiledVersion.collection_id == collection_id,
            CompiledVersion.status == "published",
            OcrProcessingRun.source_id == source_id,
            visible("document", CompiledDocument.id),
        )
    )
    if revision_no is not None:
        statement = statement.where(OcrProcessingRun.revision_no == revision_no)
    row = (
        await db.execute(
            statement.order_by(
                OcrProcessingRun.revision_no.desc(), CompiledVersion.version_no.desc()
            ).limit(1)
        )
    ).first()
    return (row[0], row[1], row[2]) if row else None


async def _serving_and_actions(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    source,
    role: str,
    extracting_revision_no: int | None,
) -> tuple[SourceServingState, SourceActionPermissions, SourcePreparationSummary | None]:
    served = await _published_version(
        db, workspace_id, collection_id, source.id, source.serving_revision_no
    )
    published = await _published_version(db, workspace_id, collection_id, source.id, None)
    served_version_id = served[0] if served is not None else None
    served_document_id = served[1] if served is not None else None
    if served is not None:
        version = await db.get(CompiledVersion, served[0])
        readiness = await document_readiness(
            db, blob, actor, workspace_id, collection_id, served[1]
        )
        # A publication pointer alone never claims serving: the active manifest
        # must contain this exact version state and bundle.
        if (
            version is None
            or version.status != "published"
            or readiness.status != "ready"
            or readiness.version_id != version.id
            or readiness.version_state != version.state_version
            or readiness.bundle_sha256 != version.bundle_sha256
        ):
            served_version_id, served_document_id = None, None
    intent = await db.scalar(
        select(PreparationIntent)
        .where(
            PreparationIntent.workspace_id == workspace_id,
            PreparationIntent.collection_id == collection_id,
            PreparationIntent.source_id == source.id,
        )
        .order_by(PreparationIntent.created_at.desc(), PreparationIntent.id)
        .limit(1)
    )
    pending_delete = await db.scalar(
        select(LifecycleAction.id)
        .where(
            LifecycleAction.workspace_id == workspace_id,
            LifecycleAction.kind == "source",
            LifecycleAction.resource_id == source.id,
            LifecycleAction.action == "delete",
            # Only a confirmed deletion locks edits; an open preview or an expired
            # preview must not narrow the user's actions.
            LifecycleAction.status == "pending",
        )
        .limit(1)
    )
    lifecycle = await db.get(
        ResourceState, (workspace_id, "source", source.id), populate_existing=True
    )
    source_active = lifecycle is None or lifecycle.status == "active"
    is_writer = role in {"admin", "editor"}
    is_admin = role == "admin"
    active_intent = intent is not None and intent.status in ACTIVE_PREPARATION_STATUSES
    preparing_revision_no = extracting_revision_no
    if active_intent:
        preparing_revision_no = intent.revision_no
    elif preparing_revision_no is None:
        if served_version_id is None and published is not None:
            preparing_revision_no = published[2]
        elif (
            served_version_id is not None and source.latest_revision_no > source.serving_revision_no
        ):
            preparing_revision_no = source.latest_revision_no
    serving = SourceServingState(
        served_revision_no=(source.serving_revision_no if served_version_id is not None else None),
        preparing_revision_no=preparing_revision_no,
        published_revision_no=published[2] if published is not None else None,
        served_version_id=served_version_id,
        served_document_id=served_document_id,
    )
    actions = SourceActionPermissions(
        can_stop=is_writer and (active_intent or extracting_revision_no is not None),
        can_withdraw=is_admin and source_active and (served is not None or published is not None),
        can_update=is_writer and source_active and pending_delete is None,
        can_delete=is_admin and pending_delete is None,
    )
    preparation = (
        SourcePreparationSummary(
            intent_id=intent.id,
            status=intent.status,
            step=PREPARATION_STEPS.get(intent.status, intent.status),
            error_code=intent.error_code,
        )
        if intent is not None
        else None
    )
    return serving, actions, preparation
