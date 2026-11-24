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


def test_decree_30_persona_compact_and_immediate_draft_placeholders():
    persona = document_export.DECREE_30_DRAFTING_PERSONA
    assert 1400 <= len(persona) <= 2000
    assert "30/2020/NĐ-CP" in persona
    assert "[Nơi nhận]" in persona
    assert "[Ngày bắt đầu]" in persona
    assert "tối đa 1 lượt" in persona.lower()

    addon = document_export.export_policy_prompt_addon(["docx", "pdf"])
    assert "tối đa 1 lượt" in addon.lower()
    assert "soạn giúp mình" in addon
    assert "[Nơi nhận]" in addon
    assert "[Ngày bắt đầu]" in addon
    assert "[Ngày kết thúc]" in addon
    assert "[Chức vụ/Đơn vị]" in addon


def test_vietnam_time_context_and_truncated_reply_guard():
    from datetime import UTC, datetime

    fixed_utc = datetime(2026, 11, 24, 10, 30, tzinfo=UTC)  # 17:30 Asia/Ho_Chi_Minh (Tuesday)
    ctx = document_export.vietnam_time_context(fixed_utc)
    assert "Asia/Ho_Chi_Minh" in ctx
    assert "Thứ Ba, 24/11/2026 17:30" in ctx
    assert "ngày mai" in ctx

    assert document_export.is_abnormally_truncated_reply("Cảm", "Soạn giúp mình đơn xin nghỉ phép")
    assert document_export.is_abnormally_truncated_reply("Vâng,", "Tôi nghỉ 2 ngày")
    assert document_export.is_abnormally_truncated_reply("   ", "Soạn công văn")
    assert not document_export.is_abnormally_truncated_reply(
        "Cảm ơn bạn!", "cảm ơn"
    )
    assert not document_export.is_abnormally_truncated_reply(
        "Chào bạn! Mình là Trợ lý soạn thảo văn bản hành chính.", "xin chào"
    )


@pytest.mark.asyncio
async def test_direct_llm_turn_injects_vietnam_time_and_no_repeated_greeting(monkeypatch):
    from qnu.domains.conversations import execution

    captured_messages: list[list] = []

    class FakeChat:
        async def complete(self, messages, _request):
            captured_messages.append(messages)
            return SimpleNamespace(
                content="Đã ghi nhận thông tin. Dưới đây là bản thảo đơn xin nghỉ phép của bạn.",
                total_tokens=120,
            )

    fake_runtime = SimpleNamespace(
        provider_id="prov_1",
        model_name="qwen3.8-27b-q4",
        inference_configuration_hash=lambda _task: "cfg_hash",
    )
    fake_budget = SimpleNamespace(total_reserved_tokens=512)
    monkeypatch.setattr(
        execution,
        "prepare_chat_request",
        AsyncMock(return_value=(fake_runtime, SimpleNamespace(), fake_budget)),
    )
    monkeypatch.setattr(
        execution.usage_service,
        "reserve",
        AsyncMock(return_value=SimpleNamespace(id="usg_1")),
    )
    monkeypatch.setattr(execution.usage_service, "settle", AsyncMock())
    monkeypatch.setattr(execution, "_live_export_formats", AsyncMock(return_value=["docx"]))
    monkeypatch.setattr(execution, "bind_usage", lambda req, _uid: req)

    fake_conv = SimpleNamespace(
        id="conv_time_1",
        assistant_id="ast_1",
        assistant_snapshot={
            "persona": document_export.DECREE_30_DRAFTING_PERSONA,
            "history_turns": 3,
            "rag_policy": {"allow_export_docx": True},
        },
    )

    # Case 1: prior_turns == 0
    fake_db_first = SimpleNamespace(
        scalars=AsyncMock(return_value=SimpleNamespace(all=list))
    )
    turn_1 = SimpleNamespace(
        id="turn_1",
        turn_no=1,
        question="Xin chào",
        resolved_question="Xin chào",
        history_turn_ids=[],
        rewrite_trace={},
    )
    await execution._direct_llm_turn(
        fake_db_first,
        SimpleNamespace(actor_id="act_1"),
        "ws_1",
        fake_conv,
        turn_1,
        FakeChat(),
        "prov_1",
    )
    sys_turn_1 = captured_messages[0][0].content
    assert "Asia/Ho_Chi_Minh" in sys_turn_1
    assert "lượt đầu" in sys_turn_1.lower()
    assert "chào mở đầu" in sys_turn_1.lower()

    # Case 2: prior_turns > 0
    prior_turn = SimpleNamespace(
        id="turn_1",
        status="completed",
        question="Xin chào",
        result={"answer": "Chào bạn! Bạn cần soạn văn bản gì?"},
        rewrite_trace={},
    )
    fake_db_followup = SimpleNamespace(
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [prior_turn]))
    )
    turn_2 = SimpleNamespace(
        id="turn_2",
        turn_no=2,
        question="tôi bắt đầu nghỉ từ ngày mai, nơi nhận tôi tự ghi",
        resolved_question="tôi bắt đầu nghỉ từ ngày mai, nơi nhận tôi tự ghi",
        history_turn_ids=[],
        rewrite_trace={},
    )
    await execution._direct_llm_turn(
        fake_db_followup,
        SimpleNamespace(actor_id="act_1"),
        "ws_1",
        fake_conv,
        turn_2,
        FakeChat(),
        "prov_1",
    )
    assert turn_2.history_turn_ids == ["turn_1"]
    sys_turn_2 = captured_messages[1][0].content
    assert "Asia/Ho_Chi_Minh" in sys_turn_2
    assert 'TUYỆT ĐỐI KHÔNG mở đầu bằng "Chào bạn", "Xin chào"' in sys_turn_2


