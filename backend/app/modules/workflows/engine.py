"""Workflow DAG Runtime Engine — Executes Directed Acyclic Graphs with State & Branching."""

from __future__ import annotations

import logging
import time

from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.registry import node_registry
from app.modules.workflows.schemas import (
    WorkflowDagSpec,
    WorkflowExecuteResponse,
    WorkflowNodeSpec,
)

logger = logging.getLogger(__name__)


class WorkflowDAGEngine:
    """Runtime engine executing declarative DAG workflows step-by-step."""

    async def execute(
        self,
        dag_spec: WorkflowDagSpec,
        context: WorkflowContext,
        max_steps: int = 25,
    ) -> WorkflowExecuteResponse:
        start_time = time.perf_counter()

        # Build lookup tables for nodes and edges
        nodes_by_id: dict[str, WorkflowNodeSpec] = {n.id: n for n in dag_spec.nodes}
        edges_by_source: dict[str, list[str]] = {}
        for edge in dag_spec.edges:
            edges_by_source.setdefault(edge.source, []).append(edge.target)

        current_node_id: str | None = dag_spec.entry_node_id
        executed_nodes: list[str] = []
        steps_taken = 0

        while current_node_id and steps_taken < max_steps:
            steps_taken += 1
            node_spec = nodes_by_id.get(current_node_id)
            if not node_spec:
                logger.error("Node [%s] not found in DAG specification", current_node_id)
                break

            executed_nodes.append(current_node_id)
            handler = node_registry.get(node_spec.type)
            if not handler:
                logger.warning(
                    "No handler found for node type [%s] on node [%s], skipping",
                    node_spec.type,
                    current_node_id,
                )
                break

            # Execute node
            result = await handler.execute(node_spec, context)

            if result.status == "paused_for_approval":
                elapsed = (time.perf_counter() - start_time) * 1000
                return WorkflowExecuteResponse(
                    execution_id=context.workflow_id,
                    workflow_id=context.workflow_id,
                    status="paused_for_approval",
                    outputs=result.output,
                    executed_nodes=executed_nodes,
                    latency_ms=round(elapsed, 2),
                )

            if result.status == "failed":
                elapsed = (time.perf_counter() - start_time) * 1000
                return WorkflowExecuteResponse(
                    execution_id=context.workflow_id,
                    workflow_id=context.workflow_id,
                    status="failed",
                    outputs=context.outputs,
                    executed_nodes=executed_nodes,
                    latency_ms=round(elapsed, 2),
                    error_message=result.error or f"Node {current_node_id} execution failed",
                )

            # Determine next node in DAG
            if result.next_node_override:
                current_node_id = result.next_node_override
            else:
                next_targets = edges_by_source.get(current_node_id, [])
                current_node_id = next_targets[0] if next_targets else None

            # Terminal condition: Output node reached
            if node_spec.type in ("output.chat", "chat_output", "output.file"):
                break

        elapsed = (time.perf_counter() - start_time) * 1000
        return WorkflowExecuteResponse(
            execution_id=context.workflow_id,
            workflow_id=context.workflow_id,
            status="completed",
            outputs=context.outputs,
            executed_nodes=executed_nodes,
            latency_ms=round(elapsed, 2),
        )


dag_engine = WorkflowDAGEngine()
