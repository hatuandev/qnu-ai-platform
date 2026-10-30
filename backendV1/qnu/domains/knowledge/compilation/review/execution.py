"""Durable review: one call when it fits, exhaustive parts when it does not."""

import asyncio
import hashlib
import json
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review import artifacts, parts, report, service
from qnu.domains.knowledge.compilation.review.models import (
    CompilationReview,
    CompilationReviewSegment,
)
from qnu.domains.knowledge.compilation.review.report import (
    build_report,
    decode_keyed,
    markdown_for,
    report_from_assessments,
    validate_content,
)
from qnu.domains.knowledge.compilation.review.schemas import (
    ReviewContent,
    ReviewRequest,
    ReviewResponse,
)
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.public_api import resolve_chat_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel, ChatResponseError
from qnu.ports.provider_execution import bind_usage

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
    prepared = await service.prepare(
        db, blob, actor, workspace_id, collection_id, run_id, req, key
    )
    run, row, material, runtime = prepared.run, prepared.review, prepared.material, prepared.runtime
    if material is None:
        if row.status == "completed":
            await service.target_matches(db, blob, row, run)
        return ReviewResponse.model_validate(row)
    assert runtime is not None
    row_id = row.id
    if prepared.segmented:
        return await _execute_segments(
            db, blob, chat, actor, workspace_id, run, row, material, runtime
        )
    assert prepared.request is not None and prepared.messages is not None
    request, messages = prepared.request, prepared.messages
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
            result = await chat.complete(messages, bind_usage(request, usage.id))
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
        built = build_report(content, material.payload, row_id, row.bundle_sha256)
        await artifacts.store(db, blob, row, "report_json", json_bytes(built))
        await artifacts.store(db, blob, row, "markdown", markdown_for(built))
        row.verdict, row.status, row.finished_at = built["verdict"], "completed", utcnow()
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="compilation.review_completed",
            detail={
                "review_id": row_id,
                "verdict": row.verdict,
                "finding_count": built["summary"]["finding_count"],
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


async def _execute_segments(
    db: AsyncSession,
    blob: BlobStore,
    chat: ChatModel,
    actor: AuthActor,
    workspace_id: str,
    run: CompilationRun,
    row: CompilationReview,
    material,
    runtime,
) -> ReviewResponse:
    row_id = row.id
    token = row.trace["execution_token"]
    segments = await _load_segments(db, row_id)
    if not segments:
        raise AppException(
            "Review nhiều phần không có phần nào để chạy.",
            code="compilation_review_segments_missing",
            status_code=409,
        )
    try:
        await _verify_manifest(db, blob, row, segments)
        await service.checkpoint(db, blob, actor, row, run)
        total = len(segments)
        for segment in segments:
            await _owned_checkpoint(db, blob, actor, row, run, token)
            if segment.status == "completed":
                continue
            await _resume_segment(db, blob, row, segment)
            if segment.status in {"failed", "uncertain"}:
                raise AppException(
                    "Một phần review không hoàn tất.",
                    code=segment.error_code or "compilation_review_segment_failed",
                    status_code=409,
                )
            if segment.status == "completed":
                continue
            await _run_segment(
                db,
                blob,
                chat,
                actor,
                workspace_id,
                row,
                segment,
                material,
                runtime,
                total,
                token,
            )
        await _owned_checkpoint(db, blob, actor, row, run, token)
        assessed = await _merged_assessments(db, blob, segments, material)
        built = report_from_assessments(
            assessed, material.payload, row_id, row.bundle_sha256
        )
        await artifacts.store(db, blob, row, "report_json", json_bytes(built))
        await artifacts.store(db, blob, row, "markdown", markdown_for(built))
        tokens = [segment.usage_tokens for segment in segments if segment.usage_tokens]
        row.usage_tokens = sum(tokens) if tokens else None
        row.verdict, row.status, row.finished_at = built["verdict"], "completed", utcnow()
        row.error_code = None
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="compilation.review_completed",
            detail={
                "review_id": row_id,
                "verdict": row.verdict,
                "finding_count": built["summary"]["finding_count"],
                "segments": len(segments),
            },
        )
        await db.commit()
        return ReviewResponse.model_validate(row)
    except asyncio.CancelledError:
        await _mark_uncertain(db, row_id, token)
        failed = await db.get(CompilationReview, row_id, populate_existing=True, with_for_update=True)
        if (
            failed is not None
            and failed.status == "running"
            and failed.trace.get("execution_token") == token
        ):
            failed.status = "uncertain"
            failed.error_code = "compilation_review_interrupted"
            failed.finished_at = utcnow()
            await db.commit()
        raise
    except Exception as exc:
        await _mark_uncertain(db, row_id, token)
        failed = await db.get(CompilationReview, row_id, populate_existing=True, with_for_update=True)
        code = exc.code if isinstance(exc, AppException) else "compilation_review_interrupted"
        uncertain = await _has_uncertain(db, row_id)
        if (
            failed is not None
            and failed.status == "running"
            and failed.trace.get("execution_token") == token
        ):
            failed.status = (
                "uncertain"
                if uncertain or not isinstance(exc, AppException) or "interrupted" in code
                else "failed"
            )
            failed.error_code = code
            failed.finished_at = utcnow()
            await db.commit()
        raise AppException(
            "Review nhiều phần dừng trước khi đủ báo cáo.",
            code=code,
            status_code=409,
        ) from exc


