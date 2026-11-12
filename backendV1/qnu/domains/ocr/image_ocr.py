"""Supplement mixed-page pictures through independent, durable MinerU crop tasks."""

import asyncio
import hashlib
import json
from dataclasses import dataclass

from qnu.domains.knowledge.public_api import WRITE_ROLES, resolve_revision_scope
from qnu.domains.modelops.public_api import resolve_ocr_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.ocr.artifacts.render import _render_lock
from qnu.domains.ocr.errors import is_uncertain
from qnu.domains.ocr.image_regions import image_pdf
from qnu.domains.ocr.lease import assert_claim, commit_owned
from qnu.domains.ocr.mineru_layout import VERSION, archive_pages
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.warnings import LOCAL_IMAGE_FAILURE_CODES, failure_record
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException, EntityNotFound
from qnu.ports.ocr_engine import OcrDocumentRequest
from qnu.ports.provider_execution import ProviderExecution


def _render_image(payload: bytes):
    try:
        return image_pdf(payload)
    except AppException:
        raise
    except Exception as exc:
        raise AppException(
            "Ảnh nhúng không giải mã được để OCR.",
            code="embedded_image_decode_failed",
            status_code=422,
            title="Ảnh nhúng không dùng được",
        ) from exc


def execution_guard(db, actor, run, runtime):
    async def guard():
        await assert_claim(db, run)
        await resolve_workspace_access(db, actor, run.workspace_id, required_roles=WRITE_ROLES)
        scope = await resolve_revision_scope(
            db, run.workspace_id, run.collection_id, run.source_id, run.revision_id
        )
        current = await resolve_ocr_runtime(db, run.workspace_id, runtime.provider_id)
        if (
            scope.sha256 != run.source_sha256
            or current.configuration_hash != runtime.configuration_hash
        ):
            raise AppException(
                "Nguồn hoặc provider đã thay đổi.",
                code="provider_changed",
                status_code=409,
            )
        await db.commit()

    return guard


async def _remember_alias(db, run, image_sha: str, asset: int) -> None:
    # Another task session may have written config since this one loaded it.
    await assert_claim(db, run)
    await db.refresh(run, ["config"])
    config = dict(run.config or {})
    aliases = dict(config.get("mineru_image_aliases") or {})
    if aliases.get(image_sha) is None:
        aliases[image_sha] = asset
        config["mineru_image_aliases"] = aliases
        run.config = config
    await commit_owned(db, run)


@dataclass
class _ImagePrep:
    block: object
    asset: int
    sha256: str
    pdf: bytes
    boxes: list
    archive: bytes | None = None
    leader: int | None = None


