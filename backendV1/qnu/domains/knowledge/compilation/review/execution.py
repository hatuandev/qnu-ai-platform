"""Durable review: one call when it fits, exhaustive parts when it does not."""

import asyncio
import json
from collections import Counter
from contextlib import suppress
from dataclasses import replace
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review import artifacts, parts, refinement, repair, service
from qnu.domains.knowledge.compilation.review.literal import assess as assess_literal
from qnu.domains.knowledge.compilation.review.literal import assess_source_prose
from qnu.domains.knowledge.compilation.review.models import (
    CompilationReview,
    CompilationReviewSegment,
)
from qnu.domains.knowledge.compilation.review.report import (
    decode_keyed,
    diagnose_contract,
    markdown_for,
    messages_for,
    output_schema,
    report_from_assessments,
    segment_markdown_for,
    validate_content,
)
from qnu.domains.knowledge.compilation.review.schemas import (
    ReviewContent,
    ReviewRequest,
    ReviewResponse,
)
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.public_api import resolve_chat_runtime
from qnu.domains.modelops.reasoning import ReasoningDirective
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel, ChatResponseError
from qnu.ports.provider_execution import bind_usage

logger = get_logger(__name__)

# Decided, terminal stops that keep their own code instead of the generic wrapper.
TERMINAL_CODE_PREFIXES = (
    "compilation_review_refinement_",
    "compilation_review_budget_",
    "compilation_review_recovery_",
)
CONTRACT_RECOVERY_STOPS = {
    "compilation_review_recovery_exhausted",
    "compilation_review_refinement_depth_exceeded",
    "compilation_review_refinement_atomic_limit",
}


def _persisted_review_stop(segments: list[CompilationReviewSegment]) -> str | None:
    return next(
        (
            segment.error_code
            for segment in refinement.ordered_leaves(segments)
            if segment.status == "failed"
            and (segment.error_code or "").startswith(TERMINAL_CODE_PREFIXES)
        ),
        None,
    )


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
    prepared = await service.prepare(db, blob, actor, workspace_id, collection_id, run_id, req, key)
    run, row, material = prepared.run, prepared.review, prepared.material
    if material is None:
        if row.status == "completed":
            await service.target_matches(db, blob, row, run)
        return ReviewResponse.model_validate(row)
    return await execute_prepared(db, blob, chat, actor, workspace_id, prepared, req)


async def run_queued(db: AsyncSession, blob: BlobStore, chat: ChatModel, review_id: str) -> str:
    row = await db.get(CompilationReview, review_id)
    if row is None or row.status != "queued":
        return "not_claimed"
    actor = background_actor(row.created_by)
    try:
        await service.authorize(db, actor, row.workspace_id, row.collection_id, write=True)
        await db.refresh(row, with_for_update=True)
        if row.status != "queued":
            return "not_claimed"
        run = await service.get_run(
            db, actor, row.workspace_id, row.collection_id, row.compilation_run_id
        )
        material = await service.target_matches(db, blob, row, run)
        req = ReviewRequest(
            provider_id=row.provider_id,
            max_output_tokens=row.trace["max_output_tokens"],
            structured_output=row.trace["structured_output"],
        )
        segmented = bool(row.trace.get("segmentation"))
        request, messages = None, None
        if segmented:
            runtime = await resolve_chat_runtime(db, row.workspace_id, row.provider_id)
        else:
            messages = messages_for(material.payload, structured=req.structured_output)
            schema = (
                output_schema(material.payload, require_references=2)
                if req.structured_output
                else None
            )
            runtime, request, budget = await prepare_chat_request(
                db,
                actor,
                row.workspace_id,
                messages,
                provider_id=row.provider_id,
                task="compiler_review",
                max_output_tokens=req.max_output_tokens,
                output_schema=schema,
                reasoning_task="compiler_review",
            )
            request = replace(request, automatic_output_budget=row.trace["automatic_output_budget"])
            if budget.total_reserved_tokens != row.trace["total_reserved_tokens"]:
                raise Conflict(
                    "Ngân sách review đã thay đổi.", code="compilation_review_provider_changed"
                )
        if runtime.configuration_hash != row.trace["configuration_hash"]:
            raise Conflict("Model review đã thay đổi.", code="compilation_review_provider_changed")
        now = utcnow()
        count = (row.trace.get("segmentation") or {}).get("segment_count", 1)
        row.trace = {**row.trace, "execution_started_at": now.isoformat()}
        row.status = "running"
        row.expires_at = now + timedelta(seconds=max(900, runtime.timeout_seconds + 60) * count)
        await db.commit()
        prepared = service.PreparedReview(run, row, material, runtime, request, messages, segmented)
        result = await execute_prepared(db, blob, chat, actor, row.workspace_id, prepared, req)
        return result.status
    except Exception as exc:
        await db.rollback()
        row = await db.get(
            CompilationReview, review_id, populate_existing=True, with_for_update=True
        )
        if row is None:
            return "missing"
        if row.status in {"queued", "running"}:
            terminal = (
                None
                if isinstance(exc, AppException)
                else _persisted_review_stop(await _load_segments(db, review_id))
            )
            code = exc.code if isinstance(exc, AppException) else terminal
            row.status, row.finished_at = "failed", utcnow()
            row.error_code = code or "compilation_review_internal_error"
            await db.commit()
            logger.warning(
                "manual_review_job_failed",
                review_id=review_id,
                error_code=row.error_code,
                error_type=type(exc).__name__,
            )
        return row.status


