"""Unit Tests for Tool Gateway, Builtin QNU Tools & Function Calling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundException
from app.modules.tools.builtin.admission_score_tool import AdmissionScoreLookupTool
from app.modules.tools.builtin.document_exporter import DocumentExporterTool
from app.modules.tools.builtin.exam_matrix_tool import ExamMatrixExporterTool
from app.modules.tools.registry import ToolRegistry
from app.modules.tools.schemas import ToolExecuteRequest
from app.modules.tools.service import ToolService


@pytest.mark.asyncio
async def test_admission_score_tool_found():
    tool = AdmissionScoreLookupTool()
    assert tool.name == "lookup_admission_score"
    assert tool.category == "admissions"

    res = await tool.execute({"major_name": "Công nghệ thông tin", "year": 2024})
    assert res["found"] is True
    assert res["total"] >= 1
    assert res["records"][0]["cutoff_score"] == 24.5
    assert "0256.3846.156" in res["hotline"]


@pytest.mark.asyncio
async def test_admission_score_tool_not_found():
    tool = AdmissionScoreLookupTool()
    res = await tool.execute({"major_name": "Ngành Không Tồn Tại", "year": 2024})
    assert res["found"] is False
    assert "0256.3846.156" in res["hotline"]


@pytest.mark.asyncio
async def test_document_exporter_nd30(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.tools.builtin.document_exporter.settings.LOCAL_STORAGE_PATH", str(tmp_path))
    tool = DocumentExporterTool()
    assert tool.name == "export_administrative_document"
    assert tool.category == "drafting"

    schema = tool.get_openapi_schema()
    assert schema["name"] == "export_administrative_document"
    assert "document_type" in schema["parameters"]["properties"]

    res = await tool.execute({
        "document_type": "THÔNG BÁO",
        "title": "Về việc tổ chức hội thảo khoa học trí tuệ nhân tạo",
        "body_paragraphs": [
            "Căn cứ kế hoạch công tác năm học 2026-2027 của Trường Đại học Quy Nhơn.",
            "Nhà trường thông báo tổ chức Hội thảo Khoa học ứng dụng AI trong giảng dạy.",
        ],
        "signer_title": "HIỆU TRƯỞNG",
        "signer_name": "PGS.TS. Đỗ Ngọc Mỹ",
    })

    assert res["status"] == "generated"
    assert res["standard"] == "Decree 30/2020/ND-CP"
    assert res["size_bytes"] > 0
    assert res["file_name"].endswith(".docx")


@pytest.mark.asyncio
async def test_exam_matrix_exporter(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.tools.builtin.exam_matrix_tool.settings.LOCAL_STORAGE_PATH", str(tmp_path))
    tool = ExamMatrixExporterTool()
    assert tool.name == "export_exam_matrix"
    assert tool.category == "question_bank"

    res = await tool.execute({
        "course_name": "Cấu trúc dữ liệu và giải thuật",
        "course_code": "CS201",
        "exam_duration_minutes": 90,
        "topics": [
            {
                "topic_name": "Chương 1: Mảng và Danh sách liên kết",
                "recognition_count": 5,
                "comprehension_count": 3,
                "application_count": 2,
                "advanced_application_count": 0,
                "total_score": 3.0,
            },
            {
                "topic_name": "Chương 2: Cây nhị phân tìm kiếm & Đồ thị",
                "recognition_count": 4,
                "comprehension_count": 4,
                "application_count": 4,
                "advanced_application_count": 2,
                "total_score": 7.0,
            },
        ],
    })

    assert res["status"] == "generated"
    assert res["course_code"] == "CS201"
    assert res["total_questions"] == 24
    assert res["total_score"] == 10.0
    assert res["bloom_distribution"]["recognition"] == 9
    assert res["size_bytes"] > 0
    assert res["file_name"].endswith(".xlsx")


def test_tool_registry():
    registry = ToolRegistry()
    tools = registry.list_all()
    assert len(tools) >= 3

    tool_admissions = registry.get("lookup_admission_score")
    assert tool_admissions is not None
    assert tool_admissions.category == "admissions"

    schemas = registry.list_schemas(category="admissions")
    assert len(schemas) == 1
    assert schemas[0]["name"] == "lookup_admission_score"


@pytest.mark.asyncio
async def test_tool_service_execution():
    service = ToolService()
    tools = service.list_tools()
    assert len(tools) >= 3

    detail = service.get_tool("lookup_admission_score")
    assert detail.name == "lookup_admission_score"

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    req = ToolExecuteRequest(
        tool_name="lookup_admission_score",
        parameters={"major_name": "Sư phạm Toán học", "year": 2024},
        tenant_id="tenant_qnu",
        assistant_code="admissions_assistant",
    )
    resp = await service.execute_tool(mock_session, req)
    assert resp.status == "success"
    assert resp.result["found"] is True
    assert resp.result["records"][0]["cutoff_score"] == 26.25
    assert resp.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_tool_service_not_found():
    service = ToolService()
    mock_session = AsyncMock()
    req = ToolExecuteRequest(tool_name="non_existent_tool", parameters={})
    with pytest.raises(NotFoundException):
        await service.execute_tool(mock_session, req)


@pytest.mark.asyncio
async def test_tool_service_assistant_allowlist_enforcement():
    """Verify tool execution is blocked if tool is not in assistant's enabled_tools."""
    from app.core.exceptions import AppException
    from app.modules.assistants.models import AssistantModel

    service = ToolService()
    mock_session = AsyncMock()

    # Mock assistant record with enabled_tools not containing lookup_admission_score
    mock_assistant = AssistantModel(
        code="drafting_assistant",
        name="Trợ lý Soạn thảo",
        config={"tools": {"enabled_tools": ["export_administrative_document"]}},
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_assistant
    mock_session.execute.return_value = mock_res

    req = ToolExecuteRequest(
        tool_name="lookup_admission_score",
        parameters={"major_name": "Sư phạm Toán", "year": 2024},
        assistant_code="drafting_assistant",
    )

    with pytest.raises(AppException) as exc_info:
        await service.execute_tool(mock_session, req)

    assert exc_info.value.code == "tool_not_allowed_for_assistant"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_tool_service_requires_approval_enforcement():
    """Verify tool execution requires human approval when tool.requires_approval is True."""
    from app.core.exceptions import AppException
    from app.modules.tools.builtin.base import BaseTool

    class SensitiveTool(BaseTool):
        @property
        def name(self) -> str:
            return "sensitive_action_tool"

        @property
        def display_name(self) -> str:
            return "Thao tác nhạy cảm"

        @property
        def description(self) -> str:
            return "Cần duyệt trước khi thi hành"

        @property
        def requires_approval(self) -> bool:
            return True

        def get_openapi_schema(self) -> dict:
            return {"name": self.name, "description": self.description}

        async def execute(self, **kwargs):
            return {"done": True}

    service = ToolService()
    service.registry.register(SensitiveTool())

    mock_session = AsyncMock()

    # Attempt 1: Not approved -> Must fail with 403
    req_unapproved = ToolExecuteRequest(
        tool_name="sensitive_action_tool",
        parameters={"is_approved": False},
    )
    with pytest.raises(AppException) as exc_info:
        await service.execute_tool(mock_session, req_unapproved)
    assert exc_info.value.status_code == 403

    # Attempt 2: Approved -> Must succeed
    req_approved = ToolExecuteRequest(
        tool_name="sensitive_action_tool",
        parameters={"is_approved": True},
    )
    resp = await service.execute_tool(mock_session, req_approved)
    assert resp.status == "success"

