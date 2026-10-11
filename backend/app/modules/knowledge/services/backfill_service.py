"""Backfill Service — Migration of published sources into KnowledgeSourceRevision & ChunkSets (ADR-012 Phiên 8)."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeChunkSet,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.services.scope_helper import get_scoped_collection

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


class BackfillV3Report(BaseModel):
    collection_id: str
    total_bindings: int
    source_revisions_created: int
    chunk_sets_created: int
    index_revisions_updated: int
    vector_generation_id: str | None
    already_migrated: int
    status: str = "completed"


class BackfillV3Service:
    """Idempotently backfills published sources into V3 KnowledgeSourceRevision, ChunkSets & VectorGenerations."""

    async def backfill_collection_v3(
        self,
        db: AsyncSession,
        collection_id: str,
        actor: Any | None = None,
    ) -> BackfillV3Report:
        col = await get_scoped_collection(db, collection_id, actor=actor)

        # 1. Ensure a default active VectorGeneration exists
        gen_stmt = (
            select(KnowledgeVectorGeneration)
            .where(
                KnowledgeVectorGeneration.collection_id == col.id,
            )
            .order_by(KnowledgeVectorGeneration.created_at.asc())
        )
        gen = (await db.execute(gen_stmt)).scalars().first()

        if not gen:
            cname = f"col_{col.id.replace('-', '_').lower()}"
            gen = KnowledgeVectorGeneration(
                id=f"vg_{uuid.uuid4().hex[:12]}",
                collection_id=col.id,
                tenant_id=col.tenant_id,
                workspace_id=col.workspace_id,
                provider_id="default",
                embedding_model="BAAI/bge-m3",
                embedding_dimension=1024,
                qdrant_collection_name=cname,
                config_hash=hashlib.sha256(b"BAAI/bge-m3:1024").hexdigest(),
                generation_epoch=1,
                status="active",
            )
            db.add(gen)
            await db.flush()

        meta = dict(col.collection_metadata or {})
        if not meta.get("active_vector_generation_id"):
            meta["active_vector_generation_id"] = gen.id
            meta["embedding_model"] = gen.embedding_model
            meta["embedding_dimension"] = gen.embedding_dimension
            col.collection_metadata = meta

        # 2. Query all bindings for this collection
        b_stmt = select(KnowledgeBinding).where(
            KnowledgeBinding.collection_id == col.id,
            KnowledgeBinding.status.in_(["active", "pending"]),
        )
        bindings = list((await db.execute(b_stmt)).scalars().all())

        total_bindings = len(bindings)
        source_revs_created = 0
        chunk_sets_created = 0
        index_revs_updated = 0
        already_migrated = 0

        for b in bindings:
            # Check if binding already fully migrated
            if b.active_source_revision_id:
                already_migrated += 1
                idx_stmt = select(KnowledgeIndexRevision).where(
                    KnowledgeIndexRevision.binding_id == b.id
                )
                for idx_rev in (await db.execute(idx_stmt)).scalars().all():
                    if not idx_rev.vector_generation_id:
                        idx_rev.vector_generation_id = gen.id
                        index_revs_updated += 1
                    if not idx_rev.source_revision_v2_id:
                        idx_rev.source_revision_v2_id = b.active_source_revision_id
                        index_revs_updated += 1
                continue

            chk_stmt = (
                select(KnowledgeChunk)
                .where(
                    KnowledgeChunk.binding_id == b.id,
                )
                .order_by(KnowledgeChunk.chunk_index.asc())
            )
            chunks = list((await db.execute(chk_stmt)).scalars().all())

            # A. Create KnowledgeSourceRevision if missing
            source_rev = None
            if b.active_source_revision_id:
                source_rev = await db.get(KnowledgeSourceRevision, b.active_source_revision_id)

            if not source_rev:
                markdown_text = (
                    "\n\n".join(
                        c.content.strip() for c in chunks if c.content and c.content.strip()
                    )
                    or "Nội dung gốc không khả dụng"
                )
                c_hash = hashlib.sha256(markdown_text.encode()).hexdigest()
                file_hash = (
                    chunks[0].chunk_hash
                    if chunks and getattr(chunks[0], "chunk_hash", None)
                    else c_hash
                )

                page_manifest = []
                for c in chunks:
                    page_manifest.append(
                        {
                            "page_number": c.page_number or 1,
                            "section": c.section or "",
                            "char_count": len(c.content or ""),
                        }
                    )

                source_rev = KnowledgeSourceRevision(
                    id=f"ks_rev_{uuid.uuid4().hex[:12]}",
                    binding_id=b.id,
                    revision_no=1,
                    origin_document_id=b.repository_document_id or b.id,
                    origin_file_hash=file_hash,
                    snapshot_storage_path=f"snapshots/{col.tenant_id}/{col.workspace_id}/{b.id}/v1.md",
                    canonical_markdown=markdown_text,
                    canonical_hash=c_hash,
                    page_manifest=page_manifest,
                    quality_report={"overall_status": "passed", "backfilled": True},
                    parse_provenance={"backfilled_from_v2": True},
                    status="ready",
                )
                db.add(source_rev)
                await db.flush()
                b.active_source_revision_id = source_rev.id
                source_revs_created += 1

            # B. Create KnowledgeChunkSet if missing
            manifest = []
            for idx, c in enumerate(chunks):
                manifest.append(
                    {
                        "index": idx,
                        "content": c.content,
                        "chunk_hash": (
                            getattr(c, "chunk_hash", None)
                            or hashlib.sha256(c.content.encode()).hexdigest()
                        ),
                        "section": c.section,
                        "page_number": c.page_number or 1,
                    }
                )

            strategy = b.chunk_strategy or "ClauseBasedChunker"
            cfg_hash = hashlib.sha256(f"{strategy}:default".encode()).hexdigest()

            chunk_set = KnowledgeChunkSet(
                id=f"kcs_{uuid.uuid4().hex[:12]}",
                source_revision_id=source_rev.id,
                chunk_strategy=strategy,
                config_hash=cfg_hash,
                chunk_count=len(chunks),
                chunk_config={"_manifest": manifest, "strategy": strategy},
                status="ready",
            )
            db.add(chunk_set)
            await db.flush()
            chunk_sets_created += 1

            # C. Update IndexRevisions for this binding
            idx_stmt = select(KnowledgeIndexRevision).where(
                KnowledgeIndexRevision.binding_id == b.id
            )
            for idx_r in (await db.execute(idx_stmt)).scalars().all():
                if not idx_r.vector_generation_id:
                    idx_r.vector_generation_id = gen.id
                    index_revs_updated += 1
                if not idx_r.chunk_set_id:
                    idx_r.chunk_set_id = chunk_set.id
                    index_revs_updated += 1
                if not idx_r.source_revision_v2_id:
                    idx_r.source_revision_v2_id = source_rev.id
                    index_revs_updated += 1

        await db.commit()

        logger.info(
            "Backfilled collection %s to V3: %d bindings, %d source revs, %d chunk sets",
            col.id,
            total_bindings,
            source_revs_created,
            chunk_sets_created,
        )

        return BackfillV3Report(
            collection_id=col.id,
            total_bindings=total_bindings,
            source_revisions_created=source_revs_created,
            chunk_sets_created=chunk_sets_created,
            index_revisions_updated=index_revs_updated,
            vector_generation_id=gen.id,
            already_migrated=already_migrated,
            status="completed",
        )


backfill_v3_service = BackfillV3Service()
