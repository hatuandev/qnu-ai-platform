"""Workflow Service — Loading DAG Specifications, Executing Workflows & Storing Audit Traces."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workflows.engine import dag_engine
from app.modules.workflows.models import WorkflowDefinition, WorkflowExecution
from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.schemas import (
    WorkflowDagSpec,
    WorkflowDefinitionResponse,
    WorkflowEdgeSpec,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowNodeSpec,
)

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for managing declarative DAG workflows and executing them."""

    def __init__(self) -> None:
        # Base directory for workflow template JSON files
        self.workflows_dir = Path(__file__).resolve().parents[4] / "configs" / "workflows"

    @staticmethod
    def _read_json_file(file_path: Path) -> dict:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def _parse_spec_from_json(self, raw_data: dict) -> WorkflowDagSpec:
        """Parse raw JSON workflow format into WorkflowDagSpec."""
        spec_data = raw_data.get("spec", raw_data)
        raw_nodes = spec_data.get("nodes", [])
        raw_edges = spec_data.get("edges", [])

        nodes = [
            WorkflowNodeSpec(
                id=n.get("id"),
                type=n.get("type", "input.chat"),
                version=n.get("version", "1.0.0"),
                display_name=n.get("display_name"),
                config=n.get("config", {}),
                policy=n.get("policy", {}),
            )
            for n in raw_nodes
        ]

        edges = [
            WorkflowEdgeSpec(
                source=e.get("source"),
                target=e.get("target"),
                condition=e.get("condition"),
                label=e.get("label"),
            )
            for e in raw_edges
        ]

        return WorkflowDagSpec(
            execution_mode=spec_data.get("execution_mode", "conversational"),
            entry_node_id=spec_data.get("entry_node_id", nodes[0].id if nodes else "chat_input"),
            input_schema=spec_data.get("input_schema", {}),
            output_schema=spec_data.get("output_schema", {}),
            nodes=nodes,
            edges=edges,
        )

    async def get_workflow_spec(
        self, db: AsyncSession | None, workflow_id: str
    ) -> WorkflowDagSpec:
        """Retrieve workflow DAG specification from DB or fallback to configs/workflows/*.json."""
        # 1. Try DB first if available
        if db:
            try:
                stmt = select(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id)
                res = await db.execute(stmt)
                wf_def = res.scalar_one_or_none()
                if wf_def:
                    return self._parse_spec_from_json(wf_def.dag_spec)
            except Exception as e:
                logger.debug("Database query for workflow definition skipped or failed: %s", e)

        # 2. Try filesystem configs/workflows/*.json
        clean_id = workflow_id.replace(".v1alpha1", "").replace(".json", "")
        candidates = [
            self.workflows_dir / f"{clean_id}.v1alpha1.json",
            self.workflows_dir / f"{clean_id}.json",
            self.workflows_dir / f"{clean_id}-assistant.v1alpha1.json",
        ]

        for file_path in candidates:
            if file_path.exists():
                try:
                    data = await asyncio.to_thread(self._read_json_file, file_path)
                    return self._parse_spec_from_json(data)
                except Exception as read_err:
                    logger.warning("Failed to read workflow file %s: %s", file_path, read_err)

        # 3. Default fallback minimal DAG if file not found
        logger.warning(
            "Workflow definition [%s] not found in DB or filesystem. Returning standard fallback DAG.",
            workflow_id,
        )
        return WorkflowDagSpec(
            entry_node_id="chat_input",
            nodes=[
                WorkflowNodeSpec(id="chat_input", type="input.chat"),
                WorkflowNodeSpec(id="rag_answer", type="core.knowledge.answer"),
                WorkflowNodeSpec(id="chat_output", type="output.chat"),
            ],
            edges=[
                WorkflowEdgeSpec(source="chat_input", target="rag_answer"),
                WorkflowEdgeSpec(source="rag_answer", target="chat_output"),
            ],
        )

    async def execute(
        self, db: AsyncSession, req: WorkflowExecuteRequest
    ) -> WorkflowExecuteResponse:
        """Run workflow DAG end-to-end and audit execution trace."""
        dag_spec = await self.get_workflow_spec(db, req.workflow_id)

        context = WorkflowContext(
            workflow_id=req.workflow_id,
            tenant_id=req.tenant_id,
            conversation_id=req.conversation_id,
            inputs=req.inputs,
            db=db,
        )

        resp = await dag_engine.execute(dag_spec, context)

        # Record Execution Audit Trace
        try:
            exec_record = WorkflowExecution(
                workflow_id=req.workflow_id,
                tenant_id=req.tenant_id,
                conversation_id=req.conversation_id,
                status=resp.status,
                inputs=req.inputs,
                outputs=resp.outputs,
                error_message=resp.error_message,
                latency_ms=resp.latency_ms,
                node_execution_count=len(resp.executed_nodes),
            )
            db.add(exec_record)
            await db.commit()
            resp.execution_id = exec_record.id
        except Exception as db_err:
            logger.warning("Failed to persist workflow execution record: %s", db_err)

        return resp

    async def list_definitions(
        self, db: AsyncSession
    ) -> list[WorkflowDefinitionResponse]:
        """List all available workflow definitions from DB and configuration files."""
        results = []
        if self.workflows_dir.exists():
            for p in self.workflows_dir.glob("*.json"):
                try:
                    data = await asyncio.to_thread(self._read_json_file, p)
                    meta = data.get("metadata", {})
                    spec = data.get("spec", {})
                    results.append(
                        WorkflowDefinitionResponse(
                            id=meta.get("name", p.stem),
                            name=meta.get("name", p.stem),
                            display_name=meta.get("display_name", p.stem),
                            description=meta.get("description"),
                            module_code=meta.get("module_code", "general"),
                            version="1.0.0",
                            is_active=True,
                            nodes_count=len(spec.get("nodes", [])),
                            edges_count=len(spec.get("edges", [])),
                        )
                    )
                except Exception as e:
                    logger.debug("Failed reading workflow file %s: %s", p, e)

        return results


workflow_service = WorkflowService()
