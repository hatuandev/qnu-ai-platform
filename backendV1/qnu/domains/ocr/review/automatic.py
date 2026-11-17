"""Run an automatic review across the whole saved document."""

import asyncio
import json
from collections import deque
from datetime import timedelta

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.public_api import resolve_revision_scope
from qnu.domains.modelops.inference.service import (
    available_input_tokens,
    input_token_upper_bound,
    prepare_chat_limits,
)
from qnu.domains.ocr.ids import new_id
from qnu.domains.ocr.models import OcrProcessingRun, utcnow
from qnu.domains.ocr.review import defaults, detection, service
from qnu.domains.ocr.review.context import CONTEXT_VERSION, ContextIndex, build_context
from qnu.domains.ocr.review.models import SpellingRun
from qnu.domains.ocr.review.schemas import (
    ContextSuggestedText,
    DetectionResponse,
    DetectRequest,
    ReviewDocument,
    TextUnit,
)
from qnu.domains.workspaces.access import actor_ref
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException, EntityNotFound
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatMessage, ChatModel

logger = get_logger(__name__)

BATCH_SIZE = 25
SCOPE_WAIT_SECONDS = 2
SPLIT_ERRORS = {
    "model_input_limit_exceeded",
    "model_context_limit_exceeded",
    "chat_output_truncated",
}


async def _latest_selected(
    db: AsyncSession, run: OcrProcessingRun, version: int, actor: AuthActor
) -> SpellingRun | None:
    return await db.scalar(
        select(SpellingRun)
        .where(
            SpellingRun.run_id == run.id,
            SpellingRun.workspace_id == run.workspace_id,
            SpellingRun.collection_id == run.collection_id,
            SpellingRun.version == version,
            SpellingRun.created_by == actor_ref(actor),
            SpellingRun.trace["scope"].astext == "selected",
        )
        .order_by(SpellingRun.created_at.desc())
        .limit(1)
        .execution_options(populate_existing=True)
    )


async def _wait_for_selected(
    db: AsyncSession, actor: AuthActor, run: OcrProcessingRun, version: int
) -> tuple[SpellingRun | None, bool]:
    """Caller holds the source lock. Release it while the earlier task uses ModelOps."""
    waited = False
    while selected := await _latest_selected(db, run, version, actor):
        if selected.status != "running" or selected.expires_at <= utcnow():
            return selected, waited and selected.status in {"running", "uncertain"}
        waited = True
        await db.commit()
        await asyncio.sleep(SCOPE_WAIT_SECONDS)
        await service.authorize(db, actor, run, write=True, lock=True)
    return None, False