async def _complete_until_stopped(chat, messages, request, review_id: str):
    """Cancel the local provider wait after a durable stop, even across processes."""
    task = asyncio.create_task(chat.complete(messages, request))
    try:
        while not (await asyncio.wait({task}, timeout=2))[0]:
            async with AsyncSessionFactory() as monitor:
                status = await monitor.scalar(
                    select(CompilationReview.status).where(CompilationReview.id == review_id)
                )
            if status == "cancelled":
                raise Conflict(
                    "Đã dừng chờ mô hình; kết quả phía nhà cung cấp chưa xác định.",
                    code="compilation_review_cancelled_uncertain",
                )
        return task.result()
    finally:
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


async def execute_prepared(
    db: AsyncSession,
    blob: BlobStore,
    chat: ChatModel,
    actor: AuthActor,
    workspace_id: str,
    prepared: service.PreparedReview,
    req: ReviewRequest,
) -> ReviewResponse:
    run, row, material, runtime = prepared.run, prepared.review, prepared.material, prepared.runtime
    assert runtime is not None and material is not None
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
            result = await _complete_until_stopped(
                chat, messages, bind_usage(request, usage.id), row_id
            )
        except ChatResponseError as exc:
            row.usage_tokens = exc.usage_tokens
            await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
            await retain_raw(db, blob, row, exc.raw_body)
            await db.commit()
            raise
        except (Exception, asyncio.CancelledError):
            await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
            await db.commit()
            raise
        row.usage_tokens = result.total_tokens
        await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
        await retain_raw(db, blob, row, result.raw_body)
        await db.commit()
        await service.checkpoint(db, blob, actor, row, run)
        await require_provider(db, workspace_id, runtime.provider_id, runtime.configuration_hash)
        content = (
            decode_keyed(result.content, material.payload)
            if req.structured_output
            else result.content
        )
        checked = validate_content(content, material.payload, unverified="uncited")
        built = report_from_assessments(checked, material.payload, row_id, row.bundle_sha256)
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
        failed = await db.get(
            CompilationReview, row_id, populate_existing=True, with_for_update=True
        )
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
        root_count = max(1, sum(1 for seg in segments if seg.parent_segment_id is None))
        limits = refinement.limits_for(row.trace, root_count, segments=segments)
        concurrency = 2 if row.trace.get("review_concurrency") == 2 else 1
        while True:
            await _owned_checkpoint(db, blob, actor, row, run, token)
            segments = await _load_segments(db, row_id)
            leaves = refinement.ordered_leaves(segments)
            refined_in_pass = False
            for leaf in leaves:
                if leaf.status == "completed":
                    continue
                await _resume_segment(db, blob, row, leaf)
                reason = refinement.refine_reason(leaf)
                if reason is not None:
                    await _refine_segment(
                        db, blob, actor, row, run, segments, leaf, material, limits, token, reason
                    )
                    refined_in_pass = True
                    break
                if leaf.status in {"failed", "uncertain"}:
                    raise AppException(
                        "Một phần review không hoàn tất.",
                        code=leaf.error_code or "compilation_review_segment_failed",
                        status_code=409,
                    )
            if refined_in_pass:
                continue
            runnable = [leaf for leaf in leaves if leaf.status != "completed"]
            if not runnable:
                break
            total_active = len(leaves)
            if concurrency == 2 and len(runnable) > 1:
                await db.commit()  # Release the review lock before independent part sessions.
                for offset in range(0, len(runnable), concurrency):
                    batch = runnable[offset : offset + concurrency]
                    outcomes = await asyncio.gather(
                        *(
                            _part_session(
                                blob,
                                chat,
                                actor,
                                workspace_id,
                                run.id,
                                row_id,
                                part.id,
                                material,
                                runtime,
                                total_active,
                                token,
                            )
                            for part in batch
                        ),
                        return_exceptions=True,
                    )
                    refine_seen = False
                    first_error: BaseException | None = None
                    for outcome in outcomes:
                        if isinstance(outcome, asyncio.CancelledError):
                            raise outcome
                        if isinstance(outcome, BaseException):
                            if refinement.refine_reason_for_exc(outcome) is not None:
                                refine_seen = True
                            elif first_error is None:
                                first_error = outcome
                    if first_error is not None:
                        raise first_error
                    if refine_seen:
                        break
            else:
                for segment in runnable:
                    await _owned_checkpoint(db, blob, actor, row, run, token)
                    try:
                        await _run_segment(
                            db,
                            blob,
                            chat,
                            actor,
                            workspace_id,
                            run,
                            row,
                            segment,
                            material,
                            runtime,
                            total_active,
                            token,
                        )
                    except AppException as exc:
                        if refinement.refine_reason_for_exc(exc) is not None:
                            break
                        raise
        await _owned_checkpoint(db, blob, actor, row, run, token)
        segments = await _load_segments(db, row_id)
        assessed = await _merged_assessments(db, blob, row, segments, material)
        planner_limited = {
            item["draft_id"]
            for segment in refinement.ordered_leaves(segments)
            for item in segment.scope.get("preassessed_drafts", [])
        }
        built = report_from_assessments(
            assessed, material.payload, row_id, row.bundle_sha256, planner_limited=planner_limited
        )
        await artifacts.store(db, blob, row, "report_json", json_bytes(built))
        await artifacts.store(db, blob, row, "markdown", markdown_for(built))
        row.usage_tokens = refinement.total_usage(segments)
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
                "segments": len(refinement.ordered_leaves(segments)),
                "total_nodes": len(segments),
            },
        )
        await db.commit()
        return ReviewResponse.model_validate(row)
    except asyncio.CancelledError:
        await _mark_uncertain(db, row_id, token)
        failed = await db.get(
            CompilationReview, row_id, populate_existing=True, with_for_update=True
        )
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
        try:
            await _mark_uncertain(db, row_id, token)
        except Exception as recovery_error:
            logger.warning(
                "compilation_review_recovery_write_failed",
                review_id=row_id,
                error_type=type(recovery_error).__name__,
            )
            raise exc from recovery_error
        failed = await db.get(
            CompilationReview, row_id, populate_existing=True, with_for_update=True
        )
        all_segments = await _load_segments(db, row_id)
        terminal = (
            _persisted_review_stop(all_segments) if not isinstance(exc, AppException) else None
        )
        code = (
            exc.code
            if isinstance(exc, AppException)
            else terminal or "compilation_review_internal_error"
        )
        logger.warning(
            "compilation_review_segments_failed",
            review_id=row_id,
            error_type=type(exc).__name__,
            error_code=code,
        )
        # A request having been sent is not by itself uncertainty: a complete answer that
        # broke the contract, a spent budget or a known provider error are all decided
        # outcomes. Only a part whose provider result is truly unknown makes the review so.
        has_uncertain_segment = any(seg.status == "uncertain" for seg in all_segments)
        is_uncertain = (
            has_uncertain_segment
            or (not isinstance(exc, AppException) and terminal is None)
            or "uncertain" in code
            or "interrupted" in code
            or "expired" in code
        )
        if (
            failed is not None
            and failed.status == "running"
            and failed.trace.get("execution_token") == token
        ):
            failed.status = "uncertain" if is_uncertain else "failed"
            failed.error_code = code
            failed.finished_at = utcnow()
            await db.commit()
        if isinstance(exc, AppException) and code.startswith(TERMINAL_CODE_PREFIXES):
            raise
        raise AppException(
            "Review nhiều phần dừng trước khi đủ báo cáo.",
            code=code,
            status_code=409,
        ) from exc


