"""Unit & Integration Tests for Workflow DAG Engine, Nodes, Branching & Executions."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.modules.workflows.engine import dag_engine
from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.nodes.chat_input_node import ChatInputNodeHandler
from app.modules.workflows.nodes.condition_route_node import ConditionRouteNodeHandler
from app.modules.workflows.nodes.human_approval_node import HumanApprovalNodeHandler
from app.modules.workflows.schemas import (
    WorkflowDagSpec,
    WorkflowEdgeSpec,
    WorkflowNodeSpec,
)


@pytest.mark.asyncio
async def test_chat_input_node_handler():
    """Verify ChatInputNode trims and extracts user question into context."""
    handler = ChatInputNodeHandler()
    spec = WorkflowNodeSpec(id="in_1", type="input.chat", config={"trim": True, "max_length": 100})
    ctx = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"message": "   Điểm chuẩn ngành CNTT năm 2024?   "},
    )
    res = await handler.execute(spec, ctx)
    assert res.status == "completed"
    assert ctx.node_data["user_message"] == "Điểm chuẩn ngành CNTT năm 2024?"


@pytest.mark.asyncio
async def test_condition_route_node_branching():
    """Verify ConditionRouteNode branches to greeting or default node according to regex intent."""
    handler = ConditionRouteNodeHandler()
    spec = WorkflowNodeSpec(
        id="route_1",
        type="condition.route",
        config={
            "rules": [
                {
                    "id": "greet_rule",
                    "match": {"intent": r"\b(?:xin\s+chào|chào|hi|hello)\b"},
                    "to": "greeting_node",
                }
            ],
            "default_node": "knowledge_node",
        },
    )

    # Test Branch 1: Greeting
    ctx_greet = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
        node_data={"user_message": "Xin chào Trợ lý Tuyển sinh!"},
    )
    res_greet = await handler.execute(spec, ctx_greet)
    assert res_greet.next_node_override == "greeting_node"

    # Test Branch 2: General Knowledge Question
    ctx_faq = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
        node_data={"user_message": "Chỉ tiêu tuyển sinh năm 2025 là bao nhiêu?"},
    )
    res_faq = await handler.execute(spec, ctx_faq)
    assert res_faq.next_node_override == "knowledge_node"


@pytest.mark.asyncio
async def test_human_approval_node_checkpoint():
    """Verify HumanApprovalNode halts DAG execution until supervisor grants approval."""
    handler = HumanApprovalNodeHandler()
    spec = WorkflowNodeSpec(id="app_1", type="tool.human_approval", config={"description": "Duyệt đề thi"})

    # Case 1: Not approved yet -> pause DAG
    ctx_unapproved = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"is_approved": False},
    )
    res_unapproved = await handler.execute(spec, ctx_unapproved)
    assert res_unapproved.status == "paused_for_approval"

    # Case 2: Approved by supervisor -> continue DAG
    ctx_approved = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"is_approved": True, "approved_by": "truong_khoa"},
    )
    res_approved = await handler.execute(spec, ctx_approved)
    assert res_approved.status == "completed"


@pytest.mark.asyncio
async def test_dag_engine_branching_execution():
    """Verify WorkflowDAGEngine follows conditional branching correctly."""
    dag_spec = WorkflowDagSpec(
        entry_node_id="input_node",
        nodes=[
            WorkflowNodeSpec(id="input_node", type="input.chat"),
            WorkflowNodeSpec(
                id="router_node",
                type="condition.route",
                config={
                    "rules": [{"id": "r1", "match": {"intent": "chào"}, "to": "greeting_node"}],
                    "default_node": "answer_node",
                },
            ),
            WorkflowNodeSpec(
                id="greeting_node",
                type="output.chat",
                config={"output_template": "Chào bạn! Mình là Trợ lý QNU."},
            ),
            WorkflowNodeSpec(
                id="answer_node",
                type="output.chat",
                config={"output_template": "Thông tin tra cứu chính thức."},
            ),
        ],
        edges=[
            WorkflowEdgeSpec(source="input_node", target="router_node"),
        ],
    )

    ctx = WorkflowContext(
        workflow_id="wf_branch_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"message": "Chào em!"},
    )

    resp = await dag_engine.execute(dag_spec, ctx)
    assert resp.status == "completed"
    assert "greeting_node" in resp.executed_nodes
    assert "answer_node" not in resp.executed_nodes
    assert resp.outputs["answer"] == "Chào bạn! Mình là Trợ lý QNU."


@pytest.mark.asyncio
async def test_api_list_workflow_definitions():
    """Verify GET /platform/v1alpha1/workflows/definitions lists all available DAGs."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/platform/v1alpha1/workflows/definitions")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    defs = response.json()
    assert len(defs) >= 5
    codes = [d["name"] for d in defs]
    assert any("admissions" in c for c in codes)
    assert any("regulations" in c for c in codes)


@pytest.mark.asyncio
async def test_api_execute_workflow_greeting():
    """Verify POST /platform/v1alpha1/workflows/execute runs DAG to completion."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        payload = {
            "workflow_id": "admissions-assistant",
            "inputs": {"message": "Xin chào QNU!"},
            "tenant_id": "tenant_qnu",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/platform/v1alpha1/workflows/execute", json=payload)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["executed_nodes"]) >= 2
    assert "Chào bạn" in data["outputs"]["answer"]
