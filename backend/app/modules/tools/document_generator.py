"""Document Generator Service — Renders ND 30 Word (.docx) via docxtpl and converts to PDF via Gotenberg."""

from __future__ import annotations

import io
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
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
    "cong_van": "mau_to_trinh_nd30.docx",
}


def _normalize_context(context: dict[str, Any]) -> dict[str, Any]:
    """Ensure standard variables exist with respectable default values."""
    now = datetime.now(UTC)
    normalized = dict(context)

    normalized.setdefault("ngay", f"{now.day:02d}")
    normalized.setdefault("thang", f"{now.month:02d}")
    normalized.setdefault("nam", str(now.year))
    normalized.setdefault(
        "ngay_thang",
        f"ngày {now.day:02d} tháng {now.month:02d} năm {now.year}",
    )
    normalized.setdefault("so_hieu", ".../TTr-ĐHQN")
    normalized.setdefault("don_vi_ban_hanh", "TRƯỜNG ĐẠI HỌC QUY NHƠN")
    normalized.setdefault("kinh_gui", "Ban Giám hiệu Trường Đại học Quy Nhơn")
    normalized.setdefault("trich_yeu", "Về việc triển khai nhiệm vụ công tác")
    normalized.setdefault(
        "noi_dung",
        "Kính đề nghị Ban Giám hiệu xem xét và phê duyệt nội dung theo quy định hiện hành.",
    )
    normalized.setdefault("noi_nhan", "- Như kính gửi;\n- Lưu: VT, ĐT.")
    normalized.setdefault("chuc_vu_nguoi_ky", "HIỆU TRƯỞNG")
    normalized.setdefault("ho_ten_nguoi_ky", "PGS.TS. Đỗ Ngọc Mỹ")
    normalized.setdefault(
        "can_cu_phap_ly",
        "Căn cứ Quyết định số 4740/QĐ-BGDĐT của Bộ Giáo dục và Đào tạo;\nCăn cứ Quy chế tổ chức và hoạt động của Trường Đại học Quy Nhơn;",
    )
    return normalized


def render_docx_template(template_code: str, context: dict[str, Any]) -> bytes:
    """Render a DOCX document using docxtpl from a registered template code."""
    filename = TEMPLATE_MAP.get(template_code.lower()) or "mau_to_trinh_nd30.docx"
    template_path = TEMPLATES_DIR / filename

    if not template_path.is_file():
        raise FileNotFoundError(f"Template '{filename}' not found in {TEMPLATES_DIR}")

    prepared_context = _normalize_context(context)
    doc = DocxTemplate(str(template_path))
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

    base = base_name or f"qnu_van_ban_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    clean_base = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base)
    artifacts: list[dict[str, Any]] = []

    # 1. Render DOCX
    docx_bytes = render_docx_template(template_code, context)
    docx_filename = f"{clean_base}.docx"
    docx_rel_path = f"artifacts/{docx_filename}"
    await storage_service.save(docx_rel_path, docx_bytes)

    artifacts.append(
        {
            "id": f"art_docx_{uuid.uuid4().hex[:8]}",
            "name": docx_filename,
            "type": "docx",
            "size": len(docx_bytes),
            "url": f"/platform/v1alpha1/tools/artifacts/{docx_filename}",
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
                    "url": f"/platform/v1alpha1/tools/artifacts/{pdf_filename}",
                    "mime_type": "application/pdf",
                }
            )

    return artifacts
