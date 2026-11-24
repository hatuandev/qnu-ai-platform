"""Unit tests for assistant export toggles and flexible DOCX / XLSX / PDF generation."""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pymupdf
import pytest
from docx import Document
from openpyxl import load_workbook

from qnu.domains.assistants.schemas import AssistantCreate, AssistantRagPolicy
from qnu.domains.conversations import document_export
from qnu.domains.conversations.document_export import (
    DocumentDraft,
    _render_pdf_pymupdf,
    content_disposition_header,
    enabled_export_formats,
    export_turn_document,
    extract_document_draft,
    render_docx,
    render_xlsx,
)
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.platform.errors import Forbidden


def test_assistant_export_toggles_default_false_and_compatible_with_answer_request():
    policy = AssistantRagPolicy()
    assert policy.allow_export_docx is False
    assert policy.allow_export_pdf is False
    assert policy.allow_export_xlsx is False

    enabled = AssistantRagPolicy(
        allow_export_docx=True,
        allow_export_pdf=False,
        allow_export_xlsx=True,
    )
    persisted = enabled.model_dump(mode="json")
    assert persisted["allow_export_docx"] is True
    assert persisted["allow_export_pdf"] is False
    assert persisted["allow_export_xlsx"] is True

    # Callers like public_service / answer_review exclude guardrail_policy before AnswerRequest.
    for_answer = enabled.model_dump(
        mode="json", exclude={"guardrail_policy", "suggested_prompts"}
    )
    assert "allow_export_docx" not in for_answer
    assert "allow_export_pdf" not in for_answer
    assert "allow_export_xlsx" not in for_answer
    req = AnswerRequest(question="Kiểm tra tương thích", **for_answer)
    assert req.question == "Kiểm tra tương thích"

    created = AssistantCreate(
        name="Trợ lý Hành chính",
        rag_policy={"allow_export_docx": True, "allow_export_pdf": True},
    )
    assert enabled_export_formats(created.model_dump(mode="json")) == ["docx", "pdf"]
    addon = document_export.drafting_prompt_addon(["docx"])
    assert "TUYỆT ĐỐI KHÔNG tự suy đoán hoặc bịa thông tin thực tế" in addon
    assert "[...]" in addon


def test_extract_document_draft_parses_explicit_markers_and_separates_chat():
    raw = (
        "Mình đã soạn mẫu kế hoạch theo yêu cầu của bạn.\n\n"
        '<<<DOCUMENT title="Kế hoạch tổ chức hội thảo khoa học" layout="administrative">>>\n'
        "# KẾ HOẠCH TỔ CHỨC HỘI THẢO\n\n"
        "## 1. Mục đích\n"
        "- Trao đổi học thuật tại [Đơn vị].\n\n"
        "## 2. Tiến độ thực hiện\n"
        "| STT | Nội dung | Thời gian |\n"
        "| --- | --- | --- |\n"
        "| 1 | Lập danh sách đại biểu | [Ngày/Tháng] |\n"
        "<<<END_DOCUMENT>>>\n\n"
        "Bạn muốn bổ sung thêm mục kinh phí không?"
    )
    chat_text, draft = extract_document_draft(raw, "Soạn kế hoạch tổ chức hội thảo")
    assert "<<<DOCUMENT" not in chat_text
    assert "Mình đã soạn mẫu kế hoạch" in chat_text
    assert "bổ sung thêm mục kinh phí" in chat_text
    assert draft is not None
    assert draft.title == "Kế hoạch tổ chức hội thảo khoa học"
    assert draft.layout == "administrative"
    assert draft.has_tables is True
    assert "Mình đã soạn mẫu kế hoạch" not in draft.markdown
    assert "| STT | Nội dung | Thời gian |" in draft.markdown


def test_extract_document_draft_heuristic_strips_conversational_edges():
    raw = (
        "Dưới đây là mẫu tờ trình bạn yêu cầu:\n\n"
        "# TỜ TRÌNH ĐỀ XUẤT MUA SẮM THIẾT BỊ\n\n"
        "## 1. Lý do đề xuất\n"
        "Phục vụ công tác giảng dạy năm học [2026-2027].\n\n"
        "## 2. Dự toán kinh phí\n"
        "- Máy chiếu: [Số lượng]\n\n"
        "Nếu bạn cần chỉnh sửa thêm hãy nhắn mình nhé!"
    )
    _, draft = extract_document_draft(raw, "Soạn tờ trình mua sắm thiết bị")
    assert draft is not None
    assert draft.layout == "administrative"
    assert "Dưới đây là" not in draft.markdown
    assert "Nếu bạn cần chỉnh sửa" not in draft.markdown