async def _refine_segment(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    row: CompilationReview,
    run: CompilationRun,
    segments: list[CompilationReviewSegment],
    parent: CompilationReviewSegment,
    material,
    limits: refinement.ReviewRefinementLimits,
    token: str,
    reason: str,
) -> list[CompilationReviewSegment]:
    """Replace a failed node by two children over its exact owned scope.

    ``reason`` is the measured failure that justifies narrowing: a cut-off output or a
    complete response that broke the ownership contract. The parent keeps its raw,
    usage and ledger as history; only the children are executed again, and each child
    request is checked against the review-wide budget at the provider boundary.
    """
    await _owned_checkpoint(db, blob, actor, row, run, token)
    active_leaves = len(refinement.ordered_leaves(segments))
    next_index = max((seg.segment_index for seg in segments), default=0) + 1
    targeted = None
    if (
        reason == refinement.CONTRACT_INVALID
        and parent.prompt_version == parts.CONCISE_SEGMENT_PROMPT_VERSION
        and not (parent.config or {}).get("targeted_repair")
    ):
        targeted = await _targeted_plan(db, blob, parent, material, next_index, active_leaves + 1)
        if targeted is not None and targeted.children is None:
            payload = parts.plan_from_scope(parent.scope)
            check = _checked_reuse(material, payload, targeted.accepted)
            parent.config = {
                **parent.config,
                "ignored_context_assessments": targeted.ignored_context,
            }
            await _store_checked_part(db, blob, row, parent, material, check)
            return []
    try:
        refinement.check_limits(row, segments, parent, limits, child_requests=1 if targeted else 2)
        if (
            reason == refinement.CONTRACT_INVALID
            and refinement.contract_recoveries(row) >= limits.max_contract_recoveries
        ):
            raise AppException(
                "Đã dùng hết số lần phục hồi phản hồi sai hợp đồng của review.",
                code="compilation_review_recovery_exhausted",
                status_code=422,
            )
        children_plans = (
            targeted.children
            if targeted
            else refinement.split_segment_plans(
                material.payload,
                parent,
                next_index=next_index,
                total_estimate=active_leaves + 1,
            )
        )
        assert children_plans is not None
    except AppException as exc:
        parent.config = {
            **(parent.config or {}),
            "refinement_exhausted": True,
            "refinement_stop": exc.code,
            "refinement_reason": reason,
        }
        if (
            reason == refinement.CONTRACT_INVALID
            and exc.code in CONTRACT_RECOVERY_STOPS
            and await _retain_unverified_part(db, blob, row, parent, material, active_leaves)
        ):
            return []
        parent.error_code = exc.code
        await db.commit()
        raise
    children = refinement.create_child_segments(
        row,
        parent,
        children_plans,
        request_total=active_leaves + 1,
        split_reason=reason,
    )
    for child in children:
        db.add(child)
    refinement_events = list((row.trace or {}).get("refinement_events") or [])
    refinement_events.append(
        {
            "parent_segment_id": parent.id,
            "parent_segment_index": parent.segment_index,
            "child_segment_ids": [child.id for child in children],
            "child_segment_indices": [child.segment_index for child in children],
            "depth": refinement.segment_depth(parent) + 1,
            "reason": reason,
            "policy": "repair_owned_units/v1" if targeted else "split_owned_scope/v1",
            **({"ignored_context_assessments": targeted.ignored_context} if targeted else {}),
            "parent_input_sha256": parent.input_sha256,
            "diagnosis": ((parent.config or {}).get("last_failure") or {}).get("diagnosis"),
        }
    )
    row.trace = {
        **row.trace,
        "refinement_policy": limits.to_dict(),
        "refinement_events": refinement_events,
    }
    if targeted:
        for child in children:
            child.config = {**child.config, "targeted_repair": True}
        await db.flush()
        reused = children[0]
        reused.config = {**reused.config, "assessment_method": "reused_valid_checks/v1"}
        reused.usage_tokens = 0
        check = _checked_reuse(material, children_plans[0], targeted.accepted)
        await _store_checked_part(db, blob, row, reused, material, check)
    else:
        await db.commit()
    return children


