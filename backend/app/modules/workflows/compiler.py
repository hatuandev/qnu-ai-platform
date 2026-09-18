"""Workflow compiler that validates publishable DAG specifications before runtime use."""

from __future__ import annotations

from collections import defaultdict, deque

from app.modules.workflows.registry import node_registry
from app.modules.workflows.schemas import (
    WorkflowDagSpec,
    WorkflowValidationIssue,
    WorkflowValidationReport,
)

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

_RAG_NODE_TYPES = frozenset(
    {
        "core.knowledge.answer",
        "rag.knowledge",
        "rag.answer",
        "rag.search",
    }
)

_CITATION_GUARD_TYPES = frozenset(
    {
        "guard.citation",
        "guard.citation_policy",
        "guardrail",
        "output.no_answer",
        "no_answer_output",
        "human.approval",
        "tool.human_approval",
    }
)


class WorkflowCompiler:
    """Performs deterministic static checks shared by save, publish, and rollback flows."""

    def validate(self, dag_spec: WorkflowDagSpec) -> WorkflowValidationReport:
        """Return all validation findings without mutating the supplied working copy."""
        issues: list[WorkflowValidationIssue] = []
        node_ids = [node.id.strip() for node in dag_spec.nodes]
        known_node_ids = set(node_ids)

        self._validate_nodes(dag_spec, node_ids, known_node_ids, issues)
        self._validate_edges(dag_spec, known_node_ids, issues)
        self._validate_graph_shape(dag_spec, known_node_ids, issues)
        self._validate_runtime_policy(dag_spec, issues)

        return WorkflowValidationReport(
            is_valid=not any(issue.severity == "error" for issue in issues),
            issues=issues,
            node_count=len(dag_spec.nodes),
            edge_count=len(dag_spec.edges),
        )

    def _validate_nodes(
        self,
        dag_spec: WorkflowDagSpec,
        node_ids: list[str],
        known_node_ids: set[str],
        issues: list[WorkflowValidationIssue],
    ) -> None:
        if not dag_spec.nodes:
            issues.append(
                WorkflowValidationIssue(
                    code="workflow_nodes_empty",
                    message="Workflow phải có ít nhất một node.",
                )
            )
            return

        if len(node_ids) != len(known_node_ids) or any(not node_id for node_id in node_ids):
            issues.append(
                WorkflowValidationIssue(
                    code="workflow_node_id_invalid",
                    message="Mỗi node phải có mã định danh duy nhất và không rỗng.",
                )
            )

        if dag_spec.entry_node_id not in known_node_ids:
            issues.append(
                WorkflowValidationIssue(
                    code="workflow_entry_missing",
                    message=f"Node bắt đầu '{dag_spec.entry_node_id}' không tồn tại.",
                    node_id=dag_spec.entry_node_id,
                )
            )

        for node in dag_spec.nodes:
            if node_registry.get(node.type):
                continue
            issues.append(
                WorkflowValidationIssue(
                    code="workflow_node_type_unsupported",
                    message=f"Node '{node.id}' dùng loại chưa được runtime hỗ trợ: '{node.type}'.",
                    node_id=node.id,
                )
            )

    @staticmethod
    def _validate_edges(
        dag_spec: WorkflowDagSpec,
        known_node_ids: set[str],
        issues: list[WorkflowValidationIssue],
    ) -> None:
        seen_edges: set[tuple[str, str, str | None]] = set()
        for edge_index, edge in enumerate(dag_spec.edges):
            edge_identity = (edge.source, edge.target, edge.source_port)
            if edge_identity in seen_edges:
                issues.append(
                    WorkflowValidationIssue(
                        code="workflow_edge_duplicate",
                        message=f"Cạnh '{edge.source}' → '{edge.target}' bị khai báo trùng.",
                        edge_index=edge_index,
                    )
                )
            seen_edges.add(edge_identity)

            if edge.source not in known_node_ids or edge.target not in known_node_ids:
                issues.append(
                    WorkflowValidationIssue(
                        code="workflow_edge_node_missing",
                        message=f"Cạnh '{edge.source}' → '{edge.target}' phải nối hai node có tồn tại.",
                        edge_index=edge_index,
                    )
                )

    def _validate_graph_shape(
        self,
        dag_spec: WorkflowDagSpec,
        known_node_ids: set[str],
        issues: list[WorkflowValidationIssue],
    ) -> None:
        if dag_spec.entry_node_id not in known_node_ids:
            return

        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in dag_spec.edges:
            if edge.source in known_node_ids and edge.target in known_node_ids:
                adjacency[edge.source].append(edge.target)

        reachable = self._find_reachable_nodes(dag_spec.entry_node_id, adjacency)
        unreachable = sorted(known_node_ids - reachable)
        for node_id in unreachable:
            issues.append(
                WorkflowValidationIssue(
                    code="workflow_node_unreachable",
                    message=f"Node '{node_id}' không thể tới từ node bắt đầu.",
                    severity="warning",
                    node_id=node_id,
                )
            )

        if self._has_cycle(known_node_ids, adjacency):
            issues.append(
                WorkflowValidationIssue(
                    code="workflow_cycle_detected",
                    message="Workflow phải là DAG; phát hiện vòng lặp trong các cạnh.",
                )
            )

        reachable_terminal_nodes = [
            node
            for node in dag_spec.nodes
            if node.id in reachable and node.type in _TERMINAL_NODE_TYPES
        ]
        if not reachable_terminal_nodes:
            issues.append(
                WorkflowValidationIssue(
                    code="workflow_terminal_missing",
                    message="Workflow cần ít nhất một node đầu ra có thể tới từ node bắt đầu.",
                )
            )

        rag_nodes = [node for node in dag_spec.nodes if node.type in _RAG_NODE_TYPES]
        if rag_nodes:
            has_guard = any(
                node.type in _CITATION_GUARD_TYPES
                for node in dag_spec.nodes
                if node.id in reachable
            )
            if not has_guard:
                issues.append(
                    WorkflowValidationIssue(
                        code="workflow_rag_missing_citation_guard",
                        message=(
                            "Workflow sử dụng RAG tri thức bắt buộc phải có chốt chặn kiểm tra "
                            "trích dẫn (guard.citation_policy) hoặc đường rẽ nhánh không trả lời "
                            "(output.no_answer) để chống bịa đặt (Anti-Hallucination)."
                        ),
                    )
                )

    @staticmethod
    def _validate_runtime_policy(
        dag_spec: WorkflowDagSpec,
        issues: list[WorkflowValidationIssue],
    ) -> None:
        max_steps = dag_spec.policies.get("max_steps", 25)
        if not isinstance(max_steps, int) or not 1 <= max_steps <= 200:
            issues.append(
                WorkflowValidationIssue(
                    code="workflow_max_steps_invalid",
                    message="Chính sách max_steps phải là số nguyên từ 1 đến 200.",
                )
            )

    @staticmethod
    def _find_reachable_nodes(start_node_id: str, adjacency: dict[str, list[str]]) -> set[str]:
        reachable: set[str] = set()
        queue: deque[str] = deque([start_node_id])
        while queue:
            node_id = queue.popleft()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            queue.extend(adjacency.get(node_id, []))
        return reachable

    @staticmethod
    def _has_cycle(node_ids: set[str], adjacency: dict[str, list[str]]) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False

            visiting.add(node_id)
            for target_id in adjacency.get(node_id, []):
                if visit(target_id):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        return any(visit(node_id) for node_id in node_ids if node_id not in visited)


workflow_compiler = WorkflowCompiler()
