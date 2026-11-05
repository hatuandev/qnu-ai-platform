"""Whole-PDF OCR on the existing authorized run, lease, artifacts and usage ledger."""

import asyncio
import hashlib
import json

from qnu.domains.knowledge.public_api import WRITE_ROLES, resolve_revision_scope
from qnu.domains.modelops.public_api import resolve_ocr_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.ocr.errors import is_uncertain
from qnu.domains.ocr.lease import assert_claim, commit_owned
from qnu.domains.ocr.mineru_layout import VERSION, archive_pages, parse_mineru_page
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import AppException
from qnu.ports.ocr_engine import OcrDocumentRequest
from qnu.ports.provider_execution import ProviderExecution


def _subset_pdf(payload, selected):
    import pymupdf

    with pymupdf.open(stream=payload, filetype="pdf") as document:
        document.select([number - 1 for number in selected])
        return document.tobytes(no_new_id=True, garbage=4)


async def ocr_pdf_pages(db, blob, run, actor, runtime, rendered, rows, engine, payload, plan):
    from qnu.domains.ocr.artifacts.render import _render_lock
    from qnu.domains.ocr.image_ocr import ocr_embedded_images

    selected = tuple(p.page_number for p in plan.pages if p.needs_ocr and not p.native_text)
    if selected:
        transport = payload
        if len(selected) != len(plan.pages):
            async with _render_lock:
                transport = await asyncio.to_thread(_subset_pdf, payload, selected)
        await ocr_document(
            db,
            blob,
            run,
            actor,
            runtime,
            rendered,
            rows,
            engine,
            transport,
            selected_pages=selected,
        )
    for page in plan.pages:
        if page.needs_ocr and page.native_text:
            await ocr_embedded_images(
                db, blob, run, actor, runtime, page, rows[page.page_number], engine
            )


async def ocr_document(
    db, blob, run, actor, runtime, rendered, rows, engine, pdf, *, selected_pages=None
):
    from qnu.domains.ocr.execution import (
        _artifact,
        _refresh_page_counters,
        _save_raw,
        _store_artifact,
        read_artifact_bytes,
    )

    page_map = (
        selected_pages
        if selected_pages is not None
        else tuple(p.page_number for p in rendered.pages)
    )
    pending = [
        rows[number] for number in page_map if rows[number].status not in {"completed", "blank"}
    ]
    if not pending:
        return
    if not pdf:
        raise AppException(
            "Thiếu PDF cố định cho MinerU.", code="mineru_pdf_required", status_code=422
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
                "Nguồn hoặc provider đã thay đổi.", code="provider_changed", status_code=409
            )
        await db.commit()

    async def save(state):
        await guard()
        run.config = {**run.config, "mineru_task": state}
        await commit_owned(db, run)

    await guard()
    source_hash = run.source_sha256
    if selected_pages is not None:
        source_hash = hashlib.sha256(pdf).hexdigest() + ":" + ",".join(map(str, page_map))
    usage = await usage_service.reserve(
        db,
        actor,
        run.workspace_id,
        "ocr",
        f"ocr:{run.id}:document",
        hashlib.sha256(
            f"{run.id}|{source_hash}|{runtime.configuration_hash}|{VERSION}".encode()
        ).hexdigest(),
        0,
        runtime.provider_id,
        document_ocr=True,
    )
    state = run.config.get("mineru_task", {})
    archive_record = await _artifact(db, run.id, "provider_document", 0)
    if not state and archive_record is None and any(r.status != "pending" for r in pending):
        raise AppException(
            "Lượt OCR chưa xác định; không gửi lại PDF.",
            code="ocr_provider_timeout",
            status_code=504,
        )
    for row in pending:
        row.status, row.error_code = "in_flight", None
        if not state and archive_record is None:
            row.attempts += 1
    await commit_owned(db, run)
    try:
        if archive_record:
            _, archive = await read_artifact_bytes(db, blob, run, "provider_document", 0)
        else:
            call = await engine.extract_document(
                pdf,
                OcrDocumentRequest(
                    endpoint=runtime.base_url,
                    model=runtime.model_name,
                    timeout_seconds=runtime.timeout_seconds,
                    api_key=runtime.api_key,
                    auth_optional=runtime.auth_optional,
                    wait_for_completion=runtime.wait_for_completion,
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
            archive = call.archive
            await _store_artifact(db, blob, run, "provider_document", 0, archive)
            await commit_owned(db, run)
        pages = await asyncio.to_thread(archive_pages, archive, len(page_map))
        archive_hash = hashlib.sha256(archive).hexdigest()
        source_to_transport = {number: index for index, number in enumerate(page_map, 1)}
        for page in rendered.pages:
            row = rows[page.page_number]
            if row not in pending:
                continue
            raw = {**pages[source_to_transport[page.page_number]], "archive_sha256": archive_hash}
            if selected_pages is not None:
                raw.update(
                    source_page=page.page_number,
                    transport_page=source_to_transport[page.page_number],
                )
            elif run.config.get("extraction"):
                from qnu.domains.ocr.image_ocr import supplement_images
                from qnu.domains.ocr.native import page_from_payload

                _, native_bytes = await read_artifact_bytes(
                    db, blob, run, "native_page", page.page_number
                )
                raw = await supplement_images(
                    db,
                    blob,
                    run,
                    actor,
                    runtime,
                    page_from_payload(json.loads(native_bytes)),
                    raw,
                    engine,
                    guard,
                )
            await _save_raw(
                db, blob, run, row, json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()
            )
            layout = await asyncio.to_thread(parse_mineru_page, raw)
            if not layout.blocks and not page.blank:
                raise AppException(
                    "MinerU bỏ trống trang có nội dung.", code="mineru_page_empty", status_code=502
                )
            row.text, row.blocks_count, row.has_tables = (
                layout.text,
                len(layout.blocks),
                layout.has_tables,
            )
            row.status, row.error_code, row.usage_tokens = (
                ("blank" if page.blank else "completed"),
                None,
                None,
            )
            _refresh_page_counters(run, rows)
            await commit_owned(db, run)
        await guard()
    except AppException as exc:
        await assert_claim(db, run)
        for row in pending:
            if row.status == "in_flight":
                row.status = "uncertain" if is_uncertain(exc.code) else "failed"
                row.error_code = exc.code
        _refresh_page_counters(run, rows)
        await commit_owned(db, run)
        await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
        raise
    await usage_service.settle(db, usage.id, total_tokens=None)
