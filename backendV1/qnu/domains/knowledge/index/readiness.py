"""Readiness is an exact active-generation binding, never an ordering of timestamps."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.models import IndexRun
from qnu.domains.knowledge.index.schemas import IndexReadiness
from qnu.domains.knowledge.index.search import _eligible, manifest
from qnu.domains.knowledge.publication.access import authorize, document
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import Conflict
from qnu.ports.blob_store import BlobStore


async def document_readiness(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    document_id: str,
) -> IndexReadiness:
    await resolve_workspace_access(db, actor, workspace_id, for_update=True)
    await authorize(db, actor, workspace_id, collection_id)
    await document(db, workspace_id, collection_id, document_id)
    run = await db.scalar(
        select(IndexRun).where(
            IndexRun.workspace_id == workspace_id,
            IndexRun.collection_id == collection_id,
            IndexRun.is_active.is_(True),
            IndexRun.status == "completed",
        )
    )
    if run is None:
        return IndexReadiness(status="not_indexed")
    sealed = await manifest(db, blob, run)
    try:
        allowed, _ = await _eligible(db, blob, actor, run, [document_id])
    except Conflict as exc:
        if exc.code != "index_outdated":
            raise
        return IndexReadiness(status="outdated", index_run_id=run.id, generation=run.generation)
    if not allowed:
        return IndexReadiness(status="unavailable", index_run_id=run.id, generation=run.generation)
    binding = allowed[0]
    identity = {
        field: getattr(binding, field)
        for field in (
            "document_id", "version_id", "publication_decision_id", "bundle_sha256", "version_state"
        )
    }
    if identity not in sealed.get("inputs", []):
        raise Conflict("Binding không khớp manifest index.", code="index_manifest_invalid")
    return IndexReadiness(
        status="ready",
        index_run_id=run.id,
        generation=run.generation,
        version_id=binding.version_id,
        publication_decision_id=binding.publication_decision_id,
        bundle_sha256=binding.bundle_sha256,
        version_state=binding.version_state,
    )