@pytest.mark.asyncio
async def test_direct_llm_turn_retries_once_on_truncated_reply(monkeypatch):
    from qnu.domains.conversations import execution

    attempts = 0
    reserve_keys: list[str] = []

    class TruncatedThenFullChat:
        async def complete(self, _messages, _request):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return SimpleNamespace(content="Cảm", total_tokens=20)
            return SimpleNamespace(
                content=(
                    "Dưới đây là bản thảo đơn xin nghỉ phép hoàn chỉnh:\n\n"
                    '<<<DOCUMENT title="Đơn xin nghỉ phép" layout="administrative" format="docx">>>\n'
                    "# ĐƠN XIN NGHỈ PHÉP\n\n"
                    "Kính gửi: [Nơi nhận]\n\n"
                    "Tôi tên là Nguyễn Văn A, đơn vị Phòng Hành chính, Trường Đại học Quy Nhơn. "
                    "Xin nghỉ phép 02 ngày từ [Ngày bắt đầu] đến [Ngày kết thúc] vì lý do nghỉ ốm.\n"
                    "<<<END_DOCUMENT>>>"
                ),
                total_tokens=240,
            )

    async def fake_reserve(_db, _actor, _ws, _task, idem_key, *_args, **_kwargs):
        reserve_keys.append(idem_key)
        return SimpleNamespace(id=f"usg_{len(reserve_keys)}")

    fake_runtime = SimpleNamespace(
        provider_id="prov_1",
        model_name="qwen3.8-27b-q4",
        inference_configuration_hash=lambda _task: "cfg_hash",
    )
    fake_budget = SimpleNamespace(total_reserved_tokens=512)
    monkeypatch.setattr(
        execution,
        "prepare_chat_request",
        AsyncMock(return_value=(fake_runtime, SimpleNamespace(), fake_budget)),
    )
    monkeypatch.setattr(execution.usage_service, "reserve", fake_reserve)
    monkeypatch.setattr(execution.usage_service, "settle", AsyncMock())
    monkeypatch.setattr(execution, "_live_export_formats", AsyncMock(return_value=["docx"]))
    monkeypatch.setattr(execution, "bind_usage", lambda req, _uid: req)

    prior_turn = SimpleNamespace(
        id="turn_2",
        status="completed",
        question="tôi muốn soạn 1 đơn xin nghỉ phép",
        result={"answer": "Bạn cho mình biết họ tên, đơn vị, lý do và số ngày nghỉ nhé."},
        rewrite_trace={},
    )
    fake_db = SimpleNamespace(
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [prior_turn]))
    )
    fake_conv = SimpleNamespace(
        id="conv_retry_1",
        assistant_id="ast_1",
        assistant_snapshot={
            "persona": document_export.DECREE_30_DRAFTING_PERSONA,
            "history_turns": 3,
            "rag_policy": {"allow_export_docx": True},
        },
    )
    turn_3 = SimpleNamespace(
        id="turn_3",
        turn_no=3,
        question="tôi làm tại trường đại học quy nhơn, họ tên là nguyễn văn a, đơn vị phòng hành chính, lý do là nghỉ ốm thời gian là 2 ngày",
        resolved_question="tôi làm tại trường đại học quy nhơn, họ tên là nguyễn văn a, đơn vị phòng hành chính, lý do là nghỉ ốm thời gian là 2 ngày",
        history_turn_ids=[],
        rewrite_trace={},
    )

    reply = await execution._direct_llm_turn(
        fake_db,
        SimpleNamespace(actor_id="act_1"),
        "ws_1",
        fake_conv,
        turn_3,
        TruncatedThenFullChat(),
        "prov_1",
    )
    assert attempts == 2
    assert reserve_keys == ["direct_chat:turn_3", "direct_chat_retry:turn_3"]
    assert turn_3.rewrite_trace["retried_truncated"] is True
    assert turn_3.rewrite_trace["total_tokens"] == 260
    assert turn_3.rewrite_trace["document_draft"]["title"] == "Đơn xin nghỉ phép"
    assert "[Nơi nhận]" in turn_3.rewrite_trace["document_draft"]["markdown"]
    assert reply.answer != "Cảm"


def test_export_preserves_placeholders_and_vietnamese_diacritics_across_all_formats():
    import pymupdf

    raw_doc = (
        "Dưới đây là bản thảo hoàn chỉnh.\n\n"
        '<<<DOCUMENT title="Đơn xin nghỉ phép" layout="administrative" format="docx">>>\n'
        "# ĐƠN XIN NGHỈ PHÉP\n\n"
        "Kính gửi: [Nơi nhận]\n\n"
        "Tôi tên là: **Nguyễn Văn Ánh**\n"
        "Chức vụ/Đơn vị: [Chức vụ/Đơn vị] — Trường Đại học Quy Nhơn\n"
        "Thời gian nghỉ: Từ [Ngày bắt đầu] đến [Ngày kết thúc]\n"
        "Lý do: Nghỉ ốm theo chỉ định bác sĩ.\n\n"
        "| Mục | Thông tin |\n"
        "| --- | --- |\n"
        "| Nơi nhận | [Nơi nhận] |\n"
        "| Thời gian | Từ [Ngày bắt đầu] đến [Ngày kết thúc] |\n"
        "<<<END_DOCUMENT>>>"
    )
    _, draft = extract_document_draft(raw_doc, "Soạn giúp mình đơn xin nghỉ phép")
    assert draft is not None
    expected_tokens = [
        "[Nơi nhận]",
        "[Ngày bắt đầu]",
        "[Ngày kết thúc]",
        "[Chức vụ/Đơn vị]",
        "Nguyễn Văn Ánh",
        "Trường Đại học Quy Nhơn",
    ]

    # 1. DOCX
    docx_doc = Document(io.BytesIO(render_docx(draft)))
    docx_text = "\n".join(
        [p.text for p in docx_doc.paragraphs]
        + [c.text for t in docx_doc.tables for r in t.rows for c in r.cells]
    )
    for token in expected_tokens:
        assert token in docx_text

    # 2. XLSX
    wb = load_workbook(io.BytesIO(render_xlsx(draft)))
    xlsx_text = "\n".join(
        str(val)
        for ws in wb.worksheets
        for row in ws.iter_rows(values_only=True)
        for val in row
        if val is not None
    )
    assert "[Nơi nhận]" in xlsx_text
    assert "[Ngày bắt đầu]" in xlsx_text
    assert "[Ngày kết thúc]" in xlsx_text

    # 3. PDF (PyMuPDF fallback text extraction)
    pdf_bytes = document_export._render_pdf_pymupdf(draft)
    assert pdf_bytes.startswith(b"%PDF")
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf_doc:
        pdf_text = "\n".join(page.get_text("text") for page in pdf_doc)
    for token in expected_tokens:
        assert token in pdf_text

    # 4. Safe filename preserves Vietnamese readability
    assert document_export.safe_download_filename(draft.title, "docx") == "Đơn xin nghỉ phép.docx"


@pytest.mark.asyncio
async def test_long_conversation_history_is_bounded_and_syncs_history_turn_ids(monkeypatch):
    from qnu.domains.conversations import execution

    captured_messages: list[list] = []

    class CaptureChat:
        async def complete(self, messages, _request):
            captured_messages.append(messages)
            return SimpleNamespace(content="Đã cập nhật bản thảo theo yêu cầu mới nhất.", total_tokens=90)

    fake_runtime = SimpleNamespace(
        provider_id="prov_1",
        model_name="qwen3.8-27b-q4",
        inference_configuration_hash=lambda _task: "cfg_hash",
    )
    fake_budget = SimpleNamespace(total_reserved_tokens=512)
    monkeypatch.setattr(
        execution,
        "prepare_chat_request",
        AsyncMock(return_value=(fake_runtime, SimpleNamespace(), fake_budget)),
    )
    monkeypatch.setattr(
        execution.usage_service,
        "reserve",
        AsyncMock(return_value=SimpleNamespace(id="usg_long_1")),
    )
    monkeypatch.setattr(execution.usage_service, "settle", AsyncMock())
    monkeypatch.setattr(execution, "_live_export_formats", AsyncMock(return_value=["docx"]))
    monkeypatch.setattr(execution, "bind_usage", lambda req, _uid: req)

    # 10 completed prior turns with very long answers (2500 chars each)
    long_turns = [
        SimpleNamespace(
            id=f"turn_{idx}",
            status="completed",
            question=f"Câu hỏi lượt {idx}: " + ("chi tiết " * 120),
            result={"answer": f"Bản thảo lượt {idx}: " + ("nội dung dài " * 250)},
            rewrite_trace={},
        )
        for idx in range(1, 11)
    ]
    fake_db = SimpleNamespace(
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: long_turns))
    )
    fake_conv = SimpleNamespace(
        id="conv_long_1",
        assistant_id="ast_1",
        assistant_snapshot={
            "persona": document_export.DECREE_30_DRAFTING_PERSONA,
            "history_turns": 10,  # Intentionally above MAX_DIRECT_HISTORY_TURNS
            "rag_policy": {"allow_export_docx": True},
        },
    )
    turn_11 = SimpleNamespace(
        id="turn_11",
        turn_no=11,
        question="Đổi nơi nhận thành Ban Giám hiệu giúp mình",
        resolved_question="Đổi nơi nhận thành Ban Giám hiệu giúp mình",
        history_turn_ids=[],
        rewrite_trace={},
    )

    await execution._direct_llm_turn(
        fake_db,
        SimpleNamespace(actor_id="act_1"),
        "ws_1",
        fake_conv,
        turn_11,
        CaptureChat(),
        "prov_1",
    )
    sent = captured_messages[0]
    history_msgs = sent[1:-1]  # Exclude system prompt and current user question
    assert len(turn_11.history_turn_ids) <= document_export.MAX_DIRECT_HISTORY_TURNS
    assert len(turn_11.history_turn_ids) >= 1
    # Most recent prior turn is always preserved
    assert turn_11.history_turn_ids[-1] == "turn_10"
    # Every included turn produces user + assistant messages, strictly matching history_turn_ids
    assert len(history_msgs) == len(turn_11.history_turn_ids) * 2
    total_hist_chars = sum(len(m.content) for m in history_msgs)
    assert total_hist_chars <= document_export.MAX_DIRECT_HISTORY_CHARS


