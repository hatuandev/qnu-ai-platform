"""Unit & Integration Tests for Workflow DAG Engine, Nodes, Branching & Executions."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.modules.workflows.compiler import workflow_compiler
from app.modules.workflows.engine import dag_engine
from app.modules.workflows.nodes.base import BaseNodeHandler, NodeExecutionResult, WorkflowContext
from app.modules.workflows.nodes.chat_input_node import ChatInputNodeHandler
from app.modules.workflows.nodes.condition_route_node import ConditionRouteNodeHandler
from app.modules.workflows.nodes.human_approval_node import HumanApprovalNodeHandler
from app.modules.workflows.schemas import (
    WorkflowDagSpec,
    WorkflowEdgeSpec,
    WorkflowNodeSpec,
)


class _PassThroughNodeHandler(BaseNodeHandler):
    """Test-only handler that records execution order without relying on external services."""

    async def execute(self, node_spec: WorkflowNodeSpec, context: WorkflowContext) -> NodeExecutionResult:
        context.node_data.setdefault("execution_order", []).append(node_spec.id)
        return NodeExecutionResult(node_id=node_spec.id, output={"node_id": node_spec.id})


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
async def test_dag_engine_runs_fan_out_paths_before_a_fan_in_join():
    """A join must not run after only one active predecessor has completed."""
    from app.modules.workflows.registry import node_registry

    node_registry.register("test.pass_through", _PassThroughNodeHandler())
    dag_spec = WorkflowDagSpec(
        entry_node_id="split",
        nodes=[
            WorkflowNodeSpec(id="split", type="test.pass_through"),
            WorkflowNodeSpec(id="left", type="test.pass_through"),
            WorkflowNodeSpec(id="right", type="test.pass_through"),
            WorkflowNodeSpec(id="join", type="test.pass_through"),
            WorkflowNodeSpec(id="output", type="output.chat", config={"output_template": "Đã hợp nhất."}),
        ],
        edges=[
            WorkflowEdgeSpec(source="split", target="left"),
            WorkflowEdgeSpec(source="split", target="right"),
            WorkflowEdgeSpec(source="left", target="join"),
            WorkflowEdgeSpec(source="right", target="join"),
            WorkflowEdgeSpec(source="join", target="output"),
        ],
    )
    context = WorkflowContext(
        workflow_id="wf_fan_out",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
    )

    response = await dag_engine.execute(dag_spec, context)

    assert response.status == "completed"
    assert set(response.executed_nodes) == {"split", "left", "right", "join", "output"}
    execution_order = context.node_data["execution_order"]
    assert execution_order.index("left") < execution_order.index("join")
    assert execution_order.index("right") < execution_order.index("join")


def test_workflow_compiler_rejects_cycles_and_unknown_node_types():
    """Publication validation must fail closed for an invalid control-plane draft."""
    invalid_spec = WorkflowDagSpec(
        entry_node_id="input",
        nodes=[
            WorkflowNodeSpec(id="input", type="input.chat"),
            WorkflowNodeSpec(id="unsupported", type="tool.unknown"),
            WorkflowNodeSpec(id="output", type="output.chat"),
        ],
        edges=[
            WorkflowEdgeSpec(source="input", target="unsupported"),
            WorkflowEdgeSpec(source="unsupported", target="output"),
            WorkflowEdgeSpec(source="output", target="input"),
        ],
    )

    report = workflow_compiler.validate(invalid_spec)

    assert report.is_valid is False
    assert {issue.code for issue in report.issues} >= {
        "workflow_cycle_detected",
        "workflow_node_type_unsupported",
    }


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
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res
    mock_db.add = MagicMock()

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


@pytest.mark.asyncio
async def test_all_5_official_workflows_load_without_fallback():
    """Verify all 5 official workflow DAGs load their true specifications without falling back."""
    from app.modules.workflows.service import workflow_service

    expected_min_nodes = {
        "admissions-assistant": 7,
        "regulations-assistant": 5,
        "drafting-assistant": 9,
        "library-assistant": 5,
        "question-bank-assistant": 5,
    }

    for wf_id, min_count in expected_min_nodes.items():
        spec = await workflow_service.get_workflow_spec(None, wf_id)
        assert len(spec.nodes) >= min_count, f"{wf_id} fell back to dummy DAG ({len(spec.nodes)} nodes)"
        assert len(spec.edges) >= 4, f"{wf_id} has insufficient edges ({len(spec.edges)} edges)"


@pytest.mark.asyncio
async def test_all_official_workflows_pass_publication_validation():
    """Checked-in official workflows must remain publishable by the active runtime registry."""
    from app.modules.workflows.service import workflow_service

    workflow_ids = [
        "admissions-assistant",
        "regulations-assistant",
        "drafting-assistant",
        "library-assistant",
        "question-bank-assistant",
    ]

    for workflow_id in workflow_ids:
        report = workflow_compiler.validate(
            await workflow_service.get_workflow_spec(None, workflow_id)
        )
        assert report.is_valid, f"{workflow_id} has issues: {report.issues}"


@pytest.mark.asyncio
async def test_citation_guard_branches_grounded_vs_ungrounded():
    """Verify CitationGuardNodeHandler branches to chat_output or no_answer_output."""
    from unittest.mock import patch

    from app.modules.rag.schemas import AskResponse, Citation
    from app.modules.workflows.schemas import WorkflowExecuteRequest
    from app.modules.workflows.service import workflow_service

    # Case 1: Grounded with citations -> goes to chat_output
    mock_grounded = AskResponse(
        answer="Học phí ngành Sư phạm được miễn 100% theo Nghị định 116.",
        status="answered",
        citations=[Citation(source_id="ND116.pdf", title="Nghị định 116/2020", page_number=1, quote="Miễn 100%")]
    )
    with patch("app.modules.workflows.nodes.rag_answer_node.rag_service.ask", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = mock_grounded
        mock_db = AsyncMock()
        mock_definition_result = MagicMock()
        mock_definition_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_definition_result
        mock_db.add = MagicMock()
        req = WorkflowExecuteRequest(
            workflow_id="admissions-assistant",
            inputs={"message": "Học phí Sư phạm?"},
            tenant_id="tenant_qnu",
        )
        res = await workflow_service.execute(mock_db, req)
        assert res.status == "completed"
        assert "chat_output" in res.executed_nodes
        assert "no_answer_output" not in res.executed_nodes
        assert res.outputs["status"] == "answered"

    # Case 2: Ungrounded without citations -> goes to no_answer_output
    mock_ungrounded = AskResponse(
        answer="Không tìm thấy thông tin điểm chuẩn năm 2030.",
        status="insufficient_context",
        citations=[]
    )
    with patch("app.modules.workflows.nodes.rag_answer_node.rag_service.ask", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = mock_ungrounded
        mock_db = AsyncMock()
        mock_definition_result = MagicMock()
        mock_definition_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_definition_result
        mock_db.add = MagicMock()
        req = WorkflowExecuteRequest(
            workflow_id="admissions-assistant",
            inputs={"message": "Điểm chuẩn năm 2030?"},
            tenant_id="tenant_qnu",
        )
        res = await workflow_service.execute(mock_db, req)
        assert res.status == "completed"
        assert "no_answer_output" in res.executed_nodes
        assert "chat_output" not in res.executed_nodes
        assert res.outputs["status"] == "insufficient_context"
        assert "0256.3846.156" in res.outputs["answer"]


def test_workflow_compiler_detects_unreachable_and_missing_terminal():
    """Verify compiler catches unreachable nodes, duplicate edges, and missing terminal output nodes."""
    spec_with_unreachable = WorkflowDagSpec(
        entry_node_id="input_1",
        nodes=[
            WorkflowNodeSpec(id="input_1", type="input.chat"),
            WorkflowNodeSpec(id="orphan_node", type="output.chat"),
            WorkflowNodeSpec(id="connected_tool", type="tool.lookup_admission_score"),
        ],
        edges=[
            WorkflowEdgeSpec(source="input_1", target="connected_tool"),
            WorkflowEdgeSpec(source="input_1", target="connected_tool"),
        ],
    )
    report = workflow_compiler.validate(spec_with_unreachable)
    assert report.is_valid is False
    codes = {issue.code for issue in report.issues}
    assert "workflow_node_unreachable" in codes
    assert "workflow_terminal_missing" in codes
    assert "workflow_edge_duplicate" in codes


@pytest.mark.asyncio
async def test_dag_engine_detects_deadlock_stall():
    """Verify DAG engine detects when nodes cannot proceed due to circular dependency deadlock."""
    from app.modules.workflows.registry import node_registry

    node_registry.register("test.pass_through_stall", _PassThroughNodeHandler())
    dag_spec = WorkflowDagSpec(
        entry_node_id="split",
        nodes=[
            WorkflowNodeSpec(id="split", type="test.pass_through_stall"),
            WorkflowNodeSpec(id="node_a", type="test.pass_through_stall"),
            WorkflowNodeSpec(id="node_b", type="test.pass_through_stall"),
            WorkflowNodeSpec(id="output", type="output.chat"),
        ],
        edges=[
            WorkflowEdgeSpec(source="split", target="node_a"),
            WorkflowEdgeSpec(source="split", target="node_b"),
            WorkflowEdgeSpec(source="node_a", target="node_b"),
            WorkflowEdgeSpec(source="node_b", target="node_a"),
            WorkflowEdgeSpec(source="node_a", target="output"),
        ],
    )
    ctx = WorkflowContext(
        workflow_id="wf_stall",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={},
    )
    resp = await dag_engine.execute(dag_spec, ctx)
    assert resp.status == "failed"
    assert resp.error_message is not None
    assert "bị kẹt" in resp.error_message


@pytest.mark.asyncio
async def test_dag_engine_human_approval_pause_and_resume_lifecycle():
    """Verify DAG engine halts at approval node and safely resumes from checkpoint upon approval."""
    from app.modules.workflows.registry import node_registry

    node_registry.register("test.pass_through_appr", _PassThroughNodeHandler())
    dag_spec = WorkflowDagSpec(
        entry_node_id="prep_node",
        nodes=[
            WorkflowNodeSpec(id="prep_node", type="test.pass_through_appr"),
            WorkflowNodeSpec(
                id="approval_node",
                type="tool.human_approval",
                config={"description": "Duyệt cấp học bổng"},
            ),
            WorkflowNodeSpec(
                id="final_output",
                type="output.chat",
                config={"output_template": "Cấp học bổng thành công."},
            ),
        ],
        edges=[
            WorkflowEdgeSpec(source="prep_node", target="approval_node"),
            WorkflowEdgeSpec(source="approval_node", target="final_output"),
        ],
    )

    ctx_run1 = WorkflowContext(
        workflow_id="wf_appr_cycle",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"is_approved": False},
    )
    res_pause = await dag_engine.execute(dag_spec, ctx_run1)
    assert res_pause.status == "paused_for_approval"
    assert res_pause.paused_node_id == "approval_node"
    assert "prep_node" in res_pause.executed_nodes
    assert "final_output" not in res_pause.executed_nodes

    ctx_run2 = WorkflowContext(
        workflow_id="wf_appr_cycle",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"is_approved": True, "approved_by": "phong_ctsv"},
        node_data=dict(ctx_run1.node_data),
    )
    res_resume = await dag_engine.execute(
        dag_spec,
        ctx_run2,
        start_node_id="approval_node",
        completed_node_ids={"prep_node"},
    )
    assert res_resume.status == "completed"
    assert "approval_node" in res_resume.executed_nodes
    assert "final_output" in res_resume.executed_nodes
    assert res_resume.outputs["answer"] == "Cấp học bổng thành công."


@pytest.mark.asyncio
async def test_workflow_service_sync_default_workflows_idempotent():
    """Verify sync_default_workflows loads all 5 official definitions, drafts, and v1.0.0 versions."""
    from app.modules.workflows.service import workflow_service

    added_objects: list[object] = []
    mock_db = AsyncMock()
    mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    synced_count = await workflow_service.sync_default_workflows(mock_db)
    assert synced_count == 5
    assert len(added_objects) >= 15
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_workflow_control_plane_draft_optimistic_lock():
    """Verify saving draft rejects conflicting revision numbers with HTTP 409 AppException."""
    from app.core.exceptions import AppException
    from app.modules.workflows.models import WorkflowDefinition, WorkflowDraft
    from app.modules.workflows.schemas import WorkflowDraftSaveRequest
    from app.modules.workflows.service import workflow_service

    mock_db = AsyncMock()

    wf_def = WorkflowDefinition(
        id="admissions-assistant",
        name="admissions-assistant",
        display_name="Tuyển sinh",
        module_code="admissions",
        tenant_id="tenant_qnu",
        version="1.0.0",
    )
    existing_draft = WorkflowDraft(
        workflow_id="admissions-assistant",
        dag_spec={},
        revision=5,
        updated_by="admin_1",
    )

    def execute_side_effect(stmt: object) -> MagicMock:
        mock_exec = MagicMock()
        stmt_str = str(stmt)
        if "workflow_definitions" in stmt_str:
            mock_exec.scalar_one_or_none.return_value = wf_def
        else:
            mock_exec.scalar_one_or_none.return_value = existing_draft
        return mock_exec

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    conflict_request = WorkflowDraftSaveRequest(
        dag_spec=await workflow_service.get_workflow_spec(None, "admissions-assistant"),
        expected_revision=4,
        updated_by="admin_2",
    )

    with pytest.raises(AppException) as exc_info:
        await workflow_service.save_draft(mock_db, "admissions-assistant", conflict_request)

    assert exc_info.value.code == "workflow_draft_conflict"
    assert exc_info.value.status_code == 409


def test_workflow_compiler_rejects_rag_without_citation_guard():
    """Verify compiler rejects RAG workflows that lack a citation policy or no_answer guard."""
    unguarded_rag_spec = WorkflowDagSpec(
        entry_node_id="input_1",
        nodes=[
            WorkflowNodeSpec(id="input_1", type="input.chat"),
            WorkflowNodeSpec(id="rag_node", type="core.knowledge.answer"),
            WorkflowNodeSpec(id="output_node", type="output.chat"),
        ],
        edges=[
            WorkflowEdgeSpec(source="input_1", target="rag_node"),
            WorkflowEdgeSpec(source="rag_node", target="output_node"),
        ],
    )
    report = workflow_compiler.validate(unguarded_rag_spec)
    assert report.is_valid is False
    codes = {issue.code for issue in report.issues}
    assert "workflow_rag_missing_citation_guard" in codes


@pytest.mark.asyncio
async def test_workflow_publish_enforces_tm08_quality_gate():
    """Verify publish_draft blocks publication when assistant evaluation failed TM-08 standards."""
    from app.core.exceptions import AppException
    from app.modules.evaluation.models import EvaluationRun
    from app.modules.workflows.models import WorkflowDefinition, WorkflowDraft
    from app.modules.workflows.schemas import WorkflowPublishRequest
    from app.modules.workflows.service import workflow_service

    mock_db = AsyncMock()

    valid_spec = await workflow_service.get_workflow_spec(None, "admissions-assistant")
    wf_def = WorkflowDefinition(
        id="admissions-assistant",
        name="admissions-assistant",
        display_name="Tuyển sinh",
        module_code="admissions",
        tenant_id="tenant_qnu",
        version="1.0.0",
    )
    draft = WorkflowDraft(
        workflow_id="admissions-assistant",
        dag_spec=workflow_service._serialize_dag_spec(valid_spec),
        revision=2,
        updated_by="admin",
    )
    failed_eval = EvaluationRun(
        id="eval_failed_1",
        dataset_id="ds_1",
        assistant_code="admissions",
        status="completed",
        faithfulness_avg=0.65,
        answer_relevance_avg=0.70,
        context_precision_avg=0.60,
        meets_tm08_standard=False,
    )

    def execute_side_effect(stmt: object) -> MagicMock:
        mock_exec = MagicMock()
        stmt_str = str(stmt)
        if "workflow_definitions" in stmt_str:
            mock_exec.scalar_one_or_none.return_value = wf_def
        elif "workflow_drafts" in stmt_str:
            mock_exec.scalar_one_or_none.return_value = draft
        elif "evaluation_runs" in stmt_str:
            mock_exec.scalars.return_value.first.return_value = failed_eval
        else:
            mock_exec.scalar_one_or_none.return_value = None
        return mock_exec

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    publish_req = WorkflowPublishRequest(expected_revision=2, published_by="admin")

    with pytest.raises(AppException) as exc_info:
        await workflow_service.publish_draft(mock_db, "admissions-assistant", publish_req)

    assert exc_info.value.code == "workflow_quality_gate_failed"
    assert exc_info.value.status_code == 422
    assert "TM-08" in exc_info.value.message


@pytest.mark.asyncio
async def test_workflow_execution_fail_closed_on_missing_version():
    from app.core.exceptions import AppException
    from app.modules.workflows.schemas import WorkflowExecuteRequest
    from app.modules.workflows.service import workflow_service

    mock_db = AsyncMock()

    # Case 1: Execute with a published_version_id pointing to a nonexistent version row
    def execute_side_effect(stmt: object) -> MagicMock:
        mock_exec = MagicMock()
        stmt_str = str(stmt)
        if "published_version_id" in stmt_str:
            mock_exec.scalar_one_or_none.return_value = "ver_missing_999"
        elif "workflow_versions" in stmt_str:
            mock_exec.scalar_one_or_none.return_value = None  # Missing row!
        else:
            mock_exec.scalar_one_or_none.return_value = None
        return mock_exec

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    req = WorkflowExecuteRequest(
        workflow_id="admissions-assistant",
        inputs={"message": "Xin chào"},
        tenant_id="tenant_qnu",
    )

    with pytest.raises(AppException) as exc_info:
        await workflow_service.execute(mock_db, req)

    assert exc_info.value.code == "workflow_version_not_found"
    assert exc_info.value.status_code == 404
    assert "ver_missing_999" in exc_info.value.message


@pytest.mark.asyncio
async def test_api_caller_node_handler_execution():
    """Verify APICallerNodeHandler executes tool or handles fallback safely."""
    from app.modules.workflows.nodes.api_caller_node import APICallerNodeHandler
    from app.modules.workflows.registry import node_registry

    handler = node_registry.get("tool.api_caller")
    assert handler is not None
    assert isinstance(handler, APICallerNodeHandler)

    # 1. Test missing tool_id gracefully skips
    spec_empty = WorkflowNodeSpec(id="api_1", type="tool.api_caller", config={})
    ctx = WorkflowContext(
        workflow_id="wf_test",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"query": "test"},
    )
    res_empty = await handler.execute(spec_empty, ctx)
    assert res_empty.status == "completed"
    assert res_empty.output.get("status") == "skipped"

    # 2. Test nonexistent tool with return_empty fallback
    spec_not_found = WorkflowNodeSpec(
        id="api_2",
        type="tool.api_caller",
        config={"tool_id": "nonexistent_tool_xyz", "on_error_behavior": "return_empty"},
    )
    res_nf = await handler.execute(spec_not_found, ctx)
    assert res_nf.status == "completed"
    assert res_nf.output.get("status") == "error"

    # 3. Test nonexistent tool with fail_workflow
    spec_fail = WorkflowNodeSpec(
        id="api_3",
        type="tool.api_caller",
        config={"tool_id": "nonexistent_tool_xyz", "on_error_behavior": "fail_workflow"},
    )
    res_fail = await handler.execute(spec_fail, ctx)
    assert res_fail.status == "failed"
    assert "không tồn tại" in res_fail.error