async def supplement_images(
    db, blob, run, actor, runtime, native, raw, engine, guard, *, direct=False
):
    from qnu.domains.ocr.execution import _artifact, _store_artifact, read_artifact_bytes

    if not native.native_text and not direct:
        return raw  # Scans already use the complete OCR page, not a native/region merge.
    image_blocks = [block for block in native.layout.blocks if block.image]
    if not image_blocks:
        return raw
    # A local image failure is only a warning while the same page keeps native text.
    has_supplemental_text = any(
        block.text.strip() for block in native.layout.blocks if block.image is None
    )
    await assert_claim(db, run)
    await db.refresh(run, ["config"])
    await db.commit()

    preps: list[_ImagePrep] = []
    pending: dict[str, tuple[int, bytes]] = {}
    for block in image_blocks:
        asset = block.image["asset_no"]
        await guard()
        _, payload = await read_artifact_bytes(db, blob, run, "embedded_image", asset)
        if hashlib.sha256(payload).hexdigest() != block.image["sha256"]:
            raise AppException(
                "Ảnh nhúng không khớp nguồn.", code="image_source_mismatch", status_code=409
            )
        async with _render_lock:
            pdf, boxes = await asyncio.to_thread(_render_image, payload)
        image_sha = block.image["sha256"]
        prep = _ImagePrep(block=block, asset=asset, sha256=image_sha, pdf=pdf, boxes=boxes)
        if await _artifact(db, run.id, "provider_document", asset) is not None:
            _, prep.archive = await read_artifact_bytes(
                db, blob, run, "provider_document", asset
            )
        else:
            source_asset = (run.config or {}).get("mineru_image_aliases", {}).get(image_sha)
            if (
                source_asset is not None
                and source_asset != asset
                and await _artifact(db, run.id, "provider_document", source_asset) is not None
            ):
                _, prep.archive = await read_artifact_bytes(
                    db, blob, run, "provider_document", source_asset
                )
                await guard()
                await _store_artifact(db, blob, run, "provider_document", asset, prep.archive)
                await commit_owned(db, run)
            elif image_sha in pending:
                prep.leader = pending[image_sha][0]
            else:
                pending[image_sha] = (asset, pdf)
        preps.append(prep)

    results: dict[str, object] = {}
    if pending:
        semaphore = asyncio.Semaphore(max(1, get_settings().OCR_IMAGE_CONCURRENCY))
        stop = asyncio.Event()

        async def run_pending(image_sha: str, asset: int, pdf: bytes) -> None:
            await semaphore.acquire()
            try:
                if stop.is_set():
                    return
                async with AsyncSessionFactory() as task_db:
                    task_run = await task_db.get(OcrProcessingRun, run.id)
                    if task_run is None:
                        raise EntityNotFound(
                            "Không tìm thấy lượt xử lý.", code="processing_run_not_found"
                        )
                    task_guard = execution_guard(task_db, actor, task_run, runtime)
                    archive = await _extract_image(
                        task_db, task_run, actor, runtime, asset, pdf, engine, task_guard
                    )
                    await task_guard()
                    await _store_artifact(
                        task_db, blob, task_run, "provider_document", asset, archive
                    )
                    await commit_owned(task_db, task_run)
                    await _remember_alias(task_db, task_run, image_sha, asset)
                results[image_sha] = archive
            except AppException as exc:
                results[image_sha] = exc
                if exc.code not in LOCAL_IMAGE_FAILURE_CODES or not has_supplemental_text:
                    stop.set()
            except Exception as exc:
                results[image_sha] = exc
                stop.set()
            finally:
                semaphore.release()

        tasks = [
            asyncio.create_task(run_pending(image_sha, asset, pdf))
            for image_sha, (asset, pdf) in pending.items()
        ]
        try:
            await asyncio.gather(*tasks)
        finally:
            # Never cancel an upload already in flight; its checkpoint is the evidence.
            await asyncio.gather(*tasks, return_exceptions=True)

    regions: list[dict] = []
    failures: list[dict] = []
    fatal: BaseException | None = None
    for prep in preps:
        archive = prep.archive
        if archive is None:
            outcome = results.get(prep.sha256)
            if isinstance(outcome, AppException):
                if outcome.code not in LOCAL_IMAGE_FAILURE_CODES or not has_supplemental_text:
                    fatal = fatal or outcome
                    continue
                failures.append(
                    failure_record(
                        prep.asset, native.page_number, prep.block.bbox, outcome.code, 1
                    )
                )
                await guard()
                continue
            if isinstance(outcome, BaseException):
                fatal = fatal or outcome
                continue
            if outcome is None:
                continue  # A fatal outcome elsewhere already stopped this page.
            archive = outcome
            if prep.leader is not None and (
                await _artifact(db, run.id, "provider_document", prep.asset) is None
            ):
                await guard()
                await _store_artifact(db, blob, run, "provider_document", prep.asset, archive)
                await commit_owned(db, run)
        pages = await asyncio.to_thread(archive_pages, archive, len(prep.boxes))
        for number, box in enumerate(prep.boxes, 1):
            x0, y0, x1, y1 = prep.block.bbox if prep.block.bbox is not None else (0, 0, 1, 1)
            regions.append(
                {
                    "image_asset_no": prep.asset,
                    "image_region": number,
                    "bbox": [
                        x0 + box[0] * (x1 - x0),
                        y0 + box[1] * (y1 - y0),
                        x0 + box[2] * (x1 - x0),
                        y0 + box[3] * (y1 - y0),
                    ],
                    "input_sha256": hashlib.sha256(prep.pdf).hexdigest(),
                    "archive_sha256": hashlib.sha256(archive).hexdigest(),
                    "result": pages[number],
                }
            )
    if fatal is not None:
        raise fatal
    result = dict(raw)
    if regions:
        result["image_ocr"] = regions
    if failures:
        result["image_ocr_failures"] = failures
    return result


