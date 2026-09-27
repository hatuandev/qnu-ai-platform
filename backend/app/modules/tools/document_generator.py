"""Document Generator Service — Renders ND 30 Word (.docx) via docxtpl and converts to PDF via Gotenberg."""

from __future__ import annotations

import io
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from docx.text.paragraph import Paragraph
from docxtpl import DocxTemplate

from app.core.config import get_settings
from app.core.storage import storage_service

logger = logging.getLogger(__name__)
settings = get_settings()

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "documents"

TEMPLATE_MAP = {
    "to_trinh": "mau_to_trinh_nd30.docx",
    "mau_to_trinh": "mau_to_trinh_nd30.docx",
    "qnu_to_trinh": "mau_to_trinh_nd30.docx",
    "thong_bao": "mau_thong_bao_nd30.docx",
    "mau_thong_bao": "mau_thong_bao_nd30.docx",
    "qnu_thong_bao": "mau_thong_bao_nd30.docx",
    "quyet_dinh": "mau_quyet_dinh_nd30.docx",
    "mau_quyet_dinh": "mau_quyet_dinh_nd30.docx",
    "qnu_quyet_dinh": "mau_quyet_dinh_nd30.docx",
}

_TEMPLATE_INSTITUTION_NAME = "TRƯỜNG ĐẠI HỌC QUY NHƠN"


def _normalize_context(context: dict[str, Any]) -> dict[str, Any]:
    """Fill unset fields with visible placeholders instead of invented facts."""
    normalized = dict(context)

    normalized.setdefault("ngay", "[BỔ SUNG NGÀY]")
    normalized.setdefault("thang", "[BỔ SUNG THÁNG]")
    normalized.setdefault("nam", "[BỔ SUNG NĂM]")
    normalized.setdefault("ngay_thang", "[BỔ SUNG NGÀY BAN HÀNH]")
    normalized.setdefault("so_hieu", "[CHƯA CẤP SỐ VĂN BẢN]")
    issuing_unit = str(normalized.get("don_vi_ban_hanh") or "").strip()
    if issuing_unit.casefold() == _TEMPLATE_INSTITUTION_NAME.casefold():
        issuing_unit = ""
    normalized["don_vi_ban_hanh"] = issuing_unit
    normalized.setdefault("kinh_gui", "[BỔ SUNG ĐƠN VỊ KÍNH GỬI]")
    normalized.setdefault("trich_yeu", "[BỔ SUNG TRÍCH YẾU]")
    normalized.setdefault("noi_dung", "[BỔ SUNG NỘI DUNG DỰ THẢO]")
    normalized.setdefault("noi_nhan", "- [BỔ SUNG NƠI NHẬN]")
    normalized.setdefault("chuc_vu_nguoi_ky", "[BỔ SUNG CHỨC VỤ NGƯỜI KÝ]")
    normalized.setdefault("ho_ten_nguoi_ky", "[BỔ SUNG HỌ TÊN NGƯỜI KÝ]")
    normalized.setdefault(
        "can_cu_phap_ly", "[BỔ SUNG CĂN CỨ PHÁP LÝ ĐÃ ĐƯỢC XÁC NHẬN (NẾU CẦN)]"
    )
    return normalized


def _mark_document_as_draft(template: DocxTemplate) -> None:
    """Put a visible draft notice before all template content."""
    document = template.get_docx()
    paragraph_element = OxmlElement("w:p")
    document._element.body.insert(0, paragraph_element)
    paragraph = Paragraph(paragraph_element, document._body)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("DỰ THẢO — CHƯA BAN HÀNH")
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(128, 128, 128)


def _remove_optional_line(template: DocxTemplate, marker: str) -> None:
    """Remove an unused template run and the line break immediately before it."""
    document = template.get_docx()
    paragraphs = list(document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)

    for paragraph in paragraphs:
        for index, run in enumerate(paragraph.runs):
            if marker not in run.text:
                continue
            previous_run = paragraph.runs[index - 1] if index else None
            run._element.getparent().remove(run._element)
            if previous_run is not None:
                breaks = previous_run._element.findall(qn("w:br"))
                if breaks:
                    previous_run._element.remove(breaks[-1])
            return


def _apply_administrative_page_setup(template: DocxTemplate) -> None:
    """Enforce the A4 page size required by the administrative template."""
    document = template.get_docx()
    for section in document.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)


