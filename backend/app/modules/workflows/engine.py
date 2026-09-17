"""Workflow DAG Runtime Engine — Executes Directed Acyclic Graphs with State & Branching."""

from __future__ import annotations

import logging
import time

from app.modules.workflows.nodes.base import NodeExecutionTrace, WorkflowContext
from app.modules.workflows.registry import node_registry
from app.modules.workflows.schemas import (
    WorkflowDagSpec,
    WorkflowEdgeSpec,
    WorkflowExecuteResponse,
    WorkflowNodeSpec,
)

logger = logging.getLogger(__name__)

_TERMINAL_NODE_TYPES = frozenset(
    {
        "output.chat",
        "chat_output",
        "output.no_answer",
        "no_answer_output",
        "output.file",
        "output.artifact",
        "artifact.export",
    }
)


class WorkflowDAGEngine:
    """Runtime engine executing active DAG paths with fan-out and explicit branch ports."""

    async def execute(
        self,
        dag_spec: WorkflowDagSpec,
        context: WorkflowContext,
        *,
        start_node_id: str | None = None,
        completed_node_ids: set[str] | None = None,
        max_steps: int | None = None,
    ) -> WorkflowExecuteResponse:
        """Execute all ready nodes; join nodes wait for every active predecessor."""
        start_time = time.perf_counter()
        nodes_by_id: dict[str, WorkflowNodeSpec] = {n.id: n for n in dag_spec.nodes}
        edges_by_source: dict[str, list[WorkflowEdgeSpec]] = {}
        edges_by_target: dict[str, list[WorkflowEdgeSpec]] = {}
        for edge in dag_spec.edges:
            edges_by_source.setdefault(edge.source, []).append(edge)
            edges_by_target.setdefault(edge.target, []).append(edge)

        max_allowed_steps = max_steps or dag_spec.policies.get("max_steps", 25)
        active_node_ids: set[str] = {start_node_id or dag_spec.entry_node_id}
        completed_ids = set(completed_node_ids or set())
        executed_nodes: list[str] = list(completed_ids)
        steps_taken = 0

        while steps_taken < max_allowed_steps:
            ready_node_ids = self._find_ready_nodes(
                active_node_ids,
                completed_ids,
                edges_by_target,
            )
            if not ready_node_ids:
                return self._complete_or_stall_response(
                    context,
                    start_time,
                    active_node_ids,
                    completed_ids,
                    executed_nodes,
                )

            current_node_id = ready_node_ids[0]
            steps_taken += 1
            node_spec = nodes_by_id.get(current_node_id)
            if not node_spec:
                return self._failed_response(
                    context,
                    start_time,
                    executed_nodes,
                    f"Không tìm thấy node '{current_node_id}' trong đặc tả workflow.",
                )

            executed_nodes.append(current_node_id)
            handler = node_registry.get(node_spec.type)
            if not handler:
                return self._failed_response(
                    context,
                    start_time,
                    executed_nodes,
                    f"Node '{current_node_id}' dùng loại chưa được runtime hỗ trợ: '{node_spec.type}'.",
                )

            node_start_time = time.perf_counter()
            try:
                result = await handler.execute(node_spec, context)
            except Exception as exc:
                logger.exception("Node [%s] failed with an unexpected error", current_node_id)
                return self._failed_response(
                    context,
                    start_time,
                    executed_nodes,
                    f"Node '{current_node_id}' thực thi không thành công: {exc}",
                )

            context.node_traces.append(
                NodeExecutionTrace(
                    node_id=current_node_id,
                    node_type=node_spec.type,
                    status=result.status,
                    input_data={"inputs": context.inputs},
                    output_data=result.output,
                    latency_ms=round((time.perf_counter() - node_start_time) * 1000, 2),
                )
            )
            context.node_data[f"node:{current_node_id}"] = result.output

            if result.status == "paused_for_approval":
                elapsed = (time.perf_counter() - start_time) * 1000
                return WorkflowExecuteResponse(
                    execution_id=context.execution_id or context.workflow_id,
                    workflow_id=context.workflow_id,
                    status="paused_for_approval",
                    outputs=result.output,
                    executed_nodes=executed_nodes,
                    latency_ms=round(elapsed, 2),
                    paused_node_id=current_node_id,
                )

            if result.status == "failed":
                return self._failed_response(
                    context,
                    start_time,
                    executed_nodes,
                    result.error or f"Node '{current_node_id}' thực thi không thành công.",
                )

            completed_ids.add(current_node_id)
            if node_spec.type in _TERMINAL_NODE_TYPES:
                continue
            activation_error = self._activate_next_nodes(
                result.next_node_override,
                result.selected_port,
                current_node_id,
                edges_by_source,
                nodes_by_id,
                active_node_ids,
            )
            if activation_error:
                return self._failed_response(
                    context,
                    start_time,
                    executed_nodes,
                    activation_error,
                )

        return self._failed_response(
            context,
            start_time,
            executed_nodes,
            f"Workflow vượt quá giới hạn {max_allowed_steps} bước thực thi.",
        )

    @staticmethod
    def _find_ready_nodes(
        active_node_ids: set[str],
        completed_node_ids: set[str],
        edges_by_target: dict[str, list[WorkflowEdgeSpec]],
    ) -> list[str]:
        ready_node_ids: list[str] = []
        for node_id in sorted(active_node_ids - completed_node_ids):
            active_predecessors = {
                edge.source
                for edge in edges_by_target.get(node_id, [])
                if edge.source in active_node_ids
            }
            if active_predecessors.issubset(completed_node_ids):
                ready_node_ids.append(node_id)
        return ready_node_ids

    @staticmethod
    def _activate_next_nodes(
        next_node_override: str | None,
        selected_port: str | None,
        current_node_id: str,
        edges_by_source: dict[str, list[WorkflowEdgeSpec]],
        nodes_by_id: dict[str, WorkflowNodeSpec],
        active_node_ids: set[str],
    ) -> str | None:
        if next_node_override:
            if next_node_override not in nodes_by_id:
                return f"Node '{current_node_id}' điều hướng đến node không tồn tại '{next_node_override}'."
            active_node_ids.add(next_node_override)
            return None

        outgoing_edges = edges_by_source.get(current_node_id, [])
        if not selected_port:
            active_node_ids.update(edge.target for edge in outgoing_edges)
            return None

        matching_edges = [edge for edge in outgoing_edges if edge.source_port == selected_port]
        if matching_edges:
            active_node_ids.update(edge.target for edge in matching_edges)
            return None
        if not outgoing_edges:
            return None
        return (
            f"Node '{current_node_id}' chọn cổng '{selected_port}' nhưng workflow không có cạnh tương ứng."
        )

    def _complete_or_stall_response(
        self,
        context: WorkflowContext,
        start_time: float,
        active_node_ids: set[str],
        completed_node_ids: set[str],
        executed_nodes: list[str],
    ) -> WorkflowExecuteResponse:
        pending_node_ids = sorted(active_node_ids - completed_node_ids)
        if pending_node_ids:
            return self._failed_response(
                context,
                start_time,
                executed_nodes,
                f"Workflow bị kẹt khi chờ các node: {', '.join(pending_node_ids)}.",
            )
        elapsed = (time.perf_counter() - start_time) * 1000
        return WorkflowExecuteResponse(
            execution_id=context.execution_id or context.workflow_id,
            workflow_id=context.workflow_id,
            status="completed",
            outputs=context.outputs,
            executed_nodes=executed_nodes,
            latency_ms=round(elapsed, 2),
        )

    @staticmethod
    def _failed_response(
        context: WorkflowContext,
        start_time: float,
        executed_nodes: list[str],
        error_message: str,
    ) -> WorkflowExecuteResponse:
        elapsed = (time.perf_counter() - start_time) * 1000
        return WorkflowExecuteResponse(
            execution_id=context.execution_id or context.workflow_id,
            workflow_id=context.workflow_id,
            status="failed",
            outputs=context.outputs,
            executed_nodes=executed_nodes,
            latency_ms=round(elapsed, 2),
            error_message=error_message,
        )


dag_engine = WorkflowDAGEngine()