async def _load_segments(db: AsyncSession, review_id: str) -> list[CompilationReviewSegment]:
    return list(
        (
            await db.scalars(
                select(CompilationReviewSegment)
                .where(CompilationReviewSegment.review_id == review_id)
                .order_by(CompilationReviewSegment.segment_index)
            )
        ).all()
    )


async def _owned_checkpoint(db, blob, actor, row, run, token):
    with db.no_autoflush:
        await service.checkpoint(db, blob, actor, row, run)
        if row.trace.get("execution_token") != token:
            raise Conflict("Lượt review đã được tiếp quản.", code="compilation_review_claim_lost")
        await require_provider(db, row.workspace_id, row.provider_id, row.trace["configuration_hash"])


async def _verify_manifest(
    db: AsyncSession,
    blob: BlobStore,
    row: CompilationReview,
    segments: list[CompilationReviewSegment],
) -> None:
    expected = (row.trace.get("segmentation") or {}).get("manifest_sha256")
    artifact, payload = await artifacts.read(db, blob, row, "segment_manifest")
    if expected != artifact.sha256:
        raise AppException(
            "Manifest review không khớp yêu cầu.",
            code="compilation_review_segment_manifest_mismatch",
            status_code=409,
        )
    try:
        manifest = json.loads(payload)
    except ValueError as exc:
        raise AppException(
            "Manifest review không đọc được.",
            code="compilation_review_segment_manifest_mismatch",
            status_code=409,
        ) from exc
    scopes = manifest.get("segments") or []
    if (
        manifest.get("review_id") != row.id
        or manifest.get("bundle_sha256") != row.bundle_sha256
        or len(scopes) != len(segments)
        or [scope.get("index") for scope in scopes]
        != [segment.segment_index for segment in segments]
        or [
            (
                scope.get("source_ids"),
                scope.get("draft_ids"),
                scope.get("context_source_ids"),
                scope.get("context_draft_ids"),
                scope.get("input_sha256"),
            )
            for scope in scopes
        ]
        != [
            (
                segment.scope.get("source_ids"),
                segment.scope.get("draft_ids"),
                segment.scope.get("context_source_ids"),
                segment.scope.get("context_draft_ids"),
                segment.input_sha256,
            )
            for segment in segments
        ]
    ):
        raise AppException(
            "Manifest review không khớp các phần đã lưu.",
            code="compilation_review_segment_manifest_mismatch",
            status_code=409,
        )


