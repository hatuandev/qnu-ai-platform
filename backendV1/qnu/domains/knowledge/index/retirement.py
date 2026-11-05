"""Reclaim inactive vectors; retain chunks, citations, receipts and immutable manifests."""

from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict
from qnu.ports.vector_store import VectorStore


async def retirement_candidates(db: AsyncSession, vectors: VectorStore) -> list[str]:
    settings = get_settings()
    newer, active = aliased(IndexRun), aliased(IndexRun)
    newer_count = (
        select(func.count())
        .where(
            newer.collection_id == IndexRun.collection_id,
            newer.generation > IndexRun.generation,
            newer.is_active.is_(False),
            newer.status == "completed",
            newer.vectors_retired_at.is_(None),
        )
        .correlate(IndexRun)
        .scalar_subquery()
    )
    has_active = (
        select(active.id)
        .where(
            active.collection_id == IndexRun.collection_id,
            active.is_active.is_(True),
            active.generation > IndexRun.generation,
        )
        .correlate(IndexRun)
        .exists()
    )
    return list(
        (
            await db.scalars(
                select(IndexRun.id)
                .where(
                    IndexRun.is_active.is_(False),
                    IndexRun.status == "completed",
                    IndexRun.vectors_retired_at.is_(None),
                    IndexRun.deactivated_at
                    <= utcnow() - timedelta(seconds=settings.INDEX_RETIRE_AFTER_SECONDS),
                    IndexRun.config["vector_target_hash"].astext == vectors.target_hash,
                    newer_count >= settings.INDEX_RETAIN_INACTIVE,
                    has_active,
                )
                .order_by(IndexRun.deactivated_at)
                .limit(50)
            )
        ).all()
    )


async def retire_vectors(db: AsyncSession, vectors: VectorStore, run_id: str) -> bool:
    run = await db.get(IndexRun, run_id)
    if run is None:
        return False
    actor = background_actor(run.requested_by)
    await authorize(db, actor, run.workspace_id, run.collection_id, write=True)
    run = await db.get(IndexRun, run_id, populate_existing=True, with_for_update=True)
    settings = get_settings()
    cutoff = utcnow() - timedelta(seconds=settings.INDEX_RETIRE_AFTER_SECONDS)
    if (
        run.is_active
        or run.status != "completed"
        or run.vectors_retired_at is not None
        or run.deactivated_at is None
        or run.deactivated_at > cutoff
    ):
        return False
    active = await db.scalar(
        select(IndexRun.id).where(
            IndexRun.collection_id == run.collection_id,
            IndexRun.is_active.is_(True),
            IndexRun.generation > run.generation,
        )
    )
    recent = (
        list(
            (
                await db.scalars(
                    select(IndexRun.id)
                    .where(
                        IndexRun.collection_id == run.collection_id,
                        IndexRun.is_active.is_(False),
                        IndexRun.status == "completed",
                        IndexRun.vectors_retired_at.is_(None),
                    )
                    .order_by(IndexRun.generation.desc())
                    .limit(settings.INDEX_RETAIN_INACTIVE)
                )
            ).all()
        )
        if settings.INDEX_RETAIN_INACTIVE
        else []
    )
    if not active or run.id in recent:
        return False
    if vectors.target_hash != run.config.get("vector_target_hash"):
        raise Conflict("Vector target đã đổi.", code="index_configuration_changed")
    # Retrieval holds the same workspace lock through vector reads. This target is
    # inactive and cannot be selected by a newly starting turn.
    await vectors.delete_collection(run.vector_collection)
    await db.execute(update(IndexChunk).where(IndexChunk.run_id == run.id).values(vector=None))
    run.vectors_retired_at = utcnow()
    await record_workspace_event(
        db,
        workspace_id=run.workspace_id,
        actor=actor,
        action="index.vectors_retired",
        detail={"run_id": run.id, "citations_retained": True},
    )
    await db.commit()
    return True
