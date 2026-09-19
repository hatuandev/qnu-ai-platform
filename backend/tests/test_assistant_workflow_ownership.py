"""Unit and Integration Tests for Assistant Workflow Ownership, Pinned Versions, and Consistency."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.assistants.models import AssistantModel, AssistantVersionModel
from app.modules.assistants.readiness import readiness_engine
from app.modules.assistants.schemas import AssistantCloneRequest, AssistantCreateRequest
from app.modules.assistants.seeder import STANDARD_ASSISTANTS
from app.modules.assistants.service import assistant_service
from app.modules.workflows.engine import dag_engine
from app.modules.workflows.models import (
    WorkflowDefinition,
)
from app.modules.workflows.schemas import (
    WorkflowAssistantsUsageResponse,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
)
from app.modules.workflows.service import workflow_service


def _sample_assistant(code: str = "admissions") -> AssistantModel:
    template = next(item for item in STANDARD_ASSISTANTS if item["code"] == code)
    timestamp = datetime.now(UTC).replace(tzinfo=None)
    return AssistantModel(
        id=f"ast_{code}_test",
        code=code,
        name=str(template["name"]),
        description=str(template["description"]),
        avatar_url=str(template["avatar_url"]),
        category=str(template["category"]),
        system_prompt=str(template["system_prompt"]),
        workflow_id=str(template["workflow_id"]),
        published_workflow_version_id="wfv_v1_0",
        workflow_ownership="shared",
        collection_id=str(template["collection_id"]),
        is_active=True,
        tenant_id="tenant_qnu",
        config=dict(template["config"]),
        created_at=timestamp,
        updated_at=timestamp,
    )


def _sample_workflow_definition(wf_id: str = "admissions-assistant") -> WorkflowDefinition:
    timestamp = datetime.now(UTC).replace(tzinfo=None)
    return WorkflowDefinition(
        id=wf_id,
        name="admissions_flow",
        display_name="Quy trình tư vấn tuyển sinh QNU",
        description="Luồng phân nhánh",
        module_code="admissions",
        version="1.0.0",
        is_active=True,
        ownership="shared",
        assistant_id=None,
        published_version_id="wfv_v1_0",
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_create_assistant_auto_forks_private_workflow() -> None:
    """Tạo Assistant mới với workflow_ownership='private' sẽ tự động fork Workflow riêng."""
    db = AsyncMock()
    db.add = MagicMock()
    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_exec

    async def mock_refresh(rec: AssistantModel) -> None:
        rec.id = "ast_test_id"
        rec.created_at = datetime.now(UTC).replace(tzinfo=None)
        rec.updated_at = datetime.now(UTC).replace(tzinfo=None)

    db.refresh.side_effect = mock_refresh

    req = AssistantCreateRequest(
        code="test_ast_new",
        name="Trợ lý Mới",
        description="Trợ lý hỗ trợ giải đáp thắc mắc chuyên sâu dành cho cán bộ giảng viên.",
        category="general",
        system_prompt="Bạn là trợ lý AI chính thức của Trường Đại học Quy Nhơn, luôn trả lời chính xác.",
        workflow_id="admissions-assistant",
        workflow_ownership="private",
        collection_id="col_general",
        is_active=True,
        tenant_id="tenant_qnu",
        config=dict(STANDARD_ASSISTANTS[0]["config"]),
    )

    with patch.object(
        workflow_service,
        "fork_workflow",
        new_callable=AsyncMock,
    ) as mock_fork:
        mock_fork_def = _sample_workflow_definition("wf_ast_test_ast_new")
        mock_fork_def.ownership = "private"
        mock_fork.return_value = mock_fork_def

        created = await assistant_service.create_assistant(db, req)

        assert created.code == "test_ast_new"
        assert created.workflow_id == "wf_ast_test_ast_new"
        assert created.workflow_ownership == "private"
        mock_fork.assert_awaited_once()


@pytest.mark.asyncio
async def test_clone_assistant_forks_workflow() -> None:
    """Nhân bản Assistant với fork_workflow=True sẽ tạo workflow độc lập cho bản sao."""
    db = AsyncMock()
    db.add = MagicMock()
    original = _sample_assistant("admissions")

    clone_req = AssistantCloneRequest(
        new_code="ast_admissions_copy",
        new_name="Bản sao tuyển sinh",
        new_description="Mô tả bản sao phục vụ tuyển sinh chuyên ngành",
        fork_workflow=True,
    )

    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = None  # new_code chưa tồn tại
    db.execute.return_value = mock_exec

    with (
        patch.object(assistant_service, "_get_record", return_value=original),
        patch.object(
            workflow_service,
            "fork_workflow",
            new_callable=AsyncMock,
        ) as mock_fork,
    ):
        forked_wf = _sample_workflow_definition("wf_ast_ast_admissions_copy")
        mock_fork.return_value = forked_wf

        cloned = await assistant_service.clone_assistant(db, "admissions", clone_req)

        assert cloned.code == "ast_admissions_copy"
        assert cloned.workflow_id == "wf_ast_ast_admissions_copy"
        assert cloned.workflow_ownership == "private"
        mock_fork.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_assistant_pins_workflow_version() -> None:
    """Xuất bản Assistant ghim published_workflow_version_id bất biến và lưu vào snapshot."""
    db = AsyncMock()
    db.add = MagicMock()
    assistant = _sample_assistant("admissions")
    assistant.published_workflow_version_id = None

    wf_def = _sample_workflow_definition(assistant.workflow_id)
    wf_def.published_version_id = "wfv_pinned_123"

    mock_readiness = MagicMock()
    mock_readiness.is_ready_for_publish = True
    mock_readiness.overall_readiness_score = 95.0

    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = wf_def
    mock_exec.scalar.return_value = 0
    db.execute.return_value = mock_exec

    with (
        patch.object(assistant_service, "_get_record", return_value=assistant),
        patch.object(readiness_engine, "evaluate_readiness", new_callable=AsyncMock, return_value=mock_readiness),
    ):
        result = await assistant_service.publish_assistant(db, assistant.code)

        assert result.is_active is True
        assert assistant.published_workflow_version_id == "wfv_pinned_123"
        db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_rollback_assistant_restores_workflow_version() -> None:
    """Khôi phục phiên bản Assistant sẽ phục hồi chính xác workflow version và ownership."""
    db = AsyncMock()
    db.add = MagicMock()
    assistant = _sample_assistant("admissions")
    assistant.workflow_id = "wf_modified"
    assistant.published_workflow_version_id = "wfv_modified_999"
    assistant.workflow_ownership = "shared"

    snapshot_version = AssistantVersionModel(
        id="asv_001",
        assistant_id=assistant.id,
        assistant_code=assistant.code,
        version_number="v1.0",
        change_summary="Bản gốc",
        snapshot_data={
            "name": "Tên gốc",
            "description": "Mô tả gốc",
            "category": "admissions",
            "system_prompt": "Prompt gốc",
            "workflow_id": "wf_original",
            "published_workflow_version_id": "wfv_pinned_original",
            "workflow_ownership": "private",
            "collection_id": "col_original",
            "config": assistant.config,
        },
        created_by="admin",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )

    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = snapshot_version
    mock_exec.scalar.return_value = 1
    db.execute.return_value = mock_exec

    with patch.object(assistant_service, "_get_record", return_value=assistant):
        rollback_resp = await assistant_service.rollback_version(db, assistant.code, "asv_001")

        assert rollback_resp.restored_version == "v1.0"
        assert assistant.workflow_id == "wf_original"
        assert assistant.published_workflow_version_id == "wfv_pinned_original"
        assert assistant.workflow_ownership == "private"


@pytest.mark.asyncio
async def test_fork_workflow_service() -> None:
    """Hàm fork_workflow tạo workflow mới và chuyển đổi ownership thành private."""
    db = AsyncMock()
    db.add = MagicMock()
    mock_exec = MagicMock()
    mock_exec.scalar.return_value = 0
    db.execute.return_value = mock_exec
    assistant = _sample_assistant("admissions")
    assistant.workflow_ownership = "shared"

    with (
        patch.object(assistant_service, "_get_record", return_value=assistant),
        patch.object(
            workflow_service,
            "fork_workflow",
            new_callable=AsyncMock,
        ) as mock_fork,
    ):
        new_wf = _sample_workflow_definition(f"wf_ast_{assistant.code}")
        new_wf.ownership = "private"
        new_wf.assistant_id = assistant.id
        mock_fork.return_value = new_wf

        result = await assistant_service.fork_workflow(db, assistant.code)

        assert result.workflow_ownership == "private"
        assert result.new_workflow_id == f"wf_ast_{assistant.code}"
        assert assistant.workflow_ownership == "private"
        assert assistant.workflow_id == new_wf.id


@pytest.mark.asyncio
async def test_workflow_assistants_usage() -> None:
    """Tra cứu danh sách và số lượng trợ lý đang gắn với một workflow."""
    db = AsyncMock()
    wf_def = _sample_workflow_definition("admissions-assistant")
    a1 = _sample_assistant("admissions")
    a2 = _sample_assistant("admissions")
    a2.id = "ast_admissions_2"
    a2.code = "admissions_2"

    mock_wf_exec = MagicMock()
    mock_wf_exec.scalar_one_or_none.return_value = wf_def

    mock_asst_exec = MagicMock()
    mock_asst_exec.scalars.return_value.all.return_value = [a1, a2]

    db.execute.side_effect = [mock_wf_exec, mock_asst_exec]

    usage: WorkflowAssistantsUsageResponse = await workflow_service.get_workflow_assistants(
        db, "admissions-assistant"
    )

    assert usage.workflow_id == "admissions-assistant"
    assert usage.ownership == "shared"
    assert usage.total_assistants == 2
    assert len(usage.assistants) == 2
    assert usage.assistants[0].code == "admissions"
    assert usage.assistants[1].code == "admissions_2"


@pytest.mark.asyncio
async def test_execute_workflow_with_exact_pinned_version() -> None:
    """WorkflowExecuteRequest hỗ trợ workflow_version_id để chạy đúng phiên bản bất biến đã pin."""
    db = AsyncMock()
    db.add = MagicMock()

    dag_spec = {
        "execution_mode": "dag",
        "entry_node_id": "n1",
        "input_schema": {},
        "output_schema": {},
        "policies": {},
        "nodes": [
            {
                "id": "n1",
                "type": "chat_input",
                "version": "1.0.0",
                "display_name": "Input",
                "config": {},
                "policy": {},
            },
            {
                "id": "n2",
                "type": "chat_output",
                "version": "1.0.0",
                "display_name": "Output",
                "config": {"template": "Kết quả từ pinned version"},
                "policy": {},
            },
        ],
        "edges": [{"source": "n1", "target": "n2"}],
    }

    req = WorkflowExecuteRequest(
        workflow_id="admissions-assistant",
        workflow_version_id="wfv_pinned_target",
        inputs={"question": "Chào bạn"},
    )

    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = dag_spec
    db.execute.return_value = mock_exec

    mock_engine_resp = WorkflowExecuteResponse(
        execution_id="exec_test",
        workflow_id="admissions-assistant",
        status="completed",
        outputs={"answer": "Chào bạn, tôi là trợ lý"},
        executed_nodes=["n1", "n2"],
        latency_ms=45,
    )

    with patch.object(dag_engine, "execute", new_callable=AsyncMock, return_value=mock_engine_resp):
        resp = await workflow_service.execute(db, req)
        assert resp.status == "completed"
        assert "n1" in resp.executed_nodes