@pytest.mark.asyncio
async def test_retry_failure_settles_both_usages_and_propagates_error(monkeypatch):
    from qnu.domains.conversations import execution
    from qnu.platform.errors import AppException
    from qnu.ports.chat_model import ChatResponseError

    settle_calls: list[tuple[str, int | None, bool]] = []
    reserve_keys: list[str] = []

    class TruncatedThenTimeoutChat:
        def __init__(self):
            self.calls = 0

        async def complete(self, _messages, _request):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(content="Cảm", total_tokens=15)
            raise ChatResponseError(
                AppException("Upstream timeout", code="model_timeout", status_code=504),
                raw_body=b"",
                usage_tokens=5,
            )

    async def fake_reserve(_db, _actor, _ws, _task, idem_key, *_args, **_kwargs):
        reserve_keys.append(idem_key)
        return SimpleNamespace(id=f"usg_{len(reserve_keys)}")

    async def fake_settle(_db, usage_id, *, total_tokens, failed=False, **_kwargs):
        settle_calls.append((usage_id, total_tokens, failed))

    fake_runtime = SimpleNamespace(
        provider_id="prov_1",
        model_name="qwen3.8-27b-q4",
        inference_configuration_hash=lambda _task: "cfg_hash",
    )
    fake_budget = SimpleNamespace(total_reserved_tokens=512)
    monkeypatch.setattr(
        execution,
        "prepare_chat_request",
        AsyncMock(return_value=(fake_runtime, SimpleNamespace(), fake_budget)),
    )
    monkeypatch.setattr(execution.usage_service, "reserve", fake_reserve)
    monkeypatch.setattr(execution.usage_service, "settle", fake_settle)
    monkeypatch.setattr(execution, "_live_export_formats", AsyncMock(return_value=["docx"]))
    monkeypatch.setattr(execution, "bind_usage", lambda req, _uid: req)

    fake_db = SimpleNamespace(
        scalars=AsyncMock(return_value=SimpleNamespace(all=list))
    )
    fake_conv = SimpleNamespace(
        id="conv_err_1",
        assistant_id="ast_1",
        assistant_snapshot={
            "persona": document_export.DECREE_30_DRAFTING_PERSONA,
            "history_turns": 3,
            "rag_policy": {"allow_export_docx": True},
        },
    )
    turn = SimpleNamespace(
        id="turn_err_1",
        turn_no=1,
        question="Soạn giúp mình đơn xin nghỉ phép 2 ngày",
        resolved_question="Soạn giúp mình đơn xin nghỉ phép 2 ngày",
        history_turn_ids=[],
        rewrite_trace={},
    )

    with pytest.raises(ChatResponseError):
        await execution._direct_llm_turn(
            fake_db,
            SimpleNamespace(actor_id="act_1"),
            "ws_1",
            fake_conv,
            turn,
            TruncatedThenTimeoutChat(),
            "prov_1",
        )
    assert reserve_keys == ["direct_chat:turn_err_1", "direct_chat_retry:turn_err_1"]
    assert settle_calls == [("usg_1", 15, False), ("usg_2", 5, True)]


@pytest.mark.asyncio
async def test_disabled_format_guard_blocks_before_llm_on_chat_send(monkeypatch):
    from datetime import UTC, datetime

    from qnu.domains.conversations import execution
    from qnu.domains.conversations.schemas import TurnRequest

    fake_conv = SimpleNamespace(
        id="conv_guard_1",
        workspace_id="ws_1",
        assistant_id="ast_guard_1",
        collection_id=None,
        document_ids=None,
        assistant_snapshot={
            "name": "Trợ lý soạn thảo",
            "persona": document_export.DECREE_30_DRAFTING_PERSONA,
            "collection_ids": [],
            "chat_provider_id": "prov_1",
            "top_k": 5,
            "history_turns": 3,
            "max_output_tokens": None,
            "rag_policy": {"allow_export_docx": True, "allow_export_xlsx": False},
        },
    )
    now = datetime.now(UTC)
    fake_turn = SimpleNamespace(
        id="turn_guard_1",
        conversation_id="conv_guard_1",
        turn_no=1,
        question="Xuất file excel bảng chấm công giúp mình",
        resolved_question="Xuất file excel bảng chấm công giúp mình",
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

    async def fail_if_llm_called(*_args, **_kwargs):
        raise AssertionError("LLM must not be invoked when requested export format is disabled")

    monkeypatch.setattr(
        execution, "reserve_turn", AsyncMock(return_value=(fake_conv, fake_turn, True))
    )
    monkeypatch.setattr(execution, "_live_export_formats", AsyncMock(return_value=["docx"]))
    monkeypatch.setattr(execution, "_direct_llm_turn", fail_if_llm_called)
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
        "conv_guard_1",
        TurnRequest(question="Xuất file excel bảng chấm công giúp mình", expected_turn_no=0),
        "idem_guard_1",
    )
    assert resp.status == "completed"
    assert resp.result is not None
    assert "Excel" in resp.result.answer
    assert "document_draft" not in (fake_turn.rewrite_trace or {})


def test_clarifying_turn_never_produces_document_draft():
    q = "tôi muốn soạn 1 đơn xin nghỉ phép"

    # Case A: Clarifying checklist without trailing question mark
    reply_no_qmark = (
        "Để soạn Đơn xin nghỉ phép chuẩn Nghị định 30/2020/NĐ-CP, bạn vui lòng cung cấp giúp mình:\n"
        "1. Họ và tên, chức vụ, đơn vị công tác.\n"
        "2. Thời gian nghỉ (từ ngày đến ngày hoặc số ngày nghỉ).\n"
        "3. Lý do nghỉ phép và nơi nhận đơn.\n"
        "Sau khi có thông tin, mình sẽ soạn ngay bản thảo hoàn chỉnh."
    )
    text_a, draft_a = extract_document_draft(reply_no_qmark, q)
    assert draft_a is None
    assert "vui lòng cung cấp" in text_a

    # Case B: Clarifying checklist with Markdown headings
    reply_with_headings = (
        "### Thông tin cần cung cấp\n"
        "- Họ và tên, đơn vị công tác\n"
        "- Thời gian và lý do nghỉ phép\n\n"
        "### Ghi chú\n"
        "Bạn hãy cung cấp các mục trên để mình soạn đơn chính xác nhất nhé."
    )
    _, draft_b = extract_document_draft(reply_with_headings, q)
    assert draft_b is None

    # Case C: Quantized model accidentally wraps a clarifying list in <<<DOCUMENT>>>
    rogue_wrapped = (
        '<<<DOCUMENT title="Thông tin cần cung cấp" layout="administrative">>>\n'
        "Để soạn đơn xin nghỉ phép, bạn vui lòng cho mình biết họ tên, đơn vị, lý do và thời gian nghỉ.\n"
        "<<<END_DOCUMENT>>>"
    )
    text_c, draft_c = extract_document_draft(rogue_wrapped, q)
    assert draft_c is None
    assert "<<<DOCUMENT" not in text_c
    assert "họ tên" in text_c


