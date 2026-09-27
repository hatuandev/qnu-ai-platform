"""Semantic quality gate and targeted one-pass repair for document AST drafts."""

from __future__ import annotations

import json
import logging

from app.core.exceptions import AppException
from app.modules.modelops.schemas import ChatMessage
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.nodes.drafting_compose_node import (
    build_draft_payload,
    generate_document_ast,
)
from app.modules.workflows.nodes.drafting_contracts import (
    DocumentAst,
    semantic_quality_issues,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)


def _get_draft(node_spec: WorkflowNodeSpec, context: WorkflowContext) -> dict:
    draft = context.node_inputs.get(node_spec.id, {}).get("draft")
    if not isinstance(draft, dict):
        draft = context.node_data.get("draft") or context.node_data.get("drafting_draft")
    if not isinstance(draft, dict) or not isinstance(draft.get("ast"), dict):
        raise AppException(
            "Không nhận được document_ast.v1 để kiểm định.",
            code="drafting_ast_missing",
            status_code=422,
            details={"node_id": node_spec.id},
        )
    return draft


class DraftingQualityNodeHandler(BaseNodeHandler):
    """Route a semantically complete AST to finalization or to targeted repair."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        draft = _get_draft(node_spec, context)
        ast = DocumentAst.model_validate(draft["ast"])
        plan = draft.get("plan") if isinstance(draft.get("plan"), dict) else {}
        obligations = [str(item) for item in plan.get("semantic_obligations", [])]
        issues = semantic_quality_issues(ast, obligations)
        covered_roles = sorted(
            {block.role for block in ast.blocks if block.role in obligations}
        )
        report = {
            "passed": not issues,
            "required_roles": obligations,
            "covered_roles": covered_roles,
            "issues": issues,
        }
        context.node_data["drafting_draft"] = draft
        context.node_data["drafting_quality_report"] = report
        selected_port = "accepted" if not issues else "repair"
        logger.info(
            "Drafting quality [%s]: passed=%s required=%d issues=%d",
            node_spec.id,
            not issues,
            len(obligations),
            len(issues),
        )
        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "draft": draft,
                "quality_report": report,
                "accepted": draft,
                "repair": {"draft": draft, "quality_report": report},
            },
            selected_port=selected_port,
        )


class DraftingRepairNodeHandler(BaseNodeHandler):
    """Repair only failed semantic obligations while preserving grounded facts."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        port_inputs = context.node_inputs.get(node_spec.id, {})
        repair_bundle = port_inputs.get("repair_bundle")
        if not isinstance(repair_bundle, dict):
            repair_bundle = {}
        draft = (
            repair_bundle.get("draft")
            or port_inputs.get("draft")
            or context.node_data.get("drafting_draft")
        )
        report = (
            repair_bundle.get("quality_report")
            or port_inputs.get("quality_report")
            or context.node_data.get("drafting_quality_report")
        )
        if not isinstance(draft, dict) or not isinstance(draft.get("ast"), dict):
            raise AppException(
                "Không nhận được bản nháp để sửa.",
                code="drafting_repair_input_missing",
                status_code=422,
            )
        if not isinstance(report, dict):
            report = {"issues": []}
        plan = draft.get("plan") if isinstance(draft.get("plan"), dict) else {}
        repair_payload = {
            "original_request": plan.get("source_text"),
            "provided_values": plan.get("explicit_fields", {}),
            "field_provenance": plan.get("field_provenance", {}),
            "semantic_obligations": plan.get("semantic_obligations", []),
            "quality_issues": report.get("issues", []),
            "current_document_ast": draft["ast"],
            "instructions": (
                "Trả lại toàn bộ document_ast.v1 sau khi sửa đúng các lỗi kiểm định. "
                "Giữ nguyên mọi dữ kiện có nguồn, placeholder và hình thái văn bản. "
                "Không kéo dài nội dung nếu không cần và không tạo căn cứ hoặc số liệu mới."
            ),
        }
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "Bạn là biên tập viên văn bản hành chính QNU. Chỉ sửa các nghĩa còn thiếu "
                    "trong document_ast.v1; không thay đổi dữ kiện đã có nguồn và không tự bịa "
                    "thông tin hành chính. Trả về duy nhất JSON hợp lệ."
                ),
            ),
            ChatMessage(role="user", content=json.dumps(repair_payload, ensure_ascii=False)),
        ]
        ast, response = await generate_document_ast(
            node_spec,
            context,
            messages,
            error_code="drafting_revision_failed",
        )
        issues = semantic_quality_issues(
            ast,
            [str(item) for item in plan.get("semantic_obligations", [])],
        )
        if issues:
            raise AppException(
                "Bản nháp vẫn thiếu nghĩa bắt buộc sau vòng sửa có mục tiêu.",
                code="drafting_semantic_quality_failed",
                status_code=502,
                details={"node_id": node_spec.id, "quality_issues": issues},
            )
        repaired = build_draft_payload(ast, plan, response)
        repaired["revision"] = {
            "reason": "semantic_quality_repair",
            "issues_resolved": report.get("issues", []),
        }
        context.node_data["drafting_draft"] = repaired
        context.node_data["drafting_ast"] = ast.model_dump(mode="json")
        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"draft": repaired, "quality_report": {"passed": True, "issues": []}},
        )
