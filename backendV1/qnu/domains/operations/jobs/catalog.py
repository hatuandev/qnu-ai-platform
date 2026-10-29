"""Map existing durable records into one scoped operations view without a second job ledger."""

from dataclasses import dataclass

from sqlalchemy import String, cast, literal, null, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review.models import CompilationReview
from qnu.domains.knowledge.compilation.workflow.models import AutoReviewJob
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.review.models import SpellingRun
from qnu.domains.operations.models import EvidenceBackup
from qnu.domains.operations.schemas import JobView
from qnu.platform.database import Base
from qnu.platform.errors import EntityNotFound


@dataclass(frozen=True)
class JobSpec:
    model: type[Base]
    id_field: str
    created_field: str
    task: str | None = None


SPECS = {
    "ocr": JobSpec(OcrProcessingRun, "id", "requested_at", "ocr_process_run"),
    "compiler": JobSpec(CompilationRun, "id", "requested_at", "compile_run"),
    "index": JobSpec(IndexRun, "id", "requested_at", "index_run"),
    "auto_review": JobSpec(
        AutoReviewJob, "compilation_run_id", "created_at", "compiler_review_job"
    ),
    "review": JobSpec(CompilationReview, "id", "created_at"),
    "spelling": JobSpec(SpellingRun, "id", "created_at"),
    "turn": JobSpec(ConversationTurn, "id", "created_at"),
    "backup": JobSpec(EvidenceBackup, "id", "created_at", "evidence_backup_job"),
}


async def load_job(
    db: AsyncSession, workspace_id: str, kind: str, job_id: str, *, lock: bool = False
) -> Base:
    spec = SPECS[kind]
    statement = select(spec.model).where(
        getattr(spec.model, spec.id_field) == job_id, spec.model.workspace_id == workspace_id
    )
    if lock:
        statement = statement.with_for_update()
    row = await db.scalar(statement.execution_options(populate_existing=True))
    if row is None:
        raise EntityNotFound("Không tìm thấy tác vụ trong đơn vị.", code="operation_job_not_found")
    return row


def recoverable(kind: str, row: Base) -> tuple[bool, str]:
    spec = SPECS[kind]
    if not spec.task:
        return (
            False,
            "Lượt gọi đồng bộ; không tự gửi lại model. Tạo yêu cầu mới nếu cần kiểm tra lại.",
        )
    if row.status == "queued":
        return True, "Giao lại việc đã lưu; worker kiểm quyền và ownership trước khi xử lý."
    lease = getattr(row, "lease_expires_at", None)
    if row.status == "running" and lease is not None and lease <= utcnow():
        return (
            True,
            "Lease đã hết; worker phục hồi từ checkpoint và không gửi lại request chưa rõ kết quả.",
        )
    return False, "Tác vụ đang được sở hữu hoặc đã kết thúc; không đổi trạng thái để chạy lại ngầm."


async def view(db: AsyncSession, kind: str, row: Base) -> JobView:
    spec = SPECS[kind]
    allowed, reason = recoverable(kind, row)
    done, total = None, None
    if kind == "ocr":
        done, total = row.pages_done, row.pages_total
    elif kind == "index":
        from sqlalchemy import func

        done = await db.scalar(
            select(func.count())
            .select_from(IndexChunk)
            .where(IndexChunk.run_id == row.id, IndexChunk.vector.is_not(None))
        )
        total = row.chunks_total
    return JobView(
        kind=kind,
        id=getattr(row, spec.id_field),
        workspace_id=row.workspace_id,
        collection_id=getattr(row, "collection_id", None),
        source_id=getattr(row, "source_id", None),
        revision_id=getattr(row, "revision_id", None),
        compilation_run_id=(
            getattr(row, "compilation_run_id", None) or (row.id if kind == "compiler" else None)
        ),
        status=row.status,
        created_at=getattr(row, spec.created_field),
        started_at=getattr(row, "started_at", None),
        finished_at=getattr(row, "finished_at", None),
        lease_expires_at=getattr(row, "lease_expires_at", None),
        error_code=getattr(row, "error_code", None),
        attempts=getattr(row, "attempt_count", None),
        progress_done=done,
        progress_total=total,
        usage_tokens=getattr(row, "usage_tokens", None),
        provider_id=getattr(row, "provider_id", None),
        recovery_allowed=allowed,
        recovery_reason=reason,
    )


def job_union(workspace_id: str, kind: str | None, status: str | None, collection_id: str | None):
    statements = []
    for name, spec in SPECS.items():
        if kind and kind != name:
            continue
        model = spec.model
        collection = getattr(model, "collection_id", cast(null(), String))
        stmt = select(
            literal(name).label("kind"),
            getattr(model, spec.id_field).label("id"),
            getattr(model, spec.created_field).label("created_at"),
            model.status.label("status"),
        ).where(model.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(model.status == status)
        if collection_id:
            stmt = stmt.where(collection == collection_id)
        statements.append(stmt)
    return union_all(*statements).subquery()
