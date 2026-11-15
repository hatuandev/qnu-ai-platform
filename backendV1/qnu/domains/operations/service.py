"""Workspace operations authorize before every lookup and expose safe observed metadata."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.policies.access import load_collection
from qnu.domains.modelops.models import ModelUsageRecord
from qnu.domains.operations.jobs.catalog import job_union, load_job, page_views, view
from qnu.domains.operations.models import EvidenceBackup, OperationAction
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.platform.errors import EntityNotFound

READ_ROLES = ("admin", "editor", "reviewer")


async def authorize(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    *,
    write: bool = False,
    admin: bool = False,
    lock: bool = False,
) -> None:
    roles = ("admin",) if admin else (("admin", "editor") if write else READ_ROLES)
    await resolve_workspace_access(db, actor, workspace_id, required_roles=roles, for_update=lock)


def background_actor(actor: AuthActor | str) -> AuthActor:
    ref = actor if isinstance(actor, str) else actor_ref(actor)
    return AuthActor(username=ref, actor_id=ref, roles=[], permissions=[])


async def list_jobs(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    kind: str | None,
    status: str | None,
    collection_id: str | None,
    limit: int,
    offset: int,
) -> dict:
    await authorize(db, actor, workspace_id)
    if collection_id:
        await load_collection(db, workspace_id, collection_id)
    source = job_union(workspace_id, kind, status, collection_id)
    total = await db.scalar(select(func.count()).select_from(source))
    refs = (
        await db.execute(
            select(source.c.kind, source.c.id)
            .order_by(source.c.created_at.desc(), source.c.kind, source.c.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    items = await page_views(db, workspace_id, [(kind, job_id) for kind, job_id in refs])
    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def job_detail(db: AsyncSession, actor: AuthActor, workspace_id: str, kind: str, job_id: str):
    await authorize(db, actor, workspace_id)
    return await view(db, kind, await load_job(db, workspace_id, kind, job_id))


async def summary(db: AsyncSession, actor: AuthActor, workspace_id: str) -> dict:
    await authorize(db, actor, workspace_id)
    source = job_union(workspace_id, None, None, None)
    counts = (
        await db.execute(
            select(source.c.kind, source.c.status, func.count()).group_by(
                source.c.kind, source.c.status
            )
        )
    ).all()
    usage = (
        await db.execute(
            select(
                ModelUsageRecord.status,
                func.count(),
                func.sum(ModelUsageRecord.total_tokens),
                func.sum(ModelUsageRecord.reserved_tokens),
                func.sum(ModelUsageRecord.cost_usd),
                func.count(ModelUsageRecord.cost_usd),
            )
            .where(ModelUsageRecord.workspace_id == workspace_id)
            .group_by(ModelUsageRecord.status)
        )
    ).all()
    return {
        "jobs": [{"kind": k, "status": s, "count": n} for k, s, n in counts],
        "usage": [
            {
                "status": s,
                "records": n,
                "observed_tokens": t,
                "reserved_tokens": r,
                "observed_cost_usd": cost,
                "cost_records": known,
            }
            for s, n, t, r, cost, known in usage
        ],
    }


async def retention(db: AsyncSession, actor: AuthActor, workspace_id: str) -> dict:
    from qnu.domains.knowledge.compilation.models import utcnow

    await authorize(db, actor, workspace_id, admin=True)
    rows = list(
        (
            await db.scalars(
                select(EvidenceBackup)
                .where(
                    EvidenceBackup.workspace_id == workspace_id,
                    EvidenceBackup.status == "completed",
                    EvidenceBackup.retain_until.is_not(None),
                    EvidenceBackup.retain_until <= utcnow(),
                )
                .order_by(EvidenceBackup.retain_until)
                .limit(100)
            )
        ).all()
    )
    return {
        "original_and_raw_evidence": "keep_forever",
        "backup_default": "keep_forever",
        "automatic_delete": False,
        "eligible_backup_ids": [r.id for r in rows],
        "requires_preview_and_acceptance": True,
    }


async def action_status(db: AsyncSession, actor: AuthActor, workspace_id: str, action_id: str):
    await authorize(db, actor, workspace_id)
    row = await db.scalar(
        select(OperationAction).where(
            OperationAction.id == action_id, OperationAction.workspace_id == workspace_id
        )
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy thao tác vận hành.", code="operation_action_not_found")
    await authorize(db, actor, workspace_id, admin=row.kind == "backup")
    return row