async def review_document(
    db: AsyncSession,
    blob: BlobStore,
    chat: ChatModel,
    actor: AuthActor,
    run: OcrProcessingRun,
    version: int,
    *,
    retry: bool = False,
    automatic: bool = False,
) -> str:
    run_id = run.id
    await service.authorize(db, actor, run, write=True, lock=True)
    selected_review = None
    if not automatic:
        selected_review, interrupted = await _wait_for_selected(db, actor, run, version)
        if interrupted and selected_review is not None:
            return (await detection.readable_check(db, selected_review)).status
    doc, canonical = await service.load_review(db, blob, run, version)
    if doc.version != version:
        return "version_not_found"
    evidence_ids = list(dict.fromkeys(unit.evidence_id for unit in doc.units))
    full_key = f"auto:spl:document:{run.id}:{version}:{detection.PROMPT_VERSION}"
    base_key = full_key
    scope = "full"
    if automatic:
        revision = await resolve_revision_scope(
            db, run.workspace_id, run.collection_id, run.source_id, run.revision_id
        )
        policy = await defaults.read(db)
        selected = defaults.eligible_ids(canonical, revision.extension, policy)
        if not selected:
            scope = "skipped"
        elif len(selected) < len(evidence_ids):
            scope = "selected"
        evidence_ids = [key for key in evidence_ids if key in selected]
        if scope != "full":
            base_key += f":{scope}"
    same_request = or_(
        SpellingRun.idempotency_key == base_key,
        SpellingRun.idempotency_key.startswith(base_key + ":retry:", autoescape=True),
    )
    if automatic:
        # Redelivery must use the scope already recorded before settings changed.
        same_request = or_(
            same_request,
            SpellingRun.trace["automatic_document"].astext == "true",
            SpellingRun.idempotency_key == full_key,
            SpellingRun.idempotency_key.startswith(full_key + ":retry:", autoescape=True),
        )
    existing = await db.scalar(
        select(SpellingRun)
        .where(
            SpellingRun.workspace_id == run.workspace_id,
            SpellingRun.collection_id == run.collection_id,
            SpellingRun.run_id == run.id,
            SpellingRun.version == version,
            SpellingRun.created_by == actor_ref(actor),
            same_request,
        )
        .order_by(SpellingRun.created_at.desc())
        .limit(1)
    )
    retry_of = None
    if existing is not None:
        if not (retry and existing.status in {"failed", "uncertain"}):
            return (await detection.readable_check(db, existing)).status
        retry_of = existing.id
        key = f"{base_key}:retry:{existing.id}"
    else:
        key = base_key
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
            "context_version": CONTEXT_VERSION,
            "total_evidence_count": len(evidence_ids),
            "scope": scope,
            **({"automatic_document": True} if automatic else {}),
            "withheld_suggestions": [],
            "rejected_suggestions": [],
            **({"retry_of": retry_of} if retry_of else {}),
        },
        expires_at=utcnow()
        + timedelta(seconds=get_settings().WORKER_MODEL_JOB_TIMEOUT_SECONDS + 60),
    )
    db.add(parent)
    await db.commit()
    if not evidence_ids:
        return "completed"

    try:
        runtime, budget = await prepare_chat_limits(
            db,
            actor,
            run.workspace_id,
            provider_id=None,
            max_output_tokens=None,
            task="ocr_review",
        )
        configuration_hash = runtime.inference_configuration_hash("ocr_review")
        parent = await detection.check_running(db, parent_id)
        parent.trace = {
            **parent.trace,
            "provider_id": runtime.provider_id,
            "model_name": runtime.model_name,
            "configuration_hash": configuration_hash,
            "routing": list(runtime.routing_trace),
        }
        inherited = await _resume_results(db, existing or selected_review, parent)
        positions = {evidence_id: index for index, evidence_id in enumerate(evidence_ids)}
        covered = {
            evidence_id for result in inherited for evidence_id in result.checked_evidence_ids
        }
        await _aggregate(db, parent, inherited, positions)
        index = await asyncio.to_thread(ContextIndex.from_document, canonical)
        batches = await asyncio.to_thread(
            plan_batches,
            [evidence_id for evidence_id in evidence_ids if evidence_id not in covered],
            {unit.evidence_id: unit for unit in doc.units},
            index,
            doc.version,
            doc.canonical_sha256,
            runtime.token_limits,
            runtime.token_limits.max_output_tokens or budget.max_output_tokens,
        )
        return await _review_batches(
            db,
            blob,
            chat,
            actor,
            run_id,
            doc,
            index,
            runtime,
            configuration_hash,
            parent_id,
            batches,
            inherited,
            positions,
        )
    except AppException as exc:
        logger.warning(
            "spelling_review_failed",
            run_id=run_id,
            check_id=parent_id,
            code=exc.code,
            cause=_safe_cause(exc),
        )
        await db.rollback()
        status = "uncertain" if exc.code == "chat_provider_uncertain" else "failed"
        return await _finish(db, parent_id, status, exc.code)
    except (Exception, asyncio.CancelledError):
        await db.rollback()
        await _finish(db, parent_id, "uncertain", "ocr_spelling_interrupted")
        raise


async def _resume_results(
    db: AsyncSession, previous: SpellingRun | None, current: SpellingRun
) -> list[DetectionResponse]:
    if previous is None or previous.canonical_sha256 != current.canonical_sha256:
        return []
    trace = previous.trace
    previous_context = trace.get("context_version")
    if any(
        trace.get(key) != current.trace[key]
        for key in ("prompt_version", "provider_id", "configuration_hash")
    ) or previous_context not in (None, CONTEXT_VERSION):
        return []

    # A completed child can be committed just before the worker loses its connection
    # or stops, leaving the parent aggregate one batch behind.
    children = await db.scalars(
        select(SpellingRun)
        .where(
            SpellingRun.run_id == current.run_id,
            SpellingRun.workspace_id == current.workspace_id,
            SpellingRun.collection_id == current.collection_id,
            SpellingRun.created_by == current.created_by,
            SpellingRun.version == current.version,
            SpellingRun.canonical_sha256 == current.canonical_sha256,
            SpellingRun.status == "completed",
            SpellingRun.trace["automatic_parent"].astext == previous.id,
            SpellingRun.trace["context_version"].astext == CONTEXT_VERSION,
        )
        .order_by(SpellingRun.created_at, SpellingRun.id)
    )
    # Older parent rows omitted the context version. Recover those from child
    # records, which recorded the version used to produce each result.
    results = [detection.detection_response(previous)] if previous_context else []
    covered = set(previous.checked_evidence_ids) if previous_context else set()
    for child in children:
        if covered.isdisjoint(child.checked_evidence_ids):
            results.append(detection.detection_response(child))
            covered.update(child.checked_evidence_ids)
    return results