async def _targeted_plan(db, blob, parent, material, next_index: int, total: int):
    if not await artifacts.segment_artifact(db, parent.id, "raw_response"):
        return None
    _, raw = await artifacts.read_segment(db, blob, parent, "raw_response")
    try:
        choice = json.loads(raw)["choices"][0]
        if choice.get("finish_reason") != "stop":
            return None
        content = choice["message"]["content"]
    except (ValueError, KeyError, IndexError, AttributeError, TypeError):
        return None
    plan, _, _ = parts.rebuild_part(material.payload, parent.scope, total=total, structured=True)
    return repair.plan_repair(
        material.payload,
        plan,
        content,
        next_index=next_index,
        total=total,
        reasoning_shares_budget=((parent.config or {}).get("reasoning") or {}).get("level")
        != "off",
    )


def _checked_reuse(material, plan, accepted: ReviewContent) -> ReviewContent:
    payload = parts.payload_for(
        material.payload,
        plan.source_ids,
        plan.draft_ids,
        plan.context_source_ids,
        plan.context_draft_ids,
        projection=plan.projection,
    )
    return validate_content(accepted.model_dump_json(), payload)


async def _part_session(
    blob, chat, actor, workspace_id, run_id, review_id, part_id, material, runtime, total, token
):
    async with AsyncSessionFactory() as db:
        row = await db.get(CompilationReview, review_id)
        run = await db.get(CompilationRun, run_id)
        segment = await db.get(CompilationReviewSegment, part_id)
        await _owned_checkpoint(db, blob, actor, row, run, token)
        if segment.status == "completed":
            return
        await _resume_segment(db, blob, row, segment)
        if segment.status in {"failed", "uncertain"}:
            raise AppException(
                "Một phần review không hoàn tất.",
                code=segment.error_code or "compilation_review_segment_failed",
                status_code=409,
            )
        if segment.status != "completed":
            await _run_segment(
                db,
                blob,
                chat,
                actor,
                workspace_id,
                run,
                row,
                segment,
                material,
                runtime,
                total,
                token,
            )


