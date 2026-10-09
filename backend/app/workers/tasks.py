"""Asynchronous Background Worker Tasks for QNU AI Platform (ARQ + Redis).

Every task is job-tracked: it loads its ``JobRecord``, reports progress,
supports cooperative cancellation (checks between phases), and finishes with
an honest result — real counts, never fabricated numbers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.core.storage import storage_service
from app.modules.jobs.models import JobRecord
from app.modules.jobs.service import is_job_cancelled
from app.modules.knowledge.models import KnowledgeChunk
from app.modules.knowledge.service import knowledge_service

logger = structlog.get_logger(__name__)


async def _load_job(db, job_id: str) -> JobRecord | None:
    res = await db.execute(
        select(JobRecord)
        .where(JobRecord.id == job_id)
        .execution_options(populate_existing=True)
    )
    return res.scalar_one_or_none()


async def _set_job(
    db,
    job: JobRecord,
    status: str,
    progress: float | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> bool:
    """Update job state. Returns True if updated, or False if blocked due to cancellation."""
    if await is_job_cancelled(job.id, db=db):
        fresh_res = await db.execute(
            select(JobRecord)
            .where(JobRecord.id == job.id)
            .execution_options(populate_existing=True)
        )
        fresh_job = fresh_res.scalar_one_or_none()
        if fresh_job:
            fresh_job.status = "cancelled"
            fresh_job.phase = "cancelled"
            fresh_job.heartbeat_at = datetime.now(UTC)
            if not getattr(fresh_job, "error", None):
                fresh_job.error = "Tác vụ đã bị hủy bởi người dùng (cooperative cancel)."
            await db.commit()
        return False

    job.status = status
    job.phase = status
    job.heartbeat_at = datetime.now(UTC)
    if progress is not None:
        job.progress = progress
    if result is not None:
        job.result = result
    if error is not None:
        job.error = error
    await db.commit()
    return True


async def _is_cancelled(db, job_id: str) -> bool:
    return await is_job_cancelled(job_id, db=db)


async def _check_pre_execution_cancelled(db, job: JobRecord) -> bool:
    if await is_job_cancelled(job.id, db=db):
        fresh_res = await db.execute(
            select(JobRecord)
            .where(JobRecord.id == job.id)
            .execution_options(populate_existing=True)
        )
        fresh_job = fresh_res.scalar_one_or_none()
        if fresh_job:
            fresh_job.status = "cancelled"
            fresh_job.phase = "cancelled"
            if not getattr(fresh_job, "error", None):
                fresh_job.error = "Tác vụ đã bị hủy bởi người dùng (cooperative cancel)."
            await db.commit()
        return True
    return False


async def task_document_ingestion(ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Background reprocessing: reload bytes, parse+OCR, replace chunks/facts."""
    async with AsyncSessionFactory() as db:
        job = await _load_job(db, job_id)
        if job is None:
            return {"status": "failed", "job_id": job_id, "error": "Job record not found"}
        if await _check_pre_execution_cancelled(db, job):
            return {"status": "cancelled", "job_id": job_id}
        document_id = job.document_id or (job.payload or {}).get("document_id", "")
        try:
            if not await _set_job(db, job, "running", progress=5.0):
                return {"status": "cancelled", "job_id": job_id}
            doc = await knowledge_service.get_document(db, document_id)
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}

            raw_bytes = await storage_service.get(doc.storage_path)
            if not raw_bytes:
                raise FileNotFoundError(f"Missing stored file: {doc.storage_path}")
            if not await _set_job(db, job, "running", progress=30.0):
                return {"status": "cancelled", "job_id": job_id}

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
            if not await _set_job(db, job, "running", progress=70.0):
                return {"status": "cancelled", "job_id": job_id}

            count = await knowledge_service.replace_document_content(
                db, doc, doc.collection_id, collection.module_code, prepared
            )
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}

            result = {
                "status": "completed",
                "job_id": job_id,
                "document_id": document_id,
                "collection_id": doc.collection_id,
                "indexed_chunks": count,
            }
            if not await _set_job(db, job, "completed", progress=100.0, result=result):
                return {"status": "cancelled", "job_id": job_id}
            logger.info("task_document_ingestion_completed", **result)
            return result
        except Exception as exc:
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}
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
        if await _check_pre_execution_cancelled(db, job):
            return {"status": "cancelled", "job_id": job_id}
        collection_id = job.collection_id or (job.payload or {}).get("collection_id", "")
        try:
            if not await _set_job(db, job, "running", progress=10.0):
                return {"status": "cancelled", "job_id": job_id}
            res = await db.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.collection_id == collection_id)
            )
            chunks = list(res.scalars().all())
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}
            if not await _set_job(db, job, "running", progress=40.0):
                return {"status": "cancelled", "job_id": job_id}

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
            # Checkpoint: Verify cancellation after embedding/upsert and before marking completed
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}

            result = {
                "status": "completed",
                "job_id": job_id,
                "collection_id": collection_id,
                "points_reindexed": indexed,
                "total_chunks": len(chunks),
            }
            if not await _set_job(db, job, "completed", progress=100.0, result=result):
                return {"status": "cancelled", "job_id": job_id}
            logger.info("task_reindex_collection_completed", **result)
            return result
        except Exception as exc:
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}
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
                db,
                job,
                "completed",
                progress=100.0,
                result={"output_file": output_file, "paragraphs": len(body_paragraphs)},
            )
    logger.info("task_export_document_completed", job_id=job_id, output_file=output_file)
    return {
        "status": "completed",
        "job_id": job_id,
        "document_type": document_type,
        "output_file": output_file,
    }


