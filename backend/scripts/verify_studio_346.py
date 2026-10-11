"""Opt-in live PostgreSQL/MinIO/OCR verification using isolated, disposable DB rows.

Does not reset databases, mutate existing sources, or delete any snapshot files.
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import delete, select

from app.core.database import AsyncSessionFactory, engine
from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.main import app  # noqa: F401 — register all ORM mappings
from app.modules.auth.schemas import AuthActor
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.services.binding_service import binding_service
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
from app.modules.knowledge.services.source_reparse import queue_reparse, run_reparse


async def main():
    suffix = uuid.uuid4().hex[:12]
    collection_id, source_id = f"col_studio346_{suffix}", f"bnd_studio346_{suffix}"
    async with AsyncSessionFactory() as db:
        base = (await db.execute(select(KnowledgeSourceRevision).where(
            KnowledgeSourceRevision.status == "ready",
            KnowledgeSourceRevision.snapshot_metadata["file_name"].astext.ilike("%e2e%scan%"),
        ).order_by(KnowledgeSourceRevision.created_at.desc()).limit(1))).scalar_one_or_none()
        if not base:
            raise RuntimeError("Missing existing E2E scan fixture; no data was created.")
        snapshot_path = base.snapshot_storage_path
        col = KnowledgeCollection(id=collection_id, name="Studio 346 isolated verification", module_code="admissions")
        binding = KnowledgeBinding(id=source_id, collection_id=collection_id, status="active")
        db.add(col)
        await db.flush()
        db.add(binding)
        await db.flush()
        revision = KnowledgeSourceRevision(
            id=f"ks_studio346_{suffix}", binding_id=source_id, revision_no=1, status="ready",
            origin_document_id=base.origin_document_id, origin_file_hash=base.origin_file_hash,
            snapshot_storage_path=base.snapshot_storage_path, snapshot_metadata=dict(base.snapshot_metadata),
            canonical_markdown=base.canonical_markdown, page_manifest=list(base.page_manifest),
        )
        db.add(revision)
        await db.flush()
        binding.active_source_revision_id = revision.id
        await db.commit()
    try:
        async def request():
            async with AsyncSessionFactory() as session:
                try:
                    rev = await queue_reparse(session, collection_id, source_id, "vision_ocr", "paddleocr", "tenant_qnu", "workspace_qnu")
                    return rev.id
                except AppException as exc:
                    return exc.code
        with patch("app.modules.knowledge.services.source_reparse.enqueue_arq_job", new_callable=AsyncMock, return_value=None):
            outcomes = await asyncio.gather(request(), request())
        assert outcomes.count("REPARSE_ALREADY_IN_PROGRESS") == 1, outcomes
        revision_id = next(o for o in outcomes if o != "REPARSE_ALREADY_IN_PROGRESS")
        print("Concurrent requests: one queued, one 409 (real PostgreSQL row lock)")
        async with AsyncSessionFactory() as db:
            job = (await db.execute(select(JobRecord).where(JobRecord.collection_id == collection_id))).scalar_one()
            result = await run_reparse(db, job)
            assert result.id == revision_id and result.status in ("ready", "review_required")
            studio = await source_ingestion_service.get_source_studio_data(db, collection_id, source_id, result.id)
            assert len(studio.pages) >= 2 and all(p.bounding_boxes for p in studio.pages)
            image, media = await source_ingestion_service.get_source_page_image(db, collection_id, source_id, 2, result.id)
            assert len(image) > 1000 and media == "image/jpeg"
            edited = await source_ingestion_service.update_revision_content(db, collection_id, source_id, result.id, result.canonical_markdown)
            assert edited.id != result.id and edited.page_manifest[0]["blocks"] == result.page_manifest[0]["blocks"]
            print("Real PaddleOCR + snapshot images + immutable edit preserves bbox: passed")
            actor = AuthActor(actor_id="studio346", username="studio346", display_name="Studio Test", tenant_id="tenant_qnu", workspace_id="workspace_qnu", role="admin", roles=["AI.Admin"], permissions=["ai.knowledge.delete"])
            removed = await binding_service.detach_binding(db, source_id, actor)
            assert removed.status == "detached"
            assert await storage_service.get(snapshot_path)
            print("Delete source retains original snapshot: passed (no vector generation in this fixture)")
    finally:
        # Only IDs created by this invocation are eligible for cleanup.
        async with AsyncSessionFactory() as db:
            await db.execute(delete(JobRecord).where(JobRecord.collection_id == collection_id))
            await db.execute(delete(KnowledgeCollection).where(KnowledgeCollection.id == collection_id))
            await db.commit()
        print("Isolated test DB rows removed; existing sources and snapshot files untouched")
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
