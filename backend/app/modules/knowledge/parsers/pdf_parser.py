"""PyMuPDF Document Parser Strategy — High-speed text, layout & table extraction."""

from __future__ import annotations

import logging

import fitz  # PyMuPDF

from app.modules.knowledge.parsers.base import BaseDocumentParser, ExtractedTable, ParsedContent

logger = logging.getLogger(__name__)


class PyMuPdfParser(BaseDocumentParser):
    """Fast PDF parser preserving page numbers, structure and tables."""

    async def parse(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = len(doc)
        full_text_parts: list[str] = []
        extracted_tables: list[ExtractedTable] = []

        for page_idx in range(page_count):
            page = doc[page_idx]
            page_num = page_idx + 1

            # 1. Extract tables from page using PyMuPDF native table finder
            page_tables = page.find_tables()
            table_markdowns: list[str] = []
            for tab in page_tables:
                extracted = tab.extract()
                if not extracted or len(extracted) < 2:
                    continue
                headers = [str(c or "").strip() for c in extracted[0]]
                rows = [[str(c or "").strip() for c in r] for r in extracted[1:]]

                # Convert to markdown table format
                header_line = "| " + " | ".join(headers) + " |"
                sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
                data_lines = ["| " + " | ".join(r) + " |" for r in rows]
                md_table = "\n".join([header_line, sep_line] + data_lines)
                table_markdowns.append(md_table)

                extracted_tables.append(
                    ExtractedTable(
                        page_number=page_num,
                        headers=headers,
                        rows=rows,
                        markdown_repr=md_table,
                    )
                )

            # 2. Extract standard page text
            page_text = page.get_text("text").strip()
            if page_text:
                page_header = f"\n\n<!-- Page {page_num} -->\n"
                full_text_parts.append(page_header + page_text)

            # Append markdown tables if detected
            if table_markdowns:
                full_text_parts.append("\n\n" + "\n\n".join(table_markdowns))

        raw_text = "\n".join(full_text_parts).strip()
        metadata = {
            "title": doc.metadata.get("title") or file_name,
            "author": doc.metadata.get("author") or "",
            "page_count": page_count,
            "table_count": len(extracted_tables),
        }
        doc.close()

        return ParsedContent(
            raw_text=raw_text,
            page_count=page_count,
            tables=extracted_tables,
            metadata=metadata,
        )