async def task_document_revision_parse(ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Worker task to process a DocumentRevision through parsing, OCR, and Quality Gate."""
    from app.modules.documents.revision_service import document_revision_service

    async with AsyncSessionFactory() as db:
        job = await _load_job(db, job_id)
        if job is None:
            return {"status": "failed", "job_id": job_id, "error": "Job record not found"}

        payload = job.payload or {}
        revision_id = payload.get("revision_id")
        ocr_engine = payload.get("ocr_engine")

        if not revision_id:
            await _set_job(db, job, "failed", error="Missing revision_id in job payload")
            return {"status": "failed", "job_id": job_id, "error": "Missing revision_id"}

        if await _check_pre_execution_cancelled(db, job):
            return {"status": "cancelled", "job_id": job_id}

        if not await _set_job(db, job, "running", progress=10.0):
            return {"status": "cancelled", "job_id": job_id}
        if await _is_cancelled(db, job_id):
            return {"status": "cancelled", "job_id": job_id}

        try:
            rev = await document_revision_service.process_revision(
                db=db,
                revision_id=revision_id,
                ocr_engine=ocr_engine,
            )
            if await _is_cancelled(db, job_id):
                if rev.status == "ready":
                    rev.status = "failed"
                    rev.failure_code = "JOB_CANCELLED"
                    rev.failure_detail = "Tác vụ bóc tách đã bị hủy bởi người dùng (cooperative cancel)."
                    await db.commit()
                return {"status": "cancelled", "job_id": job_id}

            final_status = "completed" if rev.status in ("ready", "review_required") else "failed"
            err = rev.failure_detail if rev.status == "failed" else None
            if not await _set_job(
                db,
                job,
                final_status,
                progress=100.0,
                result={
                    "revision_id": rev.id,
                    "revision_status": rev.status,
                    "quality_overall": (rev.quality_report or {}).get("overall_status"),
                },
                error=err,
            ):
                return {"status": "cancelled", "job_id": job_id}
            if final_status == "failed":
                raise RuntimeError(err or f"Revision {rev.id} processing failed")
            return {
                "status": final_status,
                "job_id": job_id,
                "revision_id": rev.id,
                "revision_status": rev.status,
            }
        except Exception as exc:
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}
            logger.exception("task_document_revision_parse_failed", job_id=job_id, error=str(exc))
            await _set_job(db, job, "failed", error=str(exc)[:500])
            raise


async def task_knowledge_index_build(ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Worker task to build a KnowledgeIndexRevision in staging, verify parity gate, and prepare for promotion."""
    from app.modules.knowledge.services.index_build_service import index_build_service

    async with AsyncSessionFactory() as db:
        job = await _load_job(db, job_id)
        if job is None:
            return {"status": "failed", "job_id": job_id, "error": "Job record not found"}

        payload = job.payload or {}
        binding_id = payload.get("binding_id")
        source_revision_id = payload.get("source_revision_id")

        if not binding_id or not source_revision_id:
            await _set_job(
                db, job, "failed", error="Missing binding_id or source_revision_id in job payload"
            )
            return {"status": "failed", "job_id": job_id, "error": "Missing parameters"}

        if await _check_pre_execution_cancelled(db, job):
            return {"status": "cancelled", "job_id": job_id}

        if not await _set_job(db, job, "running", progress=10.0):
            return {"status": "cancelled", "job_id": job_id}
        if await _is_cancelled(db, job_id):
            return {"status": "cancelled", "job_id": job_id}

        try:
            index_rev = await index_build_service.build_staging_index(
                db=db,
                binding_id=binding_id,
                source_revision_id=source_revision_id,
                job_id=job.id,
            )
            if await _is_cancelled(db, job_id):
                if index_rev.status in ("ready", "active"):
                    index_rev.status = "failed"
                    index_rev.failure_code = "JOB_CANCELLED"
                    index_rev.failure_detail = "Tác vụ dựng chỉ mục đã bị hủy bởi người dùng (cooperative cancel)."
                    await db.commit()
                return {"status": "cancelled", "job_id": job_id}

            final_status = "completed" if index_rev.status in ("ready", "active") else "failed"
            err = index_rev.failure_detail if index_rev.status == "failed" else None
            if not await _set_job(
                db,
                job,
                final_status,
                progress=100.0,
                result={
                    "index_revision_id": index_rev.id,
                    "index_revision_status": index_rev.status,
                    "chunk_count": index_rev.chunk_count,
                    "fact_count": index_rev.fact_count,
                    "parity_passed": (index_rev.parity_report or {}).get("parity_status")
                    == "passed",
                },
                error=err,
            ):
                return {"status": "cancelled", "job_id": job_id}
            if final_status == "failed":
                raise RuntimeError(err or f"Index revision {index_rev.id} build failed")
            return {
                "status": final_status,
                "job_id": job_id,
                "index_revision_id": index_rev.id,
                "index_revision_status": index_rev.status,
            }
        except Exception as exc:
            if await _is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": job_id}
            logger.exception("task_knowledge_index_build_failed", job_id=job_id, error=str(exc))
            await _set_job(db, job, "failed", error=str(exc)[:500])
            raise


async def task_knowledge_garbage_collection(ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Worker task to execute or simulate system-wide artifact garbage collection with rollback protection."""
    from app.modules.knowledge.services.gc_service import gc_service

    async with AsyncSessionFactory() as db:
        job = await _load_job(db, job_id)
        if job is None:
            return {"status": "failed", "job_id": job_id, "error": "Job record not found"}

        payload = job.payload or {}
        dry_run = bool(payload.get("dry_run", False))
        collection_id = payload.get("collection_id")
        keep_revisions = int(payload.get("keep_revisions", 2))

        if await _check_pre_execution_cancelled(db, job):
            return {"status": "cancelled", "job_id": job_id}

        if not await _set_job(db, job, "running", progress=10.0):
            return {"status": "cancelled", "job_id": job_id}

        try:
            if collection_id:
                report = await gc_service.collect_garbage(
                    db=db,
                    collection_id=collection_id,
                    keep_revisions=keep_revisions,
                    dry_run=dry_run,
                    job_id=job_id,
                )
                res_dict = report.model_dump(mode="json")
            else:
                sys_report = await gc_service.collect_garbage_system_wide(
                    db=db,
                    default_keep_revisions=keep_revisions,
                    dry_run=dry_run,
                    job_id=job_id,
                )
                res_dict = sys_report.model_dump(mode="json")

            if await is_job_cancelled(job_id, db=db):
                return {"status": "cancelled", "job_id": job_id}

            await _set_job(
                db,
                job,
                "completed",
                progress=100.0,
                result=res_dict,
            )
            return {"status": "completed", "job_id": job_id, "result": res_dict}
        except Exception as exc:
            if await is_job_cancelled(job_id):
                return {"status": "cancelled", "job_id": job_id}
            logger.exception(
                "task_knowledge_garbage_collection_failed", job_id=job_id, error=str(exc)
            )
            await _set_job(db, job, "failed", error=str(exc)[:500])
            return {"status": "failed", "job_id": job_id, "error": str(exc)[:500]}


async def task_reconcile_pending_jobs(ctx: dict[str, Any]) -> dict[str, int]:
    """Periodically recover durable jobs that could not be dispatched to Redis."""
    from app.modules.jobs.service import jobs_service

    async with AsyncSessionFactory() as db:
        dispatched = await jobs_service.reconcile_pending_dispatches(db)
    if dispatched:
        logger.info("pending_jobs_redispatched", dispatched=dispatched)
    return {"dispatched": dispatched}
