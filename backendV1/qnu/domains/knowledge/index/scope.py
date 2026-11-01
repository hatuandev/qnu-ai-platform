"""Resolve a verified metadata allow-list before either retrieval branch selects TopK."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.index.models import IndexChunk, IndexInput, IndexRun
from qnu.domains.knowledge.metadata import MetadataFilter, matches_metadata
from qnu.domains.knowledge.publication.evidence import digest
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict


async def metadata_chunk_ids(
    db: AsyncSession,
    run: IndexRun,
    allowed: list[IndexInput],
    scope: MetadataFilter,
    sealed: dict,
    *,
    alternatives: list[MetadataFilter] | None = None,
) -> list[str] | None:
    scopes = alternatives or [scope]
    if any(not item.model_dump(exclude_none=True) for item in scopes):
        return None
    rows = (
        await db.execute(
            select(IndexChunk.id, IndexChunk.structure)
            .where(
                IndexChunk.run_id == run.id,
                IndexChunk.input_id.in_([b.id for b in allowed]),
            )
            .limit(get_settings().INDEX_MAX_CHUNKS + 1)
        )
    ).all()
    if len(rows) > get_settings().INDEX_MAX_CHUNKS:
        raise Conflict("Phạm vi metadata vượt giới hạn index.", code="index_scope_too_large")
    proofs = {c["id"]: c["structure_sha256"] for c in sealed["chunks"]}
    matched = []
    for identifier, structure in rows:
        if digest(structure) != proofs.get(identifier):
            raise Conflict("Metadata khác manifest đã ghim.", code="index_metadata_changed")
        if any(matches_metadata(structure, item) for item in scopes):
            matched.append(identifier)
    return matched
