"""Script to reconcile Qdrant vector collections and clean orphan facts.

1. Migrate vectors from legacy `col_col_question_bank` to canonical `col_question_bank`
2. Ensure all chunks of `col_question_bank` in PostgreSQL have vectors in Qdrant
3. Verify parity, then safely remove legacy collection `col_col_question_bank`
4. Clean up orphan facts in PostgreSQL `knowledge_facts`
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.rag.vector_indexer import vector_indexer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconcile")
settings = get_settings()


async def reconcile_qdrant_collections(db: AsyncSession) -> dict[str, Any]:
    """Migrate legacy points, verify parity, and remove legacy Qdrant collection."""
    client = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
    cols_res = await client.get_collections()
    col_names = [c.name for c in cols_res.collections]
    logger.info("Existing Qdrant collections: %s", col_names)

    canonical_col = "col_question_bank"
    legacy_col = "col_col_question_bank"

    # Ensure canonical collection exists
    await vector_indexer.ensure_collection(canonical_col)

    # 1. Fetch chunks in DB for col_question_bank
    stmt = (
        select(KnowledgeChunk)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(
            KnowledgeChunk.collection_id == canonical_col,
            KnowledgeDocument.is_active.is_(True),
        )
    )
    chunks_in_db = (await db.execute(stmt)).scalars().all()
    logger.info("Found %d active chunks in DB for %s", len(chunks_in_db), canonical_col)

    # 2. Inspect legacy points if legacy collection exists
    legacy_points: list[Any] = []
    if legacy_col in col_names:
        res = await client.scroll(
            collection_name=legacy_col,
            limit=100,
            with_payload=True,
            with_vectors=True,
        )
        legacy_points = res[0]
        logger.info("Found %d points in legacy collection %s", len(legacy_points), legacy_col)

    # Index or migrate into canonical collection
    points_to_upsert: list[qmodels.PointStruct] = []
    migrated_count = 0

    # Build lookup of legacy points by chunk_id or content
    legacy_vector_by_chunk_id: dict[str, list[float]] = {}
    for lp in legacy_points:
        pl = lp.payload or {}
        cid = pl.get("chunk_id")
        if cid and lp.vector:
            legacy_vector_by_chunk_id[cid] = lp.vector

    for c in chunks_in_db:
        # Check if vector is available in legacy point
        vector = legacy_vector_by_chunk_id.get(c.id)
        if not vector:
            # Generate deterministic or model vector
            logger.info("Generating embedding for chunk %s", c.id)
            vector = (await vector_indexer.embed_texts([c.content]))[0]
        else:
            migrated_count += 1

        # Qdrant point IDs must be valid UUID or unsigned int
        try:
            point_id = str(uuid.UUID(c.id))
        except (ValueError, AttributeError):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{canonical_col}_{c.id}"))

        payload = {
            "chunk_id": c.id,
            "document_id": c.document_id,
            "collection_id": canonical_col,
            "content": c.content,
            "section": c.section,
            "page_number": c.page_number,
            "is_active": True,
        }
        if c.chunk_metadata:
            payload.update(c.chunk_metadata)

        points_to_upsert.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )

    if points_to_upsert:
        await client.upsert(collection_name=canonical_col, points=points_to_upsert)
        logger.info("Successfully upserted %d points into canonical %s", len(points_to_upsert), canonical_col)

    # Verify canonical collection point count
    info = await client.get_collection(canonical_col)
    logger.info("Canonical collection %s now has %d points", canonical_col, info.points_count)

    # Clean up legacy collection only if canonical has at least as many points
    deleted_legacy = False
    if legacy_col in col_names and info.points_count >= len(legacy_points):
        await client.delete_collection(legacy_col)
        logger.info("Successfully deleted legacy Qdrant collection %s", legacy_col)
        deleted_legacy = True

    return {
        "canonical_points": info.points_count,
        "migrated_from_legacy": migrated_count,
        "legacy_collection_deleted": deleted_legacy,
    }


async def purge_orphan_facts(db: AsyncSession) -> int:
    """Purge knowledge_facts rows that reference non-existent knowledge_documents."""
    # Find orphan count
    check_stmt = text(
        "SELECT count(*) FROM knowledge_facts WHERE document_id NOT IN (SELECT id FROM knowledge_documents)"
    )
    orphan_count = (await db.execute(check_stmt)).scalar() or 0
    logger.info("Found %d orphan facts in knowledge_facts", orphan_count)

    if orphan_count > 0:
        del_stmt = text(
            "DELETE FROM knowledge_facts WHERE document_id NOT IN (SELECT id FROM knowledge_documents)"
        )
        await db.execute(del_stmt)
        await db.commit()
        logger.info("Successfully purged %d orphan facts", orphan_count)

    return int(orphan_count)


async def main() -> None:
    """Run full reconciliation."""
    logger.info("--- Starting QNU AI Platform RAG Reconcile ---")
    async with AsyncSessionFactory() as db:
        purged = await purge_orphan_facts(db)
        qdrant_res = await reconcile_qdrant_collections(db)

    logger.info("--- Reconcile Completed ---")
    logger.info("Orphan facts purged: %d", purged)
    logger.info("Qdrant reconcile result: %s", qdrant_res)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
