"""Operations outbox and evidence backup tasks on the existing v1 worker."""

from datetime import timedelta

from sqlalchemy import select

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.operations.backups import execution, service
from qnu.domains.operations.jobs import actions
from qnu.domains.operations.models import EvidenceBackup, OperationAction
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.logging import get_logger

logger = get_logger(__name__)


async def evidence_backup_job(ctx: dict, backup_id: str) -> str:
    async with AsyncSessionFactory() as db:
        return await execution.execute(
            db, ctx["container"].blob_store, backup_id, ctx.get("worker_id", "arq")
        )


async def evidence_backup_delete(ctx: dict, backup_id: str, action_id: str) -> str:
    async with AsyncSessionFactory() as db:
        return await execution.delete(db, ctx["container"].blob_store, backup_id, action_id)


async def operations_reconcile(ctx: dict) -> int:
    from qnu.domains.lifecycle.purge import reconcile

    container, now = ctx["container"], utcnow()
    cutoff, count = now - timedelta(seconds=execution.LEASE_SECONDS), await reconcile(ctx)
    async with AsyncSessionFactory() as db:
        pending = list(
            (
                await db.scalars(
                    select(OperationAction.id).where(OperationAction.status == "pending").limit(50)
                )
            ).all()
        )
        for action_id in pending:
            try:
                count += int(await actions.dispatch(db, action_id, container.job_queue))
            except Exception:
                await db.rollback()
                logger.warning("operation_reconcile_stopped", action_id=action_id)
        rows = list(
            (
                await db.scalars(
                    select(EvidenceBackup)
                    .where(
                        (
                            (EvidenceBackup.status == "queued")
                            & (
                                EvidenceBackup.dispatched_at.is_(None)
                                | (EvidenceBackup.dispatched_at < cutoff)
                            )
                        )
                        | (
                            EvidenceBackup.status.in_(("running", "deleting"))
                            & (EvidenceBackup.lease_expires_at < now)
                        )
                    )
                    .limit(50)
                )
            ).all()
        )
        for row in rows:
            backup_id = row.id
            try:
                if row.status == "queued":
                    count += int(await service.dispatch(db, row, container.job_queue))
                else:
                    task = (
                        "evidence_backup_delete"
                        if row.status == "deleting"
                        else "evidence_backup_job"
                    )
                    args = (row.id, row.delete_action_id) if row.status == "deleting" else (row.id,)
                    count += int(
                        await container.job_queue.enqueue(
                            task,
                            *args,
                            job_id=f"qnu:v1:backup-recover:{row.id}:{int(now.timestamp()) // 300}",
                        )
                    )
            except Exception:
                await db.rollback()
                logger.warning("backup_reconcile_stopped", backup_id=backup_id)
    return count