@pytest.mark.asyncio
async def test_edit_turn_always_attaches_updated_document_draft(monkeypatch):
    from qnu.domains.conversations import execution

    # Direct unit test: updated draft without <<<DOCUMENT>>> tags and with a closing question
    updated_plain = (
        "Mình đã cập nhật nơi nhận theo yêu cầu của bạn:\n\n"
        "**CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM**\n"
        "**Độc lập - Tự do - Hạnh phúc**\n\n"
        "**ĐƠN XIN NGHỈ PHÉP**\n\n"
        "Kính gửi: Ban Giám hiệu Trường Đại học Quy Nhơn\n\n"
        "Tôi tên là Nguyễn Văn A, đơn vị Phòng Hành chính. "
        "Xin nghỉ phép 02 ngày từ 25/11/2026 đến 26/11/2026 vì lý do nghỉ ốm.\n\n"
        "Người làm đơn: Nguyễn Văn A\n\n"
        "Bạn có muốn chỉnh sửa thêm phần nào không?"
    )
    _, extracted = extract_document_draft(
        updated_plain,
        "Đổi nơi nhận thành Ban Giám hiệu giúp mình",
        has_active_draft=True,
    )
    assert extracted is not None
    assert "Ban Giám hiệu" in extracted.markdown
    assert extracted.layout == "administrative"

    # End-to-end _direct_llm_turn on Turn 4 with prior draft in Turn 3
    class EditTurnChat:
        async def complete(self, _messages, _request):
            return SimpleNamespace(content=updated_plain, total_tokens=180)

    fake_runtime = SimpleNamespace(
        provider_id="prov_1",
        model_name="qwen3.8-27b-q4",
        inference_configuration_hash=lambda _task: "cfg_hash",
    )
    fake_budget = SimpleNamespace(total_reserved_tokens=512)
    monkeypatch.setattr(
        execution,
        "prepare_chat_request",
        AsyncMock(return_value=(fake_runtime, SimpleNamespace(), fake_budget)),
    )
    monkeypatch.setattr(
        execution.usage_service,
        "reserve",
        AsyncMock(return_value=SimpleNamespace(id="usg_edit_4")),
    )
    monkeypatch.setattr(execution.usage_service, "settle", AsyncMock())
    monkeypatch.setattr(execution, "_live_export_formats", AsyncMock(return_value=["docx"]))
    monkeypatch.setattr(execution, "bind_usage", lambda req, _uid: req)

    prior_turn_3 = SimpleNamespace(
        id="turn_3",
        status="completed",
        question="Soạn giúp mình đơn xin nghỉ phép",
        result={"answer": "Mình đã soạn xong bản thảo Đơn xin nghỉ phép."},
        rewrite_trace={
            "document_draft": {
                "title": "Đơn xin nghỉ phép",
                "layout": "administrative",
                "markdown": "# ĐƠN XIN NGHỈ PHÉP\n\nKính gửi: [Nơi nhận]\n\nTôi tên là Nguyễn Văn A.",
                "has_tables": False,
                "preferred_format": "docx",
            }
        },
    )
    fake_db = SimpleNamespace(
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [prior_turn_3]))
    )
    fake_conv = SimpleNamespace(
        id="conv_edit_4",
        assistant_id="ast_1",
        assistant_snapshot={
            "persona": document_export.DECREE_30_DRAFTING_PERSONA,
            "history_turns": 3,
            "rag_policy": {"allow_export_docx": True},
        },
    )
    turn_4 = SimpleNamespace(
        id="turn_4",
        turn_no=4,
        question="Đổi nơi nhận thành Ban Giám hiệu giúp mình",
        resolved_question="Đổi nơi nhận thành Ban Giám hiệu giúp mình",
        history_turn_ids=[],
        rewrite_trace={},
    )

    await execution._direct_llm_turn(
        fake_db,
        SimpleNamespace(actor_id="act_1"),
        "ws_1",
        fake_conv,
        turn_4,
        EditTurnChat(),
        "prov_1",
    )
    draft_4 = turn_4.rewrite_trace.get("document_draft")
    assert draft_4 is not None
    assert "Ban Giám hiệu" in draft_4["markdown"]
    assert draft_4["preferred_format"] == "docx"


def test_strip_leading_repeated_greeting_and_content_disposition_vietnamese_d():
    assert (
        document_export.strip_leading_repeated_greeting(
            "Chào bạn. Để soạn đơn xin nghỉ phép, bạn vui lòng cung cấp thông tin sau.",
            prior_turns=1,
        )
        == "Để soạn đơn xin nghỉ phép, bạn vui lòng cung cấp thông tin sau."
    )
    assert (
        document_export.strip_leading_repeated_greeting(
            "Chào bạn! Mình là Trợ lý soạn thảo văn bản hành chính.",
            prior_turns=0,
        )
        == "Chào bạn! Mình là Trợ lý soạn thảo văn bản hành chính."
    )
    header = document_export.content_disposition_header("Đơn xin nghỉ phép.docx")
    assert 'filename="Don_xin_nghi_phep.docx"' in header


@pytest.mark.asyncio
async def test_direct_llm_turn_retries_when_model_stops_at_draft_preamble(monkeypatch):
    from qnu.domains.conversations import execution

    calls = 0

    class PreambleThenDraftChat:
        async def complete(self, messages, _request):
            nonlocal calls
            calls += 1
            if calls == 1:
                return SimpleNamespace(
                    content=(
                        'Tôi đã cập nhật lý do nghỉ phép thành "về quê có việc gấp" và '
                        'điều chỉnh phần "Kính gửi" thành Ban Giám hiệu. '
                        "Dưới đây là bản thảo hoàn chỉnh của văn bản:"
                    ),
                    total_tokens=None,
                )
            assert "chưa xuất nội dung văn bản" in messages[-1].content
            return SimpleNamespace(
                content=(
                    '<<<DOCUMENT title="Đơn xin nghỉ phép" layout="administrative" format="docx">>>\n'
                    "# ĐƠN XIN NGHỈ PHÉP\n\n"
                    "Kính gửi: Ban Giám hiệu Trường Đại học Quy Nhơn\n\n"
                    "Tôi tên là [Họ và tên]. Xin nghỉ phép 02 ngày từ 25/11/2026 đến 26/11/2026 "
                    "vì lý do về quê có việc gấp.\n"
                    "<<<END_DOCUMENT>>>"
                ),
                total_tokens=None,
            )

    fake_runtime = SimpleNamespace(
        provider_id="prov_1",
        model_name="qwen3.8-27b-q4",
        inference_configuration_hash=lambda _task: "cfg_hash",
    )
    fake_budget = SimpleNamespace(total_reserved_tokens=512)
    monkeypatch.setattr(
        execution,
        "prepare_chat_request",
        AsyncMock(return_value=(fake_runtime, SimpleNamespace(), fake_budget)),
    )
    monkeypatch.setattr(
        execution.usage_service,
        "reserve",
        AsyncMock(side_effect=[SimpleNamespace(id="usg_p1"), SimpleNamespace(id="usg_p2")]),
    )
    monkeypatch.setattr(execution.usage_service, "settle", AsyncMock())
    monkeypatch.setattr(execution, "_live_export_formats", AsyncMock(return_value=["docx"]))
    monkeypatch.setattr(execution, "bind_usage", lambda req, _uid: req)

    prior_turn_3 = SimpleNamespace(
        id="turn_3",
        status="completed",
        question="nghỉ từ ngày mai, 2 ngày, lý do việc gia đình, phần thiếu tự điền",
        result={"answer": "Đã soạn xong bản thảo Đơn xin nghỉ phép."},
        rewrite_trace={
            "document_draft": {
                "title": "Đơn xin nghỉ phép",
                "layout": "administrative",
                "markdown": "# ĐƠN XIN NGHỈ PHÉP\n\nKính gửi: [Nơi nhận]\n\nLý do: Việc gia đình.",
                "has_tables": False,
                "preferred_format": "docx",
            }
        },
    )
    fake_db = SimpleNamespace(
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [prior_turn_3]))
    )
    fake_conv = SimpleNamespace(
        id="conv_preamble_4",
        assistant_id="ast_1",
        assistant_snapshot={
            "persona": document_export.DECREE_30_DRAFTING_PERSONA,
            "history_turns": 3,
            "rag_policy": {"allow_export_docx": True},
        },
    )
    turn_4 = SimpleNamespace(
        id="turn_4",
        turn_no=4,
        question="sửa lý do thành về quê có việc gấp, và ghi nơi nhận là Ban Giám hiệu",
        resolved_question="sửa lý do thành về quê có việc gấp, và ghi nơi nhận là Ban Giám hiệu",
        history_turn_ids=[],
        rewrite_trace={},
    )

    await execution._direct_llm_turn(
        fake_db,
        SimpleNamespace(actor_id="act_1"),
        "ws_1",
        fake_conv,
        turn_4,
        PreambleThenDraftChat(),
        "prov_1",
    )
    assert calls == 2
    assert turn_4.rewrite_trace["retried_truncated"] is True
    # None + None stays None (never fake 0)
    assert turn_4.rewrite_trace["total_tokens"] is None
    draft_4 = turn_4.rewrite_trace.get("document_draft")
    assert draft_4 is not None
    assert "Ban Giám hiệu" in draft_4["markdown"]
    assert "về quê có việc gấp" in draft_4["markdown"]
    assert "[Họ và tên]" in draft_4["markdown"]


