"""Parsers Package — Factory & Strategy Registry for Document Intelligence."""

from __future__ import annotations

from app.modules.knowledge.parsers.base import BaseDocumentParser, ExtractedTable, ParsedContent
from app.modules.knowledge.parsers.office_parser import DocxParser, PlainTextParser, XlsxParser
from app.modules.knowledge.parsers.pdf_parser import PyMuPdfParser

_PARSERS: dict[str, BaseDocumentParser] = {
    "pdf": PyMuPdfParser(),
    "docx": DocxParser(),
    "doc": DocxParser(),
    "xlsx": XlsxParser(),
    "xls": XlsxParser(),
    "txt": PlainTextParser(),
    "md": PlainTextParser(),
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
    "ParsedContent",
    "PlainTextParser",
    "PyMuPdfParser",
    "XlsxParser",
    "get_document_parser",
]