async def _load_segments(db: AsyncSession, review_id: str) -> list[CompilationReviewSegment]:
    return list(
        (
            await db.scalars(
                select(CompilationReviewSegment)
                .where(CompilationReviewSegment.review_id == review_id)
                .order_by(CompilationReviewSegment.segment_index)
                .execution_options(populate_existing=True)
            )
        ).all()
    )


async def _owned_checkpoint(db, blob, actor, row, run, token):
    with db.no_autoflush:
        await service.checkpoint(db, blob, actor, row, run)
        if row.trace.get("execution_token") != token:
            raise Conflict("Lượt review đã được tiếp quản.", code="compilation_review_claim_lost")
        await require_provider(
            db, row.workspace_id, row.provider_id, row.trace["configuration_hash"]
        )


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
    roots = [segment for segment in segments if segment.parent_segment_id is None]
    if (
        manifest.get("review_id") != row.id
        or manifest.get("bundle_sha256") != row.bundle_sha256
        or len(scopes) != len(roots)
        or [scope.get("index") for scope in scopes] != [segment.segment_index for segment in roots]
        or [
            (
                scope.get("source_ids"),
                scope.get("draft_ids"),
                scope.get("context_source_ids"),
                scope.get("context_draft_ids"),
                scope.get("input_sha256"),
                scope.get("preassessed_drafts", []),
                scope.get("literal_only", False),
                scope.get("source_copy_only", False),
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
                segment.scope.get("preassessed_drafts", []),
                segment.scope.get("literal_only", False),
                segment.scope.get("source_copy_only", False),
            )
            for segment in roots
        ]
    ):
        raise AppException(
            "Manifest review không khớp các phần đã lưu.",
            code="compilation_review_segment_manifest_mismatch",
            status_code=409,
        )
    refinement.verify_parent_child_coverage(segments)


