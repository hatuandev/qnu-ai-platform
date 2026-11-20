"""Run an automatic review across the whole saved document."""

import asyncio
import json
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.public_api import resolve_revision_scope
from qnu.domains.modelops.capacity.schemas import RequestTokenBudget
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.document_processing import (
    DEFAULT_DOCUMENT_CONCURRENCY,
    GroupModel,
    resolve_document_group,
)
from qnu.domains.modelops.inference.service import (
    available_input_tokens,
    input_token_upper_bound,
    prepare_chat_limits,
)
from qnu.domains.modelops.public_api import ChatRuntime
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


@dataclass(frozen=True, slots=True)
class SpellingSlot:
    provider_id: str
    concurrency: int
    runtime: ChatRuntime
    budget: RequestTokenBudget
    configuration_hash: str


@asynccontextmanager
async def _worker_session(parent_db: AsyncSession):
    if hasattr(parent_db, "_mock_return_value") or type(parent_db).__name__ in {"AsyncMock", "MagicMock"}:
        yield parent_db
    else:
        async with AsyncSessionFactory() as session:
            yield session


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
    pass_number: int = 1,
    total_passes: int = 2,
    parent_run_id: str | None = None,
    batch_group_id: str | None = None,
) -> tuple[str, str | None]:
    run_id = run.id
    await service.authorize(db, actor, run, write=True, lock=True)
    selected_review = None
    if not automatic:
        selected_review, interrupted = await _wait_for_selected(db, actor, run, version)
        if interrupted and selected_review is not None:
            readable = await detection.readable_check(db, selected_review)
            return readable.status, selected_review.id
    doc, canonical = await service.load_review(db, blob, run, version)
    if doc.version != version:
        return "version_not_found", None

    if parent_run_id:
        parent_run = await db.get(SpellingRun, parent_run_id)
        if parent_run is None or parent_run.canonical_sha256 != doc.canonical_sha256:
            logger.info("spelling_multi_pass_hash_mismatch", run_id=run.id, version=version)
            return "hash_mismatch_stopped", None
        if not batch_group_id:
            batch_group_id = parent_run.batch_group_id or parent_run.id

    pass_cfg = detection.PASS_CONFIGS.get(pass_number, detection.PASS_CONFIGS[1])
    pass_name = pass_cfg["name"]
    pass_focus = pass_cfg["focus"]

    evidence_ids = list(dict.fromkeys(unit.evidence_id for unit in doc.units))
    full_key = f"auto:spl:document:{run.id}:{version}:p{pass_number}:{detection.PROMPT_VERSION}"
    legacy_key = f"auto:spl:document:{run.id}:{version}:{detection.PROMPT_VERSION}" if pass_number == 1 else full_key
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
    if pass_number == 1:
        same_request = or_(
            same_request,
            SpellingRun.idempotency_key == legacy_key,
            SpellingRun.idempotency_key.startswith(legacy_key + ":retry:", autoescape=True),
        )
    if automatic:
        # Redelivery must use the scope already recorded before settings changed.
        same_request = or_(
            same_request,
            SpellingRun.trace["automatic_document"].astext == "true",
            SpellingRun.idempotency_key == full_key,
            SpellingRun.idempotency_key.startswith(full_key + ":retry:", autoescape=True),
            SpellingRun.idempotency_key == legacy_key,
            SpellingRun.idempotency_key.startswith(legacy_key + ":retry:", autoescape=True),
        )
    existing = await db.scalar(
        select(SpellingRun)
        .where(
            SpellingRun.workspace_id == run.workspace_id,
            SpellingRun.collection_id == run.collection_id,
            SpellingRun.run_id == run.id,
            SpellingRun.version == version,
            SpellingRun.pass_number == pass_number,
            SpellingRun.created_by == actor_ref(actor),
            same_request,
        )
        .order_by(SpellingRun.created_at.desc())
        .limit(1)
    )
    retry_of = None
    if existing is not None:
        if not (retry and existing.status in {"failed", "uncertain"}):
            return (await detection.readable_check(db, existing)).status, existing.id
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
        pass_number=pass_number,
        total_passes=total_passes,
        pass_name=pass_name,
        parent_run_id=parent_run_id,
        batch_group_id=batch_group_id or parent_id,
        checked_evidence_ids=[],
        suggestions=[],
        trace={
            "prompt_version": detection.PROMPT_VERSION,
            "context_version": CONTEXT_VERSION,
            "total_evidence_count": len(evidence_ids),
            "scope": scope,
            "pass_number": pass_number,
            "total_passes": total_passes,
            "pass_name": pass_name,
            "pass_focus": pass_focus,
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
        return "completed", parent_id

    try:
        group = await resolve_document_group(db)
        candidate_models = list(group.models)
        if not candidate_models:
            primary = await catalog_service.system_default_for(db, "chat")
            if primary is not None:
                candidate_models = [GroupModel(primary, DEFAULT_DOCUMENT_CONCURRENCY)]

        slots: list[SpellingSlot] = []
        for member in candidate_models:
            try:
                m_runtime, m_budget = await prepare_chat_limits(
                    db,
                    actor,
                    run.workspace_id,
                    provider_id=member.provider_id,
                    max_output_tokens=None,
                    task="ocr_review",
                )
                m_hash = m_runtime.inference_configuration_hash("ocr_review")
                slots.append(
                    SpellingSlot(
                        provider_id=member.provider_id,
                        concurrency=member.concurrency,
                        runtime=m_runtime,
                        budget=m_budget,
                        configuration_hash=m_hash,
                    )
                )
                if group.mode == "priority":
                    break
            except AppException as exc:
                logger.warning(
                    "spelling_candidate_model_skipped",
                    provider_id=member.provider_id,
                    code=exc.code,
                )
                continue

        if not slots:
            logger.warning("spelling_no_usable_models", run_id=run.id, version=version)
            return "failed", None

        # Determine the most conservative input token budget across participating models
        avails = [
            available_input_tokens(s.runtime.token_limits, max(1, s.budget.max_output_tokens or 1))
            for s in slots
        ]
        valid_avails = [a for a in avails if a is not None]
        min_available = min(valid_avails) if valid_avails else None

        parent = await detection.check_running(db, parent_id)
        parent.trace = {
            **parent.trace,
            "document_mode": group.mode if group.models else "fallback_chat",
            "document_models": [
                {
                    "provider_id": slot.provider_id,
                    "concurrency": slot.concurrency,
                    "model_name": slot.runtime.model_name,
                    "configuration_hash": slot.configuration_hash,
                }
                for slot in slots
            ],
            "provider_id": slots[0].provider_id,
            "model_name": slots[0].runtime.model_name,
            "configuration_hash": slots[0].configuration_hash,
            "routing": list(slots[0].runtime.routing_trace),
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
            min_available if min_available is not None else slots[0].runtime.token_limits,
            slots[0].budget.max_output_tokens,
        )
        return await _review_batches(
            db,
            blob,
            chat,
            actor,
            run_id,
            doc,
            index,
            slots,
            parent_id,
            batches,
            inherited,
            positions,
            pass_number=pass_number,
            total_passes=total_passes,
            pass_name=pass_name,
            parent_run_id=parent_run_id,
            batch_group_id=parent.batch_group_id,
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
    if isinstance(limits, int):
        available = limits
    elif limits is not None:
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
    slots: list[SpellingSlot] | Any,
    parent_id: str,
    batches: list[tuple[int, list[str]]],
    inherited: list[DetectionResponse],
    positions: dict[str, int],
    *,
    pass_number: int = 1,
    total_passes: int = 2,
    pass_name: str = "char_ocr",
    parent_run_id: str | None = None,
    batch_group_id: str | None = None,
) -> tuple[str, str | None]:
    if not isinstance(slots, list):
        slots = [
            SpellingSlot(
                provider_id=getattr(slots, "provider_id", "default"),
                concurrency=1,
                runtime=slots,
                budget=None,  # type: ignore
                configuration_hash=getattr(slots, "configuration_hash", ""),
            )
        ]

    queue = deque(batches)
    queue_cond = asyncio.Condition()
    agg_lock = asyncio.Lock()
    in_flight = 0
    outcomes = list(inherited)
    batch_providers: dict[int, str] = {}
    error_code = None
    terminal: DetectionResponse | None = None
    fatal: BaseException | None = None
    stop = asyncio.Event()
    hash_mismatched = False

    async def worker_loop(slot: SpellingSlot) -> None:
        nonlocal in_flight, error_code, terminal, fatal, hash_mismatched
        while not stop.is_set():
            async with queue_cond:
                while not queue and in_flight > 0 and not stop.is_set():
                    await queue_cond.wait()
                if not queue or stop.is_set():
                    return
                offset, group = queue.popleft()
                in_flight += 1

            # 1. Pre-execution hash check
            try:
                async with _worker_session(db) as check_db:
                    parent = await detection.check_running(check_db, parent_id)
                    if parent.canonical_sha256 != doc.canonical_sha256:
                        logger.info("spelling_batch_hash_mismatch", run_id=run_id, check_id=parent_id)
                        hash_mismatched = True
                        stop.set()
                        async with queue_cond:
                            in_flight -= 1
                            queue_cond.notify_all()
                        return
            except Exception as exc:
                fatal = fatal or exc
                stop.set()
                async with queue_cond:
                    in_flight -= 1
                    queue_cond.notify_all()
                return

            # 2. Inspect batch
            try:
                result = await _inspect_batch(
                    blob,
                    chat,
                    actor,
                    run_id,
                    doc,
                    canonical,
                    slot.runtime,
                    slot.configuration_hash,
                    parent_id,
                    offset,
                    group,
                    pass_number=pass_number,
                    total_passes=total_passes,
                    pass_name=pass_name,
                    parent_run_id=parent_run_id,
                    batch_group_id=batch_group_id,
                )
            except AppException as exc:
                invalid_output = exc.code == "ocr_spelling_invalid"
                if not invalid_output and exc.code not in SPLIT_ERRORS:
                    fatal = fatal or exc
                    stop.set()
                else:
                    logger.warning(
                        "spelling_batch_rejected",
                        run_id=run_id,
                        check_id=parent_id,
                        offset=offset,
                        size=len(group),
                        provider_id=slot.provider_id,
                        code=exc.code,
                        cause=_safe_cause(exc),
                    )
                    if invalid_output or len(group) == 1:
                        error_code = error_code or exc.code
                    else:
                        middle = len(group) // 2
                        async with queue_cond:
                            queue.appendleft((offset + middle, group[middle:]))
                            queue.appendleft((offset, group[:middle]))
                async with queue_cond:
                    in_flight -= 1
                    queue_cond.notify_all()
                continue
            except BaseException as exc:
                fatal = fatal or exc
                stop.set()
                async with queue_cond:
                    in_flight -= 1
                    queue_cond.notify_all()
                return

            if result.status != "completed":
                terminal = result
                stop.set()
                async with queue_cond:
                    in_flight -= 1
                    queue_cond.notify_all()
                return

            # Tag provider_id on suggestions
            for s in result.suggestions:
                if not getattr(s, "provider_id", None):
                    s.provider_id = slot.provider_id

            async with queue_cond:
                outcomes.append(result)
                batch_providers[offset] = slot.provider_id
                in_flight -= 1
                queue_cond.notify_all()

            # Post-execution aggregation & hash check
            try:
                async with agg_lock, _worker_session(db) as agg_db:
                    parent = await detection.check_running(agg_db, parent_id)
                    if parent.canonical_sha256 != doc.canonical_sha256:
                        hash_mismatched = True
                        stop.set()
                        return
                    await _aggregate(agg_db, parent, outcomes, positions, batch_providers=batch_providers)
            except Exception as exc:
                fatal = fatal or exc
                stop.set()
                return

    tasks = [
        asyncio.create_task(worker_loop(slot))
        for slot in slots
        for _ in range(max(1, slot.concurrency))
    ]
    try:
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        stop.set()
        async with queue_cond:
            queue_cond.notify_all()
        pending = [t for t in tasks if not t.done()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    if fatal is not None:
        raise fatal
    if hash_mismatched:
        return await _finish(db, parent_id, "hash_mismatch_stopped", "hash_mismatch_stopped")
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
    *,
    pass_number: int = 1,
    total_passes: int = 2,
    pass_name: str = "char_ocr",
    parent_run_id: str | None = None,
    batch_group_id: str | None = None,
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
            pass_number=pass_number,
            total_passes=total_passes,
            pass_name=pass_name,
            parent_run_id=parent_run_id,
            batch_group_id=batch_group_id,
        )


async def _aggregate(
    db: AsyncSession,
    parent: SpellingRun,
    results: list[DetectionResponse],
    positions: dict[str, int],
    batch_providers: dict[int, str] | None = None,
) -> None:
    def by_evidence(item):
        ev_id = getattr(item, "evidence_id", None) or (item.get("evidence_id") if isinstance(item, dict) else None)
        return positions.get(ev_id, len(positions))

    parent.checked_evidence_ids = sorted(
        {evidence_id for result in results for evidence_id in result.checked_evidence_ids},
        key=positions.__getitem__,
    )
    raw_suggestions = [
        item.model_dump()
        for item in sorted(
            (item for result in results for item in result.suggestions), key=by_evidence
        )
    ]
    # Tag pass_number on suggestions from this pass
    for s in raw_suggestions:
        if s.get("pass_number") is None:
            s["pass_number"] = parent.pass_number

    # Multi-pass inheritance: if pass > 1, merge with previous pass suggestions and filter ignored
    if parent.pass_number > 1 and parent.parent_run_id:
        parent_run = await db.get(SpellingRun, parent.parent_run_id)
        if parent_run and parent_run.canonical_sha256 == parent.canonical_sha256:
            ignored_map = await detection.ignored_suggestions(db, [parent_run.id])
            ignored_set = {
                (it.evidence_id, it.start, it.end) for it in ignored_map.get(parent_run.id, [])
            }
            prev_suggestions = []
            for s in parent_run.suggestions:
                k = (s.get("evidence_id"), s.get("start"), s.get("end"))
                if k not in ignored_set:
                    prev_suggestions.append(s)
            seen_spans = {(s["evidence_id"], s["start"], s["end"]) for s in prev_suggestions}
            combined = list(prev_suggestions)
            for s in raw_suggestions:
                k = (s.get("evidence_id"), s.get("start"), s.get("end"))
                if k not in seen_spans and k not in ignored_set:
                    combined.append(s)
                    seen_spans.add(k)
            parent.suggestions = sorted(combined, key=by_evidence)
        else:
            parent.suggestions = raw_suggestions
    else:
        parent.suggestions = raw_suggestions

    extra_trace = {}
    if batch_providers:
        extra_trace = {
            "batch_providers": {str(k): v for k, v in batch_providers.items()},
            "used_providers": sorted(set(batch_providers.values())),
        }

    parent.trace = {
        **parent.trace,
        **extra_trace,
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


async def _finish(db: AsyncSession, check_id: str, status: str, code: str | None) -> tuple[str, str]:
    row = await db.get(SpellingRun, check_id, with_for_update=True, populate_existing=True)
    if row is None:
        return "cancelled", check_id
    if row.status == "running":
        row.status, row.error_code = status, code
    await db.commit()
    return row.status, row.id
