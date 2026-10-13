"""Bounded reconciliation of workflow hard deadlines after process loss."""

from typing import Any

import structlog

from app.core.database import AsyncSessionFactory
from app.modules.workflows.execution_audit import expire_abandoned_executions

logger = structlog.get_logger(__name__)


async def task_reconcile_workflow_executions(ctx: dict[str, Any]) -> dict[str, int]:
    async with AsyncSessionFactory() as db:
        expired = await expire_abandoned_executions(db)
    if expired:
        logger.warning("workflow_deadlines_expired", count=expired)
    return {"expired": expired}