async def _resume_segment(
    db: AsyncSession, blob: BlobStore, row: CompilationReview, segment: CompilationReviewSegment
) -> None:
    if segment.status == "completed":
        return
    if segment.status == "pending" and segment.request_started_at is None:
        # The attempt was recorded but the send was never started: nothing can have been
        # consumed, so the reservation is released instead of counting a phantom request.
        entries = refinement.attempts_of(segment)
        if entries and entries[-1].get("state") == "reserved":
            refinement.settle_attempt(segment, "released")
            if segment.usage_id:
                await usage_service.settle(db, segment.usage_id, total_tokens=0, failed=True)
            await db.commit()
        return
    raw = await artifacts.segment_artifact(db, segment.id, "raw_response")
    if segment.status == "running":
        # A durable assessment means the part finished before its status commit.
        assessed = await artifacts.segment_artifact(db, segment.id, "assessment_json")
        if assessed is not None and segment.usage_tokens is not None:
            refinement.settle_attempt(segment, "settled", usage_tokens=segment.usage_tokens)
            if segment.usage_id:
                await usage_service.settle(db, segment.usage_id, total_tokens=segment.usage_tokens)
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            await db.commit()
            return
        if segment.request_started_at is not None and raw is None:
            refinement.settle_attempt(segment, "unknown")
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
            refinement.settle_attempt(segment, "settled", usage_tokens=segment.usage_tokens)
            if segment.usage_id:
                await usage_service.settle(db, segment.usage_id, total_tokens=segment.usage_tokens)
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            await db.commit()
            return
        refinement.settle_attempt(segment, "unknown")
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
    run: CompilationRun,
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
    if plan.source_copy_only:
        await _owned_checkpoint(db, blob, actor, row, run, token)
        assessment = assess_source_prose(material.payload, plan.payload)
        if assessment is None or segment.request_started_at is not None:
            raise Conflict(
                "Phần văn bản không còn khớp kế hoạch đối chiếu cục bộ.",
                code="compilation_review_segment_mismatch",
            )
        checked = validate_content(json_bytes(assessment).decode(), plan.payload)
        segment.usage_tokens = 0
        segment.config = {**segment.config, "assessment_method": "source_prose/v1"}
        await _store_checked_part(db, blob, row, segment, material, checked)
        return
    preassessed = list((segment.scope or {}).get("preassessed_drafts") or ())
    if preassessed:
        # Server checks are pinned in the root manifest and need no model call.
        await _owned_checkpoint(db, blob, actor, row, run, token)
        checked = validate_content(
            json.dumps(
                {"source_assessments": [], "draft_assessments": preassessed},
                ensure_ascii=False,
            ),
            plan.payload,
        )
        await artifacts.store_segment(
            db, blob, row, segment, "assessment_json", json_bytes(checked.model_dump())
        )
        await artifacts.store_segment(
            db,
            blob,
            row,
            segment,
            "markdown",
            segment_markdown_for(
                row,
                segment,
                checked,
                material.payload,
                parent_index=(segment.scope or {}).get("parent_segment_index"),
            ),
        )
        segment.status, segment.finished_at, segment.usage_tokens = "completed", utcnow(), 0
        if any(item["status"] != "supported" for item in preassessed):
            method = "planner_limit/v1"
        elif any(":paragraph:" in item["draft_id"] for item in preassessed):
            method = "source_structure/v1"
        else:
            method = "source_headings/v1"
        segment.config = {
            **segment.config,
            "assessment_method": method,
            "preassessed": True,
        }
        await db.commit()
        return
    if (plan.literal_only or row.trace.get("literal_check_version") == 1) and (
        segment.request_started_at is None
    ):
        assessment = assess_literal(material.payload, plan.payload)
        if assessment is not None:
            await _owned_checkpoint(db, blob, actor, row, run, token)
            checked = validate_content(json.dumps(assessment, ensure_ascii=False), plan.payload)
            await artifacts.store_segment(
                db, blob, row, segment, "assessment_json", json_bytes(checked.model_dump())
            )
            await artifacts.store_segment(
                db,
                blob,
                row,
                segment,
                "markdown",
                segment_markdown_for(
                    row,
                    segment,
                    checked,
                    material.payload,
                    parent_index=(segment.scope or {}).get("parent_segment_index"),
                ),
            )
            segment.status, segment.finished_at, segment.usage_tokens = "completed", utcnow(), 0
            segment.config = {
                **segment.config,
                "assessment_method": "literal_equality/v1",
                "literal_assessed": True,
            }
            await db.commit()
            return
    if plan.literal_only:
        raise Conflict(
            "Phần đối chiếu cục bộ không còn khớp ô nguồn.",
            code="compilation_review_segment_mismatch",
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
        recorded = "reasoning" in (segment.config or {})
        reasoning = (
            ReasoningDirective.from_public_dict(segment.config.get("reasoning"))
            if recorded
            else None
        )
        current_runtime, request, budget = await prepare_chat_request(
            db,
            actor,
            workspace_id,
            messages,
            provider_id=row.provider_id,
            task="compiler_review",
            max_output_tokens=segment.config["max_output_tokens"],
            output_schema=schema,
            reasoning=reasoning,
        )
        if row.trace.get("automatic_output_budget"):
            request = replace(request, automatic_output_budget=True)
        if current_runtime.configuration_hash != row.trace["configuration_hash"]:
            raise Conflict("Model review đã thay đổi.", code="compilation_review_provider_changed")
        if current_runtime.provider_id != segment.config["provider_id"]:
            raise Conflict(
                "Provider review đã thay đổi.", code="compilation_review_provider_changed"
            )
        if recorded:
            live = current_runtime.reasoning_directive("compiler_review")
            if (live.public_dict() if live is not None else None) != (
                reasoning.public_dict() if reasoning is not None else None
            ):
                raise Conflict(
                    "Chính sách reasoning review đã đổi so với phần đã lập.",
                    code="compilation_review_reasoning_changed",
                )
        # Take the review row lock, then check and record the attempt before anything can
        # be sent: concurrent workers serialize here, so the ceilings cannot be overspent.
        await _owned_checkpoint(db, blob, actor, row, run, token)
        siblings = await _load_segments(db, row.id)
        limits = refinement.limits_for(
            row.trace,
            max(1, sum(1 for seg in siblings if seg.parent_segment_id is None)),
            segments=siblings,
        )
        refinement.reserve_attempt(
            row, siblings, segment, limits, estimate_tokens=budget.total_reserved_tokens
        )
        usage = await usage_service.reserve(
            db,
            actor,
            workspace_id,
            "chat",
            f"compiler-review:{row.id}:segment:{segment.segment_index}:{segment.attempt_count + 1}",
            segment.request_hash,
            budget.total_reserved_tokens,
            runtime.provider_id,
        )
        # Reserving usage commits the transaction and releases the review lock.
        await db.refresh(row, with_for_update=True)
        segment.usage_id = usage.id
        if row.status == "cancelled":
            refinement.settle_attempt(segment, "released")
            await usage_service.settle(db, usage.id, total_tokens=0, failed=True)
            await db.commit()
            return
        segment.status, segment.worker_id = "running", row.created_by
        segment.attempt_count += 1
        segment.request_started_at = utcnow()
        await db.commit()
        try:
            result = await _complete_until_stopped(
                chat, messages, bind_usage(request, usage.id), row.id
            )
        except ChatResponseError as exc:
            # A response arrived: its usage is whatever the provider reported, else unknown.
            refinement.settle_attempt(
                segment,
                "settled" if exc.usage_tokens is not None else "usage_unknown",
                usage_tokens=exc.usage_tokens,
            )
            if exc.raw_body:
                await artifacts.store_segment(db, blob, row, segment, "raw_response", exc.raw_body)
            segment.usage_tokens = exc.usage_tokens
            await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
            await _fail_segment(db, segment, exc.code)
            await _owned_checkpoint(db, blob, actor, row, run, token)
            raise
        except (Exception, asyncio.CancelledError) as exc:
            # Possibly sent, outcome unknown: it keeps counting at its reserved bound.
            refinement.settle_attempt(segment, "unknown")
            await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
            if isinstance(exc, AppException) and "uncertain" in exc.code:
                segment.status = "uncertain"
                segment.error_code = exc.code
                segment.finished_at = utcnow()
            await db.commit()
            raise
        await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
        segment.usage_tokens = result.total_tokens
        refinement.settle_attempt(
            segment,
            "settled" if result.total_tokens is not None else "usage_unknown",
            usage_tokens=result.total_tokens,
        )
        if result.raw_body:
            await artifacts.store_segment(db, blob, row, segment, "raw_response", result.raw_body)
        segment.status = "received"
        await db.commit()
        await _owned_checkpoint(db, blob, actor, row, run, token)
        content = result.content
    await _owned_checkpoint(db, blob, actor, row, run, token)
    # Decode and validation share one boundary: any complete-but-wrong response is the
    # same decided outcome (raw and usage kept, node failed), never "received forever".
    original = content
    try:
        if structured:
            content = decode_keyed(content, plan.payload)
        checked = validate_content(content, plan.payload, unverified="uncited")
    except AppException as exc:
        if exc.code != refinement.CONTRACT_INVALID:
            raise
        segment.config = {
            **(segment.config or {}),
            "last_failure": {
                "code": exc.code,
                "attempt": int(segment.attempt_count or 0),
                "source": "raw_replay" if raw is not None else "provider_response",
                "diagnosis": diagnose_contract(original, plan.payload),
            },
        }
        await _fail_segment(db, segment, refinement.CONTRACT_INVALID)
        raise
    await _store_checked_part(db, blob, row, segment, material, checked)


async def _retain_unverified_part(db, blob, row, segment, material, total: int) -> bool:
    raw = await artifacts.segment_artifact(db, segment.id, "raw_response")
    if raw is None:
        return False
    _, payload = await artifacts.read_segment(db, blob, segment, "raw_response")
    structured = bool(row.trace.get("structured_output"))
    plan, _, _ = parts.rebuild_part(
        material.payload, segment.scope, total=total, structured=structured
    )
    try:
        choice = json.loads(payload)["choices"][0]
        if choice.get("finish_reason") != "stop":
            return False
        content = choice["message"]["content"]
        if structured:
            content = decode_keyed(content, plan.payload)
        checked = validate_content(content, plan.payload, unverified="exhausted")
    except (AppException, ValueError, AttributeError, KeyError, IndexError, TypeError):
        return False
    segment.config = {**segment.config, "assessment_method": "unverified_after_refinement/v1"}
    await _store_checked_part(db, blob, row, segment, material, checked)
    return True


async def _store_checked_part(db, blob, row, segment, material, checked: ReviewContent) -> None:
    await artifacts.store_segment(
        db, blob, row, segment, "assessment_json", json_bytes(checked.model_dump(mode="json"))
    )
    await artifacts.store_segment(
        db,
        blob,
        row,
        segment,
        "markdown",
        segment_markdown_for(
            row,
            segment,
            checked,
            material.payload,
            parent_index=(segment.scope or {}).get("parent_segment_index"),
        ),
    )
    segment.status, segment.error_code = "completed", None
    segment.finished_at = utcnow()
    await db.commit()


async def _fail_segment(db: AsyncSession, segment: CompilationReviewSegment, code: str) -> None:
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
            refinement.settle_attempt(
                segment,
                "settled" if segment.usage_tokens is not None else "usage_unknown",
                usage_tokens=segment.usage_tokens,
            )
            segment.status = "received"
            segment.worker_id = None
            changed = True
            continue
        refinement.settle_attempt(segment, "unknown")
        segment.status = "uncertain"
        segment.error_code = "compilation_review_request_interrupted"
        segment.finished_at = utcnow()
        changed = True
    if changed:
        await db.commit()


async def _anything_sent(db: AsyncSession, review_id: str) -> bool:
    """Did any part reach the provider? Only then is the review's outcome unknown."""
    return not await service.untouched(db, review_id)


async def _merged_assessments(
    db: AsyncSession,
    blob: BlobStore,
    row: CompilationReview,
    segments: list[CompilationReviewSegment],
    material,
) -> "ReviewContent":
    refinement.verify_parent_child_coverage(segments)
    leaves = refinement.ordered_leaves(segments)
    if not leaves or any(leaf.status != "completed" for leaf in leaves):
        raise AppException(
            "Còn phần review chưa hoàn tất; không thể hợp nhất báo cáo.",
            code="compilation_review_segment_incomplete",
            status_code=409,
        )
    source_assessments_list: list[dict] = []
    draft_assessments_list: list[dict] = []
    by_source_id: dict[str, dict] = {}
    by_draft_id: dict[str, dict] = {}
    for segment in leaves:
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
        if await artifacts.segment_artifact(db, segment.id, "markdown") is None:
            await artifacts.store_segment(
                db,
                blob,
                row,
                segment,
                "markdown",
                segment_markdown_for(
                    row,
                    segment,
                    value,
                    material.payload,
                    parent_index=(segment.scope or {}).get("parent_segment_index"),
                ),
            )
        for s_item in value.source_assessments:
            dumped = s_item.model_dump()
            source_assessments_list.append(dumped)
            by_source_id[s_item.source_id] = dumped
        for d_item in value.draft_assessments:
            dumped = d_item.model_dump()
            draft_assessments_list.append(dumped)
            by_draft_id[d_item.draft_id] = dumped
    source_ids = [unit["id"] for unit in material.payload["source_units"]]
    draft_ids = [unit["id"] for unit in material.payload["draft_units"]]
    if Counter(a["source_id"] for a in source_assessments_list) != Counter(source_ids):
        raise AppException(
            "Báo cáo review ghép không phủ đủ nguồn.",
            code="compilation_review_coverage_invalid",
            status_code=409,
        )
    if Counter(a["draft_id"] for a in draft_assessments_list) != Counter(draft_ids):
        raise AppException(
            "Báo cáo review ghép không phủ đủ bản nháp.",
            code="compilation_review_coverage_invalid",
            status_code=409,
        )
    parent_ids = refinement.parent_ids_for(segments)
    for parent in sorted(
        (seg for seg in segments if seg.id in parent_ids),
        key=lambda item: refinement.segment_depth(item),
        reverse=True,
    ):
        p_plan = parts.plan_from_scope(parent.scope)
        p_payload = parts.payload_for(
            material.payload,
            p_plan.source_ids,
            p_plan.draft_ids,
            p_plan.context_source_ids,
            p_plan.context_draft_ids,
        )
        p_assembled = {
            "source_assessments": [by_source_id[key] for key in p_plan.source_ids],
            "draft_assessments": [by_draft_id[key] for key in p_plan.draft_ids],
        }
        p_checked = validate_content(
            json.dumps(p_assembled, ensure_ascii=False),
            p_payload,
        )
        await artifacts.store_segment(
            db, blob, row, parent, "assessment_json", json_bytes(p_checked.model_dump())
        )
        await artifacts.store_segment(
            db,
            blob,
            row,
            parent,
            "markdown",
            segment_markdown_for(
                row,
                parent,
                p_checked,
                material.payload,
                parent_index=(parent.scope or {}).get("parent_segment_index"),
                child_indices=[
                    child.segment_index
                    for child in segments
                    if child.parent_segment_id == parent.id
                ],
            ),
        )
        parent.status = "completed"
        parent.error_code = None
        parent.finished_at = parent.finished_at or utcnow()
    ordered_assembled = {
        "source_assessments": [by_source_id[key] for key in source_ids],
        "draft_assessments": [by_draft_id[key] for key in draft_ids],
    }
    return ReviewContent.model_validate(ordered_assembled)


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
