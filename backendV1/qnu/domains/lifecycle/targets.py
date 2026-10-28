"""Resolve lifecycle targets after workspace authorization; preview only IDs and counts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.conversations.models import Conversation, ConversationTurn
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import CompilationInput
from qnu.domains.knowledge.index.models import IndexInput, IndexRun
from qnu.domains.knowledge.models import KBCollection, KBFolder, KBSource
from qnu.domains.knowledge.publication.models import CompiledDocument, CompiledVersion
from qnu.domains.lifecycle.models import ResourceState
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.operations.jobs.catalog import SPECS, load_job
from qnu.domains.workspaces.access import actor_ref
from qnu.platform.database import Base
from qnu.platform.errors import Conflict, EntityNotFound

MODELS = {
    "collection": KBCollection,
    "folder": KBFolder,
    "source": KBSource,
    "document": CompiledDocument,
    "assistant": Assistant,
    "conversation": Conversation,
    "index": IndexRun,
}


async def target(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    kind: str,
    resource_id: str,
    parameters: dict,
) -> Base:
    if kind == "job":
        job_kind = parameters.get("job_kind")
        if job_kind not in SPECS or job_kind == "backup":
            raise Conflict("Cần loại tác vụ hợp lệ.", code="lifecycle_job_kind_required")
        row = await load_job(db, workspace_id, job_kind, resource_id, lock=True)
        if job_kind == "turn":
            conversation = await db.get(Conversation, row.conversation_id)
            if conversation.owner_ref != actor_ref(actor):
                raise EntityNotFound(
                    "Không tìm thấy lượt hỏi của bạn.", code="lifecycle_target_not_found"
                )
        return row
    model = MODELS[kind]
    row = await db.scalar(
        select(model)
        .where(model.id == resource_id, model.workspace_id == workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None or (kind == "conversation" and row.owner_ref != actor_ref(actor)):
        raise EntityNotFound("Không tìm thấy tài nguyên.", code="lifecycle_target_not_found")
    return row


async def state(
    db: AsyncSession, workspace_id: str, kind: str, resource_id: str
) -> ResourceState | None:
    return await db.get(ResourceState, (workspace_id, kind, resource_id), populate_existing=True)


async def related_jobs(
    db: AsyncSession, workspace_id: str, kind: str, row: Base
) -> list[tuple[str, Base]]:
    """No user questions or conversation IDs from other owners appear in previews."""
    source_ids, compilation_ids = [], []
    if kind == "source":
        source_ids = [row.id]
        compilation_ids = list(
            (
                await db.scalars(
                    select(CompilationInput.run_id)
                    .join(OcrProcessingRun, OcrProcessingRun.id == CompilationInput.ocr_run_id)
                    .where(OcrProcessingRun.source_id == row.id)
                )
            ).all()
        )
    elif kind == "document":
        compilation_ids = list(
            (
                await db.scalars(
                    select(CompiledVersion.compilation_run_id).where(
                        CompiledVersion.document_id == row.id
                    )
                )
            ).all()
        )
    elif kind in {"assistant", "conversation"}:
        ids = select(Conversation.id).where(Conversation.workspace_id == workspace_id)
        ids = (
            ids.where(Conversation.assistant_id == row.id)
            if kind == "assistant"
            else ids.where(Conversation.id == row.id)
        )
        return [
            ("turn", t)
            for t in (
                await db.scalars(
                    select(ConversationTurn)
                    .where(
                        ConversationTurn.conversation_id.in_(ids),
                        ConversationTurn.status == "running",
                    )
                    .with_for_update()
                )
            ).all()
        ]
    jobs = []
    for name, spec in SPECS.items():
        if name in {"backup", "turn"}:
            continue
        model = spec.model
        stmt = select(model).where(
            model.workspace_id == workspace_id, model.status.in_(("queued", "running"))
        )
        if kind == "collection":
            stmt = stmt.where(model.collection_id == row.id)
        elif kind in {"source", "document"}:
            if name in {"ocr", "spelling"} and source_ids:
                if name == "ocr":
                    stmt = stmt.where(model.source_id.in_(source_ids))
                else:
                    stmt = stmt.where(
                        model.run_id.in_(
                            select(OcrProcessingRun.id).where(
                                OcrProcessingRun.source_id.in_(source_ids)
                            )
                        )
                    )
            elif name == "compiler":
                stmt = stmt.where(model.id.in_(compilation_ids))
            elif name in {"auto_review", "review"}:
                stmt = stmt.where(model.compilation_run_id.in_(compilation_ids))
            elif name == "index":
                stmt = stmt.where(model.collection_id == row.collection_id)
            else:
                continue
        else:
            continue
        jobs.extend((name, job) for job in (await db.scalars(stmt.with_for_update())).all())
    return jobs


async def snapshot(
    db: AsyncSession, workspace_id: str, kind: str, row: Base, parameters: dict
) -> tuple[dict, dict]:
    resource_id = (
        row.compilation_run_id
        if kind == "job" and parameters.get("job_kind") == "auto_review"
        else row.id
    )
    lifecycle = await state(db, workspace_id, kind, resource_id)
    impact = {
        "resource_status": lifecycle.status
        if lifecycle
        else (row.status if kind == "conversation" else "active"),
        "originals_and_raw_evidence": "retained",
        "related_history": "retained",
    }
    fields = (
        "status",
        "revision",
        "latest_revision_no",
        "serving_revision_no",
        "change_sequence",
        "last_turn_no",
        "is_active",
        "config",
        "input_sha256",
        "worker_id",
        "pending_batch",
        "request_started_at",
    )
    current = {key: getattr(row, key, None) for key in fields}
    current = {
        key: value.isoformat() if hasattr(value, "isoformat") else value
        for key, value in current.items()
    }
    current["lifecycle"] = (lifecycle.status, lifecycle.revision) if lifecycle else None
    if kind in {"source", "collection", "document", "assistant", "conversation"}:
        jobs = await related_jobs(db, workspace_id, kind, row)
        current["jobs"] = sorted(
            (name, getattr(job, SPECS[name].id_field), job.status) for name, job in jobs
        )
        impact["jobs_to_cancel"] = len(jobs)
    if kind in {"source", "collection", "document"}:
        versions = select(CompiledVersion).where(CompiledVersion.workspace_id == workspace_id)
        if kind == "source":
            inputs = (
                select(CompilationInput.run_id)
                .join(OcrProcessingRun, OcrProcessingRun.id == CompilationInput.ocr_run_id)
                .where(OcrProcessingRun.source_id == row.id)
            )
            versions = versions.where(CompiledVersion.compilation_run_id.in_(inputs))
        elif kind == "document":
            versions = versions.where(CompiledVersion.document_id == row.id)
        else:
            versions = versions.where(CompiledVersion.collection_id == row.id)
        rows = (await db.scalars(versions)).all()
        current["versions"] = sorted((v.id, v.state_version, v.status) for v in rows)
        impact["published_versions_affected"] = sum(v.status == "published" for v in rows)
        active_versions = set(
            (
                await db.scalars(
                    select(IndexInput.version_id)
                    .join(IndexRun, IndexRun.id == IndexInput.run_id)
                    .where(
                        IndexRun.collection_id
                        == (row.id if kind == "collection" else row.collection_id),
                        IndexRun.is_active.is_(True),
                    )
                )
            ).all()
        )
        required_versions = {v.id for v in rows if v.status == "published"}
        impact["restore_requires_new_index"] = not required_versions.issubset(active_versions)
        if kind == "source":
            impact["revision_count"] = row.latest_revision_no
        elif kind == "collection":
            impact["source_count"] = len(
                (
                    await db.scalars(select(KBSource.id).where(KBSource.collection_id == row.id))
                ).all()
            )
    if kind == "index":
        impact.update(
            {
                "generation": row.generation,
                "chunks": row.chunks_total,
                "vector_collection": row.vector_collection,
                "active": row.is_active,
            }
        )
    if kind in {"collection", "source", "document", "assistant"}:
        collection_id = row.id if kind == "collection" else row.collection_id
        assistants = select(Assistant.id).where(
            Assistant.workspace_id == workspace_id, Assistant.collection_id == collection_id
        )
        if kind == "assistant":
            assistants = assistants.where(Assistant.id == row.id)
        assistant_ids = list((await db.scalars(assistants.order_by(Assistant.id))).all())
        conversation_ids = list(
            (
                await db.scalars(
                    select(Conversation.id)
                    .where(
                        Conversation.workspace_id == workspace_id,
                        Conversation.assistant_id.in_(assistant_ids),
                    )
                    .order_by(Conversation.id)
                )
            ).all()
        )
        current["dependants"] = {"assistants": assistant_ids, "conversations": conversation_ids}
        impact["assistants_affected"] = len(assistant_ids)
        impact["conversations_affected"] = len(conversation_ids)
    return current, impact


def require_operation(kind: str, action: str, row: Base, lifecycle: ResourceState | None) -> None:
    status = lifecycle.status if lifecycle else (row.status if kind == "conversation" else "active")
    allowed = {
        "collection": {"archive", "delete", "restore"},
        "source": {"archive", "delete", "restore"},
        "document": {"archive", "delete", "restore", "replace"},
        "assistant": {"pause", "resume", "archive", "delete", "restore"},
        "conversation": {"archive", "delete", "restore"},
        "job": {"cancel"},
        "index": {"cleanup"},
    }
    if action not in allowed[kind]:
        raise Conflict("Thao tác không hợp lệ cho tài nguyên này.", code="lifecycle_action_invalid")
    if action == "restore" and status == "active":
        raise Conflict("Tài nguyên chưa được lưu trữ/xóa.", code="lifecycle_transition_invalid")
    if (
        action in {"archive", "delete", "pause", "resume", "replace"}
        and status != "active"
        and not (action == "delete" and status == "archived")
    ):
        raise Conflict(
            "Cần khôi phục trước khi thực hiện thao tác.", code="lifecycle_transition_invalid"
        )
    if action == "cancel" and row.status not in {"queued", "running"}:
        raise Conflict("Tác vụ đã kết thúc.", code="lifecycle_job_finished")
    if action == "cleanup" and row.status in {"queued", "running"}:
        raise Conflict("Chỉ dọn generation đã ngừng sử dụng.", code="lifecycle_index_in_use")
