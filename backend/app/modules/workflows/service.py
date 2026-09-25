"""Workflow Service — Loading DAG Specifications, Executing Workflows & Storing Audit Traces."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.evaluation.models import EvaluationRun

if TYPE_CHECKING:
    from app.modules.assistants.schemas import AssistantRuntimeProfile
from app.modules.workflows.compiler import workflow_compiler
from app.modules.workflows.engine import dag_engine
from app.modules.workflows.models import (
    WorkflowApprovalRequest,
    WorkflowCheckpoint,
    WorkflowDefinition,
    WorkflowDraft,
    WorkflowExecution,
    WorkflowNodeExecution,
    WorkflowVersion,
)
from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.schemas import (
    WorkflowApprovalDecisionRequest,
    WorkflowApprovalResponse,
    WorkflowAssistantItem,
    WorkflowAssistantsUsageResponse,
    WorkflowDagSpec,
    WorkflowDefinitionResponse,
    WorkflowDraftResponse,
    WorkflowDraftSaveRequest,
    WorkflowEdgeSpec,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowNodeSpec,
    WorkflowPublishRequest,
    WorkflowValidationReport,
    WorkflowVersionResponse,
)

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for managing declarative DAG workflows and executing them."""

    def __init__(self) -> None:
        from app.core.paths import get_configs_dir

        # Base directory for workflow template JSON files
        self.workflows_dir = get_configs_dir() / "workflows"

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

        parsed_edges: list[WorkflowEdgeSpec] = []
        for e in raw_edges:
            src = e.get("source")
            tgt = e.get("target")

            source_id = src.get("node_id") if isinstance(src, dict) else str(src or "")
            source_port = (src.get("port") if isinstance(src, dict) else None) or e.get("source_port")

            target_id = tgt.get("node_id") if isinstance(tgt, dict) else str(tgt or "")
            target_port = (tgt.get("port") if isinstance(tgt, dict) else None) or e.get("target_port")

            parsed_edges.append(
                WorkflowEdgeSpec(
                    source=source_id,
                    target=target_id,
                    source_port=source_port,
                    target_port=target_port,
                    condition=e.get("condition"),
                    label=e.get("label"),
                )
            )

        edges = parsed_edges

        return WorkflowDagSpec(
            execution_mode=spec_data.get("execution_mode", "conversational"),
            entry_node_id=spec_data.get("entry_node_id", nodes[0].id if nodes else "chat_input"),
            input_schema=spec_data.get("input_schema", {}),
            output_schema=spec_data.get("output_schema", {}),
            policies=spec_data.get("policies", {}),
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def _serialize_dag_spec(dag_spec: WorkflowDagSpec) -> dict[str, Any]:
        """Serialize one canonical specification for storage and content hashing."""
        return dag_spec.model_dump(mode="json")

    @staticmethod
    def _to_draft_response(record: WorkflowDraft) -> WorkflowDraftResponse:
        return WorkflowDraftResponse(
            workflow_id=record.workflow_id,
            dag_spec=WorkflowDagSpec.model_validate(record.dag_spec),
            revision=record.revision,
            updated_by=record.updated_by,
            created_at=record.created_at.replace(tzinfo=UTC).isoformat(),
            updated_at=record.updated_at.replace(tzinfo=UTC).isoformat(),
        )

    @staticmethod
    def _to_version_response(record: WorkflowVersion) -> WorkflowVersionResponse:
        return WorkflowVersionResponse(
            id=record.id,
            workflow_id=record.workflow_id,
            version_number=record.version_number,
            content_hash=record.content_hash,
            dag_spec=WorkflowDagSpec.model_validate(record.dag_spec),
            validation_report=WorkflowValidationReport.model_validate(record.validation_report),
            published_by=record.published_by,
            published_at=record.published_at.replace(tzinfo=UTC).isoformat(),
        )

    @staticmethod
    def _content_hash(dag_spec: WorkflowDagSpec) -> str:
        canonical_json = json.dumps(
            dag_spec.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    async def _get_definition(self, db: AsyncSession, workflow_id: str) -> WorkflowDefinition:
        result = await db.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id)
        )
        workflow_definition = result.scalar_one_or_none()
        if workflow_definition is None:
            raise AppException(
                f"Không tìm thấy workflow '{workflow_id}'.",
                code="workflow_not_found",
                status_code=404,
                details={"workflow_id": workflow_id},
            )
        return workflow_definition

    async def get_workflow_spec(
        self, db: AsyncSession | None, workflow_id: str
    ) -> WorkflowDagSpec:
        """Retrieve a persisted DAG, or a checked-in template before first database seed."""
        if db is not None:
            stmt = select(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id)
            result = await db.execute(stmt)
            workflow_definition = result.scalar_one_or_none()
            if workflow_definition is not None:
                return self._parse_spec_from_json(workflow_definition.dag_spec)

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

        raise AppException(
            f"Không tìm thấy workflow '{workflow_id}'.",
            code="workflow_not_found",
            status_code=404,
            details={"workflow_id": workflow_id},
        )

    async def get_draft(self, db: AsyncSession, workflow_id: str) -> WorkflowDraftResponse:
        """Load the working copy, initializing it once from the active definition."""
        await self._get_definition(db, workflow_id)
        result = await db.execute(
            select(WorkflowDraft).where(WorkflowDraft.workflow_id == workflow_id)
        )
        draft = result.scalar_one_or_none()
        if draft is None:
            dag_spec = await self.get_workflow_spec(db, workflow_id)
            draft = WorkflowDraft(
                workflow_id=workflow_id,
                dag_spec=self._serialize_dag_spec(dag_spec),
            )
            db.add(draft)
            await db.commit()
            await db.refresh(draft)
        return self._to_draft_response(draft)

    async def save_draft(
        self,
        db: AsyncSession,
        workflow_id: str,
        request: WorkflowDraftSaveRequest,
    ) -> WorkflowDraftResponse:
        """Persist a workflow working copy with optimistic concurrency protection."""
        await self._get_definition(db, workflow_id)
        result = await db.execute(
            select(WorkflowDraft).where(WorkflowDraft.workflow_id == workflow_id)
        )
        draft = result.scalar_one_or_none()
        if draft is None:
            if request.expected_revision not in (None, 1):
                raise AppException(
                    "Bản nháp đã thay đổi trước khi được lưu.",
                    code="workflow_draft_conflict",
                    status_code=409,
                    details={"workflow_id": workflow_id, "actual_revision": 0},
                )
            draft = WorkflowDraft(
                workflow_id=workflow_id,
                dag_spec=self._serialize_dag_spec(request.dag_spec),
                revision=1,
                updated_by=request.updated_by,
            )
            db.add(draft)
        else:
            if (
                request.expected_revision is not None
                and request.expected_revision != draft.revision
            ):
                raise AppException(
                    "Bản nháp đã được một người dùng khác cập nhật. Hãy tải lại trước khi lưu.",
                    code="workflow_draft_conflict",
                    status_code=409,
                    details={
                        "workflow_id": workflow_id,
                        "expected_revision": request.expected_revision,
                        "actual_revision": draft.revision,
                    },
                )
            draft.dag_spec = self._serialize_dag_spec(request.dag_spec)
            draft.revision += 1
            draft.updated_by = request.updated_by

        await db.commit()
        await db.refresh(draft)
        return self._to_draft_response(draft)

    async def validate_draft(
        self, db: AsyncSession, workflow_id: str
    ) -> WorkflowValidationReport:
        """Compile the mutable working copy without publishing it."""
        draft = await self.get_draft(db, workflow_id)
        return workflow_compiler.validate(draft.dag_spec)

    async def publish_draft(
        self,
        db: AsyncSession,
        workflow_id: str,
        request: WorkflowPublishRequest,
    ) -> WorkflowVersionResponse:
        """Publish a validated draft as a new immutable version and activate it."""
        workflow_definition = await self._get_definition(db, workflow_id)
        draft_result = await db.execute(
            select(WorkflowDraft).where(WorkflowDraft.workflow_id == workflow_id)
        )
        draft = draft_result.scalar_one_or_none()
        if draft is None:
            raise AppException(
                "Workflow chưa có bản nháp để xuất bản.",
                code="workflow_draft_not_found",
                status_code=404,
                details={"workflow_id": workflow_id},
            )
        if request.expected_revision is not None and request.expected_revision != draft.revision:
            raise AppException(
                "Bản nháp đã thay đổi trước khi xuất bản.",
                code="workflow_draft_conflict",
                status_code=409,
                details={
                    "workflow_id": workflow_id,
                    "expected_revision": request.expected_revision,
                    "actual_revision": draft.revision,
                },
            )

        dag_spec = WorkflowDagSpec.model_validate(draft.dag_spec)
        validation_report = workflow_compiler.validate(dag_spec)
        if not validation_report.is_valid:
            raise AppException(
                "Workflow chưa đạt điều kiện xuất bản.",
                code="workflow_validation_failed",
                status_code=422,
                details=validation_report.model_dump(mode="json"),
            )

        # Quality Gate TM-08: Verify evaluation benchmark metrics if available
        assistant_code = workflow_id.replace("-assistant", "")
        eval_run_result = await db.execute(
            select(EvaluationRun)
            .where(
                (EvaluationRun.assistant_code == workflow_id)
                | (EvaluationRun.assistant_code == assistant_code)
            )
            .order_by(EvaluationRun.created_at.desc())
        )
        latest_eval = eval_run_result.scalars().first()
        if (
            latest_eval
            and latest_eval.status == "completed"
            and not latest_eval.meets_tm08_standard
        ):
            raise AppException(
                f"Workflow chưa đạt chuẩn chất lượng TM-08 (Faithfulness: {latest_eval.faithfulness_avg:.2f}, "
                f"Answer Relevance: {latest_eval.answer_relevance_avg:.2f}, Context Precision: {latest_eval.context_precision_avg:.2f}). "
                "Cần đạt tiêu chuẩn TM-08 trước khi phát hành chính thức.",
                code="workflow_quality_gate_failed",
                status_code=422,
                details={
                    "faithfulness_avg": latest_eval.faithfulness_avg,
                    "answer_relevance_avg": latest_eval.answer_relevance_avg,
                    "context_precision_avg": latest_eval.context_precision_avg,
                    "meets_tm08_standard": False,
                },
            )

        version_result = await db.execute(
            select(func.max(WorkflowVersion.version_number)).where(
                WorkflowVersion.workflow_id == workflow_id
            )
        )
        latest_version = version_result.scalar_one_or_none() or 0
        version = WorkflowVersion(
            workflow_id=workflow_id,
            version_number=latest_version + 1,
            content_hash=self._content_hash(dag_spec),
            dag_spec=self._serialize_dag_spec(dag_spec),
            validation_report=validation_report.model_dump(mode="json"),
            published_by=request.published_by,
        )
        db.add(version)
        await db.flush()

        workflow_definition.dag_spec = self._serialize_dag_spec(dag_spec)
        workflow_definition.version = f"1.0.{version.version_number}"
        workflow_definition.published_version_id = version.id
        await db.commit()
        await db.refresh(version)
        return self._to_version_response(version)

    async def list_versions(
        self, db: AsyncSession, workflow_id: str
    ) -> list[WorkflowVersionResponse]:
        """List immutable snapshots newest first for audit and rollback selection."""
        await self._get_definition(db, workflow_id)
        result = await db.execute(
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .order_by(WorkflowVersion.version_number.desc())
        )
        return [self._to_version_response(version) for version in result.scalars().all()]

    async def rollback_to_version(
        self,
        db: AsyncSession,
        workflow_id: str,
        version_id: str,
        published_by: str | None,
    ) -> WorkflowVersionResponse:
        """Promote a historical snapshot by creating a new immutable publication event."""
        source_result = await db.execute(
            select(WorkflowVersion).where(
                WorkflowVersion.id == version_id,
                WorkflowVersion.workflow_id == workflow_id,
            )
        )
        source_version = source_result.scalar_one_or_none()
        if source_version is None:
            raise AppException(
                f"Không tìm thấy phiên bản workflow '{version_id}'.",
                code="workflow_version_not_found",
                status_code=404,
                details={"workflow_id": workflow_id, "version_id": version_id},
            )

        workflow_definition = await self._get_definition(db, workflow_id)
        dag_spec = WorkflowDagSpec.model_validate(source_version.dag_spec)
        validation_report = workflow_compiler.validate(dag_spec)
        if not validation_report.is_valid:
            raise AppException(
                "Phiên bản lịch sử không còn hợp lệ với runtime hiện tại.",
                code="workflow_validation_failed",
                status_code=422,
                details=validation_report.model_dump(mode="json"),
            )

        version_result = await db.execute(
            select(func.max(WorkflowVersion.version_number)).where(
                WorkflowVersion.workflow_id == workflow_id
            )
        )
        latest_version = version_result.scalar_one_or_none() or 0
        restored_version = WorkflowVersion(
            workflow_id=workflow_id,
            version_number=latest_version + 1,
            content_hash=self._content_hash(dag_spec),
            dag_spec=self._serialize_dag_spec(dag_spec),
            validation_report=validation_report.model_dump(mode="json"),
            published_by=published_by,
        )
        db.add(restored_version)
        await db.flush()

        workflow_definition.dag_spec = self._serialize_dag_spec(dag_spec)
        workflow_definition.version = f"1.0.{restored_version.version_number}"
        workflow_definition.published_version_id = restored_version.id
        await db.commit()
        await db.refresh(restored_version)
        return self._to_version_response(restored_version)

    async def execute(
        self,
        db: AsyncSession,
        req: WorkflowExecuteRequest,
        *,
        assistant_profile: AssistantRuntimeProfile | None = None,
        correlation_id: str | None = None,
    ) -> WorkflowExecuteResponse:
        """Run workflow DAG end-to-end and audit execution trace."""
        # Check if caller requested an exact immutable workflow version (e.g. pinned by assistant)
        target_version_id = req.workflow_version_id
        if not target_version_id:
            version_result = await db.execute(
                select(WorkflowDefinition.published_version_id).where(
                    WorkflowDefinition.id == req.workflow_id
                )
            )
            target_version_id = version_result.scalar_one_or_none()

        workflow_version_id = target_version_id

        # Exact-version resolution: read immutable dag_spec from published version if present
        if workflow_version_id:
            version_stmt = select(WorkflowVersion.dag_spec).where(WorkflowVersion.id == workflow_version_id)
            v_spec = (await db.execute(version_stmt)).scalar_one_or_none()
            if not v_spec:
                raise AppException(
                    f"Không tìm thấy phiên bản workflow đã công bố '{workflow_version_id}'.",
                    code="workflow_version_not_found",
                    status_code=404,
                    details={"workflow_id": req.workflow_id, "workflow_version_id": workflow_version_id},
                )
            dag_spec = WorkflowDagSpec.model_validate(v_spec)
        else:
            dag_spec = await self.get_workflow_spec(db, req.workflow_id)
        context = WorkflowContext(
            workflow_id=req.workflow_id,
            tenant_id=req.tenant_id,
            conversation_id=req.conversation_id,
            inputs=req.inputs,
            db=db,
            assistant_profile=assistant_profile,
            correlation_id=correlation_id,
        )
        execution_record = WorkflowExecution(
            workflow_id=req.workflow_id,
            tenant_id=req.tenant_id,
            conversation_id=req.conversation_id,
            assistant_id=assistant_profile.assistant_id if assistant_profile else None,
            assistant_revision=assistant_profile.assistant_revision if assistant_profile else None,
            workflow_version_id=workflow_version_id,
            correlation_id=correlation_id,
            runtime_profile=assistant_profile.model_dump(mode="json") if assistant_profile else None,
            inputs=req.inputs,
        )
        db.add(execution_record)
        await db.flush()
        context.execution_id = execution_record.id
        resp = await dag_engine.execute(dag_spec, context)
        execution_record.status = resp.status
        execution_record.outputs = resp.outputs
        execution_record.error_message = resp.error_message
        execution_record.latency_ms = resp.latency_ms
        execution_record.node_execution_count = len(resp.executed_nodes)
        if resp.status != "paused_for_approval":
            execution_record.completed_at = datetime.now(UTC).replace(tzinfo=None)

        self._add_node_execution_records(execution_record.id, context, db)
        if resp.status == "paused_for_approval" and resp.paused_node_id:
            approval = await self._create_approval_checkpoint(
                db,
                execution_record.id,
                context,
                resp,
            )
            resp.outputs["approval_id"] = approval.id
            execution_record.outputs = resp.outputs

        await db.commit()
        resp.execution_id = execution_record.id
        return resp

    @staticmethod
    def _add_node_execution_records(
        execution_id: str,
        context: WorkflowContext,
        db: AsyncSession,
    ) -> None:
        for trace in context.node_traces:
            db.add(
                WorkflowNodeExecution(
                    execution_id=execution_id,
                    node_id=trace.node_id,
                    node_type=trace.node_type,
                    status=trace.status,
                    input_data=trace.input_data,
                    output_data=trace.output_data,
                    latency_ms=trace.latency_ms,
                )
            )

    async def _create_approval_checkpoint(
        self,
        db: AsyncSession,
        execution_id: str,
        context: WorkflowContext,
        response: WorkflowExecuteResponse,
    ) -> WorkflowApprovalRequest:
        checkpoint = WorkflowCheckpoint(
            execution_id=execution_id,
            resume_node_id=response.paused_node_id or "",
            completed_node_ids=[
                node_id
                for node_id in response.executed_nodes
                if node_id != response.paused_node_id
            ],
            node_data=context.node_data,
            outputs=context.outputs,
        )
        db.add(checkpoint)
        await db.flush()
        node_id = response.paused_node_id or ""
        node_output = response.outputs.get(node_id, {})
        params = node_output.get("parameters") or node_output.get("inputs") or {}
        import hashlib
        import json
        clean_params = {k: v for k, v in params.items() if k not in ("approval_id", "is_approved", "approved_by")}
        payload_hash = (
            hashlib.sha256(json.dumps(clean_params, sort_keys=True).encode("utf-8")).hexdigest()
            if clean_params
            else None
        )
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=24)

        approval = WorkflowApprovalRequest(
            execution_id=execution_id,
            checkpoint_id=checkpoint.id,
            node_id=node_id,
            tool_name=response.outputs.get("tool_name"),
            payload_hash=payload_hash,
            requested_by=context.inputs.get("actor_id") or context.inputs.get("username") or "user",
            expires_at=expires_at,
            description=str(response.outputs.get("action_required", "Cần phê duyệt thủ công.")),
        )
        db.add(approval)
        await db.flush()
        return approval

    @staticmethod
    def _to_approval_response(record: WorkflowApprovalRequest) -> WorkflowApprovalResponse:
        return WorkflowApprovalResponse(
            id=record.id,
            execution_id=record.execution_id,
            checkpoint_id=record.checkpoint_id,
            node_id=record.node_id,
            tool_name=record.tool_name,
            payload_hash=record.payload_hash,
            requested_by=record.requested_by,
            expires_at=(record.expires_at.replace(tzinfo=UTC).isoformat() if record.expires_at else None),
            description=record.description,
            status=record.status,
            decided_by=record.decided_by,
            decision_reason=record.decision_reason,
            created_at=record.created_at.replace(tzinfo=UTC).isoformat(),
            decided_at=(record.decided_at.replace(tzinfo=UTC).isoformat() if record.decided_at else None),
        )

    async def list_pending_approvals(
        self, db: AsyncSession
    ) -> list[WorkflowApprovalResponse]:
        """List real pending approval checkpoints; no synthetic approval cards are returned."""
        result = await db.execute(
            select(WorkflowApprovalRequest)
            .where(WorkflowApprovalRequest.status == "pending")
            .order_by(WorkflowApprovalRequest.created_at.desc())
        )
        return [self._to_approval_response(record) for record in result.scalars().all()]

    async def decide_approval(
        self,
        db: AsyncSession,
        execution_id: str,
        approval_id: str,
        request: WorkflowApprovalDecisionRequest,
    ) -> WorkflowExecuteResponse:
        """Persist a human decision and resume only the approved checkpoint."""
        approval_result = await db.execute(
            select(WorkflowApprovalRequest).where(
                WorkflowApprovalRequest.id == approval_id,
                WorkflowApprovalRequest.execution_id == execution_id,
            )
        )
        approval = approval_result.scalar_one_or_none()
        if approval is None:
            raise AppException(
                f"Không tìm thấy yêu cầu phê duyệt '{approval_id}'.",
                code="workflow_approval_not_found",
                status_code=404,
                details={"execution_id": execution_id, "approval_id": approval_id},
            )
        if approval.status != "pending":
            raise AppException(
                "Yêu cầu phê duyệt đã được xử lý trước đó.",
                code="workflow_approval_already_decided",
                status_code=409,
                details={"approval_id": approval_id, "status": approval.status},
            )

        if approval.expires_at:
            exp = approval.expires_at
            if exp.tzinfo is not None:
                exp = exp.astimezone(UTC).replace(tzinfo=None)
            now_utc = datetime.now(UTC).replace(tzinfo=None)
            if exp < now_utc:
                approval.status = "expired"
                await db.commit()
                raise AppException(
                    f"Yêu cầu phê duyệt '{approval_id}' đã hết hạn.",
                    code="approval_expired",
                    status_code=403,
                    details={"approval_id": approval_id, "expires_at": approval.expires_at.isoformat()},
                )

        execution_result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution_record = execution_result.scalar_one_or_none()
        if execution_record is None:
            raise AppException(
                f"Không tìm thấy phiên chạy workflow '{execution_id}'.",
                code="workflow_execution_not_found",
                status_code=404,
                details={"execution_id": execution_id},
            )
        checkpoint_result = await db.execute(
            select(WorkflowCheckpoint).where(WorkflowCheckpoint.id == approval.checkpoint_id)
        )
        checkpoint = checkpoint_result.scalar_one_or_none()
        if checkpoint is None or checkpoint.status != "pending":
            raise AppException(
                "Không tìm thấy checkpoint đang chờ phê duyệt.",
                code="workflow_checkpoint_not_found",
                status_code=409,
                details={"execution_id": execution_id, "approval_id": approval_id},
            )

        approval.status = "approved" if request.approved else "rejected"
        approval.decided_by = request.decided_by
        approval.decision_reason = request.decision_reason
        approval.decided_at = datetime.now(UTC).replace(tzinfo=None)
        checkpoint.status = "resumed" if request.approved else "rejected"
        checkpoint.resumed_at = datetime.now(UTC).replace(tzinfo=None)

        if not request.approved:
            execution_record.status = "failed"
            execution_record.error_message = "Yêu cầu đã bị từ chối tại bước phê duyệt thủ công."
            execution_record.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await db.commit()
            return WorkflowExecuteResponse(
                execution_id=execution_record.id,
                workflow_id=execution_record.workflow_id,
                status="failed",
                outputs=execution_record.outputs,
                error_message=execution_record.error_message,
            )

        # Exact-version resume: read immutable dag_spec from version when available
        if execution_record.workflow_version_id:
            version_stmt = select(WorkflowVersion.dag_spec).where(WorkflowVersion.id == execution_record.workflow_version_id)
            v_spec = (await db.execute(version_stmt)).scalar_one_or_none()
            if not v_spec:
                raise AppException(
                    f"Không tìm thấy phiên bản workflow '{execution_record.workflow_version_id}' để tiếp tục thực thi.",
                    code="workflow_version_not_found",
                    status_code=404,
                    details={
                        "workflow_id": execution_record.workflow_id,
                        "workflow_version_id": execution_record.workflow_version_id,
                    },
                )
            dag_spec = WorkflowDagSpec.model_validate(v_spec)
        else:
            dag_spec = await self.get_workflow_spec(db, execution_record.workflow_id)
        from app.modules.assistants.schemas import AssistantRuntimeProfile

        runtime_profile = (
            AssistantRuntimeProfile.model_validate(execution_record.runtime_profile)
            if execution_record.runtime_profile
            else None
        )
        resume_inputs = {
            **execution_record.inputs,
            "is_approved": True,
            "approved_by": request.decided_by,
        }
        context = WorkflowContext(
            workflow_id=execution_record.workflow_id,
            tenant_id=execution_record.tenant_id,
            conversation_id=execution_record.conversation_id,
            inputs=resume_inputs,
            outputs=checkpoint.outputs,
            node_data=checkpoint.node_data,
            db=db,
            assistant_profile=runtime_profile,
            execution_id=execution_record.id,
            correlation_id=execution_record.correlation_id,
        )
        response = await dag_engine.execute(
            dag_spec,
            context,
            start_node_id=checkpoint.resume_node_id,
            completed_node_ids=set(checkpoint.completed_node_ids),
        )
        execution_record.status = response.status
        execution_record.outputs = response.outputs
        execution_record.error_message = response.error_message
        execution_record.latency_ms += response.latency_ms
        execution_record.node_execution_count += len(context.node_traces)
        if response.status != "paused_for_approval":
            execution_record.completed_at = datetime.now(UTC).replace(tzinfo=None)
        self._add_node_execution_records(execution_record.id, context, db)
        await db.commit()
        response.execution_id = execution_record.id
        return response

    async def list_definitions(
        self, db: AsyncSession
    ) -> list[WorkflowDefinitionResponse]:
        """List persisted definitions, using checked-in templates only before initial seed."""
        database_result = await db.execute(
            select(WorkflowDefinition).order_by(WorkflowDefinition.display_name)
        )
        database_records = database_result.scalars().all()
        if database_records:
            return [
                WorkflowDefinitionResponse(
                    id=record.id,
                    name=record.name,
                    display_name=record.display_name,
                    description=record.description,
                    module_code=record.module_code,
                    version=record.version,
                    is_active=record.is_active,
                    nodes_count=len(self._parse_spec_from_json(record.dag_spec).nodes),
                    edges_count=len(self._parse_spec_from_json(record.dag_spec).edges),
                    published_version_id=record.published_version_id,
                )
                for record in database_records
            ]

        results: list[WorkflowDefinitionResponse] = []
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

    async def list_executions(self, db: AsyncSession) -> list[dict[str, Any]]:
        """List only execution records actually persisted by the runtime."""
        result = await db.execute(
            select(WorkflowExecution)
            .order_by(WorkflowExecution.created_at.desc())
            .limit(50)
        )
        records = result.scalars().all()
        if not records:
            return []

        node_result = await db.execute(
            select(WorkflowNodeExecution)
            .where(WorkflowNodeExecution.execution_id.in_([record.id for record in records]))
            .order_by(WorkflowNodeExecution.created_at)
        )
        executed_nodes_by_run: dict[str, list[str]] = {}
        for node_record in node_result.scalars().all():
            executed_nodes_by_run.setdefault(node_record.execution_id, []).append(node_record.node_id)
        return [
            {
                "id": record.id,
                "workflow_id": record.workflow_id,
                "workflow_name": f"Luồng {record.workflow_id}",
                "status": record.status,
                "duration_ms": round(record.latency_ms, 1),
                "steps_completed": record.node_execution_count,
                "total_steps": record.node_execution_count,
                "started_at": record.created_at.replace(tzinfo=UTC).isoformat(),
                "executed_nodes": executed_nodes_by_run.get(record.id, []),
            }
            for record in records
        ]

    async def sync_default_workflows(self, db: AsyncSession) -> int:
        """Seed checked-in workflow definitions, drafts, and initial published versions."""
        if not self.workflows_dir.exists():
            return 0

        synced = 0
        for json_file in sorted(self.workflows_dir.glob("*.json")):
            # Skip reusable templates (e.g. _base-assistant): loadable via
            # get_workflow_spec/fork but never seeded as live definitions.
            if json_file.name.startswith("_"):
                continue
            try:
                data = await asyncio.to_thread(self._read_json_file, json_file)
                meta = data.get("metadata", {})
                workflow_id = meta.get("name") or json_file.stem.replace(".v1alpha1", "")
                display_name = meta.get("display_name") or workflow_id
                description = meta.get("description") or ""
                module_code = meta.get("module_code") or "general"
                tenant_id = meta.get("scope", {}).get("tenant_id", "tenant_qnu")

                dag_spec = self._parse_spec_from_json(data)
                validation = workflow_compiler.validate(dag_spec)
                if not validation.is_valid:
                    continue

                serialized_spec = self._serialize_dag_spec(dag_spec)
                content_hash = self._content_hash(dag_spec)

                stmt = select(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id)
                res = await db.execute(stmt)
                wf_def = res.scalar_one_or_none()
                if wf_def is None:
                    wf_def = WorkflowDefinition(
                        id=workflow_id,
                        name=workflow_id,
                        display_name=display_name,
                        description=description,
                        module_code=module_code,
                        tenant_id=tenant_id,
                        version="1.0.0",
                        is_active=True,
                        dag_spec=serialized_spec,
                    )
                    db.add(wf_def)
                    await db.flush()
                else:
                    wf_def.display_name = display_name
                    wf_def.description = description
                    wf_def.module_code = module_code
                    wf_def.dag_spec = serialized_spec

                draft_stmt = select(WorkflowDraft).where(WorkflowDraft.workflow_id == workflow_id)
                draft_res = await db.execute(draft_stmt)
                draft = draft_res.scalar_one_or_none()
                if draft is None:
                    draft = WorkflowDraft(
                        workflow_id=workflow_id,
                        dag_spec=serialized_spec,
                        revision=1,
                        updated_by="system_seeder",
                    )
                    db.add(draft)
                    await db.flush()
                else:
                    draft.dag_spec = serialized_spec
                    draft.revision += 1

                ver_stmt = select(WorkflowVersion).where(
                    WorkflowVersion.workflow_id == workflow_id,
                    WorkflowVersion.version_number == 1,
                )
                ver_res = await db.execute(ver_stmt)
                version = ver_res.scalar_one_or_none()
                if version is None:
                    version = WorkflowVersion(
                        workflow_id=workflow_id,
                        version_number=1,
                        content_hash=content_hash,
                        dag_spec=serialized_spec,
                        validation_report=validation.model_dump(mode="json"),
                        published_by="system_seeder",
                    )
                    db.add(version)
                    await db.flush()
                else:
                    version.dag_spec = serialized_spec
                    version.content_hash = content_hash
                    version.validation_report = validation.model_dump(mode="json")

                if wf_def.published_version_id != version.id:
                    wf_def.published_version_id = version.id

                synced += 1
            except Exception as exc:
                logger.warning("Failed to sync default workflow %s: %s", json_file.name, exc)

        await db.commit()
        return synced

    async def get_workflow_assistants(
        self, db: AsyncSession, workflow_id: str
    ) -> WorkflowAssistantsUsageResponse:
        """Query assistants currently bound to this workflow to audit shared mutable usage."""
        from app.modules.assistants.models import AssistantModel

        wf_res = await db.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id)
        )
        wf = wf_res.scalar_one_or_none()
        ownership = getattr(wf, "ownership", "shared") if wf else "shared"

        asst_res = await db.execute(
            select(AssistantModel).where(AssistantModel.workflow_id == workflow_id)
        )
        assistants = asst_res.scalars().all()

        items = [
            WorkflowAssistantItem(
                id=a.id,
                code=a.code,
                name=a.name,
                is_active=a.is_active,
                workflow_ownership=getattr(a, "workflow_ownership", "private"),
            )
            for a in assistants
        ]
        return WorkflowAssistantsUsageResponse(
            workflow_id=workflow_id,
            ownership=ownership,
            total_assistants=len(items),
            assistants=items,
        )

    @staticmethod
    def _inject_assistant_bindings(
        dag_spec: WorkflowDagSpec,
        *,
        module_code: str | None = None,
        collection_id: str | None = None,
        system_prompt: str | None = None,
        rewrite_instruction: str | None = None,
    ) -> WorkflowDagSpec:
        """Inject assistant-specific bindings into a cloned DAG spec.

        Reusable for any new assistant: sets RAG collection/module,
        system prompt, and query-rewrite instruction without manual JSON edits.
        """
        for node in dag_spec.nodes:
            if node.type == "core.knowledge.answer":
                if module_code:
                    node.config["module_code"] = module_code
                if collection_id:
                    node.config["collection_id"] = collection_id
                if system_prompt:
                    node.config["system_prompt"] = system_prompt
            elif node.type == "query.rewrite" and rewrite_instruction:
                node.config["instruction"] = rewrite_instruction
        return dag_spec

    async def fork_workflow(
        self,
        db: AsyncSession,
        source_workflow_id: str,
        new_workflow_id: str,
        new_name: str,
        assistant_id: str | None = None,
        module_code: str | None = None,
        collection_id: str | None = None,
        system_prompt: str | None = None,
        rewrite_instruction: str | None = None,
    ) -> WorkflowDefinitionResponse:
        """Fork an existing or template workflow into an isolated private workflow for an assistant."""
        existing = (
            await db.execute(
                select(WorkflowDefinition).where(WorkflowDefinition.id == new_workflow_id)
            )
        ).scalar_one_or_none()
        if existing:
            return WorkflowDefinitionResponse(
                id=existing.id,
                name=existing.name,
                display_name=existing.display_name,
                description=existing.description,
                module_code=existing.module_code,
                version=existing.version,
                is_active=existing.is_active,
                nodes_count=len(self._parse_spec_from_json(existing.dag_spec).nodes),
                edges_count=len(self._parse_spec_from_json(existing.dag_spec).edges),
                published_version_id=existing.published_version_id,
                ownership=existing.ownership,
                assistant_id=existing.assistant_id,
            )

        source_draft = (
            await db.execute(
                select(WorkflowDraft).where(WorkflowDraft.workflow_id == source_workflow_id)
            )
        ).scalar_one_or_none()
        if source_draft:
            dag_spec = WorkflowDagSpec.model_validate(source_draft.dag_spec)
        else:
            dag_spec = await self.get_workflow_spec(db, source_workflow_id)

        dag_spec = self._inject_assistant_bindings(
            dag_spec,
            module_code=module_code,
            collection_id=collection_id,
            system_prompt=system_prompt,
            rewrite_instruction=rewrite_instruction,
        )

        serialized_spec = self._serialize_dag_spec(dag_spec)
        new_record = WorkflowDefinition(
            id=new_workflow_id,
            name=new_workflow_id,
            display_name=new_name,
            description=f"Quy trình riêng tạo lập cho trợ lý {new_name}.",
            module_code=module_code or "custom",
            version="1.0.0",
            published_version_id=None,
            ownership="private",
            assistant_id=assistant_id,
            is_active=True,
            dag_spec=serialized_spec,
        )
        db.add(new_record)
        await db.flush()

        new_draft = WorkflowDraft(
            workflow_id=new_workflow_id,
            dag_spec=serialized_spec,
            revision=1,
            updated_by="Hệ thống (Fork)",
        )
        db.add(new_draft)
        await db.commit()
        await db.refresh(new_record)

        return WorkflowDefinitionResponse(
            id=new_record.id,
            name=new_record.name,
            display_name=new_record.display_name,
            description=new_record.description,
            module_code=new_record.module_code,
            version=new_record.version,
            is_active=new_record.is_active,
            nodes_count=len(dag_spec.nodes),
            edges_count=len(dag_spec.edges),
            published_version_id=None,
            ownership=new_record.ownership,
            assistant_id=new_record.assistant_id,
        )



workflow_service = WorkflowService()