def test_render_docx_produces_valid_vietnamese_document_with_tables():
    draft = DocumentDraft(
        title="Kế hoạch triển khai chuyển đổi số",
        layout="administrative",
        markdown=(
            "# KẾ HOẠCH TRIỂN KHAI CHUYỂN ĐỔI SỐ\n\n"
            "## 1. Mục tiêu\n"
            "- Hoàn thiện **hệ thống học liệu số** tại [Đơn vị].\n\n"
            "## 2. Bảng phân công\n"
            "| STT | Hạng mục | Đơn vị chủ trì |\n"
            "| --- | --- | --- |\n"
            "| 1 | Số hóa giáo trình | Trung tâm Số & Học liệu |\n"
            "| 2 | Tập huấn giảng viên | Phòng Đào tạo |\n"
        ),
        has_tables=True,
    )
    data = render_docx(draft)
    assert data[:2] == b"PK"

    loaded = Document(io.BytesIO(data))
    full_text = "\n".join(p.text for p in loaded.paragraphs)
    assert "KẾ HOẠCH TRIỂN KHAI CHUYỂN ĐỔI SỐ" in full_text
    assert "hệ thống học liệu số" in full_text
    # 1 administrative header table + 1 content table
    assert len(loaded.tables) == 2
    content_table = loaded.tables[1]
    assert content_table.cell(0, 1).text == "Hạng mục"
    assert content_table.cell(1, 2).text == "Trung tâm Số & Học liệu"


def test_render_xlsx_produces_valid_workbook_for_tables_and_outline():
    table_draft = DocumentDraft(
        title="Bảng tổng hợp chỉ tiêu",
        layout="spreadsheet",
        markdown=(
            "## Chỉ tiêu tuyển sinh\n"
            "| Mã ngành | Tên ngành | Chỉ tiêu |\n"
            "| --- | --- | --- |\n"
            "| 7480201 | Công nghệ thông tin | 250 |\n"
            "| 7140218 | Sư phạm Lịch sử | 60 |\n"
        ),
        has_tables=True,
    )
    xlsx_bytes = render_xlsx(table_draft)
    assert xlsx_bytes[:2] == b"PK"
    wb = load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    assert ws.cell(row=3, column=1).value == "Mã ngành"
    assert ws.cell(row=4, column=2).value == "Công nghệ thông tin"

    outline_draft = DocumentDraft(
        title="Ghi chú cuộc họp",
        layout="standard",
        markdown="## Nội dung\n- Thống nhất tiến độ quý II",
        has_tables=False,
    )
    outline_wb = load_workbook(io.BytesIO(render_xlsx(outline_draft)))
    assert outline_wb.active.cell(row=4, column=2).value == "Thống nhất tiến độ quý II"


def test_render_xlsx_keeps_formula_like_markup_as_literal_text():
    draft = DocumentDraft(
        title="Bảng thử",
        markdown="| =1+2 | Giá trị |\n| --- | --- |\n| =2+3 | #N/A |",
    )
    sheet = load_workbook(io.BytesIO(render_xlsx(draft))).active
    for address, expected in {"A3": "=1+2", "A4": "=2+3", "B4": "#N/A"}.items():
        assert sheet[address].value == expected
        assert sheet[address].data_type == "s"


def test_render_pdf_fallback_produces_valid_pdf_bytes():
    draft = DocumentDraft(
        title="Đơn xin nghỉ phép",
        layout="administrative",
        markdown=(
            "# ĐƠN XIN NGHỈ PHÉP\n\n"
            "Kính gửi: [Trưởng đơn vị]\n\n"
            "Tôi tên là: [Họ và tên], xin nghỉ phép từ ngày [../../....] đến [../../....]."
        ),
        has_tables=False,
    )
    pdf_bytes = _render_pdf_pymupdf(draft)
    assert pdf_bytes.startswith(b"%PDF")
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf_doc:
        assert len(pdf_doc) >= 1