async def _resume_segment(
    db: AsyncSession, blob: BlobStore, row: CompilationReview, segment: CompilationReviewSegment
) -> None:
    if segment.status == "completed":
        return
    raw = await artifacts.segment_artifact(db, segment.id, "raw_response")
    if segment.status == "running":
        # A durable assessment means the part finished before its status commit.
        assessed = await artifacts.segment_artifact(db, segment.id, "assessment_json")
        if assessed is not None and segment.usage_tokens is not None:
            if segment.usage_id:
                await usage_service.settle(
                    db, segment.usage_id, total_tokens=segment.usage_tokens
                )
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            await db.commit()
            return
        if segment.request_started_at is not None and raw is None:
            if segment.usage_id:
                await usage_service.settle(db, segment.usage_id, total_tokens=None, failed=True)
            segment.status = "uncertain"
            segment.error_code = "compilation_review_request_interrupted"
            segment.finished_at = utcnow()
            await db.commit()
            return
        segment.status = "pending" if raw is None else "received"
        segment.worker_id = None
        await db.commit()
    if segment.status == "received" and raw is None:
        assessed = await artifacts.segment_artifact(db, segment.id, "assessment_json")
        if assessed is not None and segment.usage_tokens is not None:
            if segment.usage_id:
                await usage_service.settle(
                    db, segment.usage_id, total_tokens=segment.usage_tokens
                )
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            await db.commit()
            return
        if segment.usage_id:
            await usage_service.settle(db, segment.usage_id, total_tokens=None, failed=True)
        segment.status = "uncertain"
        segment.error_code = "compilation_review_segment_raw_missing"
        segment.finished_at = utcnow()
        await db.commit()


