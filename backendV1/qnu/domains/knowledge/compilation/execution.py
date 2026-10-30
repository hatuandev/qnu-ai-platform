"""Execute one durable compilation: reauthorize, call once, retain raw, validate draft."""

from __future__ import annotations

import asyncio
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation.artifacts import (
    artifact,
    json_bytes,
    read,
    read_segment,
    segment_artifact,
    store,
    store_segment,
)
from qnu.domains.knowledge.compilation.drafting import (
    SYSTEM_PROMPT,
    build_draft,
    markdown_for,
    messages_for,
    output_schema,
)
from qnu.domains.knowledge.compilation.evidence import load_bound_documents
from qnu.domains.knowledge.compilation.lease import (
    ClaimLost,
    assert_claim,
    claim,
    commit_owned,
    heartbeat,
)
from qnu.domains.knowledge.compilation.models import (
    CompilationInput,
    CompilationRun,
    CompilationSegment,
    utcnow,
)
from qnu.domains.knowledge.compilation import outputs as compilation_outputs
from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation.service import authorize_collection
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.usage.service import usage_service
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel, ChatResponseError
from qnu.ports.provider_execution import bind_usage

logger = get_logger(__name__)


async def finish(
    db: AsyncSession, run: CompilationRun, status: str, code: str | None = None
) -> str:
    await assert_claim(db, run)
    if status == "completed":
        from qnu.domains.knowledge.compilation.workflow.automatic import schedule

        await schedule(db, run)
    run.status, run.error_code, run.finished_at = status, code, utcnow()
    run.lease_expires_at = None
    await commit_owned(db, run)
    logger.info(
        "compilation_finished",
        run_id=run.id,
        workspace_id=run.workspace_id,
        provider_id=run.provider_id,
        status=status,
        error_code=code,
        usage_tokens=run.usage_tokens,
    )
    return status


async def _inputs(db: AsyncSession, blob: BlobStore, run: CompilationRun) -> list[dict]:
    bindings = list(
        (
            await db.scalars(
                select(CompilationInput).where(
                    CompilationInput.run_id == run.id,
                )
            )
        ).all()
    )
    documents = await load_bound_documents(
        db,
        blob,
        run.workspace_id,
        run.collection_id,
        bindings,
    )
    _, original = await read(db, blob, run, "input_snapshot")
    snapshot = {
        "schema_version": "qnu.compiler.input/v1",
        "topic": run.topic,
        "documents": documents,
    }
    if (
        hashlib.sha256(original).hexdigest() != run.input_sha256
        or json_bytes(snapshot) != original
        or any(
            (b.canonical_sha256, b.manifest_sha256)
            != (
                next(d for d in documents if d["ocr_run_id"] == b.ocr_run_id)["canonical_sha256"],
                next(d for d in documents if d["ocr_run_id"] == b.ocr_run_id)["manifest_sha256"],
            )
            for b in bindings
        )
    ):
        raise Conflict("Nguồn đã khác snapshot Compiler.", code="compilation_source_mismatch")
    return documents


async def _settle(
    db: AsyncSession, run: CompilationRun, tokens: int | None, *, failed: bool = False
) -> None:
    if run.usage_id is not None:
        await usage_service.settle(db, run.usage_id, total_tokens=tokens, failed=failed)