def test_content_disposition_supports_vietnamese_utf8():
    header = content_disposition_header("Kế hoạch năm 2026.docx")
    assert "attachment;" in header
    assert "filename*=UTF-8''" in header


@pytest.mark.asyncio
async def test_export_turn_document_blocks_disabled_format(monkeypatch):
    fake_conv = SimpleNamespace(
        id="conv_1",
        assistant_id="ast_1",
        assistant_snapshot={"rag_policy": {"allow_export_docx": True, "allow_export_pdf": False}},
    )
    fake_turn = SimpleNamespace(
        id="turn_1",
        conversation_id="conv_1",
        question="Soạn kế hoạch",
        result={"status": "direct_reply", "answer": "# Kế hoạch\nNội dung"},
        rewrite_trace={
            "document_draft": {
                "title": "Kế hoạch",
                "layout": "standard",
                "markdown": "# Kế hoạch\nNội dung",
                "has_tables": False,
            }
        },
    )
    fake_assistant = SimpleNamespace(
        rag_policy={
            "allow_export_docx": True,
            "allow_export_pdf": False,
            "allow_export_xlsx": False,
        }
    )

    monkeypatch.setattr(document_export, "owned", AsyncMock(return_value=fake_conv))
    fake_db = SimpleNamespace(scalar=AsyncMock(side_effect=[fake_turn, fake_assistant]))

    with pytest.raises(Forbidden) as exc_info:
        await export_turn_document(fake_db, SimpleNamespace(), "ws_1", "conv_1", "turn_1", "pdf")
    assert exc_info.value.code == "assistant_export_format_disabled"


def test_export_policy_and_no_knowledge_prompt_rules():
    disabled_all = document_export.export_policy_prompt_addon([])
    assert "KHÔNG có chức năng tạo hoặc xuất tệp" in disabled_all
    assert "TUYỆT ĐỐI KHÔNG dùng thẻ <<<DOCUMENT" in disabled_all

    docx_only = document_export.export_policy_prompt_addon(["docx"])
    assert "DOCX" in docx_only
    assert "CÁC ĐỊNH DẠNG ĐANG TẮT: PDF, XLSX" in docx_only
    assert "TẬP TRUNG ĐÚNG 1 ĐỊNH DẠNG" in docx_only

    assert "BẮT BUỘC TỪ CHỐI THẲNG THẮN" in document_export.NO_KNOWLEDGE_GROUNDING_POLICY
    assert "KHÔNG TẠO BẢN THẢO SỚM" in docx_only


def test_extract_document_draft_skips_preliminary_inquiry():
    q = "tôi muốn làm 1 đơn xin nghỉ phép có được ko ?"
    conversational_reply = (
        "Được bạn nhé! Mình hoàn toàn có thể hỗ trợ bạn soạn đơn xin nghỉ phép. "
        "Bạn vui lòng cho mình biết thêm vài thông tin để soạn chính xác hơn: "
        "họ tên, đơn vị công tác, thời gian nghỉ và lý do nghỉ phép nhé?"
    )
    chat_text, draft = extract_document_draft(conversational_reply, q)
    assert chat_text == conversational_reply
    assert draft is None


def test_extract_document_draft_skips_no_knowledge_refusal_even_with_quy_dinh_keyword():
    q = "Quy định mức thanh toán công tác phí hiện hành của trường thế nào?"
    refusal = (
        "Hiện trợ lý chưa được gắn kho dữ liệu tri thức nội bộ, nên tôi không thể cung cấp thông tin "
        "về quy định mức thanh toán công tác phí hiện hành của trường. Bạn có thể gửi trực tiếp văn bản, "
        "số liệu hoặc nội dung quy định đó cho tôi nếu cần hỗ trợ soạn thảo hoặc chỉnh sửa văn bản liên quan."
    )
    chat_text, draft = extract_document_draft(refusal, q)
    assert chat_text == refusal
    assert draft is None

    # Even a generic factual question mentioning "quy chế" without drafting verb must not create a draft.
    q2 = "Quy chế đào tạo quy định điều kiện tốt nghiệp như thế nào?"
    reply2 = (
        "Hiện tôi chưa có dữ liệu tri thức về quy chế đào tạo của trường nên không thể trả lời chi tiết. "
        "Bạn vui lòng cung cấp văn bản liên quan nếu cần hỗ trợ tổng hợp."
    )
    _, draft2 = extract_document_draft(reply2, q2)
    assert draft2 is None


