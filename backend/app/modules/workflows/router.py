"""FastAPI Router for Workflow DAG Execution & Definitions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.workflows.schemas import (
    WorkflowApprovalDecisionRequest,
    WorkflowApprovalResponse,
    WorkflowAssistantsUsageResponse,
    WorkflowDagSpec,
    WorkflowDefinitionResponse,
    WorkflowDraftResponse,
    WorkflowDraftSaveRequest,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowPublishRequest,
    WorkflowRollbackRequest,
    WorkflowValidationReport,
    WorkflowVersionResponse,
)
from app.modules.workflows.service import workflow_service

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post(
    "/execute",
    response_model=WorkflowExecuteResponse,
    summary="Thực thi luồng công việc DAG theo đặc tả phân nhánh",
)
async def execute_workflow(
    body: WorkflowExecuteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WorkflowExecuteResponse:
    return await workflow_service.execute(
        db,
        body,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get(
    "/definitions",
    response_model=list[WorkflowDefinitionResponse],
    summary="Liệt kê danh sách các định nghĩa luồng DAG có sẵn trên hệ thống",
)
async def list_workflows(
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowDefinitionResponse]:
    return await workflow_service.list_definitions(db)


@router.get(
    "/definitions/{workflow_id}",
    response_model=WorkflowDagSpec,
    summary="Tra cứu chi tiết đặc tả cấu trúc Nodes & Edges của một Workflow",
)
async def get_workflow_definition(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
) -> WorkflowDagSpec:
    return await workflow_service.get_workflow_spec(db, workflow_id)


@router.get(
    "/definitions/{workflow_id}/assistants",
    response_model=WorkflowAssistantsUsageResponse,
    summary="Tra cứu danh sách các trợ lý AI đang gắn với quy trình này",
)
async def get_workflow_assistants(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
) -> WorkflowAssistantsUsageResponse:
    return await workflow_service.get_workflow_assistants(db, workflow_id)


@router.get(
    "/definitions/{workflow_id}/draft",
    response_model=WorkflowDraftResponse,
    summary="Lấy bản nháp Canvas hiện tại của workflow",
)
async def get_workflow_draft(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
) -> WorkflowDraftResponse:
    return await workflow_service.get_draft(db, workflow_id)


@router.put(
    "/definitions/{workflow_id}/draft",
    response_model=WorkflowDraftResponse,
    summary="Lưu bản nháp Canvas với kiểm soát xung đột phiên bản",
)
async def save_workflow_draft(
    workflow_id: str,
    body: WorkflowDraftSaveRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowDraftResponse:
    return await workflow_service.save_draft(db, workflow_id, body)


@router.post(
    "/definitions/{workflow_id}/draft/validate",
    response_model=WorkflowValidationReport,
    summary="Kiểm tra cấu trúc DAG trước khi xuất bản",
)
async def validate_workflow_draft(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
) -> WorkflowValidationReport:
    return await workflow_service.validate_draft(db, workflow_id)


@router.post(
    "/definitions/{workflow_id}/publish",
    response_model=WorkflowVersionResponse,
    summary="Xuất bản bản nháp hợp lệ thành phiên bản bất biến",
)
async def publish_workflow_draft(
    workflow_id: str,
    body: WorkflowPublishRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowVersionResponse:
    return await workflow_service.publish_draft(db, workflow_id, body)


@router.get(
    "/definitions/{workflow_id}/versions",
    response_model=list[WorkflowVersionResponse],
    summary="Liệt kê lịch sử phiên bản workflow",
)
async def list_workflow_versions(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowVersionResponse]:
    return await workflow_service.list_versions(db, workflow_id)


@router.post(
    "/definitions/{workflow_id}/versions/{version_id}/rollback",
    response_model=WorkflowVersionResponse,
    summary="Khôi phục một phiên bản bằng sự kiện xuất bản mới",
)
async def rollback_workflow_version(
    workflow_id: str,
    version_id: str,
    body: WorkflowRollbackRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowVersionResponse:
    return await workflow_service.rollback_to_version(
        db,
        workflow_id,
        version_id,
        body.published_by,
    )


@router.get(
    "/executions",
    summary="Lịch sử các phiên thực thi luồng DAG (Audit Execution Trails)",
)
async def list_executions(
    db: AsyncSession = Depends(get_db),
):
    return await workflow_service.list_executions(db)


@router.get(
    "/approvals",
    response_model=list[WorkflowApprovalResponse],
    summary="Liệt kê các checkpoint đang chờ phê duyệt thật",
)
async def list_pending_approvals(
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowApprovalResponse]:
    return await workflow_service.list_pending_approvals(db)


@router.post(
    "/executions/{execution_id}/approvals/{approval_id}/decision",
    response_model=WorkflowExecuteResponse,
    summary="Ghi nhận quyết định của cán bộ và tiếp tục checkpoint đã duyệt",
)
async def decide_workflow_approval(
    execution_id: str,
    approval_id: str,
    body: WorkflowApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowExecuteResponse:
    return await workflow_service.decide_approval(db, execution_id, approval_id, body)