async def _compile(db: AsyncSession, blob: BlobStore, run: CompilationRun, model: ChatModel) -> str:
    actor = background_actor(run.requested_by)
    await authorize_collection(db, actor, run.workspace_id, run.collection_id, write=True)
    documents = await _inputs(db, blob, run)
    if run.config.get("workflow_version") == "qnu.compiler.workflow/v2":
        return await _compile_segmented(db, blob, run, documents, model)
    existing_raw = await artifact(db, run.id, "raw_response")
    if run.request_started_at is not None and existing_raw is None:
        await _settle(db, run, None, failed=True)
        return await finish(db, run, "uncertain", "compilation_request_interrupted")
    if run.attempt_count > 3:
        return await finish(db, run, "failed", "compilation_attempts_exhausted")
    if existing_raw is not None:
        _, payload = await read(db, blob, run, "raw_response")
        try:
            content = json.loads(payload)["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AppException("Raw chat không đọc được.", code="compilation_raw_invalid") from exc
        await _settle(db, run, run.usage_tokens)
    else:
        content = await _call(db, blob, run, actor, documents, model)
    draft = build_draft(content, run.topic, documents, run.id)
    await assert_claim(db, run)
    await store(db, blob, run, "draft_json", json_bytes(draft))
    await store(db, blob, run, "markdown", markdown_for(draft).encode("utf-8"))
    await commit_owned(db, run)
    return await finish(db, run, "completed")


async def _call(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    actor: AuthActor,
    documents: list[dict],
    model: ChatModel,
) -> str:
    messages = messages_for(run.topic, documents)
    schema = output_schema(documents) if run.config.get("structured_output") else None
    runtime, request, budget = await prepare_chat_request(
        db,
        actor,
        run.workspace_id,
        messages,
        provider_id=run.provider_id,
        max_output_tokens=run.config["max_output_tokens"],
        output_schema=schema,
    )
    if (
        runtime.configuration_hash != run.config["provider"]["configuration_hash"]
        or hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest() != run.config["prompt_sha256"]
        or (
            schema is not None
            and hashlib.sha256(json_bytes(schema)).hexdigest()
            != run.config.get("output_schema_sha256")
        )
    ):
        raise Conflict(
            "Model hoặc prompt đã đổi so với yêu cầu.", code="compilation_provider_changed"
        )
    await assert_claim(db, run)
    usage = await usage_service.reserve(
        db,
        actor,
        run.workspace_id,
        "chat",
        f"compile:{run.id}",
        run.request_hash,
        budget.total_reserved_tokens,
        run.provider_id,
    )
    await assert_claim(db, run)
    run.usage_id, run.request_started_at = usage.id, utcnow()
    await commit_owned(db, run)
    try:
        result = await model.complete(messages, bind_usage(request, usage.id))
    except ChatResponseError as exc:
        try:
            await assert_claim(db, run)
        except ClaimLost:
            await _settle(db, run, exc.usage_tokens, failed=True)
            raise
        await store(db, blob, run, "raw_response", exc.raw_body)
        run.usage_tokens = exc.usage_tokens
        # The raw reply may be diagnostic but must never later become a draft.
        run.config = {**run.config, "response_error_code": exc.code}
        await commit_owned(db, run)
        await _settle(db, run, exc.usage_tokens, failed=True)
        raise
    except AppException:
        await _settle(db, run, None, failed=True)
        raise
    try:
        await assert_claim(db, run)
    except ClaimLost:
        await _settle(db, run, result.total_tokens, failed=True)
        raise
    await store(db, blob, run, "raw_response", result.raw_body)
    run.usage_tokens = result.total_tokens
    await commit_owned(db, run)
    await _settle(db, run, result.total_tokens)
    return result.content


async def _segments(db: AsyncSession, run_id: str) -> list[CompilationSegment]:
    return list(
        (
            await db.scalars(
                select(CompilationSegment)
                .where(CompilationSegment.run_id == run_id)
                .order_by(CompilationSegment.segment_index)
            )
        ).all()
    )


def _scope_key(scope: dict) -> tuple:
    return (
        scope.get("index"),
        json.dumps(scope.get("owned"), sort_keys=True),
        json.dumps(scope.get("context"), sort_keys=True),
        scope.get("input_sha256"),
        scope.get("schema_sha256"),
    )


async def _verify_manifest(
    db: AsyncSession, blob: BlobStore, run: CompilationRun, segments: list[CompilationSegment]
) -> None:
    expected = (run.config.get("segmentation") or {}).get("manifest_sha256")
    artifact_row, payload = await read(db, blob, run, "segment_manifest")
    if expected != artifact_row.sha256:
        raise Conflict(
            "Manifest Compiler không khớp yêu cầu.",
            code="compilation_segment_manifest_mismatch",
        )
    try:
        manifest = json.loads(payload)
    except ValueError as exc:
        raise Conflict(
            "Manifest Compiler không đọc được.",
            code="compilation_segment_manifest_mismatch",
        ) from exc
    if (
        manifest.get("run_id") != run.id
        or manifest.get("input_sha256") != run.input_sha256
        or [_scope_key(scope) for scope in manifest.get("segments") or []]
        != [_scope_key(segment.scope) for segment in segments]
    ):
        raise Conflict(
            "Manifest Compiler không khớp các phần đã lưu.",
            code="compilation_segment_manifest_mismatch",
        )


async def _resume_segment(
    db: AsyncSession, blob: BlobStore, run: CompilationRun, segment: CompilationSegment
) -> None:
    if segment.status == "completed":
        return
    raw = await segment_artifact(db, segment.id, "raw_response")
    if segment.status == "running":
        # The part artifact may have been written before an interrupted status
        # commit; a validated part is complete even when its raw body is gone.
        draft = await segment_artifact(db, segment.id, "draft_json")
        if draft is not None and segment.usage_tokens is not None:
            if segment.usage_id:
                await usage_service.settle(
                    db, segment.usage_id, total_tokens=segment.usage_tokens
                )
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            await commit_owned(db, run)
            return
        if segment.request_started_at is not None and raw is None:
            if segment.usage_id:
                await usage_service.settle(
                    db, segment.usage_id, total_tokens=None, failed=True
                )
            segment.status = "uncertain"
            segment.error_code = "compilation_request_interrupted"
            segment.finished_at = utcnow()
            await commit_owned(db, run)
            return
        segment.status = "pending" if raw is None else "received"
        segment.worker_id = None
        await commit_owned(db, run)
    if segment.status == "received" and raw is None:
        draft = await segment_artifact(db, segment.id, "draft_json")
        if draft is not None and segment.usage_tokens is not None:
            if segment.usage_id:
                await usage_service.settle(
                    db, segment.usage_id, total_tokens=segment.usage_tokens
                )
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            await commit_owned(db, run)
            return
        # A response marked received cannot be resent safely without its raw body
        # or an already validated part artifact.
        if segment.usage_id:
            await usage_service.settle(db, segment.usage_id, total_tokens=None, failed=True)
        segment.status = "uncertain"
        segment.error_code = "compilation_segment_raw_missing"
        segment.finished_at = utcnow()
        await commit_owned(db, run)


async def _run_segment(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    segment: CompilationSegment,
    documents: list[dict],
    model: ChatModel,
    actor: AuthActor,
    total: int,
) -> None:
    if segment.status == "completed":
        return
    plan = split.plan_from_scope(segment.scope)
    payload, citations = split.build_projection(
        run.topic, documents, plan.owned, plan.context, segment.segment_index
    )
    messages = split.segment_messages(payload, segment.segment_index, total)
    structured = bool(segment.config.get("structured_output"))
    schema = split.segment_schema(citations) if structured else None
    if (
        hashlib.sha256(messages[-1].content.encode("utf-8")).hexdigest()
        != segment.input_sha256
        or segment.prompt_version != split.PROMPT_VERSION
        or (
            schema is not None
            and hashlib.sha256(json_bytes(schema)).hexdigest() != segment.schema_sha256
        )
    ):
        raise Conflict(
            "Phần biên soạn không còn khớp kế hoạch đã lưu.",
            code="compilation_segment_mismatch",
        )
    raw = await segment_artifact(db, segment.id, "raw_response")
    if raw is not None:
        _, raw_payload = await read_segment(db, blob, segment, "raw_response")
        try:
            content = json.loads(raw_payload)["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AppException(
                "Raw phần biên soạn không đọc được.", code="compilation_raw_invalid"
            ) from exc
        if segment.usage_id is not None:
            if segment.usage_tokens is None:
                raise Conflict(
                    "Phần biên soạn đã nhận phản hồi nhưng thiếu usage.",
                    code="compilation_segment_usage_unknown",
                )
            await usage_service.settle(
                db, segment.usage_id, total_tokens=segment.usage_tokens
            )
    else:
        if segment.attempt_count >= 3:
            raise AppException(
                "Phần biên soạn đã hết số lần thử.",
                code="compilation_segment_attempts_exhausted",
            )
        runtime, request, budget = await prepare_chat_request(
            db,
            actor,
            run.workspace_id,
            messages,
            provider_id=run.provider_id,
            task="compiler",
            max_output_tokens=segment.config["max_output_tokens"],
            output_schema=schema,
        )
        if (
            runtime.configuration_hash != run.config["provider"]["configuration_hash"]
            or runtime.provider_id != segment.config["provider_id"]
        ):
            raise Conflict(
                "Model hoặc prompt đã đổi so với yêu cầu.",
                code="compilation_provider_changed",
            )
        usage = await usage_service.reserve(
            db,
            actor,
            run.workspace_id,
            "chat",
            f"compile:{run.id}:segment:{segment.segment_index}:{segment.attempt_count + 1}",
            segment.request_hash,
            budget.total_reserved_tokens,
            run.provider_id,
        )
        segment.usage_id = usage.id
        segment.status = "running"
        segment.worker_id = run.worker_id
        segment.attempt_count += 1
        segment.started_at = segment.started_at or utcnow()
        segment.request_started_at = utcnow()
        await commit_owned(db, run)
        try:
            result = await model.complete(messages, bind_usage(request, usage.id))
        except ChatResponseError as exc:
            if exc.raw_body:
                await store_segment(db, blob, run, segment, "raw_response", exc.raw_body)
            segment.usage_tokens = exc.usage_tokens
            await usage_service.settle(
                db, usage.id, total_tokens=exc.usage_tokens, failed=True
            )
            segment.status = "failed"
            segment.error_code = exc.code
            segment.finished_at = utcnow()
            await commit_owned(db, run)
            raise
        except (Exception, asyncio.CancelledError):
            await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
            raise
        try:
            await assert_claim(db, run)
        except ClaimLost:
            await usage_service.settle(db, usage.id, total_tokens=result.total_tokens, failed=True)
            raise
        if result.raw_body:
            await store_segment(db, blob, run, segment, "raw_response", result.raw_body)
        segment.usage_tokens = result.total_tokens
        segment.status = "received"
        await commit_owned(db, run)
        await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
        content = result.content
    draft = split.parse_segment_draft(content, set(citations))
    await store_segment(
        db, blob, run, segment, "draft_json", json_bytes(draft)
    )
    segment.status, segment.error_code = "completed", None
    segment.finished_at = utcnow()
    await commit_owned(db, run)
    completed = await _segments(db, run.id)
    parts = await _completed_parts(db, blob, completed)
    coverage = _coverage(completed)
    merged = split.merge_drafts(
        parts,
        run.topic,
        documents,
        run.id,
        partial=True,
        segmentation=coverage,
    )
    await compilation_outputs.store_output(
        db,
        blob,
        run,
        draft_payload=json_bytes(merged),
        markdown_payload=split.partial_markdown(merged),
        coverage=coverage,
        partial=True,
    )
    await commit_owned(db, run)


async def _completed_parts(
    db: AsyncSession, blob: BlobStore, segments: list[CompilationSegment]
) -> list[dict]:
    parts = []
    for segment in segments:
        if segment.status != "completed":
            continue
        _, payload = await read_segment(db, blob, segment, "draft_json")
        parts.append(json.loads(payload))
    return parts


def _coverage(segments: list[CompilationSegment]) -> dict:
    counts: dict[str, int] = {}
    for segment in segments:
        counts[segment.status] = counts.get(segment.status, 0) + 1
    completed = counts.get("completed", 0)
    return {
        "state": "completed" if completed == len(segments) else "partial",
        "segments_total": len(segments),
        "segments_completed": completed,
        "segments_pending": counts.get("pending", 0),
        "segments_running": counts.get("running", 0),
        "segments_failed": counts.get("failed", 0),
        "segments_uncertain": counts.get("uncertain", 0),
        "segments": [
            {"index": segment.segment_index, "status": segment.status}
            for segment in segments
        ],
    }


async def _store_generation(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    draft: dict,
    coverage: dict,
    *,
    partial: bool,
) -> None:
    draft_payload = json_bytes(draft)
    markdown_payload = (
        split.partial_markdown(draft) if partial else markdown_for(draft).encode("utf-8")
    )
    if not partial:
        # Old readers and publication continue to use the original artifact kinds.
        await store(db, blob, run, "draft_json", draft_payload)
        await store(db, blob, run, "markdown", markdown_payload)
        await read(db, blob, run, "draft_json")
        await read(db, blob, run, "markdown")
    await compilation_outputs.store_output(
        db,
        blob,
        run,
        draft_payload=draft_payload,
        markdown_payload=markdown_payload,
        coverage=coverage,
        partial=partial,
    )


async def _compile_segmented(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    documents: list[dict],
    model: ChatModel,
) -> str:
    actor = background_actor(run.requested_by)
    segments = await _segments(db, run.id)
    if not segments:
        return await finish(db, run, "failed", "compilation_segment_manifest_mismatch")
    await _verify_manifest(db, blob, run, segments)
    for segment in segments:
        if segment.status == "completed":
            continue
        await _resume_segment(db, blob, run, segment)
        if segment.status in {"failed", "uncertain"}:
            return await finish(
                db,
                run,
                "uncertain" if segment.status == "uncertain" else "failed",
                segment.error_code,
            )
        await _run_segment(db, blob, run, segment, documents, model, actor, len(segments))
    segments = await _segments(db, run.id)
    coverage = _coverage(segments)
    if coverage["state"] != "completed":
        return await finish(db, run, "failed", "compilation_segments_incomplete")
    parts = await _completed_parts(db, blob, segments)
    draft = split.merge_drafts(
        parts,
        run.topic,
        documents,
        run.id,
        partial=False,
        segmentation=coverage,
    )
    await assert_claim(db, run)
    await _store_generation(db, blob, run, draft, coverage, partial=False)
    tokens = [segment.usage_tokens for segment in segments if segment.usage_tokens]
    run.usage_tokens = sum(tokens) if tokens else None
    await commit_owned(db, run)
    return await finish(db, run, "completed")


async def _uncertain_segment(db: AsyncSession, run_id: str) -> bool:
    segments = await _segments(db, run_id)
    for segment in segments:
        if segment.status == "running" and segment.request_started_at is not None:
            if await segment_artifact(db, segment.id, "raw_response") is None:
                return True
    return False


async def _mark_uncertain_segments(db: AsyncSession, run: CompilationRun) -> None:
    for segment in await _segments(db, run.id):
        if segment.status != "running" or segment.request_started_at is None:
            continue
        draft = await segment_artifact(db, segment.id, "draft_json")
        if draft is not None:
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            continue
        raw = await segment_artifact(db, segment.id, "raw_response")
        if raw is not None:
            segment.status = "received"
            segment.worker_id = None
            continue
        if segment.usage_id:
            await usage_service.settle(
                db, segment.usage_id, total_tokens=None, failed=True
            )
        segment.status = "uncertain"
        segment.error_code = "compilation_request_interrupted"
        segment.finished_at = utcnow()


async def execute_run(
    db: AsyncSession,
    blob: BlobStore,
    run_id: str,
    *,
    worker_id: str,
    model: ChatModel,
) -> str:
    seconds = get_settings().COMPILER_LEASE_SECONDS
    run = await claim(db, run_id, worker_id, seconds)
    if run is None:
        return "not_claimed"
    token = run.worker_id
    async with heartbeat(run, seconds):
        try:
            if run.config.get("response_error_code"):
                return await finish(db, run, "failed", run.config["response_error_code"])
            return await _compile(db, blob, run, model)
        except ClaimLost:
            await db.rollback()
            return "not_claimed"
        except asyncio.CancelledError:
            # Persisted in-flight marker is reconciled to uncertain; never resend.
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            run = await db.get(CompilationRun, run_id, populate_existing=True)
            if run is None or run.worker_id != token:
                return "not_claimed"
            code = exc.code if isinstance(exc, AppException) else "compilation_failed"
            try:
                if run.config.get("workflow_version") == "qnu.compiler.workflow/v2":
                    uncertain = code == "chat_provider_uncertain" or await _uncertain_segment(
                        db, run.id
                    )
                    if uncertain:
                        await _mark_uncertain_segments(db, run)
                    return await finish(
                        db, run, "uncertain" if uncertain else "failed", code
                    )
                raw = await artifact(db, run.id, "raw_response")
                uncertain = code == "chat_provider_uncertain" or (
                    run.request_started_at is not None
                    and raw is None
                    and code not in {"chat_provider_unreachable"}
                )
                return await finish(db, run, "uncertain" if uncertain else "failed", code)
            except ClaimLost:
                await db.rollback()
                return "not_claimed"