def render_docx_template(template_code: str, context: dict[str, Any]) -> bytes:
    """Render a DOCX document using docxtpl from a registered template code."""
    filename = TEMPLATE_MAP.get(template_code.lower())
    if not filename:
        raise ValueError(f"No administrative DOCX template is registered for '{template_code}'")
    template_path = TEMPLATES_DIR / filename

    if not template_path.is_file():
        raise FileNotFoundError(f"Template '{filename}' not found in {TEMPLATES_DIR}")

    prepared_context = _normalize_context(context)
    doc = DocxTemplate(str(template_path))
    _apply_administrative_page_setup(doc)

    # ``DocxTemplate.get_docx()`` reloads the original template after a render.
    # Add the draft notice first so the following render keeps both the notice
    # and the resolved template values in the final document.
    if prepared_context.get("is_draft", False):
        _mark_document_as_draft(doc)
    if not prepared_context["don_vi_ban_hanh"]:
        _remove_optional_line(doc, "{{ don_vi_ban_hanh }}")
    doc.render(prepared_context)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


async def convert_docx_to_pdf_gotenberg(docx_bytes: bytes, filename: str) -> bytes | None:
    """Convert DOCX bytes to PDF bytes via Gotenberg 8 LibreOffice endpoint.

    Gracefully returns None if Gotenberg is unreachable or fails, allowing fallback.
    """
    gotenberg_url = settings.clean_gotenberg_url
    target_url = f"{gotenberg_url}/forms/libreoffice/convert"
    docx_name = filename if filename.endswith(".docx") else f"{filename}.docx"

    try:
        async with httpx.AsyncClient(timeout=60.0, auth=settings.gotenberg_auth) as client:
            response = await client.post(
                target_url,
                files={"files": (docx_name, docx_bytes)},
            )
            if response.status_code == 200 and response.content.startswith(b"%PDF-"):
                logger.info("Successfully converted '%s' to PDF via Gotenberg", docx_name)
                return response.content
            logger.warning(
                "Gotenberg conversion failed for '%s' (status=%d): %s",
                docx_name,
                response.status_code,
                response.text[:200],
            )
            return None
    except Exception as exc:
        logger.warning(
            "Gotenberg unreachable at %s for '%s': %s (Graceful fallback to DOCX)",
            target_url,
            docx_name,
            exc,
        )
        return None


async def export_document_package(
    template_code: str,
    context: dict[str, Any],
    formats: list[str] | None = None,
    base_name: str | None = None,
) -> list[dict[str, Any]]:
    """Generate both DOCX and PDF (if requested & available), persist to storage, and return artifacts."""
    target_formats = [f.lower().strip() for f in (formats or ["docx", "pdf"])]
    if "both" in target_formats:
        target_formats = ["docx", "pdf"]
    unsupported = sorted(set(target_formats) - {"docx", "pdf"})
    if unsupported:
        raise ValueError(f"Unsupported document format(s): {', '.join(unsupported)}")

    base = base_name or f"qnu_van_ban_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    clean_base = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base)
    artifacts: list[dict[str, Any]] = []

    # DOCX is the conversion source even when only PDF was requested.
    docx_bytes = render_docx_template(template_code, context)
    docx_filename = f"{clean_base}.docx"
    if "docx" in target_formats:
        docx_rel_path = f"artifacts/{docx_filename}"
        await storage_service.save(docx_rel_path, docx_bytes)
        artifacts.append(
            {
                "id": f"art_docx_{uuid.uuid4().hex[:8]}",
                "name": docx_filename,
                "type": "docx",
                "size": len(docx_bytes),
                "url": f"/platform/v1alpha1/tools/artifacts/{quote(docx_filename, safe='')}",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
        )

    # 2. Convert to PDF if requested
    if "pdf" in target_formats:
        pdf_bytes = await convert_docx_to_pdf_gotenberg(docx_bytes, docx_filename)
        if pdf_bytes:
            pdf_filename = f"{clean_base}.pdf"
            pdf_rel_path = f"artifacts/{pdf_filename}"
            await storage_service.save(pdf_rel_path, pdf_bytes)
            artifacts.append(
                {
                    "id": f"art_pdf_{uuid.uuid4().hex[:8]}",
                    "name": pdf_filename,
                    "type": "pdf",
                    "size": len(pdf_bytes),
                    "url": f"/platform/v1alpha1/tools/artifacts/{quote(pdf_filename, safe='')}",
                    "mime_type": "application/pdf",
                }
            )

    return artifacts
