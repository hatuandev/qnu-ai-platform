"""Asynchronous Background Worker Tasks for QNU AI Platform (ARQ + Redis).

Every task is job-tracked: it loads its ``JobRecord``, reports progress,
supports cooperative cancellation (checks between phases), and finishes with
an honest result — real counts, never fabricated numbers.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.core.storage import storage_service
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import KnowledgeChunk
from app.modules.knowledge.service import knowledge_service

logger = structlog.get_logger(__name__)


async def _load_job(db, job_id: str) -> JobRecord | None:
    res = await db.execute(select(JobRecord).where(JobRecord.id == job_id))
    return res.scalar_one_or_none()


async def _set_job(
    db,
    job: JobRecord,
    status: str,
    progress: float | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    job.status = status
    if progress is not None:
        job.progress = progress
    if result is not None:
        job.result = result
    if error is not None:
        job.error = error
    await db.commit()


async def _is_cancelled(db, job_id: str) -> bool:
    job = await _load_job(db, job_id)
    return job is None or job.status == "cancelled"


async def task_document_ingestion(ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Background reprocessing: reload bytes, parse+OCR, replace chunks/facts."""
    async with AsyncSessionFactory() as db:
        job = await _load_job(db, job_id)
        if job is None:
            return {"status": "failed", "job_id": job_id, "error": "Job record not found"}
        document_id = job.document_id or (job.payload or {}).get("document_id", "")
        try:
            await _set_job(db, job, "running", progress=5.0)
            doc = await knowledge_service.get_document(db, document_id)
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}

            raw_bytes = await storage_service.get(doc.storage_path)
            if not raw_bytes:
                raise FileNotFoundError(f"Missing stored file: {doc.storage_path}")
            await _set_job(db, job, "running", progress=30.0)

            ocr_engine = (job.payload or {}).get("ocr_engine")
            collection = await knowledge_service.get_collection(db, doc.collection_id)
            prepared = await knowledge_service.prepare_ingestion(
                db=db,
                module_code=collection.module_code,
                file_bytes=raw_bytes,
                file_name=doc.file_name,
                ocr_engine=ocr_engine,
            )
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}
            await _set_job(db, job, "running", progress=70.0)

            count = await knowledge_service.replace_document_content(
                db, doc, doc.collection_id, collection.module_code, prepared
            )
            result = {
                "status": "completed",
                "job_id": job_id,
                "document_id": document_id,
                "collection_id": doc.collection_id,
                "indexed_chunks": count,
            }
            await _set_job(db, job, "completed", progress=100.0, result=result)
            logger.info("task_document_ingestion_completed", **result)
            return result
        except Exception as exc:
            logger.error("task_document_ingestion_failed", job_id=job_id, error=str(exc))
            await _set_job(db, job, "failed", error=str(exc)[:1000])
            return {"status": "failed", "job_id": job_id, "error": str(exc)[:500]}


async def task_reindex_collection(ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Re-embed every chunk of a collection and upsert to Qdrant."""
    from app.modules.rag.vector_indexer import vector_indexer

    async with AsyncSessionFactory() as db:
        job = await _load_job(db, job_id)
        if job is None:
            return {"status": "failed", "job_id": job_id, "error": "Job record not found"}
        collection_id = job.collection_id or (job.payload or {}).get("collection_id", "")
        try:
            await _set_job(db, job, "running", progress=10.0)
            res = await db.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.collection_id == collection_id)
            )
            chunks = list(res.scalars().all())
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}
            await _set_job(db, job, "running", progress=40.0)

            indexed = await vector_indexer.index_chunks(
                collection_id=collection_id,
                chunks=[
                    {
                        "id": c.id,
                        "point_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{collection_id}:{c.id}")),
                        "content": c.content,
                        "document_id": c.document_id,
                        "section": c.section,
                        "page_number": c.page_number,
                        "metadata": c.chunk_metadata or {},
                    }
                    for c in chunks
                ],
            )
            result = {
                "status": "completed",
                "job_id": job_id,
                "collection_id": collection_id,
                "points_reindexed": indexed,
                "total_chunks": len(chunks),
            }
            await _set_job(db, job, "completed", progress=100.0, result=result)
            logger.info("task_reindex_collection_completed", **result)
            return result
        except Exception as exc:
            logger.error("task_reindex_collection_failed", job_id=job_id, error=str(exc))
            await _set_job(db, job, "failed", error=str(exc)[:1000])
            return {"status": "failed", "job_id": job_id, "error": str(exc)[:500]}


async def task_export_document(
    ctx: dict[str, Any],
    job_id: str,
    document_type: str = "THONG_BAO",
    title: str = "",
    body_paragraphs: list[str] | None = None,
) -> dict[str, Any]:
    """Render a real .docx file from title + paragraphs into storage.

    Keeps the legacy positional signature (job_id, document_type, title,
    body_paragraphs) while also accepting a tracked ``job_id`` record when the
    job was enqueued through the jobs module.
    """
    import docx

    body_paragraphs = body_paragraphs or []
    output_file = f"exports/{document_type}_{job_id}.docx"
    try:
        document = docx.Document()
        if title:
            document.add_heading(title, level=1)
        for paragraph in body_paragraphs:
            if paragraph:
                document.add_paragraph(paragraph)
        import io

        buffer = io.BytesIO()
        document.save(buffer)
        await storage_service.save(output_file, buffer.getvalue())
    except Exception as exc:
        logger.error("task_export_document_failed", job_id=job_id, error=str(exc))
        return {"status": "failed", "job_id": job_id, "error": str(exc)[:500]}

    async with AsyncSessionFactory() as db:
        job = await _load_job(db, job_id)
        if job is not None:
            await _set_job(
                db, job, "completed", progress=100.0,
                result={"output_file": output_file, "paragraphs": len(body_paragraphs)},
            )
    logger.info("task_export_document_completed", job_id=job_id, output_file=output_file)
    return {
        "status": "completed",
        "job_id": job_id,
        "document_type": document_type,
        "output_file": output_file,
    }
