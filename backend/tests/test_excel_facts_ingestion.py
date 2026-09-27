"""Tests for Excel/CSV Structured Facts Parsing and Ingestion."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import openpyxl
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.modules.knowledge.excel_parser import parse_excel_facts
from app.modules.knowledge.models import KnowledgeCollection, KnowledgeFact
from app.modules.knowledge.service import knowledge_service


def _create_sample_excel_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Tuyển sinh 2024"

    ws.append(["Mã ngành", "Tên ngành đào tạo", "Điểm chuẩn 2024", "Chỉ tiêu tuyển sinh"])
    ws.append(["7480201", "Công nghệ thông tin", "24.5", "180"])
    ws.append(["7140209", "Sư phạm Toán học", "26.0", "90"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_excel_facts() -> None:
    excel_bytes = _create_sample_excel_bytes()
    facts = parse_excel_facts(excel_bytes, "diem_chuan_2024.xlsx")

    assert len(facts) >= 4  # 2 entities x multiple attributes
    cntt_facts = [f for f in facts if f["entity_name"] == "Công nghệ thông tin"]
    assert len(cntt_facts) >= 2

    # Check attribute names
    attr_names = [f["attribute_name"] for f in cntt_facts]
    assert any("diem_chuan_2024" in a for a in attr_names)
    assert any("chi_tieu" in a for a in attr_names)


def test_parse_csv_facts() -> None:
    csv_text = "Tên ngành,Điểm chuẩn,Chỉ tiêu\nKỹ thuật phần mềm,23.5,120\n"
    facts = parse_excel_facts(csv_text.encode("utf-8"), "diem_chuan.csv")

    assert len(facts) == 2
    assert facts[0]["entity_name"] == "Kỹ thuật phần mềm"
    assert facts[0]["attribute_value"] == "23.5"


@pytest.mark.asyncio
async def test_import_facts_from_excel_service() -> None:
    excel_bytes = _create_sample_excel_bytes()
    db = AsyncMock()
    db.add = MagicMock()

    col = KnowledgeCollection(
        id="col_admissions_test",
        name="Tuyển sinh",
        module_code="admissions",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
    )

    col_res = MagicMock()
    col_res.scalar_one_or_none.return_value = col
    db.execute.return_value = col_res

    with patch("app.core.storage.storage_service.save", new_callable=AsyncMock) as mock_storage:
        mock_storage.return_value = "storage/path"
        resp = await knowledge_service.import_facts_from_excel(
            db,
            collection_id="col_admissions_test",
            file_bytes=excel_bytes,
            filename="diem_chuan.xlsx",
        )

    assert resp.collection_id == "col_admissions_test"
    assert resp.imported_count >= 4
    assert resp.document_id.startswith("doc_")


@pytest.mark.asyncio
async def test_get_collection_facts_service() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    timestamp = datetime.now(UTC)

    col = KnowledgeCollection(
        id="col_test_01",
        name="Kho Tri Thức Test",
        module_code="admissions",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
    )

    f1 = KnowledgeFact(
        id="fct_01",
        collection_id="col_test_01",
        document_id="doc_01",
        entity_name="Công nghệ thông tin",
        entity_type="major",
        attribute_name="diem_chuan_2024",
        attribute_value="24.5",
        confidence=1.0,
        raw_data={"Tên ngành": "Công nghệ thông tin", "Điểm chuẩn": "24.5"},
        created_at=timestamp,
    )

    def mock_execute(query, *args, **kwargs):
        q_str = str(query).lower()
        res = MagicMock()
        if "count(knowledge_facts.id)" in q_str:
            res.scalar.return_value = 1
        elif "knowledge_facts" in q_str:
            res.scalars.return_value.all.return_value = [f1]
        else:
            res.scalar_one_or_none.return_value = col
            res.scalars.return_value.all.return_value = [col]
        return res

    db.execute = AsyncMock(side_effect=mock_execute)

    list_resp = await knowledge_service.get_collection_facts(db, "col_test_01")
    assert list_resp.total == 1
    assert len(list_resp.facts) == 1
    assert list_resp.facts[0].entity_name == "Công nghệ thông tin"
    assert list_resp.facts[0].attribute_value == "24.5"


@pytest.mark.asyncio
async def test_collection_facts_api_routes() -> None:
    db = AsyncMock()
    timestamp = datetime.now(UTC)

    col = KnowledgeCollection(
        id="col_api_test",
        name="Kho Test",
        module_code="admissions",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
    )
    f1 = KnowledgeFact(
        id="fct_api_01",
        collection_id="col_api_test",
        document_id="doc_01",
        entity_name="Sư phạm Toán học",
        entity_type="major",
        attribute_name="diem_chuan_2024",
        attribute_value="26.0",
        confidence=1.0,
        raw_data={},
        created_at=timestamp,
    )

    def mock_execute(query, *args, **kwargs):
        q_str = str(query).lower()
        res = MagicMock()
        if "count(knowledge_facts.id)" in q_str:
            res.scalar.return_value = 1
        elif "knowledge_facts" in q_str:
            res.scalars.return_value.all.return_value = [f1]
        else:
            res.scalar_one_or_none.return_value = col
            res.scalars.return_value.all.return_value = [col]
        return res

    db.execute = AsyncMock(side_effect=mock_execute)

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_db] = _get_test_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/platform/v1alpha1/knowledge/collections/col_api_test/facts")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["facts"][0]["entity_name"] == "Sư phạm Toán học"
    finally:
        app.dependency_overrides.clear()


def test_parse_excel_with_merged_cells() -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Khoa Su Pham"

    ws.append(["Khối ngành", "Tên ngành", "Điểm chuẩn"])
    ws.append(["Sư phạm", "Sư phạm Toán học", "26.0"])
    ws.append([None, "Sư phạm Tin học", "25.0"])
    ws.merge_cells(start_row=2, start_column=1, end_row=3, end_column=1)

    buf = io.BytesIO()
    wb.save(buf)
    facts = parse_excel_facts(buf.getvalue(), "merged_su_pham.xlsx")

    assert len(facts) >= 4
    sp_tin = [f for f in facts if f["entity_name"] == "Sư phạm Tin học"]
    assert len(sp_tin) >= 2
    khoi_attr = next((f for f in sp_tin if "khoi_nganh" in f["attribute_name"]), None)
    assert khoi_attr is not None
    assert khoi_attr["attribute_value"] == "Sư phạm"


def test_parse_excel_with_top_banners_and_two_tier_headers() -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "TuyenSinh2025"

    ws.append(["TRƯỜNG ĐẠI HỌC QUY NHƠN", None, None, None])
    ws.append(["ĐỀ ÁN TUYỂN SINH NĂM 2025", None, None, None])
    ws.append(["Mã ngành", "Tên ngành đào tạo", "Phương thức xét tuyển", "Phương thức xét tuyển"])
    ws.append([None, None, "PT1 Điểm thi THPT", "PT2 Xét học bạ"])
    ws.append(["7480201", "Công nghệ thông tin", "24.5", "26.0"])
    ws.append(["7140209", "Sư phạm Toán học", "26.0", "28.0"])

    ws.merge_cells(start_row=3, start_column=3, end_row=3, end_column=4)

    buf = io.BytesIO()
    wb.save(buf)
    facts = parse_excel_facts(buf.getvalue(), "tuyen_sinh_2025.xlsx")

    cntt_facts = [f for f in facts if f["entity_name"] == "Công nghệ thông tin"]
    assert len(cntt_facts) >= 3
    attr_names = [f["attribute_name"] for f in cntt_facts]
    assert any("phuong_thuc" in a and "pt1" in a for a in attr_names)
    assert any("phuong_thuc" in a and "pt2" in a for a in attr_names)


def test_parse_excel_zero_keyword_non_major() -> None:
    """Test zero-keyword entity recognition on laboratory equipment table."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "ThietBi"

    ws.append(["STT", "Mã thiết bị", "Tên thiết bị thí nghiệm", "Số lượng", "Đơn giá"])
    ws.append(["1", "TB01", "Kính hiển vi quang học OLYMPUS", "15", "45000000"])
    ws.append(["2", "TB02", "Máy quang phổ hấp thụ nguyên tử", "2", "350000000"])

    buf = io.BytesIO()
    wb.save(buf)
    facts = parse_excel_facts(buf.getvalue(), "danh_muc_thiet_bi.xlsx")

    assert len(facts) >= 6
    kinh_facts = [f for f in facts if f["entity_name"] == "Kính hiển vi quang học OLYMPUS"]
    assert len(kinh_facts) >= 3
    attr_names = [f["attribute_name"] for f in kinh_facts]
    assert any("so_luong" in a for a in attr_names)
    assert any("don_gia" in a for a in attr_names)
    assert kinh_facts[0]["entity_type"] == "equipment"