def test_render_docx_strips_raw_html_div_align_right_and_applies_decree_30_appendix_i():
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm

    raw_with_html = (
        "Dưới đây là bản thảo đơn xin nghỉ phép.\n\n"
        '<<<DOCUMENT title="Đơn xin nghỉ phép" layout="administrative" format="docx">>>\n'
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
        "Độc lập - Tự do - Hạnh phúc\n\n"
        '<div align="right"><i>Quy Nhơn, ngày 24 tháng 11 năm 2026</i></div>\n\n'
        "# ĐƠN XIN NGHỈ PHÉP\n\n"
        "Kính gửi: [Nơi nhận]\n\n"
        "Tôi tên là: <span>**Nguyễn Văn Ánh**</span>\n"
        "Chức vụ/Đơn vị: [Chức vụ/Đơn vị] — Trường Đại học Quy Nhơn\n"
        "Thời gian nghỉ: Từ [Ngày bắt đầu] đến [Ngày kết thúc]\n"
        "Lý do: Nghỉ việc gia đình.\n\n"
        '<div align="right">**Ghi chú căn phải**</div>\n\n'
        "Nơi nhận:\n"
        "- Như trên;\n"
        "- Lưu: VT.\n\n"
        "NGƯỜI LÀM ĐƠN\n"
        "(Ký và ghi rõ họ tên)\n"
        "Nguyễn Văn Ánh\n"
        "<<<END_DOCUMENT>>>"
    )
    _, draft = extract_document_draft(raw_with_html, "Soạn giúp mình đơn xin nghỉ phép")
    assert draft is not None
    # Extracted markdown itself must contain zero raw HTML tags
    assert "<div" not in draft.markdown.lower()
    assert "</div>" not in draft.markdown.lower()
    assert "<span" not in draft.markdown.lower()

    # Also test direct render_docx when a caller passes raw <div align="right"> directly in DocumentDraft
    raw_draft = DocumentDraft(
        title="Đơn xin nghỉ phép",
        layout="administrative",
        markdown=(
            "TRƯỜNG ĐẠI HỌC QUY NHƠN\n"
            "PHÒNG HÀNH CHÍNH - TỔNG HỢP\n"
            "Số: 12/ĐX-HC\n"
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
            "Độc lập - Tự do - Hạnh phúc\n"
            '<div align="right">Quy Nhơn, ngày 24 tháng 11 năm 2026</div>\n\n'
            "# ĐƠN XIN NGHỈ PHÉP\n\n"
            "Kính gửi: [Nơi nhận]\n\n"
            "Tôi tên là: <span>Nguyễn Văn Ánh</span>, đơn vị [Chức vụ/Đơn vị].\n"
            "Thời gian nghỉ: Từ [Ngày bắt đầu] đến [Ngày kết thúc].\n\n"
            '<div align="right">Đoạn căn phải riêng</div>\n\n'
            "Nơi nhận:\n"
            "- Như trên;\n"
            "- Lưu: VT.\n\n"
            "NGƯỜI LÀM ĐƠN\n"
            "(Ký và ghi rõ họ tên)\n"
            "Nguyễn Văn Ánh"
        ),
        has_tables=False,
    )
    docx_bytes = render_docx(raw_draft)
    doc = Document(io.BytesIO(docx_bytes))

    # 1. Decree 30 Appendix I page geometry (A4 + Top 20mm, Bottom 20mm, Left 30mm, Right 15mm)
    sec = doc.sections[0]
    assert abs(sec.page_width - Cm(21.0)) < 2000
    assert abs(sec.page_height - Cm(29.7)) < 2000
    assert abs(sec.top_margin - Cm(2.0)) < 2000
    assert abs(sec.bottom_margin - Cm(2.0)) < 2000
    assert abs(sec.left_margin - Cm(3.0)) < 2000
    assert abs(sec.right_margin - Cm(1.5)) < 2000

    # 2. Font Times New Roman + Page 1 hides page number + PAGE field on pages 2+
    assert doc.styles["Normal"].font.name == "Times New Roman"
    assert sec.different_first_page_header_footer is True
    assert "PAGE" in sec.header._element.xml

    # 3. Collect all text from paragraphs & tables: ZERO raw HTML tags, all placeholders & Vietnamese intact
    all_texts = [p.text for p in doc.paragraphs] + [
        c.text for tbl in doc.tables for row in tbl.rows for c in row.cells
    ]
    joined = "\n".join(all_texts)
    assert "<div" not in joined.lower()
    assert "</div>" not in joined.lower()
    assert "<span" not in joined.lower()
    for expected in (
        "TRƯỜNG ĐẠI HỌC QUY NHƠN",
        "Số: 12/ĐX-HC",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "Độc lập - Tự do - Hạnh phúc",
        "Quy Nhơn, ngày 24 tháng 11 năm 2026",
        "[Nơi nhận]",
        "[Chức vụ/Đơn vị]",
        "[Ngày bắt đầu]",
        "[Ngày kết thúc]",
        "Nguyễn Văn Ánh",
        "NGƯỜI LÀM ĐƠN",
        "Nơi nhận:",
    ):
        assert expected in joined

    # 4. Explicit <div align="right"> paragraph rendered with RIGHT alignment
    right_para = next((p for p in doc.paragraphs if "Đoạn căn phải riêng" in p.text), None)
    assert right_para is not None
    assert right_para.alignment == WD_ALIGN_PARAGRAPH.RIGHT

    # 5. Header 2-col table + Footer 2-col table both present with fixed layout
    assert len(doc.tables) >= 2
    assert len(doc.tables[0].columns) == 2
    assert len(doc.tables[-1].columns) == 2
    assert 'w:type="fixed"' in doc.tables[0]._tbl.tblPr.xml
    assert 'w:type="fixed"' in doc.tables[-1]._tbl.tblPr.xml
    assert "cantSplit" in doc.tables[-1].rows[0]._tr.xml