async def ocr_embedded_images(db, blob, run, actor, runtime, native, row, engine, *, word=False):
    from qnu.domains.ocr.execution import _save_raw

    if row.status == "completed":
        return
    if runtime.provider_type != "mineru":
        raise AppException(
            "OCR ảnh nhúng trong tài liệu cần provider MinerU.",
            code="docx_image_ocr_unsupported",
            status_code=422,
        )

    guard = execution_guard(db, actor, run, runtime)
    if row.status != "pending":
        raise AppException(
            "Chưa xác định kết quả OCR ảnh nhúng.",
            code="ocr_provider_timeout",
            status_code=504,
        )
    await guard()
    row.status = "in_flight"
    row.attempts += 1
    await commit_owned(db, run)
    try:
        raw = await supplement_images(
            db,
            blob,
            run,
            actor,
            runtime,
            native,
            {"format": VERSION, "page": {"blocks": []}},
            engine,
            guard,
            direct=word,
        )
        await guard()
        await _save_raw(
            db, blob, run, row, json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()
        )
    except AppException as exc:
        await assert_claim(db, run)
        row.status = "uncertain" if is_uncertain(exc.code) else "failed"
        row.error_code = exc.code
        await commit_owned(db, run)
        raise
    row.status = "completed"
    await commit_owned(db, run)


async def _extract_image(db, run, actor, runtime, asset, pdf, engine, guard):
    state = run.config.get("mineru_image_tasks", {}).get(str(asset), {})

    async def save(value):
        await guard()
        # This session may be one of several concurrent image tasks; re-read the
        # config under the row lock so a checkpoint never erases a sibling's write.
        await assert_claim(db, run)
        await db.refresh(run, ["config"])
        tasks = {**(run.config or {}).get("mineru_image_tasks", {}), str(asset): value}
        run.config = {**(run.config or {}), "mineru_image_tasks": tasks}
        await commit_owned(db, run)

    usage = await usage_service.reserve(
        db,
        actor,
        run.workspace_id,
        "ocr",
        f"ocr:{run.id}:image:{asset}",
        hashlib.sha256(
            f"{run.id}|{asset}|{hashlib.sha256(pdf).hexdigest()}|{runtime.configuration_hash}|ocr".encode()
        ).hexdigest(),
        0,
        runtime.provider_id,
        document_ocr=True,
    )
    try:
        call = await engine.extract_document(
            pdf,
            OcrDocumentRequest(
                endpoint=runtime.base_url,
                model=runtime.model_name,
                timeout_seconds=runtime.timeout_seconds,
                api_key=runtime.api_key,
                auth_optional=runtime.auth_optional,
                wait_for_completion=runtime.wait_for_completion,
                ocr_mode="ocr",
                execution=ProviderExecution(
                    run.workspace_id,
                    runtime.provider_id,
                    usage.id,
                    sessions=runtime.session_factory,
                ),
            ),
            checkpoint=state,
            save=save,
            guard=guard,
        )
        await guard()
    except AppException:
        await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
        raise
    await usage_service.settle(db, usage.id, total_tokens=call.usage_tokens)
    return call.archive
