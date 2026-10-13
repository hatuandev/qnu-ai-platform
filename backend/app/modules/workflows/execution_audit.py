"""Persist terminal audit in a clean transaction after execution failures."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.modules.workflows.models import WorkflowExecution


async def persist_boundary_failure(
    identity: dict[str, Any], status: str, error_code: str, stage: str,
    latency_ms: float,
) -> None:
    values = {**identity, "status": status, "completed_at": datetime.now(UTC).replace(tzinfo=None),
              "error_message": f"{error_code}: {stage}", "latency_ms": latency_ms,
              "outputs": {"error_code": error_code, "failure_stage": stage}}
    async with AsyncSessionFactory() as audit_db:
        statement = insert(WorkflowExecution).values(**values)
        await audit_db.execute(statement.on_conflict_do_update(
            index_elements=[WorkflowExecution.id],
            set_={key: values[key] for key in ("status", "completed_at", "error_message", "latency_ms", "outputs")},
            where=WorkflowExecution.status == "running",
        ))
        await audit_db.commit()


async def expire_abandoned_executions(db: AsyncSession) -> int:
    """Expire only runs with a recorded hard deadline; never replay tools."""
    now = datetime.now(UTC)
    result = await db.execute(update(WorkflowExecution).where(
        WorkflowExecution.status == "running",
        WorkflowExecution.runtime_profile["execution_deadline"].as_float() < now.timestamp() - 30,
    ).values(status="failed", completed_at=now.replace(tzinfo=None),
             error_message="WORKFLOW_DEADLINE_EXPIRED: abandoned",
             outputs={"error_code": "WORKFLOW_DEADLINE_EXPIRED", "failure_stage": "reconcile"}))
    await db.commit()
    return result.rowcount
