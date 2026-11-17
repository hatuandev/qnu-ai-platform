"""Execute one durable compilation: reauthorize, call once, retain raw, validate draft.

Independent parts may overlap up to ``COMPILER_SEGMENT_CONCURRENCY``. Each task owns
its own session and lease check; only this coroutine writes output generations, so
two parts can never interleave a draft/Markdown pair. Parts are merged in source
order, never in completion order.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation import outputs as compilation_outputs
from qnu.domains.knowledge.compilation import refinement, supplement
from qnu.domains.knowledge.compilation import segments as split
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
from qnu.domains.knowledge.compilation.quality import (
    CONFIRMED_BY_SOURCE,
    NO_ERROR_FOUND,
    PARTIALLY_CHECKED,
    quality_validation,
)
from qnu.domains.knowledge.compilation.scheduler import effective_concurrency, run_bounded
from qnu.domains.knowledge.compilation.service import authorize_collection
from qnu.domains.knowledge.compilation.source_first import build_source_draft
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.models import ModelUsageRecord
from qnu.domains.modelops.reasoning import ReasoningDirective
from qnu.domains.modelops.usage.service import usage_service
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel, ChatResponseError
from qnu.ports.provider_execution import bind_usage

logger = get_logger(__name__)
PARTIAL_OUTPUT_INTERVAL_SECONDS = 30


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
    if run.source_first:
        draft = await asyncio.to_thread(build_source_draft, run.topic, documents, run.id)
        draft = await asyncio.to_thread(
            supplement.attach, draft, documents, [], run.input_sha256, {}
        )
        if run.selective_supplement:
            error_code = run.config.get("supplement_plan_error")
            draft["supplement"]["state"] = "incomplete" if error_code else "skipped"
            if error_code:
                draft["supplement"]["planning_error"] = error_code
        await _store_final_draft(db, blob, run, draft)
        return await finish(db, run, "completed")
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
    await _store_final_draft(db, blob, run, draft)
    return await finish(db, run, "completed")


async def _store_final_draft(
    db: AsyncSession, blob: BlobStore, run: CompilationRun, draft: dict
) -> None:
    await assert_claim(db, run)
    await store(db, blob, run, "draft_json", json_bytes(draft))
    await store(db, blob, run, "markdown", markdown_for(draft).encode("utf-8"))
    await commit_owned(db, run)


def _stored_reasoning(segment: CompilationSegment) -> tuple[bool, ReasoningDirective | None]:
    """Return (recorded, directive). A legacy part recorded nothing and keeps the default."""
    if "reasoning" not in (segment.config or {}):
        return False, None
    return True, ReasoningDirective.from_public_dict(segment.config.get("reasoning"))


async def _settle_part_usage(usage_id: str, tokens: int | None, *, failed: bool) -> None:
    """Accounting may outlive the claim; never commit it with stale part objects."""
    async with AsyncSessionFactory() as accounting:
        try:
            await usage_service.settle(accounting, usage_id, total_tokens=tokens, failed=failed)
        except Conflict as exc:
            await accounting.rollback()
            if tokens is None and exc.code == "usage_already_settled":
                known = await accounting.get(ModelUsageRecord, usage_id)
                if known is not None and known.status in {"completed", "failed"}:
                    # Recovery cannot replace an observed result with unknown usage.
                    return
            raise


async def _record_segment_error(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    segment: CompilationSegment,
    usage_id: str,
    exc: ChatResponseError,
) -> None:
    await _settle_part_usage(usage_id, exc.usage_tokens, failed=True)
    await assert_claim(db, run)
    if exc.raw_body:
        await store_segment(db, blob, run, segment, "raw_response", exc.raw_body)
    segment.usage_tokens = exc.usage_tokens
    segment.status = "uncertain" if exc.code == "chat_provider_uncertain" else "failed"
    segment.error_code = exc.code
    segment.finished_at = utcnow()
    await commit_owned(db, run)


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
    recorded = "reasoning_directive" in run.config
    reasoning = ReasoningDirective.from_public_dict(run.config.get("reasoning_directive"))
    runtime, request, budget = await prepare_chat_request(
        db,
        actor,
        run.workspace_id,
        messages,
        provider_id=run.provider_id,
        max_output_tokens=run.config["max_output_tokens"],
        output_schema=schema,
        task="compiler",
        reasoning=reasoning,
    )
    if run.config.get("automatic_output_budget"):
        request = replace(request, automatic_output_budget=True)
    if recorded:
        live = runtime.reasoning_directive("compiler")
        if (live.public_dict() if live else None) != run.config["reasoning_directive"]:
            raise Conflict("Chính sách reasoning đã đổi.", code="compilation_reasoning_changed")
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
                .where(CompilationSegment.parent_segment_id.is_(None))
                .order_by(CompilationSegment.segment_index)
                .execution_options(populate_existing=True)
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
        # Missing on legacy v2 scopes on both sides, so the comparison stays exact.
        scope.get("projection_version"),
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
    if await refinement.children(db, run, segment):
        return  # This parent performs no more inference; resume its durable children.
    if (
        segment.status == "failed"
        and segment.error_code == "chat_output_truncated"
        and run.config.get("refinement")
    ):
        # A process can die after committing diagnostic raw but before planning
        # children. Recovery plans from those bytes, never resends this request.
        saved = await segment_artifact(db, segment.id, "raw_response")
        if saved is not None:
            _, raw_body = await read_segment(db, blob, segment, "raw_response")
            await refinement.create_children(
                db, run, segment, documents=await _inputs(db, blob, run), raw=raw_body
            )
        return
    raw = await segment_artifact(db, segment.id, "raw_response")
    if segment.status == "running":
        # The part artifact may have been written before an interrupted status
        # commit; a validated part is complete even when its raw body is gone.
        draft = await segment_artifact(db, segment.id, "draft_json")
        if draft is not None and segment.usage_tokens is not None:
            if segment.usage_id:
                await _settle_part_usage(segment.usage_id, segment.usage_tokens, failed=False)
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            await commit_owned(db, run)
            return
        if segment.request_started_at is not None and raw is None:
            if segment.usage_id:
                await _settle_part_usage(segment.usage_id, None, failed=True)
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
                await _settle_part_usage(segment.usage_id, segment.usage_tokens, failed=False)
            segment.status, segment.error_code = "completed", None
            segment.finished_at = utcnow()
            await commit_owned(db, run)
            return
        # A response marked received cannot be resent safely without its raw body
        # or an already validated part artifact.
        if segment.usage_id:
            await _settle_part_usage(segment.usage_id, None, failed=True)
        segment.status = "uncertain"
        segment.error_code = "compilation_segment_raw_missing"
        segment.finished_at = utcnow()
        await commit_owned(db, run)


async def _run_segment(
    db,
    blob,
    run,
    segment,
    documents,
    model,
    actor,
    total,
) -> None:
    if segment.status == "completed":
        return
    parts = await refinement.children(db, run, segment)
    if not parts:
        try:
            await _run_leaf(db, blob, run, segment, documents, model, actor, total)
            return
        except ChatResponseError as exc:
            if exc.code != "chat_output_truncated":
                raise
            parts = await refinement.create_children(db, run, segment, documents, exc.raw_body)
            if not parts:
                raise
    drafts = []
    for child in parts:
        await _resume_segment(db, blob, run, child)
        if child.status in {"failed", "uncertain"}:
            raise AppException(
                "Phần con chưa có kết quả hợp lệ.",
                code=child.error_code or "compilation_child_incomplete",
            )
        await _run_segment(
            db, blob, run, child, documents, model, actor, child.config["request_total"]
        )
        _, payload = await read_segment(db, blob, child, "draft_json")
        drafts.append(json.loads(payload))
    draft = {
        "title": drafts[0]["title"],
        "sections": split._merge_sections(drafts),
        "unknowns": list(dict.fromkeys(item for d in drafts for item in d["unknowns"])),
    }
    if run.config.get("ai_supplement"):
        draft["metadata"] = [item for child in drafts for item in child.get("metadata", [])]
        draft["events"] = [item for child in drafts for item in child.get("events", [])]
        draft["rejected_metadata_proposals"] = sum(
            child.get("rejected_metadata_proposals", 0) for child in drafts
        )
    own = segment.config["refined_usage_tokens"]
    segment.usage_tokens = (
        own + sum(child.usage_tokens for child in parts)
        if own is not None and all(c.usage_tokens is not None for c in parts)
        else None
    )
    await refinement.save_pair(
        db,
        blob,
        run,
        segment,
        refinement.node_content(
            segment,
            draft,
            documents,
            [c.id for c in parts],
        ),
    )


async def _run_leaf(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    segment: CompilationSegment,
    documents: list[dict],
    model: ChatModel,
    actor: AuthActor,
    total: int,
) -> None:
    """One part in its own session; the caller owns the session and the lease."""
    if segment.status == "completed":
        return
    plan = split.plan_from_scope(segment.scope)
    payload, citations = split.build_projection(
        run.topic,
        documents,
        plan.owned,
        plan.context,
        segment.segment_index,
        total=total,
        projection=plan.projection,
    )
    messages = split.segment_messages(
        payload, segment.segment_index, total, projection=plan.projection
    )
    structured = bool(segment.config.get("structured_output"))
    schema = split.segment_schema(citations, plan.projection) if structured else None
    if (
        hashlib.sha256(messages[-1].content.encode("utf-8")).hexdigest() != segment.input_sha256
        or segment.prompt_version != split.prompt_version_for(plan.projection)
        or (
            schema is not None
            and hashlib.sha256(json_bytes(schema)).hexdigest() != segment.schema_sha256
        )
    ):
        raise Conflict(
            "Phần biên soạn không còn khớp kế hoạch đã lưu.",
            code="compilation_segment_mismatch",
        )
    recorded, reasoning = _stored_reasoning(segment)
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
            await _settle_part_usage(segment.usage_id, segment.usage_tokens, failed=False)
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
            reasoning=reasoning,
        )
        if run.config.get("automatic_output_budget"):
            request = replace(request, automatic_output_budget=True)
        if (
            runtime.configuration_hash != run.config["provider"]["configuration_hash"]
            or runtime.provider_id != segment.config["provider_id"]
        ):
            raise Conflict(
                "Model hoặc prompt đã đổi so với yêu cầu.",
                code="compilation_provider_changed",
            )
        if recorded:
            live = runtime.reasoning_directive("compiler")
            if (live.public_dict() if live is not None else None) != (
                reasoning.public_dict() if reasoning is not None else None
            ):
                raise Conflict(
                    "Chính sách reasoning đã đổi so với yêu cầu của phần này.",
                    code="compilation_reasoning_changed",
                )
        request = replace(request, enforce_completion_timeout=True)
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
            await _record_segment_error(db, blob, run, segment, usage.id, exc)
            raise
        except (Exception, asyncio.CancelledError):
            await _settle_part_usage(usage.id, None, failed=True)
            raise
        try:
            await assert_claim(db, run)
        except ClaimLost:
            await _settle_part_usage(usage.id, result.total_tokens, failed=True)
            raise
        if result.raw_body:
            await store_segment(db, blob, run, segment, "raw_response", result.raw_body)
        segment.usage_tokens = result.total_tokens
        segment.status = "received"
        await commit_owned(db, run)
        await _settle_part_usage(usage.id, result.total_tokens, failed=False)
        content = result.content
    draft = split.parse_segment_draft(content, set(citations), plan.projection)
    if plan.projection in split.SUPPLEMENT_PROJECTIONS:
        from qnu.domains.knowledge.compilation.projection import project_documents

        owned = project_documents(documents, plan.owned, [])
        draft["metadata"] = supplement.owned_metadata(draft, owned)
        draft["events"] = supplement.owned_events(draft, owned)
        if plan.projection == split.PROJECTION_SELECTIVE:
            draft["sections"] = supplement.useful_sections(draft, owned, documents)
    if run.config.get("refinement"):
        await refinement.save_pair(
            db, blob, run, segment, refinement.node_content(segment, draft, documents)
        )
        return
    await assert_claim(db, run)
    await store_segment(db, blob, run, segment, "draft_json", json_bytes(draft))
    segment.status, segment.error_code = "completed", None
    segment.finished_at = utcnow()
    await commit_owned(db, run)


async def _completed_parts(
    db: AsyncSession, blob: BlobStore, segments: list[CompilationSegment]
) -> list[tuple[int, dict]]:
    """Parts keyed by source index; the merge sorts by it, never by completion."""
    parts: list[tuple[int, dict]] = []
    for segment in segments:
        if segment.status != "completed":
            continue
        _, payload = await read_segment(db, blob, segment, "draft_json")
        parts.append((segment.segment_index, json.loads(payload)))
    return parts


async def _supplement_segments(
    db: AsyncSession, roots: list[CompilationSegment]
) -> list[CompilationSegment]:
    """Keep completed children of an unfinished root, in source order, once."""
    nodes = list(
        (
            await db.scalars(
                select(CompilationSegment)
                .where(CompilationSegment.run_id == roots[0].run_id)
                .order_by(CompilationSegment.segment_index)
            )
        ).all()
    )
    children: dict[str, list[CompilationSegment]] = {}
    for node in nodes:
        if node.parent_segment_id:
            children.setdefault(node.parent_segment_id, []).append(node)
    completed = []

    def collect(node: CompilationSegment) -> None:
        if node.status == "completed":
            completed.append(node)
            return
        for child in children.get(node.id, []):
            collect(child)

    for root in roots:
        collect(root)
    return completed


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
        "segments_received": counts.get("received", 0),
        "segments_failed": counts.get("failed", 0),
        "segments_uncertain": counts.get("uncertain", 0),
        "segments": [
            {"index": segment.segment_index, "status": segment.status} for segment in segments
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
    if draft.get("compilation_nodes"):
        markdown_payload += (
            "\n## Các phần biên soạn\n\n"
            + "\n".join(
                f"- [Phần {node['index']}](segments/{node['index']}/artifacts/markdown)"
                for node in draft["compilation_nodes"]
            )
            + "\n"
        ).encode()
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


def _source_with_supplement(
    run: CompilationRun,
    documents: list[dict],
    parts: list[tuple[int, dict]],
    coverage: dict,
    partial: bool,
) -> dict:
    draft = build_source_draft(run.topic, documents, run.id)
    draft["segmentation"] = coverage
    draft["partial"] = partial
    draft["validation"]["quality"] = quality_validation(
        source_binding=CONFIRMED_BY_SOURCE,
        coverage=(
            NO_ERROR_FOUND
            if coverage.get("state") == "completed" and not partial
            else PARTIALLY_CHECKED
        ),
    )
    supplement.attach(draft, documents, parts, run.input_sha256, run.config)
    if run.selective_supplement:
        draft["supplement"]["state"] = (
            "running"
            if partial
            else "completed"
            if coverage["state"] == "completed"
            else "incomplete"
        )
    return draft


async def _merged_draft(
    run: CompilationRun,
    documents: list[dict],
    parts: list[tuple[int, dict]],
    coverage: dict,
    *,
    partial: bool,
) -> dict:
    if run.config.get("ai_supplement"):
        return await asyncio.to_thread(
            _source_with_supplement, run, documents, parts, coverage, partial
        )
    draft = split.merge_parts_in_order(
        parts,
        run.topic,
        documents,
        run.id,
        partial=partial,
        segmentation=coverage,
    )
    if not partial:
        await asyncio.to_thread(supplement.attach, draft, documents, [], run.input_sha256, {})
    return draft


async def _write_partial(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    documents: list[dict],
    *,
    force: bool = False,
) -> None:
    """Single writer for partial generations; called only by the orchestrator."""
    latest = await compilation_outputs.latest(db, run.id, partial=True)
    if latest and not force:
        age = (utcnow() - latest.created_at).total_seconds()
        if age < PARTIAL_OUTPUT_INTERVAL_SECONDS:
            await db.commit()
            return
    segments = await _segments(db, run.id)
    if not run.config.get("ai_supplement") and not any(
        segment.status == "completed" for segment in segments
    ):
        if not force:
            await db.commit()
        return
    complete_nodes = (
        await _supplement_segments(db, segments) if run.selective_supplement else segments
    )
    coverage = _coverage(segments)
    completed_ids = sorted(node.id for node in complete_nodes if node.status == "completed")
    if (
        latest
        and latest.coverage.get("completed_node_ids") == completed_ids
        and (not force or latest.coverage.get("segments") == coverage["segments"])
    ):
        if not force:
            await db.commit()
        return
    parts = await _completed_parts(db, blob, complete_nodes)
    merged = await _merged_draft(run, documents, parts, coverage, partial=True)
    await compilation_outputs.store_output(
        db,
        blob,
        run,
        draft_payload=json_bytes(merged),
        markdown_payload=split.partial_markdown(merged),
        coverage={**coverage, "completed_node_ids": completed_ids},
        partial=True,
    )
    await commit_owned(db, run)


async def _run_part(
    run_id: str,
    worker_id: str,
    segment_id: str,
    blob: BlobStore,
    documents: list[dict],
    model: ChatModel,
    total: int,
) -> str:
    """One independent part in its own session; never shares a session or lease row."""
    async with AsyncSessionFactory() as db:
        run = await db.get(CompilationRun, run_id, populate_existing=True)
        if run is None or run.worker_id != worker_id:
            return "claim_lost"
        segment = await db.get(CompilationSegment, segment_id, populate_existing=True)
        if segment is None:
            return "missing"
        if segment.status == "completed":
            return "completed"
        try:
            await _run_segment(
                db,
                blob,
                run,
                segment,
                documents,
                model,
                background_actor(run.requested_by),
                total,
            )
        except ClaimLost:
            await db.rollback()
            return "claim_lost"
        except asyncio.CancelledError:
            await db.rollback()
            raise
        except AppException as exc:
            await db.rollback()
            await _fail_part(run_id, worker_id, segment_id, exc.code)
            raise
        except Exception as exc:
            await db.rollback()
            logger.error(
                "compilation_part_processing_failed",
                run_id=run_id,
                segment_id=segment_id,
                error_type=type(exc).__name__,
            )
            raise
        return segment.status


async def _fail_part(run_id: str, worker_id: str, segment_id: str, code: str) -> None:
    """Record a terminal validation failure; the raw bytes stay for diagnosis."""
    async with AsyncSessionFactory() as db:
        run = await db.get(CompilationRun, run_id, populate_existing=True)
        segment = await db.get(CompilationSegment, segment_id, populate_existing=True)
        if run is None or segment is None or run.worker_id != worker_id:
            return
        if segment.status not in {"running", "received"}:
            return
        status = (
            "uncertain"
            if code in {"chat_provider_uncertain", "compilation_request_interrupted"}
            else "failed"
        )
        segment.status, segment.error_code, segment.finished_at = status, code, utcnow()
        try:
            await commit_owned(db, run)
        except ClaimLost:
            await db.rollback()


async def _run_parts(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    documents: list[dict],
    model: ChatModel,
    segment_ids: list[str],
    *,
    total: int,
) -> list[BaseException]:
    """Bounded overlap; stop launching new parts after the first failure."""
    limit = effective_concurrency(run.config)
    clock = asyncio.get_running_loop().time
    next_refresh = 0.0

    async def worker(segment_id: str) -> str:
        return await _run_part(run.id, run.worker_id, segment_id, blob, documents, model, total)

    async def settled() -> None:
        nonlocal next_refresh
        if clock() < next_refresh:
            return
        await _write_partial(db, blob, run, documents)
        next_refresh = clock() + PARTIAL_OUTPUT_INTERVAL_SECONDS

    return await run_bounded(segment_ids, worker, limit=limit, on_settled=settled)


async def _compile_segmented(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    documents: list[dict],
    model: ChatModel,
) -> str:
    segments = await _segments(db, run.id)
    if not segments:
        return await finish(db, run, "failed", "compilation_segment_manifest_mismatch")
    await _verify_manifest(db, blob, run, segments)
    if run.config.get("ai_supplement") and await compilation_outputs.latest(db, run.id) is None:
        await _write_partial(db, blob, run, documents)
    for segment in segments:
        if segment.status == "completed":
            continue
        await _resume_segment(db, blob, run, segment)
    segments = await _segments(db, run.id)
    # Reconcile every in-flight part before returning a terminal status for
    # the run. A hard stop can interrupt more than one independent request.
    uncertain_part = next((part for part in segments if part.status == "uncertain"), None)
    failed_part = next((part for part in segments if part.status == "failed"), None)
    stopped = uncertain_part or failed_part
    if stopped is not None:
        return await _finish_segment_problem(
            db,
            blob,
            run,
            documents,
            segments,
            "uncertain" if uncertain_part is not None else "failed",
            stopped.error_code,
        )
    pending = [segment.id for segment in segments if segment.status != "completed"]
    if pending:
        # Each part uses an independent session, including while waiting for a
        # model slot. The parent has only read state here and can release its
        # connection before the children need it.
        await db.commit()
        logger.info(
            "compilation_parts_started",
            run_id=run.id,
            parts=len(pending),
            concurrency=effective_concurrency(run.config),
        )
        failures = await _run_parts(db, blob, run, documents, model, pending, total=len(segments))
        # No part is in flight here: the scheduler waited for every worker it started.
        # A part that still reads "running" lost its worker on an unexpected error, so
        # its request is in doubt and must not be shown as live progress.
        await _mark_uncertain_segments(db, run)
        if run.config.get("refinement"):
            nodes = list(
                (
                    await db.scalars(
                        select(CompilationSegment).where(
                            CompilationSegment.run_id == run.id,
                        )
                    )
                ).all()
            )
            run.usage_tokens = refinement.total_usage(nodes)
        segments = await _segments(db, run.id)
        coverage = _coverage(segments)
        if coverage["state"] != "completed":
            failed_part = next(
                (segment for segment in segments if segment.status == "failed"), None
            )
            uncertain_part = next(
                (segment for segment in segments if segment.status == "uncertain"), None
            )
            stopped = failed_part or uncertain_part
            code = (
                stopped.error_code
                if stopped is not None and stopped.error_code
                else "compilation_segments_incomplete"
            )
            uncertain = uncertain_part is not None
            if failures and not uncertain:
                first = failures[0]
                code = first.code if isinstance(first, AppException) else "compilation_failed"
            return await _finish_segment_problem(
                db,
                blob,
                run,
                documents,
                segments,
                "uncertain" if uncertain else "failed",
                code,
            )
    if not pending and run.config.get("refinement"):
        nodes = list(
            (
                await db.scalars(
                    select(CompilationSegment).where(
                        CompilationSegment.run_id == run.id,
                    )
                )
            ).all()
        )
        run.usage_tokens = refinement.total_usage(nodes)
    coverage = _coverage(segments)
    if coverage["state"] != "completed":
        return await _finish_segment_problem(
            db, blob, run, documents, segments, "failed", "compilation_segments_incomplete"
        )
    await _write_partial(db, blob, run, documents, force=True)
    return await _finalize_segmented(db, blob, run, documents, segments, coverage)


def _optional_ai_failure(code: str | None) -> bool:
    if code in {
        "chat_provider_changed",
        "model_token_limits_stale",
        "model_token_limits_invalid",
        "model_connection_mismatch",
        "model_mismatch",
    }:
        return False
    return bool(
        code
        and (
            code.startswith(("chat_", "quota_", "model_"))
            or code
            in {
                "compilation_draft_invalid",
                "compilation_citation_invalid",
                "compilation_request_interrupted",
                "compilation_refinement_time_exhausted",
                "compilation_refinement_atomic_limit",
                "compilation_refinement_depth_exhausted",
                "compilation_refinement_nodes_exhausted",
            }
        )
    )


async def _finish_segment_problem(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    documents: list[dict],
    segments: list[CompilationSegment],
    status: str,
    code: str | None,
) -> str:
    if (
        run.selective_supplement
        and _optional_ai_failure(code)
        and all(
            _optional_ai_failure(segment.error_code)
            for segment in segments
            if segment.status in {"failed", "uncertain"}
        )
    ):
        return await _finalize_segmented(
            db, blob, run, documents, segments, _coverage(segments), failure_code=code
        )
    await _write_partial(db, blob, run, documents, force=True)
    return await finish(db, run, status, code)


async def _finalize_segmented(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    documents: list[dict],
    segments: list[CompilationSegment],
    coverage: dict,
    *,
    failure_code: str | None = None,
) -> str:
    complete_nodes = (
        await _supplement_segments(db, segments) if run.selective_supplement else segments
    )
    parts = await _completed_parts(db, blob, complete_nodes)
    draft = await _merged_draft(run, documents, parts, coverage, partial=False)
    if run.selective_supplement and coverage["state"] != "completed":
        draft["supplement"]["failure_code"] = failure_code
        draft["supplement"]["incomplete_groups"] = [
            {"index": segment.segment_index, "status": segment.status, "code": segment.error_code}
            for segment in segments
            if segment.status != "completed"
        ]
    await assert_claim(db, run)
    draft["compilation_nodes"] = [
        {
            "segment_id": segment.id,
            "index": segment.segment_index,
            "json": f"segments/{segment.segment_index}/artifacts/draft_json",
            "markdown": f"segments/{segment.segment_index}/artifacts/markdown",
        }
        for segment in complete_nodes
        if segment.status == "completed"
    ]
    await _store_generation(db, blob, run, draft, coverage, partial=False)
    if not run.config.get("refinement"):
        tokens = [segment.usage_tokens for segment in segments if segment.usage_tokens]
        run.usage_tokens = sum(tokens) if tokens else None
    await commit_owned(db, run)
    return await finish(db, run, "completed")


async def _uncertain_segment(db: AsyncSession, run_id: str) -> bool:
    segments = list(
        (
            await db.scalars(
                select(CompilationSegment).where(
                    CompilationSegment.run_id == run_id,
                )
            )
        ).all()
    )
    for segment in segments:
        if segment.status == "uncertain":
            return True
        if (
            segment.status == "running"
            and segment.request_started_at is not None
            and await segment_artifact(db, segment.id, "raw_response") is None
        ):
            return True
    return False


async def _mark_uncertain_segments(db: AsyncSession, run: CompilationRun) -> None:
    all_nodes = list(
        (
            await db.scalars(
                select(CompilationSegment).where(
                    CompilationSegment.run_id == run.id,
                )
            )
        ).all()
    )
    parents = {node.parent_segment_id for node in all_nodes if node.parent_segment_id}
    for segment in all_nodes:
        if segment.id in parents:
            continue
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
            await _settle_part_usage(segment.usage_id, None, failed=True)
        segment.status = "uncertain"
        segment.error_code = "compilation_request_interrupted"
        segment.finished_at = utcnow()

    by_id = {node.id: node for node in all_nodes}
    for node in all_nodes:
        if node.status != "uncertain":
            continue
        parent_id, visited = node.parent_segment_id, set()
        while parent_id in by_id and parent_id not in visited:
            visited.add(parent_id)
            parent = by_id[parent_id]
            parent.status, parent.error_code, parent.finished_at = (
                "uncertain",
                node.error_code,
                utcnow(),
            )
            parent_id = parent.parent_segment_id


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
            logger.warning(
                "compilation_run_failed",
                run_id=run_id,
                error_type=type(exc).__name__,
                error_code=code,
            )
            try:
                if run.config.get("workflow_version") == "qnu.compiler.workflow/v2":
                    uncertain = code == "chat_provider_uncertain" or await _uncertain_segment(
                        db, run.id
                    )
                    if uncertain:
                        await _mark_uncertain_segments(db, run)
                    return await finish(db, run, "uncertain" if uncertain else "failed", code)
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