def test_parse_excel_footer_filtering() -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "HocPhi"

    ws.append(["STT", "Chương trình đào tạo", "Học phí học kỳ 1"])
    ws.append(["1", "Khoa học máy tính", "14500000"])
    ws.append(["2", "Kỹ thuật phần mềm", "14500000"])
    ws.append(["Tổng cộng: 2 chương trình", None, "29000000"])
    ws.append(["* Ghi chú: Mức học phí có thể điều chỉnh theo lộ trình NĐ 97", None, None])
    ws.append(["HIỆU TRƯỞNG", None, None])

    buf = io.BytesIO()
    wb.save(buf)
    facts = parse_excel_facts(buf.getvalue(), "hoc_phi.xlsx")

    entity_names = {f["entity_name"] for f in facts}
    assert "Khoa học máy tính" in entity_names
    assert "Kỹ thuật phần mềm" in entity_names
    assert not any("tổng cộng" in name.lower() for name in entity_names)
    assert not any("ghi chú" in name.lower() for name in entity_names)
    assert not any("hiệu trưởng" in name.lower() for name in entity_names)


@pytest.mark.asyncio
async def test_xlsx_parser_markdown_table() -> None:
    from app.modules.knowledge.parsers.office_parser import XlsxParser

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "ChiTieu"

    ws.append(["TRƯỜNG ĐH QUY NHƠN", None, None])
    ws.append(["Ngành đào tạo", "Chỉ tiêu", "Tổ hợp xét tuyển"])
    ws.append(["Công nghệ thông tin", "180", "A00, A01, D01"])
    ws.append(["* Ghi chú: Chỉ tiêu dự kiến", None, None])

    buf = io.BytesIO()
    wb.save(buf)

    parser = XlsxParser()
    parsed = await parser.parse(buf.getvalue(), "chi_tieu.xlsx")

    assert parsed.page_count == 1
    assert len(parsed.tables) == 1
    md = parsed.tables[0].markdown_repr
    assert "| Ngành đào tạo | Chỉ tiêu | Tổ hợp xét tuyển |" in md
    assert "| Công nghệ thông tin | 180 | A00, A01, D01 |" in md
    assert "TRƯỜNG ĐH QUY NHƠN" not in md
    assert "* Ghi chú" not in md
