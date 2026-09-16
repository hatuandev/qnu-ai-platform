"""FastAPI Router for Workflow DAG Execution & Definitions."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.workflows.schemas import (
    WorkflowDagSpec,
    WorkflowDefinitionResponse,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
)
from app.modules.workflows.service import workflow_service

router = APIRouter(prefix="/workflows", tags=["Workflow DAG Engine"])


@router.post(
    "/execute",
    response_model=WorkflowExecuteResponse,
    summary="Thực thi luồng công việc DAG theo đặc tả phân nhánh",
)
async def execute_workflow(
    body: WorkflowExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowExecuteResponse:
    return await workflow_service.execute(db, body)


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
    "/executions",
    summary="Lịch sử các phiên thực thi luồng DAG (Audit Execution Trails)",
)
async def list_executions(
    db: AsyncSession = Depends(get_db),
):
    return await workflow_service.list_executions(db)