def test_render_docx_and_xlsx_convert_html_br_to_real_newlines():
    raw_doc = (
        "Đây là bản thảo của bạn.\n\n"
        '<<<DOCUMENT title="Giấy đề nghị thanh toán" layout="administrative">>>\n'
        "# GIẤY ĐỀ NGHỊ THANH TOÁN\n\n"
        "Kính gửi: Phòng Kế toán<br/>Đơn vị: Trung tâm Số và Học liệu\n\n"
        "| STT | Nội dung chi | Số tiền<br />(VNĐ) |\n"
        "| --- | --- | --- |\n"
        "| 1 | Vé máy bay<br>Khứ hồi | 2.400.000 |\n\n"
        "<br>\n"
        "  <BR />  \n"
        "Người đề nghị: **Hồ Anh Tuấn**\n"
        "<<<END_DOCUMENT>>>"
    )
    _, draft = extract_document_draft(raw_doc, "Xuất file docx cho mình nhé")
    assert draft is not None
    assert "<br" not in draft.markdown.splitlines()[0].lower()

    # Check DOCX
    docx_bytes = render_docx(draft)
    doc = Document(io.BytesIO(docx_bytes))
    all_docx_texts = [p.text for p in doc.paragraphs]
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                all_docx_texts.append(cell.text)
    joined_docx = "\n".join(all_docx_texts)
    assert "<br" not in joined_docx.lower()
    assert "Kính gửi: Phòng Kế toán" in joined_docx
    assert "Đơn vị: Trung tâm Số và Học liệu" in joined_docx
    assert "Vé máy bay\nKhứ hồi" in joined_docx
    assert "Số tiền\n(VNĐ)" in joined_docx

    # Check XLSX (table mode)
    xlsx_bytes = render_xlsx(draft)
    wb = load_workbook(io.BytesIO(xlsx_bytes))
    all_xlsx_vals: list[str] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            for val in row:
                if val is not None:
                    all_xlsx_vals.append(str(val))
    joined_xlsx = "\n".join(all_xlsx_vals)
    assert "<br" not in joined_xlsx.lower()
    assert "Vé máy bay\nKhứ hồi" in joined_xlsx
    assert "Số tiền\n(VNĐ)" in joined_xlsx

    # Check XLSX (outline fallback mode with raw <br> passed directly in DocumentDraft)
    outline_draft = DocumentDraft(
        title="Ghi chú nhanh",
        layout="standard",
        markdown="## Nội dung\nDòng 1<br>Dòng 2\n<BR/>\nDòng 3",
        has_tables=False,
    )
    outline_wb = load_workbook(io.BytesIO(render_xlsx(outline_draft)))
    outline_vals = [
        str(val)
        for row in outline_wb.active.iter_rows(values_only=True)
        for val in row
        if val is not None
    ]
    joined_outline = "\n".join(outline_vals)
    assert "<br" not in joined_outline.lower()
    assert "Dòng 1" in joined_outline
    assert "Dòng 2" in joined_outline
    assert "Dòng 3" in joined_outline


def test_strip_document_markers_and_unclosed_document_block():
    unclosed = (
        "Mình đã soạn xong bản thảo cho bạn.\n\n"
        '<<<DOCUMENT title="Đơn xin nghỉ phép" layout="administrative">>>\n'
        "# ĐƠN XIN NGHỈ PHÉP\n\n"
        "Tôi tên là Hồ Anh Tuấn."
    )
    chat_text, draft = extract_document_draft(unclosed, "Xuất file docx cho mình")
    assert "<<<DOCUMENT" not in chat_text
    assert "<<<END_DOCUMENT" not in chat_text
    assert draft is not None
    assert draft.title == "Đơn xin nghỉ phép"
    assert "Tôi tên là Hồ Anh Tuấn." in draft.markdown

    stray = "Nội dung phản hồi.\n<<<DOCUMENT title=\"Nháp\">>>\n<<<END_DOCUMENT>>>\nCảm ơn bạn."
    cleaned = document_export.strip_document_markers(stray)
    assert "<<<" not in cleaned
    assert "Nội dung phản hồi." in cleaned
    assert "Cảm ơn bạn." in cleaned


