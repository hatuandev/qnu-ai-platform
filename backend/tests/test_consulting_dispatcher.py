"""Test suite for Universal Agentic Consulting & Export Dispatcher."""

import pytest

from app.core.database import engine
from app.modules.tools.consulting_dispatcher import consulting_dispatcher


def test_detect_export_intent():
    """Verify export keyword recognition."""
    assert consulting_dispatcher.detect_export_intent("Xuất file excel kế hoạch nguyện vọng giúp em") is True
    assert consulting_dispatcher.detect_export_intent("Tải file pdf phiếu tư vấn") is True
    assert consulting_dispatcher.detect_export_intent("Điểm chuẩn ngành CNTT năm 2024 là bao nhiêu?") is False


def test_extract_admission_parameters():
    """Verify entity and parameter extraction from conversational queries."""
    params = consulting_dispatcher.extract_admission_parameters(
        "Em tên là Trần Hữu Nam, thi khối A00 được Toán 8.5 Lý 7.5 Hóa 8.0 ở KV1, muốn học ngành Công nghệ thông tin"
    )
    assert params["area"] == "KV1"
    assert params["combination"] == "A00"
    assert len(params["scores"]) == 3
    assert params["scores"][0] == 8.5
    assert params["scores"][1] == 7.5
    assert params["scores"][2] == 8.0
    assert params["major_name"] == "Công nghệ thông tin"
    assert "Nam" in params["candidate_name"]


@pytest.mark.asyncio
async def test_dispatch_admissions_with_export():
    """Test admissions agentic consulting dispatching with file generation."""
    await engine.dispose()
    msg = "Em thi khối A00 được 24 điểm ở KV1, tư vấn ngành và xuất file excel kế hoạch nguyện vọng giúp em"
    res = await consulting_dispatcher.dispatch("admissions", msg)
    assert res["has_agentic_guidance"] is True
    assert len(res["artifacts"]) == 1
    assert res["artifacts"][0]["type"] == "xlsx"
    assert "THÔNG TIN ĐIỂM XÉT TUYỂN" in res["guidance_context"]


@pytest.mark.asyncio
async def test_dispatch_regulations_with_export():
    """Test regulations guidebook file generation."""
    await engine.dispose()
    msg = "Xuất file quy chế học vụ và điều kiện tốt nghiệp giúp em"
    res = await consulting_dispatcher.dispatch("regulations", msg)
    assert res["has_agentic_guidance"] is True
    assert len(res["artifacts"]) >= 2
    types = [a["type"] for a in res["artifacts"]]
    assert "xlsx" in types
    assert "docx" in types
