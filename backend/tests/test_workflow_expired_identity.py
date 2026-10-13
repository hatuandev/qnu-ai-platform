"""Real async ORM expiration regression: finalize must not lazily read its ID."""

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.modules.workflows.models import WorkflowExecution, WorkflowNodeExecution
from app.modules.workflows.nodes.base import NodeExecutionTrace
from app.modules.workflows.schemas import (
    WorkflowDagSpec,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
)
from app.modules.workflows.service import workflow_service

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    os.getenv("QNU_TEST_WORKFLOW_DB") != "1", reason="Opt-in PostgreSQL expiration regression")]


@pytest.mark.parametrize("status", ["completed", "failed", "paused_for_approval"])
async def test_workflow_finalizes_real_expired_identity_after_node_rollback(status):
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    tag = uuid.uuid4().hex[:10]
    try:
        async with engine.connect() as conn:
            outer = await conn.begin()
            try:
                def session_factory():
                    return AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
                async with session_factory() as db:
                    captured = {}
                    async def expire_in_node(spec, context):
                        record = next(record for record in db.identity_map.values() if isinstance(record, WorkflowExecution))
                        captured["id"] = record.id
                        await db.execute(select(1))  # A node/ModelOps operation opens a new transaction.
                        await db.rollback()
                        assert inspect(record).expired and "id" in inspect(record).expired_attributes
                        context.node_traces.append(NodeExecutionTrace(node_id="fixture", node_type="output.chat",
                            status=status, input_data={}, output_data={"answer": "Fixture proof"}, latency_ms=1))
                        return WorkflowExecuteResponse(execution_id="engine-placeholder", workflow_id=f"test_expire_{tag}",
                            status=status, outputs={"answer": "Fixture proof"}, executed_nodes=["fixture"])
                    spec = WorkflowDagSpec(entry_node_id="fixture", nodes=[])
                    with (patch.object(workflow_service, "get_workflow_spec", AsyncMock(return_value=spec)),
                          patch("app.modules.workflows.service.dag_engine.execute", side_effect=expire_in_node),
                          patch("app.modules.workflows.execution_audit.AsyncSessionFactory", session_factory)):
                        response = await workflow_service.execute(db,
                            WorkflowExecuteRequest(workflow_id=f"test_expire_{tag}", inputs={}))
                    assert response.execution_id == captured["id"]
                    record = await db.get(WorkflowExecution, captured["id"])
                    assert record.status == status and record.outputs["answer"] == "Fixture proof"
                    traces = (await db.execute(select(WorkflowNodeExecution).where(
                        WorkflowNodeExecution.execution_id == captured["id"]))).scalars().all()
                    assert len(traces) == 1 and traces[0].status == status
            finally:
                await outer.rollback()
    finally:
        await engine.dispose()
