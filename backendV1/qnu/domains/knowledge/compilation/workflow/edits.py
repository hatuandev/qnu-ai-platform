"""Preview accepted text edits, append a new draft and schedule its own review."""

import hashlib
import json
from datetime import timedelta

from sqlalchemy import func, select

from qnu.domains.knowledge.compilation import artifacts
from qnu.domains.knowledge.compilation.drafting import build_draft, markdown_for
from qnu.domains.knowledge.compilation.evidence import load_bound_documents
from qnu.domains.knowledge.compilation.models import CompilationInput, CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review import service as review_service
from qnu.domains.knowledge.compilation.schemas import DraftContent
from qnu.domains.knowledge.compilation.service import authorize_collection, get_run
from qnu.domains.knowledge.compilation.workflow import automatic
from qnu.domains.knowledge.compilation.workflow.models import EditPreview
from qnu.domains.knowledge.publication.evidence import digest, load_bundle
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict, EntityNotFound


def editable(content):
    return DraftContent.model_validate(
        {k: content[k] for k in ("title", "sections", "unknowns")}
    ).model_dump()


async def child_count(db, run_id):
    return int(
        await db.scalar(
            select(func.count())
            .select_from(CompilationRun)
            .where(CompilationRun.parent_run_id == run_id)
        )
        or 0
    )


async def context(db, blob, actor, workspace_id, collection_id, run_id):
    await authorize_collection(db, actor, workspace_id, collection_id, write=True)
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    bundle = await load_bundle(db, blob, workspace_id, collection_id, run_id, require_current=True)
    return {
        "compilation_run_id": run.id,
        "bundle_sha256": bundle.bundle_sha256,
        "edit_count": await child_count(db, run_id),
        "content": editable(bundle.content),
        "citations": bundle.content["citations"],
        "source_tables": bundle.content["source_tables"],
        "sources": bundle.content["sources"],
    }


async def checked_review(db, blob, actor, run, review_id):
    if review_id is None:
        return None
    row, _ = await review_service.read_output(
        db, blob, actor, run.workspace_id, run.collection_id, run.id, review_id, "report_json"
    )
    return row.sha256


def preview_identity(row):
    return {
        "id": row.id,
        "run_id": row.compilation_run_id,
        "actor": row.created_by,
        "bundle_sha256": row.bundle_sha256,
        "edit_count": row.expected_edit_count,
        "content": row.content,
        "reason": row.reason,
        "review_id": row.review_id,
        "report_sha256": row.report_sha256,
        "expires_at": row.expires_at.isoformat(),
    }


async def preview(db, blob, actor, workspace_id, collection_id, run_id, req):
    await authorize_collection(db, actor, workspace_id, collection_id, write=True, lock=True)
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    bundle = await load_bundle(db, blob, workspace_id, collection_id, run_id, require_current=True)
    if bundle.bundle_sha256 != req.expected_bundle_sha256:
        raise Conflict("Bản biên soạn đã thay đổi.", code="compilation_edit_stale")
    content = req.content.model_dump()
    if not req.reason.strip():
        raise Conflict("Cần nội dung thay đổi và lý do lưu.", code="compilation_edit_empty")
    bindings = list(
        (await db.scalars(select(CompilationInput).where(CompilationInput.run_id == run_id))).all()
    )
    documents = await load_bound_documents(db, blob, workspace_id, collection_id, bindings)
    try:
        content = editable(
            build_draft(json.dumps(content, ensure_ascii=False), run.topic, documents, run.id)
        )
    except AppException as exc:
        raise AppException(
            "Bản sửa cần có nội dung và citation thuộc nguồn đã ghim.",
            code="compilation_edit_invalid",
            status_code=422,
        ) from exc
    if content == editable(bundle.content):
        raise Conflict("Cần nội dung thay đổi và lý do lưu.", code="compilation_edit_empty")
    report_sha = await checked_review(db, blob, actor, run, req.review_id)
    row = EditPreview(
        id=new_id("ced"),
        compilation_run_id=run_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        created_by=actor_ref(actor),
        bundle_sha256=bundle.bundle_sha256,
        expected_edit_count=await child_count(db, run_id),
        content=content,
        reason=req.reason.strip(),
        review_id=req.review_id,
        report_sha256=report_sha,
        expires_at=utcnow() + timedelta(seconds=get_settings().PUBLICATION_PREVIEW_TTL_SECONDS),
    )
    row.preview_sha256 = digest(preview_identity(row))
    db.add(row)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="compilation.edit_previewed",
        detail={"preview_id": row.id, "run_id": run_id, "preview_sha256": row.preview_sha256},
    )
    await db.commit()
    return {
        "preview_id": row.id,
        "preview_sha256": row.preview_sha256,
        "expires_at": row.expires_at,
        "before": editable(bundle.content),
        "after": row.content,
        "reason": row.reason,
        "source_tables": bundle.content["source_tables"],
        "review_id": row.review_id,
        "report_sha256": row.report_sha256,
    }


