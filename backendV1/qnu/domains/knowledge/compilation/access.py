"""Collection authorization and run loading shared by compilation use cases."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import CompilationRun
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES, load_collection
from qnu.domains.lifecycle.guards import require_compilation_sources
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import EntityNotFound


async def authorize_collection(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    *,
    write: bool = False,
    lock: bool = False,
) -> None:
    await resolve_workspace_access(
        db,
        actor,
        workspace_id,
        required_roles=WRITE_ROLES if write else READ_ROLES,
        for_update=lock,
    )
    await load_collection(db, workspace_id, collection_id)


async def get_run(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
) -> CompilationRun:
    await authorize_collection(db, actor, workspace_id, collection_id)
    run = await db.scalar(
        select(CompilationRun).where(
            CompilationRun.id == run_id,
            CompilationRun.workspace_id == workspace_id,
            CompilationRun.collection_id == collection_id,
        )
    )
    if run is None:
        raise EntityNotFound("Không tìm thấy lượt biên soạn.", code="compilation_not_found")
    await require_compilation_sources(db, workspace_id, run.id)
    return run