def test_export_policy_active_draft_context_and_requested_format():
    addon = document_export.export_policy_prompt_addon(["docx", "pdf"])
    assert "CÁC ĐỊNH DẠNG ĐANG BẬT (ĐƯỢC PHÉP TẠO TỆP): DOCX, PDF" in addon
    assert "TUYỆT ĐỐI KHÔNG trả lời rằng bạn không thể tạo hoặc xuất tệp" in addon
    assert "CÁC ĐỊNH DẠNG ĐANG TẮT: XLSX" in addon

    assert document_export.requested_export_format("Xuất file pdf cho mình nhé") == "pdf"
    assert document_export.requested_export_format("Chuyển sang excel giúp mình") == "xlsx"
    assert document_export.requested_export_format("Xuất bản Word nhé") == "docx"
    assert document_export.requested_export_format("Chỉnh lại tiêu đề giúp mình") is None

    assert document_export.disabled_requested_format("Xuất file excel nhé", ["docx", "pdf"]) == "xlsx"
    assert document_export.disabled_requested_format("Xuất file pdf nhé", ["docx", "pdf"]) is None
    assert (
        document_export.disabled_requested_format(
            "File excel này dùng công thức tính tổng như thế nào?", ["docx", "pdf"]
        )
        is None
    )
    assert "Excel" in document_export.disabled_format_refusal_message("xlsx")

    # remove_blocks=True strips accidental <<<DOCUMENT>>> blocks when format is disabled
    accidental = (
        "Trợ lý không hỗ trợ Excel.\n"
        '<<<DOCUMENT title="Nháp">>>\n# TIÊU ĐỀ\nNội dung bị cấm\n<<<END_DOCUMENT>>>'
    )
    cleaned = document_export.strip_document_markers(accidental, remove_blocks=True)
    assert "Nội dung bị cấm" not in cleaned
    assert "Trợ lý không hỗ trợ Excel." in cleaned

    ctx = document_export.active_draft_prompt_context(
        DocumentDraft(
            title="Giấy đề nghị thanh toán",
            layout="administrative",
            markdown="# GIẤY ĐỀ NGHỊ THANH TOÁN\nNội dung...",
            has_tables=False,
        )
    )
    assert "[BẢN THẢO HIỆN HÀNH TRONG PHIÊN]" in ctx
    assert "Giấy đề nghị thanh toán" in ctx


def test_resolve_preferred_format_and_clean_nbsp_entities():
    raw = (
        '<<<DOCUMENT title="Bảng chi phí" layout="spreadsheet" format="xlsx">>>\n'
        "# BẢNG CHI PHÍ&nbsp;CÔNG TÁC\n\n"
        "Đơn vị: Trung tâm Số &amp; Học liệu&nbsp;&nbsp;\n\n"
        "| STT | Khoản mục | Ghi chú |\n"
        "| --- | --- | --- |\n"
        "| 1 | Vé xe&#160;khứ hồi | &quot;Đính kèm hóa đơn&quot;&nbsp; |\n"
        "<<<END_DOCUMENT>>>"
    )
    _, draft = extract_document_draft(raw, "xuất file excel nhé")
    assert draft is not None
    assert draft.preferred_format == "xlsx"
    assert "&nbsp;" not in draft.markdown
    assert "&#160;" not in draft.markdown
    assert "\u00a0" not in draft.markdown
    assert "Trung tâm Số & Học liệu" in draft.markdown

    # Single concrete format resolution: requested format wins; spreadsheet defaults to xlsx if enabled; else first enabled.
    resolved_xlsx = document_export.resolve_preferred_format(
        draft, "xuất file excel nhé", ["docx", "pdf", "xlsx"]
    )
    assert resolved_xlsx.preferred_format == "xlsx"

    resolved_fallback_docx = document_export.resolve_preferred_format(
        draft.model_copy(update={"preferred_format": None}),
        "soạn giúp mình bảng chi phí",
        ["docx", "pdf"],
    )
    assert resolved_fallback_docx.preferred_format == "docx"

    resolved_none = document_export.resolve_preferred_format(
        draft, "xuất file excel nhé", []
    )
    assert resolved_none.preferred_format is None

    # Verify DOCX and XLSX contain zero &nbsp; or raw HTML entities
    docx_doc = Document(io.BytesIO(render_docx(resolved_xlsx)))
    docx_text = "\n".join(
        [p.text for p in docx_doc.paragraphs]
        + [c.text for t in docx_doc.tables for r in t.rows for c in r.cells]
    )
    assert "&nbsp;" not in docx_text
    assert "\u00a0" not in docx_text
    assert "Vé xe khứ hồi" in docx_text

    wb = load_workbook(io.BytesIO(render_xlsx(resolved_xlsx)))
    xlsx_text = "\n".join(
        str(val)
        for ws in wb.worksheets
        for row in ws.iter_rows(values_only=True)
        for val in row
        if val is not None
    )
    assert "&nbsp;" not in xlsx_text
    assert "\u00a0" not in xlsx_text
    assert "Vé xe khứ hồi" in xlsx_text


