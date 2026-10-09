"""Test suite for Universal Platform Tools & Dispatcher (Zero Hardcoded Custom Tools)."""

import pytest

from app.core.database import engine
from app.modules.tools.builtin.fact_lookup_tool import FactLayerLookupTool
from app.modules.tools.builtin.universal_report_tool import UniversalReportExportTool
from app.modules.tools.consulting_dispatcher import (
    calculate_moet_admission_score,
    classify_chance_zone,
    consulting_dispatcher,
)


def test_calculate_moet_admission_score_below_threshold():
    """When raw score < 22.5, full base priority points are added without reduction."""
    res = calculate_moet_admission_score([7.0, 7.0, 7.0], area="KV1", group="none")
    assert res["raw_total"] == 21.0
    assert res["area_points"] == 0.75
    assert res["actual_priority"] == 0.75
    assert res["final_score"] == 21.75
    assert not res["is_reduced"]


def test_calculate_moet_admission_score_above_threshold_reduced():
    """When raw score >= 22.5, priority points are reduced proportionally: ((30 - Total)/7.5) * Base."""
    res = calculate_moet_admission_score([9.0, 9.0, 9.0], area="KV1", group="none")
    assert res["raw_total"] == 27.0
    assert res["base_priority"] == 0.75
    assert res["actual_priority"] == 0.30
    assert res["final_score"] == 27.30
    assert res["is_reduced"]


def test_classify_chance_zone():
    """Test zone classifications based on delta (final - cutoff)."""
    safe = classify_chance_zone(25.0, 23.0)
    assert safe["zone"] == "safe"
    assert "+" in safe["delta_str"]

    target = classify_chance_zone(23.2, 23.0)
    assert target["zone"] == "target"

    reach = classify_chance_zone(22.0, 23.0)
    assert reach["zone"] == "reach"

    risk = classify_chance_zone(20.0, 23.0)
    assert risk["zone"] == "risk"


@pytest.mark.asyncio
async def test_fact_layer_lookup_tool():
    """Verify generic FactLayerLookupTool reads from PostgreSQL knowledge_facts."""
    await engine.dispose()
    tool = FactLayerLookupTool()
    res = await tool.execute({"keyword": "Công nghệ thông tin", "collection_id": "col_admissions"})
    assert res["status"] == "success"
    assert res["found"] is True
    assert res["total_facts"] >= 1


@pytest.mark.asyncio
async def test_universal_report_export_tool():
    """Verify generic UniversalReportExportTool produces XLSX, DOCX, and PDF artifacts."""
    tool = UniversalReportExportTool()
    params = {
        "title": "Bản Đề Xuất Kế Hoạch Nguyện Vọng — Nguyễn Hoàng Nam",
        "tables": [
            {
                "sheet_name": "Kế hoạch",
                "table_title": "DANH SÁCH NGUYỆN VỌNG XÉT TUYỂN",
                "headers": ["STT", "Mã ngành", "Tên ngành", "Điểm chuẩn 2024"],
                "rows": [[1, "7480201", "Công nghệ thông tin", 24.5]],
            }
        ],
        "formats": ["xlsx", "docx"],
        "base_name": "ke_hoach_xet_tuyen",
    }
    result = await tool.execute(params)
    assert result["status"] == "success"
    assert result["total_files"] >= 2
    assert result["xlsx_url"] is not None
    assert result["docx_url"] is not None


@pytest.mark.asyncio
async def test_dispatch_admissions_with_dynamic_facts():
    """Verify admissions consulting uses dynamic facts and export without custom tool file."""
    await engine.dispose()
    msg = "Em tên là Nguyễn Hoàng Nam, thi khối A00 được 24.5 điểm ở KV1, hãy tư vấn ngành và xuất file Excel kế hoạch nguyện vọng giúp em"
    res = await consulting_dispatcher.dispatch("admissions", msg)
    assert res["has_agentic_guidance"] is True
    assert res["score_calculation"] is not None
    assert len(res["artifacts"]) == 1
    types = [a["type"] for a in res["artifacts"]]
    assert "xlsx" in types
