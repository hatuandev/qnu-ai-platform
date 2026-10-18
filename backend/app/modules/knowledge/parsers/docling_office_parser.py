"""Docling Office parser for DOCX, XLSX and PPTX.

The Office backends are declarative parsers. They do not run OCR or local
embedding models; OCR remains an explicit Gemini/Mistral API concern in the
OCR module.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from collections import defaultdict
from io import BytesIO
from typing import Any

from app.modules.knowledge.parsers.base import BaseDocumentParser, ExtractedTable, ParsedContent

logger = logging.getLogger(__name__)


_BACKEND_CONFIG: dict[str, tuple[str, str]] = {
    "docx": ("MsWordDocumentBackend", "DOCX"),
    "doc": ("MsWordDocumentBackend", "DOC"),
    "xlsx": ("MsExcelDocumentBackend", "XLSX"),
    "xls": ("MsExcelDocumentBackend", "XLS"),
    "pptx": ("MsPowerpointDocumentBackend", "PPTX"),
    "ppt": ("MsPowerpointDocumentBackend", "PPT"),
}


def _docx_header_evidence(content: bytes, document: Any) -> dict[str, dict[str, Any]]:
    """Use original Word row roles only when the entire source grid matches uniquely."""
    from docx import Document
    from docx.oxml.ns import qn

    def signature(rows):
        return tuple(tuple(" ".join(unicodedata.normalize("NFC", cell.text).split()) for cell in row) for row in rows)

    originals = defaultdict(list)
    for index, table in enumerate(Document(BytesIO(content)).tables):
        flags = []
        for row in table.rows:
            props = row._tr.trPr
            flag = props.find(qn("w:tblHeader")) if props is not None else None
            flags.append(flag is not None and flag.get(qn("w:val"), "1") not in {"0", "false", "off"})
        depth = 0
        for enabled in flags:
            if not enabled:
                break
            depth += 1
        originals[signature([row.cells for row in table.rows])].append({
            "basis": "docx_tblHeader", "locator": f"word/document.xml/table/{index + 1}",
            "leading_header_rows": depth, "row_header_flags": flags,
        })
    converted = defaultdict(list)
    for table in getattr(document, "tables", []):
        grid = getattr(getattr(table, "data", None), "grid", None) or []
        if grid:
            converted[signature(grid)].append(table)
    evidence = {}
    for key, tables in converted.items():
        matches = originals.get(key, [])
        if len(tables) == len(matches) == 1:
            evidence[tables[0].self_ref] = matches[0]
    return evidence


class DoclingOfficeParser(BaseDocumentParser):
    """Parse Office Open XML documents through Docling's declarative backends."""

    def __init__(self, extension: str, fallback: BaseDocumentParser | None = None) -> None:
        self.extension = extension.lower().lstrip(".")
        self.fallback = fallback

    async def parse(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        try:
            return await asyncio.to_thread(self._parse_sync, file_bytes, file_name)
        except (ImportError, ModuleNotFoundError) as exc:
            if self.fallback is None:
                raise RuntimeError(
                    "Docling Office parser dependencies are unavailable. "
                    "Install docling-slim[format-office,format-pdf-pypdfium2]."
                ) from exc
            logger.warning(
                "Docling Office parser unavailable for %s; using native fallback: %s",
                file_name,
                exc,
            )
            parsed = await self.fallback.parse(file_bytes, file_name)
            parsed.metadata = {**parsed.metadata, "parser": "native_fallback"}
            return parsed

    def _parse_sync(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        if self.extension not in _BACKEND_CONFIG:
            raise ValueError(f"Unsupported Docling Office extension: {self.extension}")
        backend_name, format_name = _BACKEND_CONFIG[self.extension]

        if format_name in {"DOCX", "DOC"}:
            from docling.backend.msword_backend import MsWordDocumentBackend as backend_type
        elif format_name in {"XLSX", "XLS"}:
            from docling.backend.msexcel_backend import MsExcelDocumentBackend as backend_type
        else:
            from docling.backend.mspowerpoint_backend import (
                MsPowerpointDocumentBackend as backend_type,
            )

        from docling.datamodel.document import InputDocument, InputFormat

        input_document = InputDocument(
            path_or_stream=BytesIO(file_bytes),
            format=getattr(InputFormat, format_name),
            backend=backend_type,
            filename=file_name,
        )
        if not input_document.valid:
            raise RuntimeError(f"Docling rejected Office document: {file_name}")

        document = input_document._backend.convert()
        from app.modules.knowledge.parsers.docx_evidence import read_docx_evidence

        evidence = read_docx_evidence(file_bytes, document) if format_name in {"DOCX", "DOC"} else {}
        markdown = self._preserve_table_spans(document, document.export_to_markdown().strip())
        pages = self._page_count(document)
        tables = self._extract_markdown_tables(markdown)
        return ParsedContent(
            raw_text=markdown,
            page_count=pages,
            tables=tables,
            metadata={
                "parser": "docling",
                "parser_backend": backend_name,
                "source_format": self.extension,
            },
            docling_document=document,
            docx_header_evidence=_docx_header_evidence(file_bytes, document) if format_name in {"DOCX", "DOC"} else {},
            docx_source_evidence=evidence,
        )

    @staticmethod
    def _preserve_table_spans(document: Any, markdown: str) -> str:
        """Use the existing span-aware HTML projection for explicitly merged cells."""
        from app.modules.knowledge.services.html_tables import normalize_html_tables

        for table in getattr(document, "tables", []):
            cells = getattr(getattr(table, "data", None), "table_cells", [])
            if not any(getattr(cell, "row_span", 1) > 1 or getattr(cell, "col_span", 1) > 1 for cell in cells):
                continue
            original = table.export_to_markdown(doc=document).strip()
            projected = normalize_html_tables(table.export_to_html(doc=document)).strip()
            # Exact single occurrence: never replace an ambiguous repeated table or unrelated prose.
            if original and markdown.count(original) == 1:
                markdown = markdown.replace(original, projected, 1)
            else:
                logger.warning("docling_table_span_projection_ambiguous")
        return markdown

    @staticmethod
    def _page_count(document: Any) -> int:
        pages = getattr(document, "pages", None)
        if isinstance(pages, dict) and pages:
            return len(pages)
        max_page = 1
        try:
            for item, _level in document.iterate_items():
                for provenance in getattr(item, "prov", None) or []:
                    page_number = getattr(provenance, "page_no", None)
                    if page_number is not None:
                        max_page = max(max_page, int(page_number))
        except (AttributeError, TypeError, ValueError):
            pass
        return max_page

    @staticmethod
    def _extract_markdown_tables(markdown: str) -> list[ExtractedTable]:
        """Extract simple GFM tables while retaining the full Docling markdown."""
        lines = markdown.splitlines()
        tables: list[ExtractedTable] = []
        index = 0
        while index + 1 < len(lines):
            header = lines[index].strip()
            separator = lines[index + 1].strip()
            if not (header.startswith("|") and header.endswith("|")):
                index += 1
                continue
            if not re.fullmatch(r"\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|", separator):
                index += 1
                continue
            block = [header, separator]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                block.append(lines[index].strip())
                index += 1
            rows = [[cell.strip() for cell in row.strip("|").split("|")] for row in block[2:]]
            headers = [cell.strip() for cell in block[0].strip("|").split("|")]
            tables.append(
                ExtractedTable(
                    page_number=1,
                    headers=headers,
                    rows=rows,
                    markdown_repr="\n".join(block),
                )
            )
        return tables
