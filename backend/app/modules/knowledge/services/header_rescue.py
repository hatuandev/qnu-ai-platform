"""Selective OCR for visibly incomplete administrative fields, not table replacement."""

import logging
import re
import unicodedata
from typing import Any

import pymupdf
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.core.exceptions import AppException
from app.modules.knowledge.cleaner import extract_administrative_metadata
from app.modules.knowledge.services.temporal_metadata import extract_temporal_metadata
from app.modules.ocr.service import OCRService

logger = logging.getLogger(__name__)


def missing_header_fields(text: str) -> list[str]:
    """Field grammar/empty placeholders, never a catalog of document titles."""
    head = text.split("|", 1)[0][:1600]
    result = []
    number = re.search(r"(?im)^\s*[*#_]*\s*Số\s*:\s*([^\n]*)", head)
    if number and not re.search(r"\d", number[1]):
        result.append("document_number")
    temporal = extract_temporal_metadata(head)
    if temporal["issued_year"]["status"] == "proposed" and temporal["issued_date"]["value"] is None:
        result.append("issued_date")
    return result


def prepare_header_rescue(content: bytes, record: dict[str, Any]) -> dict[str, Any] | None:
    missing = missing_header_fields(record["extracted_text"])
    if not missing:
        return None
    with pymupdf.open(stream=content, filetype="pdf") as document:
        page = document[0]
        # Bound the crop above the first table; retain the two administrative columns.
        tops = [(block.get("coordinates") or {}).get("top", 100) / 100 * page.rect.height
                for block in record.get("blocks", []) if block.get("type") == "table"]
        bottom = min([page.rect.height * 0.4, *tops])
        crop = pymupdf.Rect(0, 0, page.rect.width, bottom)
        if crop.is_empty or crop.is_infinite:
            record["metadata_rescue"] = {"version": "header-rescue-v1", "status": "unavailable",
                "bbox": list(crop), "missing_fields": missing, "accepted_lines": [], "error_code": "HEADER_CROP_EMPTY"}
            return None
        return {"missing": missing, "bbox": list(crop),
                "content": page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=crop).tobytes("png")}


def _field_lines(text: str) -> dict[str, str]:
    result = {}
    candidates: dict[str, set[str]] = {"document_number": set(), "issued_date": set()}
    for line in unicodedata.normalize("NFC", text).splitlines():
        clean = line.strip().strip("*_# ")
        if re.match(r"Số\s*:", clean, re.IGNORECASE):
            clean = re.sub(r"\s*/\s*", "/", clean)
            number = extract_administrative_metadata(clean).get("document_number")
            if number:
                candidates["document_number"].add(clean)
        # OCR may drop whitespace at any letter/digit boundary. Change separators only,
        # never the digits, spelling, diacritics or date order supplied by the provider.
        spaced = re.sub(r"(?<=[^\W\d_])(?=\d)|(?<=\d)(?=[^\W\d_])", " ", clean)
        if extract_temporal_metadata(spaced)["issued_date"]["value"]:
            candidates["issued_date"].add(spaced)
    for field, lines in candidates.items():
        if len(lines) == 1:
            result[field] = next(iter(lines))
    return result


async def rescue_header(_db: AsyncSession, page: dict[str, Any], prepared: dict[str, Any],
                        engine: str | None, tenant_id: str) -> None:
    audit = {"version": "header-rescue-v1", "status": "unavailable", "bbox": prepared["bbox"],
             "missing_fields": prepared["missing"], "accepted_lines": []}
    page["metadata_rescue"] = audit
    try:
        # OCR persists its own usage/job logs. Never commit the caller's source transaction.
        async with AsyncSessionFactory() as ocr_db:
            response = await OCRService().extract_document(session=ocr_db, content=prepared["content"],
                filename="header.png", engine_name=engine if engine not in (None, "native", "pymupdf_ocr") else "auto",
                tenant_id=tenant_id)
        if not response.success or len(response.pages) != 1:
            raise AppException("OCR vùng đầu không trả đúng một trang.", code="HEADER_OCR_INVALID", status_code=422)
        audit["ocr_text"] = response.pages[0].extracted_text
        found = _field_lines(response.pages[0].extracted_text)
        # Compare only standalone header fields. A date inside a cited legal basis
        # is not the issuing date of this document and must not cause false conflict.
        original = {field: extract_administrative_metadata(line).get(field) for field, line in
                    _field_lines(page["extracted_text"].split("|", 1)[0]).items()}
        for field, line in found.items():
            value = extract_administrative_metadata(line).get(field)
            if original.get(field) is not None and value != original[field]:
                audit.update(status="conflict", engine=response.engine_used)
                return
        accepted = [found[field] for field in prepared["missing"] if field in found]
        audit.update(status="proposed" if len(accepted) == len(prepared["missing"]) else "incomplete",
                     engine=response.engine_used, accepted_lines=accepted)
        if accepted:
            # Only copied field lines enter canonical text. The native table remains byte-for-byte intact.
            page["extracted_text"] = "\n\n".join([*accepted, page["extracted_text"]])
    except Exception as exc:
        audit["error_code"] = getattr(exc, "code", type(exc).__name__)
        logger.warning("header_metadata_rescue_unavailable tenant=%s code=%s", tenant_id, audit["error_code"])