async def _run_segment(
    db: AsyncSession,
    blob: BlobStore,
    chat: ChatModel,
    actor: AuthActor,
    workspace_id: str,
    row: CompilationReview,
    segment: CompilationReviewSegment,
    material,
    runtime,
    total: int,
    token: str,
) -> None:
    if segment.status == "completed":
        return
    structured = bool(row.trace.get("structured_output"))
    plan, messages, schema = parts.rebuild_part(
        material.payload, segment.scope, total=total, structured=structured
    )
    raw = await artifacts.segment_artifact(db, segment.id, "raw_response")
    if raw is not None:
        _, payload = await artifacts.read_segment(db, blob, segment, "raw_response")
        try:
            content = json.loads(payload)["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            await _fail_segment(db, segment, "compilation_review_raw_invalid")
            raise AppException(
                "Raw review không đọc được.", code="compilation_review_raw_invalid"
            ) from exc
        if segment.usage_id and segment.usage_tokens is None:
            raise AppException(
                "Phần review đã nhận phản hồi nhưng thiếu usage; không gửi lại.",
                code="compilation_review_usage_unknown",
                status_code=409,
            )
    else:
        current_runtime, request, budget = await prepare_chat_request(
            db,
            actor,
            workspace_id,
            messages,
            provider_id=row.provider_id,
            task="compiler_review",
            max_output_tokens=segment.config["max_output_tokens"],
            output_schema=schema,
        )
        if current_runtime.configuration_hash != row.trace["configuration_hash"]:
            raise Conflict(
                "Model review đã thay đổi.", code="compilation_review_provider_changed"
            )
        if current_runtime.provider_id != segment.config["provider_id"]:
            raise Conflict(
                "Provider review đã thay đổi.", code="compilation_review_provider_changed"
            )
        usage = await usage_service.reserve(
            db,
            actor,
            workspace_id,
            "chat",
            f"compiler-review:{row.id}:segment:{segment.segment_index}:"
            f"{segment.attempt_count + 1}",
            segment.request_hash,
            budget.total_reserved_tokens,
            runtime.provider_id,
        )
        segment.usage_id = usage.id
        segment.status, segment.worker_id = "running", row.created_by
        segment.attempt_count += 1
        segment.request_started_at = utcnow()
        await _owned_checkpoint(db, blob, actor, row, run, token)
        await db.commit()
        try:
            result = await chat.complete(messages, bind_usage(request, usage.id))
        except ChatResponseError as exc:
            await _owned_checkpoint(db, blob, actor, row, run, token)
            if exc.raw_body:
                await artifacts.store_segment(db, blob, row, segment, "raw_response", exc.raw_body)
            segment.usage_tokens = exc.usage_tokens
            await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
            await _owned_checkpoint(db, blob, actor, row, run, token)
            await _fail_segment(db, segment, exc.code)
            raise
        except (Exception, asyncio.CancelledError):
            await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
            raise
        await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
        await _owned_checkpoint(db, blob, actor, row, run, token)
        segment.usage_tokens = result.total_tokens
        if result.raw_body:
            await artifacts.store_segment(db, blob, row, segment, "raw_response", result.raw_body)
        segment.status = "received"
        await db.commit()
        content = result.content
    await _owned_checkpoint(db, blob, actor, row, run, token)
    if structured:
        content = decode_keyed(content, plan.payload)
    try:
        validate_content(content, plan.payload)
    except AppException:
        await _fail_segment(db, segment, "compilation_review_invalid")
        raise
    await artifacts.store_segment(
        db, blob, row, segment, "assessment_json", content.encode("utf-8")
    )
    segment.status, segment.error_code = "completed", None
    segment.finished_at = utcnow()
    await db.commit()


async def _fail_segment(
    db: AsyncSession, segment: CompilationReviewSegment, code: str
) -> None:
    segment.status, segment.error_code, segment.finished_at = "failed", code, utcnow()
    await db.commit()


async def _mark_uncertain(db: AsyncSession, review_id: str, token: str) -> None:
    """A cancelled/unknown part is recovered from its own artifacts, never resent blindly."""
    await db.rollback()
    row = await db.get(CompilationReview, review_id, populate_existing=True, with_for_update=True)
    if row is None or row.trace.get("execution_token") != token:
        return
    segments = await _load_segments(db, review_id)
    changed = False
    for segment in segments:
        if segment.status != "running" or segment.request_started_at is None:
            continue
        assessed = await artifacts.segment_artifact(db, segment.id, "assessment_json")
        if assessed is not None:
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            changed = True
            continue
        raw = await artifacts.segment_artifact(db, segment.id, "raw_response")
        if raw is not None:
            segment.status = "received"
            segment.worker_id = None
            changed = True
            continue
        segment.status = "uncertain"
        segment.error_code = "compilation_review_request_interrupted"
        segment.finished_at = utcnow()
        changed = True
    if changed:
        await db.commit()


async def _has_uncertain(db: AsyncSession, review_id: str) -> bool:
    return any(
        segment.status == "uncertain" for segment in await _load_segments(db, review_id)
    )


async def _merged_assessments(
    db: AsyncSession, blob: BlobStore, segments: list[CompilationReviewSegment], material
) -> "ReviewContent":
    assembled = {"source_assessments": [], "draft_assessments": []}
    for segment in segments:
        _, payload = await artifacts.read_segment(db, blob, segment, "assessment_json")
        plan = parts.plan_from_scope(segment.scope)
        part_payload = parts.payload_for(
            material.payload,
            plan.source_ids,
            plan.draft_ids,
            plan.context_source_ids,
            plan.context_draft_ids,
        )
        value = validate_content(payload.decode("utf-8"), part_payload)
        assembled["source_assessments"].extend(
            assessment.model_dump() for assessment in value.source_assessments
        )
        assembled["draft_assessments"].extend(
            assessment.model_dump() for assessment in value.draft_assessments
        )
    value = ReviewContent.model_validate(assembled)
    source_ids = [unit["id"] for unit in material.payload["source_units"]]
    draft_ids = [unit["id"] for unit in material.payload["draft_units"]]
    if Counter(a.source_id for a in value.source_assessments) != Counter(source_ids):
        raise AppException(
            "Báo cáo review ghép không phủ đủ nguồn.",
            code="compilation_review_coverage_invalid",
            status_code=409,
        )
    if Counter(a.draft_id for a in value.draft_assessments) != Counter(draft_ids):
        raise AppException(
            "Báo cáo review ghép không phủ đủ bản nháp.",
            code="compilation_review_coverage_invalid",
            status_code=409,
        )
    return value


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