def plan_batches(
    evidence_ids: list[str],
    units: dict[str, TextUnit],
    canonical: dict | ContextIndex,
    version: int,
    canonical_sha256: str,
    limits,
    output_tokens: int | None,
) -> list[tuple[int, list[str]]]:
    """Pack contiguous units under the declared input envelope, capped by ``BATCH_SIZE``.

    The actual send still goes through ``prepare_chat_request``; an underestimate
    only means the batch is split on the provider's own limit error.
    """
    cap = max(1, BATCH_SIZE)
    available = None
    if limits is not None:
        available = available_input_tokens(limits, max(1, output_tokens or 1))
    if available is None:
        return [
            (offset, evidence_ids[offset : offset + cap])
            for offset in range(0, len(evidence_ids), cap)
        ]
    schema_size = len(
        json.dumps(ContextSuggestedText.model_json_schema(), ensure_ascii=False).encode()
    )
    index = canonical if isinstance(canonical, ContextIndex) else ContextIndex.from_document(canonical)
    batches: list[tuple[int, list[str]]] = []
    start = 0
    while start < len(evidence_ids):
        size = min(cap, len(evidence_ids) - start)
        trial = evidence_ids[start : start + size]
        if size > 1 and _upper_bound(
            trial, units, index, version, canonical_sha256, schema_size
        ) > available:
            low, high = 1, size - 1
            while low < high:
                middle = (low + high + 1) // 2
                estimate = _upper_bound(
                    trial[:middle], units, index, version, canonical_sha256, schema_size
                )
                if estimate <= available:
                    low = middle
                else:
                    high = middle - 1
            trial = trial[:low]
        batches.append((start, trial))
        start += len(trial)
    return batches


def _upper_bound(
    evidence_ids: list[str],
    units: dict[str, TextUnit],
    canonical: dict | ContextIndex,
    version: int,
    canonical_sha256: str,
    schema_size: int,
) -> int:
    context = build_context(
        canonical, {evidence_id: units[evidence_id] for evidence_id in evidence_ids}
    )
    context["text_version"] = version
    context["canonical_sha256"] = canonical_sha256
    messages = [
        ChatMessage("system", detection.SYSTEM),
        ChatMessage("user", json.dumps(context, ensure_ascii=False)),
    ]
    return (
        input_token_upper_bound(messages)
        + schema_size
        + sum(len(evidence_id) + 4 for evidence_id in evidence_ids)
    )