async def accept(db, blob, actor, workspace_id, collection_id, run_id, req, key, queue):
    await authorize_collection(db, actor, workspace_id, collection_id, write=True, lock=True)
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    await db.refresh(run, with_for_update=True)
    ledger_key = "edit:" + hashlib.sha256(key.encode()).hexdigest()
    request_hash = digest({"run_id": run_id, "collection_id": collection_id, **req.model_dump()})
    previous = await db.scalar(
        select(CompilationRun).where(
            CompilationRun.workspace_id == workspace_id,
            CompilationRun.requested_by == actor_ref(actor),
            CompilationRun.idempotency_key == ledger_key,
        )
    )
    if previous is not None:
        if previous.request_hash != request_hash:
            raise Conflict("Khóa lưu đã dùng cho bản sửa khác.", code="idempotency_conflict")
        await db.commit()
        await automatic.dispatch(db, previous.id, queue)
        return previous, False
    row = await db.scalar(
        select(EditPreview)
        .where(
            EditPreview.id == req.preview_id,
            EditPreview.compilation_run_id == run_id,
            EditPreview.workspace_id == workspace_id,
            EditPreview.collection_id == collection_id,
            EditPreview.created_by == actor_ref(actor),
        )
        .with_for_update()
    )
    if row is None:
        raise EntityNotFound(
            "Không tìm thấy bản xem trước của bạn.", code="compilation_edit_not_found"
        )
    if (
        row.preview_sha256 != req.preview_sha256
        or digest(preview_identity(row)) != row.preview_sha256
    ):
        raise Conflict("Bản xem trước không khớp.", code="compilation_edit_preview_changed")
    if (
        row.child_run_id
        or row.expires_at <= utcnow()
        or row.expected_edit_count != await child_count(db, run_id)
    ):
        raise Conflict(
            "Bản xem trước đã hết hạn hoặc đã có bản sửa mới.", code="compilation_edit_stale"
        )
    bundle = await load_bundle(db, blob, workspace_id, collection_id, run_id, require_current=True)
    if row.bundle_sha256 != bundle.bundle_sha256:
        raise Conflict("Bản gốc đã thay đổi.", code="compilation_edit_stale")
    if row.report_sha256 != await checked_review(db, blob, actor, run, row.review_id):
        raise Conflict("Báo cáo review đã thay đổi.", code="compilation_edit_stale")
    bindings = list(
        (await db.scalars(select(CompilationInput).where(CompilationInput.run_id == run_id))).all()
    )
    documents = await load_bound_documents(db, blob, workspace_id, collection_id, bindings)
    generation = 1 + int(
        await db.scalar(
            select(func.max(CompilationRun.generation)).where(
                CompilationRun.collection_id == collection_id
            )
        )
        or 0
    )
    child = CompilationRun(
        id=new_id("cmp"),
        parent_run_id=run.id,
        origin="user_edit",
        workspace_id=workspace_id,
        collection_id=collection_id,
        generation=generation,
        topic=run.topic,
        status="completed",
        requested_by=actor_ref(actor),
        idempotency_key=ledger_key,
        request_hash=request_hash,
        input_sha256=run.input_sha256,
        provider_id=run.provider_id,
        finished_at=utcnow(),
        attempt_count=0,
        config={
            **run.config,
            "auto_review": True,
            "review": run.config.get(
                "review", {"provider_id": run.provider_id}
            ),
            "workflow_version": "qnu.compiler.workflow/v1",
            "edit": {
                "preview_id": row.id,
                "preview_sha256": row.preview_sha256,
                "parent_bundle_sha256": bundle.bundle_sha256,
                "reason": row.reason,
                "accepted_by": actor_ref(actor),
                "review_id": row.review_id,
                "report_sha256": row.report_sha256,
            },
        },
    )
    db.add(child)
    await db.flush()
    for b in bindings:
        db.add(
            CompilationInput(
                id=new_id("cin"),
                run_id=child.id,
                workspace_id=workspace_id,
                collection_id=collection_id,
                ocr_run_id=b.ocr_run_id,
                canonical_sha256=b.canonical_sha256,
                manifest_sha256=b.manifest_sha256,
                text_version_id=b.text_version_id,
                original_canonical_sha256=b.original_canonical_sha256,
            )
        )
    _, snapshot = await artifacts.read(db, blob, run, "input_snapshot")
    draft = build_draft(json.dumps(row.content, ensure_ascii=False), run.topic, documents, child.id)
    draft["origin"], draft["parent_run_id"] = "user_edit", run.id
    await artifacts.store(db, blob, child, "input_snapshot", snapshot)
    await artifacts.store(db, blob, child, "draft_json", artifacts.json_bytes(draft))
    await artifacts.store(db, blob, child, "markdown", markdown_for(draft).encode("utf-8"))
    for kind in ("input_snapshot", "draft_json", "markdown"):
        await artifacts.read(db, blob, child, kind)
    row.child_run_id = child.id
    await automatic.schedule(db, child)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="compilation.edit_accepted",
        detail={
            "run_id": child.id,
            "parent_run_id": run.id,
            "preview_id": row.id,
            "preview_sha256": row.preview_sha256,
        },
    )
    await db.commit()
    await automatic.dispatch(db, child.id, queue)
    return child, True