def test_routing_prompt_forbids_clarification_block_on_drafting_requests():
    from qnu.domains.conversations import routing

    assert "soạn thảo, tạo mẫu" in routing.SYSTEM
    assert "TUYỆT ĐỐI KHÔNG đặt needs_clarification=true" in routing.SYSTEM


@pytest.mark.asyncio
async def test_execution_send_skips_resolve_turn_for_no_knowledge_assistant_turn2(monkeypatch):
    from datetime import UTC, datetime

    from qnu.domains.conversations import execution
    from qnu.domains.conversations.schemas import DirectReply, TurnRequest

    fake_conv = SimpleNamespace(
        id="conv_draft_1",
        workspace_id="ws_1",
        assistant_id="ast_draft_1",
        collection_id=None,
        document_ids=None,
        assistant_snapshot={
            "name": "Trợ lý soạn thảo văn bản",
            "persona": "Áp dụng Nghị định 30/2020/NĐ-CP",
            "collection_ids": [],
            "chat_provider_id": "prov_1",
            "top_k": 5,
            "history_turns": 3,
            "max_output_tokens": None,
            "rag_policy": {"allow_export_docx": True},
        },
    )
    now = datetime.now(UTC)
    fake_turn = SimpleNamespace(
        id="turn_2",
        conversation_id="conv_draft_1",
        turn_no=2,
        question="tôi muốn soạn 1 đơn xin nghỉ phép",
        resolved_question="tôi muốn soạn 1 đơn xin nghỉ phép",
        metadata_filter={},
        history_turn_ids=[],
        status="running",
        error_code=None,
        result=None,
        rewrite_trace={},
        created_at=now,
        finished_at=None,
        lease_expires_at=now,
    )

    async def fail_if_resolve_turn_called(*_args, **_kwargs):
        raise AssertionError("resolve_turn must not be called for no-knowledge assistants")

    fake_direct_reply = DirectReply(
        id="turn_2",
        status="direct_reply",
        route="direct_chat",
        answer="Được bạn nhé! Bạn cho mình biết họ tên, đơn vị và thời gian nghỉ phép để mình soạn đơn.",
    )

    monkeypatch.setattr(
        execution, "reserve_turn", AsyncMock(return_value=(fake_conv, fake_turn, True))
    )
    monkeypatch.setattr(execution, "resolve_turn", fail_if_resolve_turn_called)
    monkeypatch.setattr(execution, "_live_export_formats", AsyncMock(return_value=["docx"]))
    monkeypatch.setattr(execution, "_direct_llm_turn", AsyncMock(return_value=fake_direct_reply))
    monkeypatch.setattr(execution, "checkpoint", AsyncMock())
    monkeypatch.setattr(execution, "record_workspace_event", AsyncMock())

    fake_db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    resp = await execution.send(
        fake_db,
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(actor_id="act_1"),
        "ws_1",
        "conv_draft_1",
        TurnRequest(question="tôi muốn soạn 1 đơn xin nghỉ phép", expected_turn_no=1),
        "idem_key_2",
    )
    assert resp.status == "completed"
    assert resp.result is not None
    assert resp.result.status == "direct_reply"
    assert "họ tên" in resp.result.answer