async def _review_batches(
    db: AsyncSession,
    blob: BlobStore,
    chat: ChatModel,
    actor: AuthActor,
    run_id: str,
    doc: ReviewDocument,
    canonical: ContextIndex,
    runtime,
    configuration_hash: str,
    parent_id: str,
    batches: list[tuple[int, list[str]]],
    inherited: list[DetectionResponse],
    positions: dict[str, int],
) -> str:
    settings = get_settings()
    limit = max(1, min(settings.SPELLING_BATCH_CONCURRENCY, settings.MODEL_CHAT_CONCURRENCY))
    queue = deque(batches)
    active: dict[asyncio.Task, tuple[int, list[str]]] = {}
    outcomes = list(inherited)
    error_code = None
    terminal: DetectionResponse | None = None
    fatal: BaseException | None = None
    stop = False
    try:
        while active or (queue and not stop):
            while queue and not stop and len(active) < limit:
                offset, group = queue.popleft()
                active[
                    asyncio.create_task(
                        _inspect_batch(
                            blob,
                            chat,
                            actor,
                            run_id,
                            doc,
                            canonical,
                            runtime,
                            configuration_hash,
                            parent_id,
                            offset,
                            group,
                        )
                    )
                ] = (offset, group)
            if not active:
                break
            done, _ = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                offset, group = active.pop(task)
                try:
                    result = task.result()
                except AppException as exc:
                    invalid_output = exc.code == "ocr_spelling_invalid"
                    if not invalid_output and exc.code not in SPLIT_ERRORS:
                        fatal = fatal or exc
                        stop = True
                        continue
                    logger.warning(
                        "spelling_batch_rejected",
                        run_id=run_id,
                        check_id=parent_id,
                        offset=offset,
                        size=len(group),
                        code=exc.code,
                        cause=_safe_cause(exc),
                    )
                    if invalid_output or len(group) == 1:
                        error_code = error_code or exc.code
                    else:
                        middle = len(group) // 2
                        queue.appendleft((offset + middle, group[middle:]))
                        queue.appendleft((offset, group[:middle]))
                    continue
                except BaseException as exc:
                    fatal = fatal or exc
                    stop = True
                    continue
                if result.status != "completed":
                    terminal = result
                    stop = True
                    continue
                outcomes.append(result)
                parent = await detection.check_running(db, parent_id)
                await _aggregate(db, parent, outcomes, positions)
    finally:
        stop = True
        if active:
            # Never cancel a provider call that is already in flight.
            await asyncio.gather(*active, return_exceptions=True)
    if fatal is not None:
        raise fatal
    if terminal is not None:
        return await _finish(db, parent_id, terminal.status, terminal.error_code)
    return await _finish(db, parent_id, "failed" if error_code else "completed", error_code)


async def _inspect_batch(
    blob: BlobStore,
    chat: ChatModel,
    actor: AuthActor,
    run_id: str,
    doc: ReviewDocument,
    canonical: ContextIndex,
    runtime,
    configuration_hash: str,
    parent_id: str,
    offset: int,
    group: list[str],
) -> DetectionResponse:
    async with AsyncSessionFactory() as batch_db:
        batch_run = await batch_db.get(OcrProcessingRun, run_id)
        if batch_run is None:
            raise EntityNotFound("Không tìm thấy lượt xử lý.", code="processing_run_not_found")
        return await detection.inspect(
            batch_db,
            blob,
            chat,
            actor,
            batch_run,
            DetectRequest(
                source_version=doc.version,
                expected_version=doc.version,
                expected_sha256=doc.canonical_sha256,
                evidence_ids=group,
                provider_id=runtime.provider_id,
            ),
            f"auto:spl:batch:{parent_id}:{offset}:{len(group)}",
            automatic_parent=parent_id,
            configuration_hash=configuration_hash,
            review=doc,
            canonical=canonical,
        )


async def _aggregate(
    db: AsyncSession,
    parent: SpellingRun,
    results: list[DetectionResponse],
    positions: dict[str, int],
) -> None:
    def by_evidence(item):
        return positions.get(item.evidence_id, len(positions))

    parent.checked_evidence_ids = sorted(
        {evidence_id for result in results for evidence_id in result.checked_evidence_ids},
        key=positions.__getitem__,
    )
    parent.suggestions = [
        item.model_dump()
        for item in sorted(
            (item for result in results for item in result.suggestions), key=by_evidence
        )
    ]
    parent.trace = {
        **parent.trace,
        "withheld_suggestions": [
            item.model_dump()
            for item in sorted(
                (item for result in results for item in result.withheld_suggestions),
                key=by_evidence,
            )
        ],
        "rejected_suggestions": [
            item.model_dump()
            for item in sorted(
                (item for result in results for item in result.rejected_suggestions),
                key=by_evidence,
            )
        ],
    }
    await db.commit()


def _safe_cause(exc: AppException) -> str:
    """Log only the reason class/field, never model output or document text."""
    cause = exc.__cause__
    if isinstance(cause, ValidationError):
        return ",".join(sorted({str(item["type"]) for item in cause.errors()}))
    if isinstance(cause, ValueError):
        return str(cause)[:120]
    return type(cause).__name__ if cause is not None else ""


async def _finish(db: AsyncSession, check_id: str, status: str, code: str | None) -> str:
    row = await db.get(SpellingRun, check_id, with_for_update=True, populate_existing=True)
    if row is None:
        return "cancelled"
    if row.status == "running":
        row.status, row.error_code = status, code
    await db.commit()
    return row.status
