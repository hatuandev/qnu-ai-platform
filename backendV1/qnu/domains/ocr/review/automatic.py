"""Run an automatic review across the whole saved document."""

import asyncio
from collections import deque
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.public_api import resolve_chat_runtime
from qnu.domains.modelops.resilience.routing import choose_target
from qnu.domains.ocr.ids import new_id
from qnu.domains.ocr.models import OcrProcessingRun, utcnow
from qnu.domains.ocr.review import detection, service
from qnu.domains.ocr.review.models import SpellingRun
from qnu.domains.ocr.review.schemas import DetectRequest
from qnu.domains.workspaces.access import actor_ref
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel

BATCH_SIZE = 25
SPLIT_ERRORS = {
    "model_input_limit_exceeded",
    "model_context_limit_exceeded",
    "chat_output_truncated",
}


async def review_document(
    db: AsyncSession,
    blob: BlobStore,
    chat: ChatModel,
    actor: AuthActor,
    run: OcrProcessingRun,
    version: int,
) -> str:
    await service.authorize(db, actor, run, write=True, lock=True)
    doc = await service.read_review(db, blob, run, version)
    if doc.version != version:
        return "version_not_found"
    evidence_ids = list(dict.fromkeys(unit.evidence_id for unit in doc.units))
    key = f"auto:spl:document:{run.id}:{version}:{detection.PROMPT_VERSION}"
    existing = await db.scalar(
        select(SpellingRun).where(
            SpellingRun.workspace_id == run.workspace_id,
            SpellingRun.created_by == actor_ref(actor),
            SpellingRun.idempotency_key == key,
        )
    )
    if existing is not None:
        return (await detection.readable_check(db, existing)).status
    parent_id = new_id("spl")
    parent = SpellingRun(
        id=parent_id,
        run_id=run.id,
        workspace_id=run.workspace_id,
        collection_id=run.collection_id,
        created_by=actor_ref(actor),
        idempotency_key=key,
        request_hash=doc.canonical_sha256,
        status="running" if evidence_ids else "completed",
        version=doc.version,
        canonical_sha256=doc.canonical_sha256,
        checked_evidence_ids=[],
        suggestions=[],
        trace={
            "prompt_version": detection.PROMPT_VERSION,
            "total_evidence_count": len(evidence_ids),
            "withheld_suggestions": [],
        },
        expires_at=utcnow()
        + timedelta(seconds=get_settings().WORKER_MODEL_JOB_TIMEOUT_SECONDS + 60),
    )
    db.add(parent)
    await db.commit()
    if not evidence_ids:
        return "completed"

    groups = deque(
        (offset, evidence_ids[offset : offset + BATCH_SIZE])
        for offset in range(0, len(evidence_ids), BATCH_SIZE)
    )
    error_code = None
    try:
        provider_id, routing = await choose_target(db, run.workspace_id, "ocr_review", None)
        runtime = await resolve_chat_runtime(db, run.workspace_id, provider_id)
        configuration_hash = runtime.inference_configuration_hash("ocr_review")
        parent = await detection.check_running(db, parent_id)
        parent.trace = {
            **parent.trace,
            "provider_id": runtime.provider_id,
            "model_name": runtime.model_name,
            "configuration_hash": configuration_hash,
            "routing": list(routing),
        }
        await db.commit()
        while groups:
            await detection.check_running(db, parent_id)
            await db.commit()
            offset, group = groups.popleft()
            try:
                result = await detection.inspect(
                    db,
                    blob,
                    chat,
                    actor,
                    run,
                    DetectRequest(
                        source_version=version,
                        expected_version=version,
                        expected_sha256=doc.canonical_sha256,
                        evidence_ids=group,
                        provider_id=runtime.provider_id,
                    ),
                    f"auto:spl:batch:{parent_id}:{offset}:{len(group)}",
                    automatic_parent=parent_id,
                    configuration_hash=configuration_hash,
                )
            except AppException as exc:
                if exc.code not in SPLIT_ERRORS:
                    raise
                await db.rollback()
                await db.refresh(run)
                if len(group) == 1:
                    error_code = exc.code
                else:
                    middle = len(group) // 2
                    groups.appendleft((offset + middle, group[middle:]))
                    groups.appendleft((offset, group[:middle]))
                continue
            if result.status != "completed":
                return await _finish(db, parent_id, result.status, result.error_code)
            parent = await detection.check_running(db, parent_id)
            parent.checked_evidence_ids = [
                *parent.checked_evidence_ids,
                *result.checked_evidence_ids,
            ]
            parent.suggestions = [
                *parent.suggestions,
                *(item.model_dump() for item in result.suggestions),
            ]
            parent.trace = {
                **parent.trace,
                "withheld_suggestions": [
                    *parent.trace["withheld_suggestions"],
                    *(item.model_dump() for item in result.withheld_suggestions),
                ],
            }
            await db.commit()
        return await _finish(db, parent_id, "failed" if error_code else "completed", error_code)
    except AppException as exc:
        await db.rollback()
        status = "uncertain" if exc.code == "chat_provider_uncertain" else "failed"
        return await _finish(db, parent_id, status, exc.code)
    except (Exception, asyncio.CancelledError):
        await db.rollback()
        await _finish(db, parent_id, "uncertain", "ocr_spelling_interrupted")
        raise


async def _finish(db: AsyncSession, check_id: str, status: str, code: str | None) -> str:
    row = await db.get(SpellingRun, check_id, with_for_update=True, populate_existing=True)
    if row is None:
        return "cancelled"
    if row.status == "running":
        row.status, row.error_code = status, code
    await db.commit()
    return row.status
