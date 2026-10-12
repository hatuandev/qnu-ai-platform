"""Chunk Set Service — Materialized chunks and facts engine (ADR-012).

Implements 'Parse Once, Chunk Once, Embed Many' invariant:
Ensures chunks and structured facts are materialized once per (source_revision, chunk_config),
and strictly reused across multiple vector spaces without re-chunking or re-parsing.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.modules.knowledge.chunker import get_chunker
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunkSet,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.services.source_pages import chunk_source_pages, manifest_page_count

logger = logging.getLogger(__name__)


def compute_config_hash(chunk_strategy: str, chunk_config: dict[str, Any] | None) -> str:
    """Compute stable SHA-256 fingerprint for chunking strategy and hyper-parameters."""
    clean_config = {k: v for k, v in (chunk_config or {}).items() if not k.startswith("_")}
    serialized = json.dumps(clean_config, sort_keys=True)
    return hashlib.sha256(f"page-boundaries-v2:{chunk_strategy}:{serialized}".encode()).hexdigest()


def compute_chunk_set_key(canonical_hash: str | None, config_hash: str) -> str:
    """Compute content-addressed key for deduplicating chunk sets across revisions."""
    base = f"{canonical_hash or ''}:{config_hash}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


class ChunkSetService:
    """Service managing materialization and reuse of KnowledgeChunkSet."""

    async def get_or_create_chunk_set(
        self,
        db: AsyncSession,
        source_revision_id: str,
        chunk_strategy: str = "ClauseBasedChunker",
        chunk_config: dict[str, Any] | None = None,
    ) -> KnowledgeChunkSet:
        """Retrieve existing materialized ChunkSet or generate a new one from canonical Markdown.

        Guarantees:
        - Reuses ready chunk sets when config_hash matches (Zero redundant CPU).
        - Source revision MUST be in 'ready' status before chunking.
        - Manifest of chunks is cached inside chunk_config['_manifest'] for instant multi-embedding.
        """
        # 1. Fetch Source Revision
        stmt = select(KnowledgeSourceRevision).where(
            KnowledgeSourceRevision.id == source_revision_id
        )
        res = await db.execute(stmt)
        source_rev = res.scalar_one_or_none()
        if not source_rev:
            raise AppException(
                message=f"Không tìm thấy bản sửa đổi nguồn '{source_revision_id}'",
                code="SOURCE_REVISION_NOT_FOUND",
                status_code=404,
            )

        if source_rev.status != "ready":
            raise AppException(
                message=f"Chỉ bản sửa đổi nguồn 'ready' mới được tạo chunk set (hiện tại: {source_rev.status}).",
                code="SOURCE_REVISION_NOT_READY",
                status_code=409,
            )

        clean_config = {k: v for k, v in (chunk_config or {}).items() if not k.startswith("_")}
        conf_hash = compute_config_hash(chunk_strategy, clean_config)
        set_key = compute_chunk_set_key(source_rev.canonical_hash, conf_hash)

        # 2. Check for existing ChunkSet with same (source_revision_id, config_hash)
        chk_stmt = select(KnowledgeChunkSet).where(
            KnowledgeChunkSet.source_revision_id == source_revision_id,
            KnowledgeChunkSet.config_hash == conf_hash,
        )
        existing_res = await db.execute(chk_stmt)
        existing_set = existing_res.scalar_one_or_none()
        if existing_set and existing_set.status == "ready" and existing_set.chunk_set_key == set_key:
            logger.info(
                "Reusing existing chunk set %s for source revision %s (strategy=%s)",
                existing_set.id,
                source_revision_id,
                chunk_strategy,
            )
            return existing_set

        # 3. Check if another revision with identical canonical_hash already has this chunk_set_key
        key_stmt = select(KnowledgeChunkSet).join(
            KnowledgeSourceRevision, KnowledgeChunkSet.source_revision_id == KnowledgeSourceRevision.id,
        ).where(
            KnowledgeSourceRevision.binding_id == source_rev.binding_id,
            KnowledgeChunkSet.chunk_set_key == set_key,
            KnowledgeChunkSet.status == "ready",
        )
        key_res = await db.execute(key_stmt)
        key_match = key_res.scalars().first()
        if key_match and key_match.chunk_config.get("_manifest"):
            logger.info(
                "Reusing identical chunk set %s across revisions via chunk_set_key %s",
                key_match.id,
                set_key,
            )
            # Create a shallow pointer or reuse
            chunk_set = KnowledgeChunkSet(
                source_revision_id=source_revision_id,
                chunk_strategy=chunk_strategy,
                chunk_config=key_match.chunk_config,
                config_hash=conf_hash,
                chunk_set_key=set_key,
                chunk_count=key_match.chunk_count,
                fact_count=key_match.fact_count,
                manifest_hash=key_match.manifest_hash,
                status="ready",
            )
            db.add(chunk_set)
            await db.commit()
            await db.refresh(chunk_set)
            return chunk_set

        # 4. Generate new chunks
        canonical_md = source_rev.canonical_markdown or ""
        if not canonical_md.strip():
            raise AppException(
                message=f"Bản sửa đổi nguồn '{source_revision_id}' không có nội dung Markdown chuẩn hóa.",
                code="EMPTY_CANONICAL_CONTENT",
                status_code=422,
            )

        chunker = get_chunker(chunk_strategy)
        chunks_data = chunk_source_pages(chunker, canonical_md, manifest_page_count(source_rev.page_manifest), **clean_config)
        if not chunks_data:
            raise AppException(
                message=f"Chiến lược cắt đoạn '{chunk_strategy}' trả về 0 chunks từ nội dung tài liệu.",
                code="CHUNKER_RETURNED_ZERO",
                status_code=422,
            )

        manifest_items: list[dict[str, Any]] = []
        for idx, c in enumerate(chunks_data):
            c_text = getattr(c, "content", "") if not isinstance(c, dict) else (c.get("content") or c.get("text") or "")
            c_hash = getattr(c, "chunk_hash", "") if not isinstance(c, dict) else (c.get("chunk_hash") or "")
            if not c_hash:
                c_hash = hashlib.sha256(c_text.encode("utf-8")).hexdigest()
            c_tokens = getattr(c, "token_count", 0) if not isinstance(c, dict) else (c.get("token_count") or 0)
            c_section = getattr(c, "section", None) if not isinstance(c, dict) else c.get("section")
            c_page = getattr(c, "page_number", None) if not isinstance(c, dict) else c.get("page_number")
            c_meta = getattr(c, "metadata", {}) if not isinstance(c, dict) else (c.get("metadata") or {})

            manifest_items.append(
                {
                    "index": idx,
                    "content": c_text,
                    "chunk_hash": c_hash,
                    "token_count": c_tokens,
                    "section": c_section,
                    "page_number": c_page,
                    "metadata": c_meta,
                }
            )

        manifest_hash = hashlib.sha256(
            json.dumps([item["chunk_hash"] for item in manifest_items], sort_keys=True).encode("utf-8")
        ).hexdigest()

        # Save chunk set record
        saved_config = {**clean_config, "_manifest": manifest_items}
        from app.modules.knowledge.services.source_artifact import get_source_artifact

        artifact = get_source_artifact(source_rev)
        saved_config["_fact_set_hash"] = artifact["fact_set_hash"]
        chunk_set = KnowledgeChunkSet(
            source_revision_id=source_revision_id,
            chunk_strategy=chunk_strategy,
            chunk_config=saved_config,
            config_hash=conf_hash,
            chunk_set_key=set_key,
            chunk_count=len(manifest_items),
            fact_count=len(artifact["facts"]),
            manifest_hash=manifest_hash,
            status="ready",
        )
        db.add(chunk_set)
        await db.commit()
        await db.refresh(chunk_set)
        return chunk_set

    async def get_chunk_set(
        self,
        db: AsyncSession,
        chunk_set_id: str,
    ) -> KnowledgeChunkSet:
        """Fetch chunk set by ID with its parent source revision."""
        stmt = (
            select(KnowledgeChunkSet)
            .options(selectinload(KnowledgeChunkSet.source_revision))
            .where(KnowledgeChunkSet.id == chunk_set_id)
        )
        res = await db.execute(stmt)
        chunk_set = res.scalar_one_or_none()
        if not chunk_set:
            raise AppException(
                message=f"Không tìm thấy tập đoạn cắt '{chunk_set_id}'",
                code="CHUNK_SET_NOT_FOUND",
                status_code=404,
            )
        return chunk_set

    async def list_chunk_sets_for_source(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
    ) -> list[KnowledgeChunkSet]:
        """List all materialized chunk sets across all revisions of a knowledge source."""
        # Check source binding exists
        binding_stmt = select(KnowledgeBinding).where(
            KnowledgeBinding.id == source_id,
            KnowledgeBinding.collection_id == collection_id,
        )
        b_res = await db.execute(binding_stmt)
        binding = b_res.scalar_one_or_none()
        if not binding:
            raise AppException(
                message=f"Không tìm thấy nguồn tri thức '{source_id}' trong bộ sưu tập",
                code="SOURCE_NOT_FOUND",
                status_code=404,
            )

        stmt = (
            select(KnowledgeChunkSet)
            .join(
                KnowledgeSourceRevision,
                KnowledgeChunkSet.source_revision_id == KnowledgeSourceRevision.id,
            )
            .where(KnowledgeSourceRevision.binding_id == binding.id)
            .order_by(KnowledgeChunkSet.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


chunk_set_service = ChunkSetService()