def test_render_docx_personal_petition_alignment_indents_and_page_numbering():
    from docx.enum.section import WD_ORIENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm

    petition = DocumentDraft(
        title="Đơn xin nghỉ phép",
        layout="administrative",
        markdown=(
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
            "Độc lập - Tự do - Hạnh phúc\n\n"
            "*Quy Nhơn, ngày 24 tháng 11 năm 2026*\n\n"
            "# ĐƠN XIN NGHỈ PHÉP\n\n"
            "Kính gửi: Ban Giám hiệu Trường Đại học Quy Nhơn\n\n"
            "Tôi tên là: [Họ và tên], đơn vị [Chức vụ/Đơn vị]. "
            "Xin nghỉ phép 02 ngày từ 25/11/2026 đến 26/11/2026 vì lý do về quê có việc gấp.\n\n"
            "NGƯỜI LÀM ĐƠN\n"
            "(Ký và ghi rõ họ tên)\n"
            "[Họ và tên]"
        ),
        has_tables=False,
    )
    doc = Document(io.BytesIO(render_docx(petition)))
    sec = doc.sections[0]

    # Portrait A4 + Decree 30 margins + Arabic page numbering starting at 1, hidden on page 1
    assert sec.orientation == WD_ORIENT.PORTRAIT
    assert abs(sec.page_width - Cm(21.0)) < 2000
    assert abs(sec.page_height - Cm(29.7)) < 2000
    assert abs(sec.top_margin - Cm(2.0)) < 2000
    assert abs(sec.bottom_margin - Cm(2.0)) < 2000
    assert abs(sec.left_margin - Cm(3.0)) < 2000
    assert abs(sec.right_margin - Cm(1.5)) < 2000
    assert sec.different_first_page_header_footer is True
    assert 'w:start="1"' in sec._sectPr.xml
    assert "PAGE" in sec.header._element.xml

    # Motto centered with zero indent; date right-aligned with zero indent; title centered
    motto_p = next(p for p in doc.paragraphs if "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in p.text)
    assert motto_p.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert motto_p.paragraph_format.left_indent == 0
    assert motto_p.paragraph_format.first_line_indent == 0

    date_p = next(p for p in doc.paragraphs if "Quy Nhơn, ngày 24 tháng 11 năm 2026" in p.text)
    assert date_p.alignment == WD_ALIGN_PARAGRAPH.RIGHT
    assert date_p.paragraph_format.left_indent == 0
    assert date_p.paragraph_format.first_line_indent == 0

    title_p = next(p for p in doc.paragraphs if "ĐƠN XIN NGHỈ PHÉP" in p.text)
    assert title_p.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert title_p.paragraph_format.left_indent == 0

    # Personal petition signature block stays in fixed 2-col footer table (right cell centered, zero indent)
    assert len(doc.tables) == 1
    ftr = doc.tables[0]
    assert 'w:type="fixed"' in ftr._tbl.tblPr.xml
    assert "cantSplit" in ftr.rows[0]._tr.xml
    assert ftr.cell(0, 0).text.strip() == ""
    assert "NGƯỜI LÀM ĐƠN" in ftr.cell(0, 1).text
    assert ftr.cell(0, 1).paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert ftr.cell(0, 1).paragraphs[0].paragraph_format.left_indent == 0


def test_render_docx_black_white_tables_no_shading_no_stray_sep_and_clean_line_splits():
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    plan = DocumentDraft(
        title="Kế hoạch triển khai chuyển đổi số năm 2026",
        layout="administrative",
        markdown=(
            "| BỘ GIÁO DỤC VÀ ĐÀO TẠO<br>TRƯỜNG ĐẠI HỌC QUY NHƠN | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM<br>Độc lập - Tự do - Hạnh phúc |\n"
            "| :---: | :---: |\n"
            "| Số: 15/KH-ĐHQN | *Bình Định, ngày 24 tháng 11 năm 2026* |\n\n"
            "|---|---|---|\n\n"
            "# KẾ HOẠCH\n"
            "## Triển khai chuyển đổi số năm 2026\n\n"
            "## II. NỘI DUNG THỰC HIỆN\n"
            "| STT | Nhiệm vụ | Đơn vị chủ trì | Đơn vị phối hợp |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| 1 | Số hóa học liệu | Trung tâm Số & Học liệu | Phòng Đào tạo |\n"
            "| 2 | Nâng cấp hạ tầng | Phòng CNTT | Phòng Kế hoạch - Tài chính |\n\n"
            "Nơi nhận: - Các Phó Hiệu trưởng; - Các đơn vị; - Lưu: VT, S&HL.\n"
            "HIỆU TRƯỞNG PGS. TS. Đoàn Đức Tùng"
        ),
        has_tables=True,
    )
    doc = Document(io.BytesIO(render_docx(plan)))

    # 1. Zero w:shd shading anywhere in any table, black borders on content table, centered bold headers
    assert len(doc.tables) == 3  # header table + content table + footer table
    for tbl in doc.tables:
        assert "w:shd" not in tbl._tbl.xml
    content_tbl = doc.tables[1]
    assert 'w:color="000000"' in content_tbl._tbl.tblPr.xml
    assert content_tbl.cell(0, 0).paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert content_tbl.cell(0, 0).paragraphs[0].runs[0].bold is True

    # 2. Zero stray |---| or :--- separator lines in document text
    all_text = "\n".join(
        [p.text for p in doc.paragraphs]
        + [c.text for tbl in doc.tables for row in tbl.rows for c in row.cells]
    )
    assert "|---|" not in all_text
    assert ":---" not in all_text
    assert "[ĐƠN VỊ SOẠN THẢO]" not in all_text.upper()

    # 3. Header 2x2 table: Row 0 has org / Quốc hiệu-Tiêu ngữ, Row 1 has Số / date (no glued lines)
    assert len(doc.tables[0].rows) == 2
    hdr_r0_left = [p.text.strip() for p in doc.tables[0].cell(0, 0).paragraphs if p.text.strip()]
    assert hdr_r0_left == ["BỘ GIÁO DỤC VÀ ĐÀO TẠO", "TRƯỜNG ĐẠI HỌC QUY NHƠN"]
    assert doc.tables[0].cell(1, 0).text.strip() == "Số: 15/KH-ĐHQN"

    hdr_r0_right = [p.text.strip() for p in doc.tables[0].cell(0, 1).paragraphs if p.text.strip()]
    assert hdr_r0_right == ["CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "Độc lập - Tự do - Hạnh phúc"]
    assert doc.tables[0].cell(1, 1).text.strip() == "Bình Định, ngày 24 tháng 11 năm 2026"

    # 4. Footer left (Nơi nhận) & right (HIỆU TRƯỞNG / signer) split into separate paragraphs
    ftr_left_paras = [p.text.strip() for p in doc.tables[2].cell(0, 0).paragraphs if p.text.strip()]
    assert ftr_left_paras == [
        "Nơi nhận:",
        "- Các Phó Hiệu trưởng;",
        "- Các đơn vị;",
        "- Lưu: VT, S&HL.",
    ]
    ftr_right_paras = [p.text.strip() for p in doc.tables[2].cell(0, 1).paragraphs if p.text.strip()]
    assert ftr_right_paras == [
        "HIỆU TRƯỞNG",
        "PGS. TS. Đoàn Đức Tùng",
    ]


def test_render_docx_qnu_plan_full_decree_30_formatting():
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    plan = DocumentDraft(
        title="Kế hoạch triển khai số hóa học liệu năm 2026",
        layout="administrative",
        markdown=(
            "BỘ GIÁO DỤC VÀ ĐÀO TẠO\n"
            "TRƯỜNG ĐẠI HỌC QUY NHƠN\n"
            "Số: 28/KH-ĐHQN\n"
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
            "Độc lập - Tự do - Hạnh phúc\n"
            "____________________\n"
            "*Gia Lai, ngày 24 tháng 11 năm 2026*\n\n"
            "# KẾ HOẠCH\n"
            "## Triển khai số hóa học liệu năm 2026\n\n"
            "Căn cứ Quyết định số 131/QĐ-TTg của Thủ tướng Chính phủ về chuyển đổi số.\n\n"
            "Trường Đại học Quy Nhơn ban hành Kế hoạch triển khai số hóa học liệu năm 2026, cụ thể như sau:\n\n"
            "## I. MỤC ĐÍCH, YÊU CẦU\n"
            "### 1. Mục đích\n"
            "- Xây dựng kho học liệu số dùng chung toàn trường.\n"
            "### 2. Yêu cầu\n"
            "- Bảo đảm đúng tiến độ và chuẩn dữ liệu.\n\n"
            "## II. NỘI DUNG KẾ HOẠCH THỰC HIỆN\n"
            "| STT | Nội dung công việc | Thời gian | Đơn vị chủ trì | Đơn vị phối hợp | Sản phẩm |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| 1 | Rà soát danh mục giáo trình cần số hóa toàn trường | Tháng 12/2026 | Trung tâm S&HL | Các Khoa | Danh mục giáo trình số hóa được phê duyệt |\n\n"
            "## III. TỔ CHỨC THỰC HIỆN\n"
            "1. Trung tâm Số và Học liệu\n"
            "- Chủ trì triển khai và tổng hợp báo cáo định kỳ.\n\n"
            "Nơi nhận:\n"
            "- Các Phó Hiệu trưởng;\n"
            "- Các đơn vị;\n"
            "- Lưu: VT, S&HL.\n\n"
            "HIỆU TRƯỞNG\n"
            "PGS. TS. Đoàn Đức Tùng"
        ),
        has_tables=True,
    )
    doc = Document(io.BytesIO(render_docx(plan)))

    # 1. Header 2x2 table with w:pBdr rules, Số in (1,0), italic date in (1,1), zero raw ____
    hdr = doc.tables[0]
    assert len(hdr.rows) == 2 and len(hdr.columns) == 2
    assert "w:pBdr" in hdr.cell(0, 0).paragraphs[-1]._p.xml
    assert "w:pBdr" in hdr.cell(0, 1).paragraphs[-1]._p.xml
    assert hdr.cell(1, 0).text.strip() == "Số: 28/KH-ĐHQN"
    assert hdr.cell(1, 0).paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert hdr.cell(1, 1).text.strip() == "Gia Lai, ngày 24 tháng 11 năm 2026"
    assert hdr.cell(1, 1).paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert hdr.cell(1, 1).paragraphs[0].runs[0].italic is True
    all_text = "\n".join(
        [p.text for p in doc.paragraphs]
        + [c.text for t in doc.tables for r in t.rows for c in r.cells]
    )
    assert "____" not in all_text

    # 2. Title + Trích yếu + Căn cứ + Intro + Roman heading + Sub-heading + Bullet
    title_p = next(p for p in doc.paragraphs if p.text.strip() == "KẾ HOẠCH")
    assert title_p.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert title_p.runs[0].bold is True

    subtitle_p = next(p for p in doc.paragraphs if "Triển khai số hóa học liệu năm 2026" in p.text and p.alignment == WD_ALIGN_PARAGRAPH.CENTER)
    assert subtitle_p.runs[0].bold is True

    can_cu_p = next(p for p in doc.paragraphs if p.text.startswith("Căn cứ"))
    assert can_cu_p.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert abs(can_cu_p.paragraph_format.first_line_indent - Cm(1.0)) < 2000
    assert can_cu_p.runs[0].italic is True

    intro_p = next(p for p in doc.paragraphs if "cụ thể như sau:" in p.text)
    assert intro_p.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert abs(intro_p.paragraph_format.first_line_indent - Cm(1.0)) < 2000

    roman_p = next(p for p in doc.paragraphs if p.text.strip() == "I. MỤC ĐÍCH, YÊU CẦU")
    assert roman_p.alignment == WD_ALIGN_PARAGRAPH.LEFT
    assert roman_p.paragraph_format.first_line_indent == 0
    assert roman_p.runs[0].bold is True

    sub_p = next(p for p in doc.paragraphs if p.text.strip() == "1. Mục đích")
    assert abs(sub_p.paragraph_format.first_line_indent - Cm(1.0)) < 2000
    assert sub_p.runs[0].bold is True

    bullet_p = next(p for p in doc.paragraphs if p.text.startswith("- Xây dựng kho học liệu số"))
    assert bullet_p.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert abs(bullet_p.paragraph_format.first_line_indent - Cm(1.0)) < 2000

    # 3. Content table: tblHeader, cantSplit, zero w:shd, smart column alignments
    tbl = doc.tables[1]
    assert "w:shd" not in tbl._tbl.xml
    assert "tblHeader" in tbl.rows[0]._tr.xml
    assert all("cantSplit" in r._tr.xml for r in tbl.rows)
    # Header row centered & bold
    for cell in tbl.rows[0].cells:
        assert cell.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
        assert cell.paragraphs[0].runs[0].bold is True
    # Data row: STT(0), Thời gian(2), Đơn vị chủ trì(3), Đơn vị phối hợp(4) CENTER; Nội dung(1), Sản phẩm(5) LEFT
    data_row = tbl.rows[1].cells
    assert data_row[0].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert data_row[1].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.LEFT
    assert data_row[2].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert data_row[3].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert data_row[4].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert data_row[5].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.LEFT

    # 4. Footer 2-column table: left Nơi nhận (12pt bold italic + 11pt items), right HIỆU TRƯỞNG + 48pt gap + signer
    ftr = doc.tables[2]
    left_ps = [p for p in ftr.cell(0, 0).paragraphs if p.text.strip()]
    assert left_ps[0].text.strip() == "Nơi nhận:"
    assert left_ps[0].runs[0].bold is True and left_ps[0].runs[0].italic is True
    assert left_ps[0].runs[0].font.size == Pt(12)
    assert left_ps[1].runs[0].font.size == Pt(11)
    assert left_ps[1].alignment == WD_ALIGN_PARAGRAPH.LEFT

    right_ps = [p for p in ftr.cell(0, 1).paragraphs if p.text.strip()]
    assert [p.text.strip() for p in right_ps] == ["HIỆU TRƯỞNG", "PGS. TS. Đoàn Đức Tùng"]
    assert right_ps[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert right_ps[1].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert right_ps[1].paragraph_format.space_before == Pt(48)
    assert right_ps[1].runs[0].bold is True


def test_content_aware_auto_layout_header_plan_and_budget_tables_exact_165mm():
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn

    def _grid_dxa(table) -> list[int]:
        return [int(gc.get(qn("w:w"))) for gc in table._tbl.tblGrid.findall(qn("w:gridCol"))]

    def _row_tcw_dxa(row) -> list[int]:
        return [int(c._tc.tcPr.find(qn("w:tcW")).get(qn("w:w"))) for c in row.cells]

    # 1. Adaptive header column widths: standard org vs very long org, both sum to 165mm
    left_std, right_std = document_export._compute_header_col_widths_mm(
        ["BỘ GIÁO DỤC VÀ ĐÀO TẠO", "TRƯỜNG ĐẠI HỌC QUY NHƠN"], "Số: 28/KH-ĐHQN"
    )
    assert left_std >= 72.0
    assert abs((left_std + right_std) - 165.0) < 0.05

    left_long, right_long = document_export._compute_header_col_widths_mm(
        ["TRUNG TÂM CÔNG NGHỆ THÔNG TIN VÀ CHUYỂN ĐỔI SỐ QUY NHƠN"], None
    )
    assert left_long > left_std
    assert left_long <= 165.0 * 0.52 + 0.05
    assert abs((left_long + right_long) - 165.0) < 0.05

    # 2. 6-column Plan table: STT/Thời gian/Đơn vị compact, Nội dung/Sản phẩm expanded, exact 165mm (9355 dxa)
    plan = DocumentDraft(
        title="Kế hoạch triển khai chuyển đổi số",
        layout="administrative",
        markdown=(
            "BỘ GIÁO DỤC VÀ ĐÀO TẠO\n"
            "TRƯỜNG ĐẠI HỌC QUY NHƠN\n"
            "Số: 30/KH-ĐHQN\n"
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
            "Độc lập - Tự do - Hạnh phúc\n"
            "*Gia Lai, ngày 24 tháng 11 năm 2026*\n\n"
            "# KẾ HOẠCH\n"
            "## Triển khai chuyển đổi số năm 2026\n\n"
            "| STT | Nội dung công việc | Thời gian | Đơn vị chủ trì | Đơn vị phối hợp | Sản phẩm |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| 1 | Rà soát, chuẩn hóa toàn bộ danh mục giáo trình và học liệu số phục vụ đào tạo đại học | Tháng 12/2026 | Trung tâm S&HL | Không | Bộ danh mục học liệu số chuẩn hóa được Hiệu trưởng phê duyệt |\n"
        ),
        has_tables=True,
    )
    doc = Document(io.BytesIO(render_docx(plan)))
    hdr_tbl = doc.tables[0]
    assert sum(_grid_dxa(hdr_tbl)) == 9355
    assert sum(_row_tcw_dxa(hdr_tbl.rows[0])) == 9355
    # Org text paragraphs must have zero indent (not squeezed by border indents)
    assert hdr_tbl.cell(0, 0).paragraphs[0].paragraph_format.left_indent == 0
    assert hdr_tbl.cell(0, 0).paragraphs[0].paragraph_format.right_indent == 0

    plan_tbl = doc.tables[1]
    plan_grid = _grid_dxa(plan_tbl)
    assert sum(plan_grid) == 9355
    assert all(sum(_row_tcw_dxa(r)) == 9355 for r in plan_tbl.rows)
    # STT (0) >= 15mm (850 dxa) so 13pt bold "STT" stays on 1 line; Nội dung (1) & Sản phẩm (5) wider than Thời gian (2)
    assert plan_grid[0] >= 850
    assert plan_grid[0] < plan_grid[2]
    assert plan_grid[1] > plan_grid[2]
    assert plan_grid[5] > plan_grid[2]
    # Standalone "Không" in "Đơn vị phối hợp" normalized to "-"
    assert plan_tbl.rows[1].cells[4].text.strip() == "-"

    # 3. Budget / Công văn table: numeric columns right-aligned, exact 165mm, no duplicate title above V/v
    budget_cv = DocumentDraft(
        title="Công văn đề nghị cấp kinh phí",
        layout="administrative",
        markdown=(
            "BỘ GIÁO DỤC VÀ ĐÀO TẠO\n"
            "TRƯỜNG ĐẠI HỌC QUY NHƠN\n"
            "Số: 102/ĐHQN-KHTC\n"
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
            "Độc lập - Tự do - Hạnh phúc\n"
            "*Gia Lai, ngày 24 tháng 11 năm 2026*\n\n"
            "V/v đề nghị phê duyệt dự toán kinh phí triển khai hệ thống AI\n\n"
            "Kính gửi: Ban Giám hiệu Trường Đại học Quy Nhơn\n\n"
            "| STT | Nội dung chi tiêu dự toán | Số lượng | Thành tiền (VNĐ) |\n"
            "| --- | --- | --- | --- |\n"
            "| 1 | Thuê hạ tầng máy chủ GPU và lưu trữ dữ liệu đào tạo | 12 | 120.000.000 |\n"
            "| 2 | Tập huấn sử dụng trợ lý AI cho giảng viên các khoa | 5 | 25.000.000 |\n\n"
            "Nơi nhận:\n- Như trên;\n- Lưu: VT.\n\n"
            "HIỆU TRƯỞNG\nPGS. TS. Đoàn Đức Tùng"
        ),
        has_tables=True,
    )
    cv_doc = Document(io.BytesIO(render_docx(budget_cv)))
    # No duplicate centered "CÔNG VĂN ĐỀ NGHỊ..." title inserted above "V/v ..."
    assert not any(p.text.strip() == "CÔNG VĂN ĐỀ NGHỊ CẤP KINH PHÍ" for p in cv_doc.paragraphs)
    budget_tbl = cv_doc.tables[1]
    assert sum(_grid_dxa(budget_tbl)) == 9355
    assert all(sum(_row_tcw_dxa(r)) == 9355 for r in budget_tbl.rows)
    row1 = budget_tbl.rows[1].cells
    assert row1[0].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER  # STT
    assert row1[1].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.LEFT    # Nội dung chi
    assert row1[2].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.RIGHT   # Số lượng
    assert row1[3].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.RIGHT   # Thành tiền
    # Symmetric 165mm footer
    ftr_tbl = cv_doc.tables[2]
    assert sum(_grid_dxa(ftr_tbl)) == 9355


def test_extract_admin_header_parses_pipe_wrapped_rows_across_blank_lines_with_zero_pipes():
    plan = DocumentDraft(
        title="Kế hoạch triển khai chuyển đổi số",
        layout="administrative",
        markdown=(
            "| BỘ GIÁO DỤC VÀ ĐÀO TẠO | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM |\n"
            "| TRƯỜNG ĐẠI HỌC QUY NHƠN | Độc lập - Tự do - Hạnh phúc |\n\n"
            "| Số: [...]/KH-ĐHQN | Gia Lai, ngày [...] tháng [...] năm 2026 |\n\n"
            "# KẾ HOẠCH\n"
            "## Triển khai chuyển đổi số năm 2026\n\n"
            "Trường Đại học Quy Nhơn ban hành kế hoạch triển khai cụ thể như sau:"
        ),
        has_tables=False,
    )
    doc = Document(io.BytesIO(render_docx(plan)))
    hdr = doc.tables[0]
    assert len(hdr.rows) == 2 and len(hdr.columns) == 2

    left_r0 = [p.text.strip() for p in hdr.cell(0, 0).paragraphs if p.text.strip()]
    right_r0 = [p.text.strip() for p in hdr.cell(0, 1).paragraphs if p.text.strip()]
    left_r1 = hdr.cell(1, 0).text.strip()
    right_r1 = hdr.cell(1, 1).text.strip()

    assert left_r0 == ["BỘ GIÁO DỤC VÀ ĐÀO TẠO", "TRƯỜNG ĐẠI HỌC QUY NHƠN"]
    assert right_r0 == ["CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "Độc lập - Tự do - Hạnh phúc"]
    assert left_r1 == "Số: [...]/KH-ĐHQN"
    assert right_r1 == "Gia Lai, ngày [...] tháng [...] năm 2026"

    all_hdr_text = "\n".join(c.text for r in hdr.rows for c in r.cells)
    assert "|" not in all_hdr_text












