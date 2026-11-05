"""Supplement mixed-page pictures through independent, durable MinerU crop tasks."""

import asyncio
import hashlib
import json

from qnu.domains.knowledge.public_api import WRITE_ROLES, resolve_revision_scope
from qnu.domains.modelops.public_api import resolve_ocr_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.ocr.artifacts.render import _render_lock
from qnu.domains.ocr.errors import is_uncertain
from qnu.domains.ocr.image_regions import image_pdf
from qnu.domains.ocr.lease import assert_claim, commit_owned
from qnu.domains.ocr.mineru_layout import VERSION, archive_pages
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import AppException
from qnu.ports.ocr_engine import OcrDocumentRequest
from qnu.ports.provider_execution import ProviderExecution


async def supplement_images(
    db, blob, run, actor, runtime, native, raw, engine, guard, *, direct=False
):
    from qnu.domains.ocr.execution import _artifact, _store_artifact, read_artifact_bytes

    if not native.native_text and not direct:
        return raw  # Scans already use the complete OCR page, not a native/region merge.
    regions = []
    for block in native.layout.blocks:
        if not block.image:
            continue
        asset = block.image["asset_no"]
        await guard()
        _, payload = await read_artifact_bytes(db, blob, run, "embedded_image", asset)
        if hashlib.sha256(payload).hexdigest() != block.image["sha256"]:
            raise AppException(
                "Ảnh nhúng không khớp nguồn.", code="image_source_mismatch", status_code=409
            )
        async with _render_lock:
            pdf, boxes = await asyncio.to_thread(image_pdf, payload)
        record = await _artifact(db, run.id, "provider_document", asset)
        if record:
            _, archive = await read_artifact_bytes(db, blob, run, "provider_document", asset)
        else:
            archive = await _extract_image(db, run, actor, runtime, asset, pdf, engine, guard)
            await guard()
            await _store_artifact(db, blob, run, "provider_document", asset, archive)
            await commit_owned(db, run)
        pages = await asyncio.to_thread(archive_pages, archive, len(boxes))
        for number, box in enumerate(boxes, 1):
            x0, y0, x1, y1 = block.bbox if block.bbox is not None else (0, 0, 1, 1)
            regions.append(
                {
                    "image_asset_no": asset,
                    "image_region": number,
                    "bbox": [
                        x0 + box[0] * (x1 - x0),
                        y0 + box[1] * (y1 - y0),
                        x0 + box[2] * (x1 - x0),
                        y0 + box[3] * (y1 - y0),
                    ],
                    "input_sha256": hashlib.sha256(pdf).hexdigest(),
                    "archive_sha256": hashlib.sha256(archive).hexdigest(),
                    "result": pages[number],
                }
            )
    return {**raw, "image_ocr": regions} if regions else raw


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
        tasks = {**run.config.get("mineru_image_tasks", {}), str(asset): value}
        run.config = {**run.config, "mineru_image_tasks": tasks}
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
