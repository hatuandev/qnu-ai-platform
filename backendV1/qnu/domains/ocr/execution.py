"""Execute one OCR processing run against its pinned revision.

Order of work, and why:

1. **Claim** the run atomically. A second worker that loses the race does nothing.
2. **Re-authorize** the original requester: membership, role and workspace state are
   read now, not taken from the queue payload. A revoked member or suspended
   workspace stops the run before any provider call.
3. **Re-resolve** the OCR provider through ModelOps, including grant, capability,
   active state and credential. A provider that changed since the run started stops it.
4. **Read** the revision bytes and verify the pinned checksum.
5. **Render** pages, storing each image and its hash as an artifact.
6. **OCR page by page**: mark ``in_flight`` and commit *before* the request, so a
   worker that dies mid-request leaves an ``uncertain`` marker instead of a silent
   duplicate call; store the raw response; settle usage with measured tokens only.
7. **Assemble** canonical JSON, Markdown and manifest, validate, and only then set the
   final status. The original file is never touched, whatever happens here.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.index.artifact_cache import (
    get_artifact_payload,
    set_artifact_payload,
)
from qnu.domains.knowledge.public_api import (
    WRITE_ROLES,
    read_revision_bytes,
    resolve_revision_scope,
)
from qnu.domains.modelops.public_api import OcrRuntime, resolve_ocr_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.ocr.artifacts.canonical import (
    PageDocument,
    build_canonical,
    build_manifest,
    render_markdown,
)
from qnu.domains.ocr.artifacts.render import RenderedDocument, render_async, render_saved_pdf_async
from qnu.domains.ocr.artifacts.validate import validate_document
from qnu.domains.ocr.budget import page_request_budget
from qnu.domains.ocr.config import (
    LEGACY_MARKDOWN_VERSION,
    OCR_PROMPT,
    SUPPORTED_PROCESSING_EXTENSIONS,
    ProcessingConfig,
    config_from_run,
    ocr_contract_hash,
)
from qnu.domains.ocr.errors import is_uncertain
from qnu.domains.ocr.ids import new_id
from qnu.domains.ocr.layout import parse_page
from qnu.domains.ocr.lease import LeaseLost, assert_claim, commit_owned, heartbeat
from qnu.domains.ocr.models import OcrProcessingRun, OcrRunArtifact, OcrRunPage, utcnow
from qnu.domains.ocr.telemetry import observe_stage
from qnu.domains.ocr.warnings import normalize_failures
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, DependencyUnavailable
from qnu.platform.logging import get_logger
from qnu.platform.redaction import redact
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue
from qnu.ports.ocr_engine import OcrEngine, OcrRequest, OcrResponseError
from qnu.ports.provider_execution import ProviderExecution

logger = get_logger(__name__)

RETRYABLE_CODES = frozenset({"storage_unavailable", "queue_unavailable", "dependency_unavailable"})
ARTIFACT_CONTENT_TYPES = {
    "provider_document": "application/zip",
    "native_page": "application/json",
    "embedded_image": "application/octet-stream",
    "render_pdf": "application/pdf",
    "page_image": "image/png",
    "raw_response": "application/json",
    "canonical_json": "application/json",
    "markdown": "text/markdown; charset=utf-8",
    "manifest": "application/json",
}
ARTIFACT_EXTENSIONS = {
    "provider_document": "zip",
    "native_page": "json",
    "embedded_image": "bin",
    "render_pdf": "pdf",
    "page_image": "png",
    "raw_response": "json",
    "canonical_json": "json",
    "markdown": "md",
    "manifest": "json",
}
TASK_NAME = "ocr_process_run"


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    status: str
    reason: str


def artifact_key(run: OcrProcessingRun, kind: str, page_no: int, sha256: str) -> str:
    """Content-addressed per run: a retry rewrites the same object, never a new one."""
    extension = ARTIFACT_EXTENSIONS[kind]
    return (
        f"v1/workspaces/{run.workspace_id}/ocr/{run.id}/{kind}/p{page_no:04d}-{sha256}.{extension}"
    )


def job_id_for(run_id: str, attempt: int) -> str:
    return f"qnu:v1:ocr:{run_id}:{attempt}"


def _raw_text(payload: bytes) -> str:
    """Read back the stored provider text; a damaged artifact is never silently skipped."""
    try:
        data = json.loads(payload)
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise AppException(
            "Raw response đã lưu không đọc được.", code="raw_response_invalid", status_code=502
        ) from exc
    if not isinstance(content, str):
        raise AppException(
            "Raw response đã lưu không đọc được.", code="raw_response_invalid", status_code=502
        )
    return content


def _actor_for(run: OcrProcessingRun) -> AuthActor:
    return background_actor(run.requested_by)


async def _artifact(
    db: AsyncSession, run_id: str, kind: str, page_no: int
) -> OcrRunArtifact | None:
    stmt = select(OcrRunArtifact).where(
        OcrRunArtifact.run_id == run_id,
        OcrRunArtifact.kind == kind,
        OcrRunArtifact.page_no == page_no,
    )
    return (await db.execute(stmt)).scalars().first()


async def _store_artifact(
    db: AsyncSession,
    blob_store: BlobStore,
    run: OcrProcessingRun,
    kind: str,
    page_no: int,
    payload: bytes,
) -> OcrRunArtifact:
    with observe_stage(
        run, "store_artifact", logger=logger, page_number=page_no, artifact_kind=kind
    ) as observation:
        record = await _write_artifact(db, blob_store, run, kind, page_no, payload)
        observation.sha256 = record.sha256
        observation.byte_count = record.size_bytes
        return record


async def _write_artifact(
    db: AsyncSession,
    blob_store: BlobStore,
    run: OcrProcessingRun,
    kind: str,
    page_no: int,
    payload: bytes,
) -> OcrRunArtifact:
    """Store immutable bytes; an existing artifact with other bytes is a hard error."""
    await assert_claim(db, run)
    sha256 = hashlib.sha256(payload).hexdigest()
    existing = await _artifact(db, run.id, kind, page_no)
    if existing is not None:
        if existing.sha256 != sha256:
            raise AppException(
                "Artifact đã tồn tại với nội dung khác; không ghi đè bằng chứng.",
                code="artifact_conflict",
                status_code=409,
                title="Xung đột artifact",
            )
        return existing
    key = artifact_key(run, kind, page_no, sha256)
    try:
        await blob_store.put_bytes(key, payload, ARTIFACT_CONTENT_TYPES[kind])
    except Exception as exc:
        raise DependencyUnavailable(
            "Không ghi được artifact vào kho lưu trữ.", code="storage_unavailable"
        ) from exc
    record = OcrRunArtifact(
        id=new_id("art"),
        run_id=run.id,
        kind=kind,
        page_no=page_no,
        blob_key=key,
        sha256=sha256,
        size_bytes=len(payload),
        content_type=ARTIFACT_CONTENT_TYPES[kind],
    )
    db.add(record)
    await db.flush()
    return record


async def read_artifact_bytes(
    db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun, kind: str, page_no: int
) -> tuple[OcrRunArtifact, bytes]:
    with observe_stage(
        run, "read_artifact", logger=logger, page_number=page_no, artifact_kind=kind
    ) as observation:
        record, payload = await _read_artifact(db, blob_store, run, kind, page_no)
        observation.sha256 = record.sha256
        observation.byte_count = len(payload)
        return record, payload


async def _read_artifact(
    db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun, kind: str, page_no: int
) -> tuple[OcrRunArtifact, bytes]:
    """Read an artifact by kind, never by a client-supplied path, and verify its hash."""
    record = await _artifact(db, run.id, kind, page_no)
    if record is None:
        raise AppException(
            "Chưa có artifact cho yêu cầu này.", code="artifact_not_found", status_code=404
        )
    cached_payload = get_artifact_payload(record.blob_key, record.sha256)
    if cached_payload is not None:
        return record, cached_payload
    try:
        payload = await blob_store.get_bytes(record.blob_key)
    except FileNotFoundError as exc:
        raise AppException(
            "Artifact không còn trong kho lưu trữ.", code="artifact_missing", status_code=502
        ) from exc
    except Exception as exc:
        raise DependencyUnavailable(
            "Không đọc được kho lưu trữ.", code="storage_unavailable"
        ) from exc
    if len(payload) != record.size_bytes or hashlib.sha256(payload).hexdigest() != record.sha256:
        raise AppException(
            "Artifact không khớp checksum đã lưu.",
            code="artifact_integrity_failed",
            status_code=502,
        )
    set_artifact_payload(record.blob_key, record.sha256, payload)
    return record, payload


async def claim_run(
    db: AsyncSession, run_id: str, worker_id: str, lease_seconds: int
) -> OcrProcessingRun | None:
    """Atomic claim; also reclaims a run whose worker stopped renewing its lease."""
    now = utcnow()
    stmt = (
        update(OcrProcessingRun)
        .where(
            OcrProcessingRun.id == run_id,
            (
                (OcrProcessingRun.status == "queued")
                | (
                    (OcrProcessingRun.status == "running")
                    & (OcrProcessingRun.lease_expires_at < now)
                )
            ),
        )
        .values(
            status="running",
            worker_id=worker_id,
            started_at=func.coalesce(OcrProcessingRun.started_at, now),
            lease_expires_at=now + timedelta(seconds=lease_seconds),
            attempt_count=OcrProcessingRun.attempt_count + 1,
            error_code=None,
            error_detail=None,
        )
        .returning(OcrProcessingRun.id)
    )
    claimed = (await db.execute(stmt)).scalars().first()
    await db.commit()
    if claimed is None:
        return None
    return await db.get(OcrProcessingRun, run_id)


async def _fail(
    db: AsyncSession,
    run: OcrProcessingRun,
    code: str,
    detail: str,
    *,
    uncertain: bool = False,
    job_queue: JobQueue | None = None,
) -> ExecutionOutcome:
    await assert_claim(db, run)
    unresolved = await db.scalar(
        select(OcrRunPage.id)
        .where(OcrRunPage.run_id == run.id, OcrRunPage.status.in_(("in_flight", "uncertain")))
        .limit(1)
    )
    uncertain = uncertain or unresolved is not None
    retryable = code in RETRYABLE_CODES and not uncertain
    exhausted = run.attempt_count >= run.max_attempts
    run.status = (
        "uncertain" if uncertain else ("queued" if retryable and not exhausted else "failed")
    )
    run.error_code = code[:64]
    run.error_detail = redact(detail)[:500]
    run.lease_expires_at = None
    run.finished_at = None if run.status == "queued" else utcnow()
    if run.status == "queued":
        run.dispatched_at = None
    await commit_owned(db, run)

    if run.status == "queued" and job_queue is not None:
        try:
            await job_queue.enqueue(
                TASK_NAME, run.id, job_id=job_id_for(run.id, run.attempt_count + 1)
            )
            await db.execute(
                update(OcrProcessingRun)
                .where(
                    OcrProcessingRun.id == run.id,
                    OcrProcessingRun.status == "queued",
                    OcrProcessingRun.worker_id == run.worker_id,
                )
                .values(dispatched_at=utcnow())
            )
            await db.commit()
            return ExecutionOutcome(status="queued", reason="retry_scheduled")
        except Exception:
            logger.warning("ocr_retry_enqueue_failed", run_id=run.id)
    return ExecutionOutcome(status=run.status, reason=code)


async def execute_run(
    db: AsyncSession,
    blob_store: BlobStore,
    run_id: str,
    *,
    worker_id: str,
    engine: OcrEngine,
    job_queue: JobQueue | None = None,
) -> ExecutionOutcome:
    """Run one claimed generation to a truthful terminal state."""
    settings = get_settings()
    token = f"{worker_id[:80]}:{uuid.uuid4().hex}"
    run = await claim_run(db, run_id, token, settings.OCR_LEASE_SECONDS)
    if run is None:
        return ExecutionOutcome(status="not_claimed", reason="already_running_or_done")

    async with heartbeat(run, settings.OCR_LEASE_SECONDS):
        try:
            await assert_claim(db, run)
            await db.execute(
                update(OcrRunPage)
                .where(OcrRunPage.run_id == run.id, OcrRunPage.status == "in_flight")
                .values(status="uncertain", error_code="worker_interrupted")
            )
            await commit_owned(db, run)
            try:
                if run.attempt_count > run.max_attempts:
                    raise AppException(
                        "Đã hết số lần thực thi.",
                        code="processing_attempts_exhausted",
                        status_code=409,
                    )
                return await _execute_claimed(db, blob_store, run, engine, settings, job_queue)
            except LeaseLost:
                raise
            except AppException as exc:
                return await _fail(
                    db,
                    run,
                    exc.code,
                    exc.detail,
                    uncertain=is_uncertain(exc.code),
                    job_queue=job_queue,
                )
            except Exception as exc:
                await db.rollback()
                run = await db.get(OcrProcessingRun, run_id, populate_existing=True)
                if run is None or run.worker_id != token:
                    raise LeaseLost() from exc
                logger.warning(
                    "ocr_run_crashed",
                    run_id=run_id,
                    error_type=type(exc).__name__,
                    error=redact(str(exc))[:500],
                )
                return await _fail(
                    db, run, "processing_failed", type(exc).__name__, job_queue=job_queue
                )
        except LeaseLost:
            await db.rollback()
            return ExecutionOutcome(status="not_claimed", reason="worker_lease_lost")


async def _execute_claimed(
    db: AsyncSession,
    blob_store: BlobStore,
    run: OcrProcessingRun,
    engine: OcrEngine,
    settings,
    job_queue: JobQueue | None,
) -> ExecutionOutcome:
    config = config_from_run(run.config or {})
    actor = _actor_for(run)
    with observe_stage(run, "authorize", logger=logger):
        await resolve_workspace_access(db, actor, run.workspace_id, required_roles=WRITE_ROLES)

    if (run.config or {}).get("extraction", {}).get("strategy") == "auto":
        from qnu.domains.ocr.automatic import execute_auto

        return await execute_auto(db, blob_store, run, actor, engine, config, settings)

    requested = (run.config or {}).get("provider_requested")
    with observe_stage(run, "resolve_model", logger=logger):
        from dataclasses import replace

        from qnu.domains.modelops.resilience.routing import choose_target

        selected, routing = await choose_target(
            db, run.workspace_id, "ocr", run.provider_id or requested
        )
        runtime = await resolve_ocr_runtime(db, run.workspace_id, selected)
        runtime = replace(runtime, routing_trace=routing)
        pinned = (run.config or {}).get("provider")
        if run.provider_id is not None and (
            run.provider_id != runtime.provider_id
            or not pinned
            or pinned.get("configuration_hash") != runtime.configuration_hash
            or (run.config or {}).get("prompt_sha256") != ocr_contract_hash(runtime.provider_type)
        ):
            raise AppException(
                "Provider OCR đã thay đổi so với lúc bắt đầu run.",
                code="provider_changed",
                status_code=409,
                title="Provider thay đổi",
            )
        if run.provider_id is None:
            run.provider_id = runtime.provider_id
            payload = dict(run.config or {})
            payload["provider"] = runtime.public_dict()
            payload["prompt_sha256"] = ocr_contract_hash(runtime.provider_type)
            run.config = payload
            await commit_owned(db, run)

    with observe_stage(run, "load_revision", logger=logger) as observation:
        scope = await resolve_revision_scope(
            db, run.workspace_id, run.collection_id, run.source_id, run.revision_id
        )
        if scope.sha256 != run.source_sha256:
            raise AppException(
                "Revision không còn khớp checksum đã ghim.",
                code="revision_content_mismatch",
                status_code=409,
            )
        if scope.extension not in SUPPORTED_PROCESSING_EXTENSIONS:
            raise AppException(
                f"Định dạng '{scope.extension or 'không rõ'}' chưa được hỗ trợ xử lý OCR.",
                code="processing_unsupported_format",
                status_code=415,
                title="Định dạng chưa hỗ trợ xử lý",
            )
        payload_bytes = await read_revision_bytes(blob_store, scope)
        observation.byte_count = len(payload_bytes)
        observation.sha256 = scope.sha256

    if scope.extension in {".docx", ".xlsx"}:
        raise AppException(
            f"Luồng {scope.extension.upper()} đã đổi sang đọc trực tiếp. Hãy tạo lượt bóc tách mới.",
            code="native_version_changed",
            status_code=409,
        )

    with observe_stage(run, "render", logger=logger) as observation:
        rendered = await _render_for_run(
            db, blob_store, run, payload_bytes, scope.extension, config
        )
        observation.item_count = len(rendered.pages)
    await _persist_render(db, blob_store, run, rendered)

    rows = await _sync_pages(db, run, rendered)
    await _ocr_pages(
        db,
        blob_store,
        run,
        actor,
        runtime,
        config,
        rendered,
        rows,
        settings,
        engine,
        pdf=payload_bytes if scope.extension == ".pdf" else rendered.fixed_layout_pdf,
    )
    return await _assemble(db, blob_store, run, runtime, config, rendered)


async def _render_for_run(
    db: AsyncSession,
    blob_store: BlobStore,
    run: OcrProcessingRun,
    payload: bytes,
    extension: str,
    config: ProcessingConfig,
) -> RenderedDocument:
    """Resume DOCX from verified saved bytes, never by reconverting the source."""
    if extension == ".docx" and await _artifact(db, run.id, "render_pdf", 0) is not None:
        _, pdf = await read_artifact_bytes(db, blob_store, run, "render_pdf", 0)
        saved = (run.config or {}).get("render_result") or {}
        renderer = saved.get("renderer") or {
            "name": "legacy-saved",
            "version": None,
            "dpi": config.dpi,
            "converter": "legacy-saved",
            "source_artifact": "render_pdf",
        }
        warnings = tuple(saved.get("warnings", ()))
        if not saved:
            warnings = (*warnings, "legacy_converter_metadata_unavailable")
        return await render_saved_pdf_async(pdf, config, renderer, warnings)
    if extension == ".docx" and config.pin_renderer:
        from qnu.platform.config import get_settings

        if config.renderer_revision != get_settings().DOCX_RENDERER_REVISION:
            raise AppException(
                "Phiên bản bộ chuyển đổi đã thay đổi; cần tạo lượt xử lý mới.",
                code="renderer_version_changed",
                status_code=409,
            )
    return await render_async(payload, extension, config)


async def _persist_render(
    db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun, rendered: RenderedDocument
) -> None:
    if rendered.fixed_layout_pdf is not None:
        await _store_artifact(db, blob_store, run, "render_pdf", 0, rendered.fixed_layout_pdf)
        run.config = {
            **(run.config or {}),
            "render_result": {
                "renderer": rendered.renderer,
                "warnings": list(rendered.warnings),
            },
        }
        # Commit the conversion before page processing so a retry reuses identical bytes.
        await commit_owned(db, run)
    for page in rendered.pages:
        if page.png is not None:
            await _store_artifact(db, blob_store, run, "page_image", page.page_number, page.png)
    await commit_owned(db, run)


def _refresh_page_counters(run: OcrProcessingRun, rows: dict[int, OcrRunPage]) -> None:
    run.pages_done = sum(1 for row in rows.values() if row.status == "completed")
    run.pages_failed = sum(1 for row in rows.values() if row.status == "failed")


async def _sync_pages(
    db: AsyncSession, run: OcrProcessingRun, rendered: RenderedDocument
) -> dict[int, OcrRunPage]:
    existing = {
        row.page_number: row
        for row in (
            await db.execute(select(OcrRunPage).where(OcrRunPage.run_id == run.id))
        ).scalars()
    }
    if existing and len(existing) != len(rendered.pages):
        raise AppException(
            "Số trang render khác lần chạy trước; không thể tiếp tục an toàn.",
            code="render_mismatch",
            status_code=409,
        )
    for page in rendered.pages:
        row = existing.get(page.page_number)
        if row is None:
            row = OcrRunPage(
                id=new_id("opg"),
                run_id=run.id,
                page_number=page.page_number,
                status="pending",
            )
            db.add(row)
            existing[page.page_number] = row
        if row.image_sha256 is not None and row.image_sha256 != page.sha256:
            raise AppException(
                "Ảnh trang đã thay đổi so với lần render trước.",
                code="render_mismatch",
                status_code=409,
            )
        row.image_sha256 = page.sha256
        row.width = page.width
        row.height = page.height
        if page.sha256 is not None:
            row.image_key = artifact_key(run, "page_image", page.page_number, page.sha256)
    run.pages_total = len(rendered.pages)
    _refresh_page_counters(run, existing)
    await commit_owned(db, run)
    return existing


async def _ocr_pages(
    db: AsyncSession,
    blob_store: BlobStore,
    run: OcrProcessingRun,
    actor: AuthActor,
    runtime: OcrRuntime,
    config: ProcessingConfig,
    rendered: RenderedDocument,
    rows: dict[int, OcrRunPage],
    settings,
    engine: OcrEngine,
    *,
    pdf: bytes | None = None,
) -> None:
    if runtime.provider_type == "mineru":
        from qnu.domains.ocr.mineru_execution import ocr_document

        return await ocr_document(db, blob_store, run, actor, runtime, rendered, rows, engine, pdf)
    for page in rendered.pages:
        row = rows[page.page_number]
        if row.status in ("completed", "blank"):
            continue
        if row.status in ("in_flight", "uncertain"):
            continue
        if page.blank:
            row.status = "blank"
            row.text = ""
            row.blocks_count = 0
            row.has_tables = False
            await commit_owned(db, run)
            continue

        with observe_stage(run, "provider_preflight", logger=logger, page_number=page.page_number):
            runtime, budget = await page_request_budget(
                db,
                actor,
                run.workspace_id,
                runtime,
                width=page.width,
                height=page.height,
                prompt=OCR_PROMPT,
                output_tokens=config.max_output_tokens,
            )
        await assert_claim(db, run)

        request_id = f"ocr:{run.id}:{page.page_number}"
        request_hash = hashlib.sha256(
            f"{run.id}|{page.page_number}|{page.sha256}|{runtime.configuration_hash}|{budget.total_reserved_tokens}".encode()
        ).hexdigest()
        try:
            with observe_stage(run, "reserve_usage", logger=logger, page_number=page.page_number):
                usage = await usage_service.reserve(
                    db,
                    actor,
                    run.workspace_id,
                    "ocr",
                    request_id,
                    request_hash,
                    budget.total_reserved_tokens,
                    runtime.provider_id,
                )
        except AppException as exc:
            row.status = "failed"
            row.error_code = exc.code
            _refresh_page_counters(run, rows)
            await commit_owned(db, run)
            raise

        await assert_claim(db, run)
        row.status = "in_flight"
        row.attempts += 1
        await commit_owned(db, run)
        try:
            with observe_stage(
                run, "ocr_page", logger=logger, page_number=page.page_number
            ) as observation:
                call = await engine.extract_page(
                    page.png,
                    OcrRequest(
                        endpoint=runtime.base_url,
                        model=runtime.model_name,
                        prompt=OCR_PROMPT,
                        max_tokens=budget.max_output_tokens,
                        timeout_seconds=float(runtime.timeout_seconds),
                        api_key=runtime.api_key,
                        auth_optional=runtime.auth_optional,
                        execution=ProviderExecution(
                            run.workspace_id,
                            runtime.provider_id,
                            usage.id,
                            sessions=runtime.session_factory,
                        ),
                    ),
                )
                observation.usage_tokens = call.usage_tokens
        except OcrResponseError as exc:
            try:
                await assert_claim(db, run)
            except LeaseLost:
                await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
                raise
            await _save_raw(db, blob_store, run, row, exc.raw_body)
            row.status = "failed"
            row.error_code = exc.code
            _refresh_page_counters(run, rows)
            await commit_owned(db, run)
            await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
            continue
        except AppException as exc:
            row.status = "uncertain" if is_uncertain(exc.code) else "failed"
            row.error_code = exc.code
            _refresh_page_counters(run, rows)
            await commit_owned(db, run)
            await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
            continue

        try:
            await assert_claim(db, run)
        except LeaseLost:
            await usage_service.settle(db, usage.id, total_tokens=call.usage_tokens, failed=True)
            raise
        raw_payload = call.raw_body or json.dumps(
            call.raw, ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        await _save_raw(db, blob_store, run, row, raw_payload)
        try:
            with observe_stage(
                run, "parse_page", logger=logger, page_number=page.page_number
            ) as observation:
                layout = parse_page(call.text, table_layout_version=config.table_layout_version)
                observation.item_count = len(layout.blocks)
        except AppException as exc:
            row.status = "failed"
            row.error_code = exc.code
            _refresh_page_counters(run, rows)
            await commit_owned(db, run)
            await usage_service.settle(db, usage.id, total_tokens=call.usage_tokens, failed=True)
            continue

        await assert_claim(db, run)
        row.text = layout.text
        row.blocks_count = len(layout.blocks)
        row.has_tables = layout.has_tables
        row.status = "completed"
        row.error_code = None
        row.usage_tokens = call.usage_tokens
        _refresh_page_counters(run, rows)
        await commit_owned(db, run)
        await usage_service.settle(db, usage.id, total_tokens=call.usage_tokens)


async def _save_raw(db, blob_store, run, row, payload: bytes) -> None:
    artifact = await _store_artifact(db, blob_store, run, "raw_response", row.page_number, payload)
    row.raw_key = artifact.blob_key
    row.raw_sha256 = artifact.sha256
    await commit_owned(db, run)


async def _assemble(
    db: AsyncSession,
    blob_store: BlobStore,
    run: OcrProcessingRun,
    runtime: OcrRuntime | None,
    config: ProcessingConfig,
    rendered: RenderedDocument,
) -> ExecutionOutcome:
    with observe_stage(run, "assemble", logger=logger) as observation:
        outcome = await _assemble_result(db, blob_store, run, runtime, config, rendered)
        observation.status = outcome.status
        observation.error_code = run.error_code
        observation.item_count = run.pages_total
        return outcome


async def _assemble_result(
    db: AsyncSession,
    blob_store: BlobStore,
    run: OcrProcessingRun,
    runtime: OcrRuntime | None,
    config: ProcessingConfig,
    rendered: RenderedDocument,
) -> ExecutionOutcome:
    rows = {
        row.page_number: row
        for row in (
            await db.execute(select(OcrRunPage).where(OcrRunPage.run_id == run.id))
        ).scalars()
    }
    documents: list[PageDocument] = []
    for page in rendered.pages:
        row = rows[page.page_number]
        layout = None
        native = None
        image_failures: list[dict] = []
        if row.status == "completed" and row.raw_key:
            _, raw = await read_artifact_bytes(
                db, blob_store, run, "raw_response", page.page_number
            )
            payload = json.loads(raw)
            image_failures = normalize_failures(
                payload.get("image_ocr_failures"), page.page_number
            )
            if runtime and runtime.provider_type == "mineru":
                import asyncio

                from qnu.domains.ocr.mineru_layout import parse_mineru_page

                layout = await asyncio.to_thread(parse_mineru_page, payload)
            else:
                layout = parse_page(
                    _raw_text(raw), table_layout_version=config.table_layout_version
                )
        if (run.config or {}).get("extraction"):
            from qnu.domains.ocr.native import merge_layout, page_from_payload

            _, native_bytes = await read_artifact_bytes(
                db, blob_store, run, "native_page", page.page_number
            )
            native = page_from_payload(json.loads(native_bytes))
            if rendered.renderer.get("pagination") in {"document", "sheets", "slides"}:
                from qnu.domains.ocr.direct_docx import merge_docx_layout

                layout = merge_docx_layout(native, layout)
            else:
                layout = merge_layout(native, layout)
            if row.status == "completed":
                row.text = layout.text
                row.blocks_count = len(layout.blocks)
                row.has_tables = layout.has_tables
        documents.append(
            PageDocument(
                page_number=page.page_number,
                status=row.status,
                image_sha256=page.sha256,
                image_width=page.width,
                image_height=page.height,
                ink_ratio=page.ink_ratio,
                layout=layout,
                error_code=row.error_code,
                usage_tokens=row.usage_tokens,
                method=("hybrid" if native.native_text else "ocr")
                if native and native.needs_ocr
                else "native"
                if native
                else None,
                image_ocr_failures=tuple(image_failures),
            )
        )

    identity = {
        "workspace_id": run.workspace_id,
        "collection_id": run.collection_id,
        "source_id": run.source_id,
        "revision_id": run.revision_id,
        "revision_no": run.revision_no,
        "source_sha256": run.source_sha256,
        "run_id": run.id,
        "generation": run.generation,
    }
    processing = {
        "processor_version": config.processor_version,
        "prompt_version": config.prompt_version,
        "table_layout_version": config.table_layout_version,
        "config_fingerprint": run.config_fingerprint,
        "renderer": rendered.renderer,
        "provider": runtime.public_dict() if runtime else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": utcnow().isoformat(),
        "warnings": list(rendered.warnings),
    }
    if run.config.get("extraction"):
        processing["extraction"] = run.config["extraction"]
    if runtime and runtime.provider_type == "mineru":
        from qnu.domains.ocr.mineru_layout import VERSION

        processing.update(
            prompt_version=None, table_layout_version=VERSION, transport="mineru_tasks/v1"
        )
    limits = {
        "max_pages": config.max_pages,
        "dpi": config.dpi,
        "max_output_tokens": config.max_output_tokens,
        "max_page_bytes": config.max_page_bytes,
    }
    canonical = build_canonical(
        identity=identity, processing=processing, rendered=rendered, pages=documents, limits=limits
    )
    report = validate_document(canonical, expected_pages=len(rendered.pages))

    canonical_bytes = (
        json.dumps(canonical, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    canonical_artifact = await _store_artifact(
        db, blob_store, run, "canonical_json", 0, canonical_bytes
    )
    markdown_version = run.config.get("markdown_version", LEGACY_MARKDOWN_VERSION)
    markdown_bytes = render_markdown(
        canonical, legacy=markdown_version == LEGACY_MARKDOWN_VERSION
    ).encode("utf-8")
    markdown_artifact = await _store_artifact(db, blob_store, run, "markdown", 0, markdown_bytes)

    artifacts = [
        {
            "kind": item.kind,
            "page_no": item.page_no,
            "sha256": item.sha256,
            "size_bytes": item.size_bytes,
            "content_type": item.content_type,
            "blob_key": item.blob_key,
        }
        for item in (
            await db.execute(
                select(OcrRunArtifact)
                .where(OcrRunArtifact.run_id == run.id)
                .order_by(OcrRunArtifact.kind, OcrRunArtifact.page_no)
            )
        ).scalars()
    ]
    manifest = build_manifest(
        canonical=canonical,
        artifacts=artifacts,
        validation=report.as_dict(),
        canonical_sha256=canonical_artifact.sha256,
        markdown_sha256=markdown_artifact.sha256,
    )
    await _store_artifact(
        db,
        blob_store,
        run,
        "manifest",
        0,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )

    pages = canonical["pages"]
    run.pages_done = sum(1 for page in pages if page["status"] == "completed")
    run.pages_failed = sum(1 for page in pages if page["status"] == "failed")
    measured = [page["usage_tokens"] for page in pages if page["usage_tokens"] is not None]
    run.usage_tokens = sum(measured) if measured else None
    if run.config.get("extraction") and any(
        page.get("extraction_method") in {"ocr", "hybrid"} and page["usage_tokens"] is None
        for page in pages
    ):
        run.usage_tokens = None
    run.finished_at = utcnow()
    run.lease_expires_at = None

    if any(page["status"] == "uncertain" for page in pages):
        run.status = "uncertain"
        run.error_code = "page_ocr_uncertain"
        run.error_detail = "Có trang chưa xác định được kết quả gọi provider."
    elif report.errors:
        run.status = "failed"
        run.error_code = report.errors[0].code
        run.error_detail = report.errors[0].detail[:500]
    elif canonical.get("image_ocr_failures"):
        run.status = "completed_with_warnings"
        run.error_code = None
        run.error_detail = None
    else:
        run.status = "completed"
        run.error_code = None
        run.error_detail = None
    await commit_owned(db, run)
    logger.info(
        "ocr_run_finished",
        run_id=run.id,
        status=run.status,
        pages_total=run.pages_total,
        pages_done=run.pages_done,
        pages_failed=run.pages_failed,
        tokens=run.usage_tokens,
    )
    return ExecutionOutcome(status=run.status, reason=run.error_code or "done")
