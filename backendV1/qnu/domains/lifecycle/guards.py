"""The default read surface excludes archived/deleted resources, including their parents."""

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.lifecycle.models import ResourceState
from qnu.platform.errors import EntityNotFound


def visible(kind: str, resource_id):
    return ~exists().where(
        ResourceState.kind == kind,
        ResourceState.resource_id == resource_id,
        ResourceState.status != "active",
    )


async def require_available(
    db: AsyncSession, workspace_id: str, kind: str, resource_id: str
) -> None:
    with db.no_autoflush:
        status = await db.scalar(
            select(ResourceState.status).where(
                ResourceState.workspace_id == workspace_id,
                ResourceState.kind == kind,
                ResourceState.resource_id == resource_id,
            )
        )
    if status and status != "active":
        raise EntityNotFound(
            "Tài nguyên đã lưu trữ hoặc đưa vào thùng rác.", code="resource_unavailable"
        )


async def require_compilation_sources(db: AsyncSession, workspace_id: str, run_id: str) -> None:
    from qnu.domains.knowledge.compilation.models import CompilationInput
    from qnu.domains.ocr.models import OcrProcessingRun

    ids = (
        await db.scalars(
            select(OcrProcessingRun.source_id)
            .join(CompilationInput, CompilationInput.ocr_run_id == OcrProcessingRun.id)
            .where(CompilationInput.run_id == run_id)
        )
    ).all()
    for source_id in ids:
        await require_available(db, workspace_id, "source", source_id)
