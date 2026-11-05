"""Automatic native-first extraction on the existing durable run/lease/queue contract."""

import json
from dataclasses import replace

import pymupdf

from qnu.domains.knowledge.public_api import (
    WRITE_ROLES,
    read_revision_bytes,
    resolve_revision_scope,
)
from qnu.domains.modelops.public_api import resolve_ocr_runtime
from qnu.domains.modelops.resilience.routing import choose_target
from qnu.domains.ocr.config import DOCX_VERSION, PDF_INSPECTOR_VERSION, ocr_contract_hash
from qnu.domains.ocr.execution import (
    _assemble,
    _ocr_pages,
    _persist_render,
    _render_for_run,
    _store_artifact,
    _sync_pages,
    logger,
)
from qnu.domains.ocr.lease import commit_owned
from qnu.domains.ocr.native import NATIVE_VERSION, extract_native_async, page_payload
from qnu.domains.ocr.telemetry import observe_stage
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import AppException


async def resolve_runtime(db, run):
    requested = run.provider_id or (run.config or {}).get("provider_requested")
    selected, routing = await choose_target(db, run.workspace_id, "ocr", requested)
    runtime = replace(
        await resolve_ocr_runtime(db, run.workspace_id, selected), routing_trace=routing
    )
    pinned = (run.config or {}).get("provider")
    prompt_hash = ocr_contract_hash(runtime.provider_type)
    if run.provider_id is not None and (
        run.provider_id != runtime.provider_id
        or not pinned
        or pinned.get("configuration_hash") != runtime.configuration_hash
        or run.config.get("prompt_sha256") != prompt_hash
    ):
        raise AppException(
            "Provider OCR đã thay đổi so với lúc bắt đầu.", code="provider_changed", status_code=409
        )
    if run.provider_id is None:
        run.provider_id = runtime.provider_id
        run.config = {**run.config, "provider": runtime.public_dict(), "prompt_sha256": prompt_hash}
        await commit_owned(db, run)
    return runtime


async def execute_auto(db, blob, run, actor, engine, config, settings):
    pinned = run.config["extraction"]
    if pinned["version"] != NATIVE_VERSION or pinned["pymupdf"] != pymupdf.version[0]:
        raise AppException(
            "Bộ bóc tách đã thay đổi; cần tạo lượt xử lý mới.",
            code="native_version_changed",
            status_code=409,
        )
    scope = await resolve_revision_scope(
        db, run.workspace_id, run.collection_id, run.source_id, run.revision_id
    )
    if scope.sha256 != run.source_sha256:
        raise AppException(
            "Revision không khớp checksum đã ghim.",
            code="revision_content_mismatch",
            status_code=409,
        )
    payload = await read_revision_bytes(blob, scope)
    direct_word = scope.extension == ".docx"
    inspector = pinned.get("pdf_inspector")
    if direct_word:
        from qnu.domains.ocr.direct_docx import extract_docx_async

        if pinned.get("docx") != DOCX_VERSION:
            raise AppException(
                "Luồng DOCX đã đổi sang đọc trực tiếp. Hãy tạo lượt bóc tách mới.",
                code="native_version_changed",
                status_code=409,
            )
        with observe_stage(run, "read_docx", logger=logger) as observation:
            rendered, plan = await extract_docx_async(payload)
            observation.item_count = len(plan.pages[0].layout.blocks)
    else:
        rendered = await _render_for_run(db, blob, run, payload, scope.extension, config)
        if inspector:
            from qnu.domains.ocr.pdf_inspector import extract_pdf_async

            if inspector != PDF_INSPECTOR_VERSION:
                raise AppException(
                    "Phiên bản PDF Inspector đã thay đổi. Hãy tạo lượt bóc tách mới.",
                    code="native_version_changed",
                    status_code=409,
                )
            with observe_stage(run, "read_pdf", logger=logger) as observation:
                plan = await extract_pdf_async(payload, rendered)
                observation.item_count = len(plan.pages)
        else:
            plan = await extract_native_async(payload, rendered)
    await resolve_workspace_access(db, actor, run.workspace_id, required_roles=WRITE_ROLES)
    await resolve_revision_scope(
        db, run.workspace_id, run.collection_id, run.source_id, run.revision_id
    )
    await _persist_render(db, blob, run, rendered)
    rows = await _sync_pages(db, run, rendered)
    for page in plan.pages:
        native = {
            **page_payload(page, plan.source_artifact),
            "source_sha256": scope.sha256,
            "revision_id": scope.revision_id,
        }
        await _store_artifact(
            db,
            blob,
            run,
            "native_page",
            page.page_number,
            (json.dumps(native, ensure_ascii=False, sort_keys=True) + "\n").encode(),
        )
        for image in page.images:
            if len(image.payload) > config.max_page_bytes:
                raise AppException(
                    "Ảnh nhúng vượt giới hạn bóc tách.",
                    code="embedded_image_too_large",
                    status_code=422,
                )
            await _store_artifact(db, blob, run, "embedded_image", image.asset_no, image.payload)
        row = rows[page.page_number]
        if not page.needs_ocr and row.status == "pending":
            row.status = "blank" if rendered.pages[page.page_number - 1].blank else "completed"
            row.text, row.blocks_count = page.layout.text, len(page.layout.blocks)
            row.has_tables, row.usage_tokens = page.layout.has_tables, 0
    run.pages_done = sum(1 for r in rows.values() if r.status == "completed")
    run.pages_failed = sum(1 for r in rows.values() if r.status == "failed")
    await commit_owned(db, run)
    runtime = None
    if any(p.needs_ocr for p in plan.pages):
        runtime = await resolve_runtime(db, run)
        if direct_word:
            from qnu.domains.ocr.image_ocr import ocr_embedded_images

            await ocr_embedded_images(
                db, blob, run, actor, runtime, plan.pages[0], rows[1], engine, word=True
            )
        elif inspector and runtime.provider_type == "mineru":
            from qnu.domains.ocr.mineru_execution import ocr_pdf_pages

            await ocr_pdf_pages(
                db, blob, run, actor, runtime, rendered, rows, engine, payload, plan
            )
        else:
            await _ocr_pages(
                db,
                blob,
                run,
                actor,
                runtime,
                config,
                rendered,
                rows,
                settings,
                engine,
                pdf=payload,
            )
    await resolve_workspace_access(db, actor, run.workspace_id, required_roles=WRITE_ROLES)
    await resolve_revision_scope(
        db, run.workspace_id, run.collection_id, run.source_id, run.revision_id
    )
    return await _assemble(db, blob, run, runtime, config, rendered)
