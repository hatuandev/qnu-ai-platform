"""A durable single-call review; never rewrite, retry or approve compiler output."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.compilation.review import artifacts, service
from qnu.domains.knowledge.compilation.review.models import CompilationReview
from qnu.domains.knowledge.compilation.review.report import build_report, decode_keyed, markdown_for
from qnu.domains.knowledge.compilation.review.schemas import ReviewRequest, ReviewResponse
from qnu.domains.modelops.public_api import resolve_chat_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel, ChatResponseError

logger = get_logger(__name__)


async def execute(
    db: AsyncSession,
    blob: BlobStore,
    chat: ChatModel,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    req: ReviewRequest,
    key: str,
) -> ReviewResponse:
    run, row, material, runtime, call = await service.prepare(
        db, blob, actor, workspace_id, collection_id, run_id, req, key
    )
    if material is None:
        if row.status == "completed":
            await service.target_matches(db, blob, row, run)
        return ReviewResponse.model_validate(row)
    row_id = row.id
    assert runtime is not None and call is not None
    request, messages = call
    try:
        usage = await usage_service.reserve(
            db,
            actor,
            workspace_id,
            "chat",
            "compiler-review:" + row_id,
            row.request_hash,
            row.trace["total_reserved_tokens"],
            runtime.provider_id,
        )
        row.usage_id = usage.id
        await db.commit()
        try:
            await service.checkpoint(db, blob, actor, row, run)
            await require_provider(
                db, workspace_id, runtime.provider_id, runtime.configuration_hash
            )
            row.request_started_at = utcnow()
            await db.commit()
        except (Exception, asyncio.CancelledError):
            await usage_service.settle(db, usage.id, total_tokens=0, failed=True)
            raise
        try:
            result = await chat.complete(messages, request)
        except ChatResponseError as exc:
            row.usage_tokens = exc.usage_tokens
            await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
            await retain_raw(db, blob, row, exc.raw_body)
            raise
        except (Exception, asyncio.CancelledError):
            await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
            raise
        row.usage_tokens = result.total_tokens
        await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
        await retain_raw(db, blob, row, result.raw_body)
        await service.checkpoint(db, blob, actor, row, run)
        await require_provider(db, workspace_id, runtime.provider_id, runtime.configuration_hash)
        content = (
            decode_keyed(result.content, material.payload)
            if req.structured_output
            else result.content
        )
        report = build_report(content, material.payload, row_id, row.bundle_sha256)
        await artifacts.store(db, blob, row, "report_json", json_bytes(report))
        await artifacts.store(db, blob, row, "markdown", markdown_for(report))
        row.verdict, row.status, row.finished_at = report["verdict"], "completed", utcnow()
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="compilation.review_completed",
            detail={
                "review_id": row_id,
                "verdict": row.verdict,
                "finding_count": report["summary"]["finding_count"],
            },
        )
        await db.commit()
        return ReviewResponse.model_validate(row)
    except (Exception, asyncio.CancelledError) as exc:
        await db.rollback()
        failed = await db.get(CompilationReview, row_id, populate_existing=True)
        if failed is not None and failed.status == "running":
            code = exc.code if isinstance(exc, AppException) else "compilation_review_interrupted"
            failed.error_code = code
            failed.status = (
                "uncertain"
                if (
                    isinstance(exc, asyncio.CancelledError)
                    or not isinstance(exc, AppException)
                    or "uncertain" in code
                    or "expired" in code
                )
                else "failed"
            )
            failed.finished_at = utcnow()
            await db.commit()
            logger.warning(
                "compilation_review_stopped",
                review_id=row_id,
                status=failed.status,
                error_code=code,
            )
        raise


async def require_provider(
    db: AsyncSession, workspace_id: str, provider_id: str, configuration_hash: str
) -> None:
    current = await resolve_chat_runtime(db, workspace_id, provider_id)
    if current.configuration_hash != configuration_hash:
        raise Conflict("Model review đã thay đổi.", code="compilation_review_provider_changed")


async def retain_raw(db: AsyncSession, blob: BlobStore, row: CompilationReview, raw: bytes) -> None:
    if raw:
        await artifacts.store(db, blob, row, "raw_response", raw)
        await db.commit()
