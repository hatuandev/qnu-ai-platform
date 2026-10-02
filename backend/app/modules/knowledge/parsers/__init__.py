"""Parsers Package — Factory & Strategy Registry for Document Intelligence."""

from __future__ import annotations

from app.modules.knowledge.parsers.base import BaseDocumentParser, ExtractedTable, ParsedContent
from app.modules.knowledge.parsers.docling_office_parser import DoclingOfficeParser
from app.modules.knowledge.parsers.markdown_parser import MarkdownParser
from app.modules.knowledge.parsers.office_parser import (
    DocxParser,
    PlainTextParser,
    PptxParser,
    XlsxParser,
)
from app.modules.knowledge.parsers.pdf_inspector import PDFInspectionResult, PDFInspector
from app.modules.knowledge.parsers.pdf_parser import PyMuPdfParser

_PARSERS: dict[str, BaseDocumentParser] = {
    "pdf": PyMuPdfParser(),
    "docx": DoclingOfficeParser("docx", fallback=DocxParser()),
    "doc": DoclingOfficeParser("doc"),
    "xlsx": DoclingOfficeParser("xlsx", fallback=XlsxParser()),
    "xls": DoclingOfficeParser("xls"),
    "pptx": DoclingOfficeParser("pptx", fallback=PptxParser()),
    "ppt": DoclingOfficeParser("ppt"),
    "txt": PlainTextParser(),
    "md": MarkdownParser(),
    "csv": PlainTextParser(),
}


def get_document_parser(file_extension: str) -> BaseDocumentParser:
    """Factory selecting the optimal parsing strategy based on file extension."""
    clean_ext = file_extension.lower().lstrip(".")
    parser = _PARSERS.get(clean_ext)
    if parser is None:
        return PlainTextParser()
    return parser


__all__ = [
    "BaseDocumentParser",
    "DocxParser",
    "ExtractedTable",
    "MarkdownParser",
    "PDFInspectionResult",
    "PDFInspector",
    "ParsedContent",
    "PlainTextParser",
    "PyMuPdfParser",
    "XlsxParser",
    "DoclingOfficeParser",
    "PptxParser",
    "get_document_parser",
]
