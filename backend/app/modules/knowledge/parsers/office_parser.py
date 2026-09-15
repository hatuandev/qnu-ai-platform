"""Office Document Parser Strategies — Word (.docx), Excel (.xlsx), and Plain Text."""

from __future__ import annotations

import io
import logging

from app.modules.knowledge.parsers.base import BaseDocumentParser, ExtractedTable, ParsedContent

logger = logging.getLogger(__name__)


class DocxParser(BaseDocumentParser):
    """Word (.docx) document parser extracting headings, paragraphs, and tables."""

    async def parse(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        import docx

        doc = docx.Document(io.BytesIO(file_bytes))
        full_text_parts: list[str] = []
        extracted_tables: list[ExtractedTable] = []

        # 1. Extract paragraphs with markdown style formatting
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if p.style.name.startswith("Heading 1"):
                full_text_parts.append(f"# {text}")
            elif p.style.name.startswith("Heading 2"):
                full_text_parts.append(f"## {text}")
            elif p.style.name.startswith("Heading 3"):
                full_text_parts.append(f"### {text}")
            else:
                full_text_parts.append(text)

        # 2. Extract tables
        for table_idx, table in enumerate(doc.tables):
            if not table.rows:
                continue
            headers = [cell.text.strip() for cell in table.rows[0].cells]
            rows: list[list[str]] = []
            for row in table.rows[1:]:
                rows.append([cell.text.strip() for cell in row.cells])

            if headers:
                header_line = "| " + " | ".join(headers) + " |"
                sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
                data_lines = ["| " + " | ".join(r) + " |" for r in rows]
                md_table = "\n".join([header_line, sep_line] + data_lines)
                full_text_parts.append("\n\n" + md_table)

                extracted_tables.append(
                    ExtractedTable(
                        page_number=table_idx + 1,
                        headers=headers,
                        rows=rows,
                        markdown_repr=md_table,
                    )
                )

        raw_text = "\n\n".join(full_text_parts).strip()
        return ParsedContent(
            raw_text=raw_text,
            page_count=1,
            tables=extracted_tables,
            metadata={"table_count": len(extracted_tables)},
        )


class XlsxParser(BaseDocumentParser):
    """Excel (.xlsx) spreadsheet parser converting sheets into structured Markdown tables."""

    async def parse(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        full_text_parts: list[str] = []
        extracted_tables: list[ExtractedTable] = []

        for sheet_idx, sheet_name in enumerate(wb.sheetnames):
            sheet = wb[sheet_name]
            rows_data: list[list[str]] = []
            for row in sheet.iter_rows(values_only=True):
                if any(row):  # Skip completely empty rows
                    rows_data.append([str(c or "").strip() for c in row])

            if len(rows_data) < 2:
                continue

            headers = rows_data[0]
            data_rows = rows_data[1:]

            header_line = "| " + " | ".join(headers) + " |"
            sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
            data_lines = ["| " + " | ".join(r) + " |" for r in data_rows]
            md_table = f"### Bảng: {sheet_name}\n" + "\n".join([header_line, sep_line] + data_lines)

            full_text_parts.append(md_table)
            extracted_tables.append(
                ExtractedTable(
                    page_number=sheet_idx + 1,
                    headers=headers,
                    rows=data_rows,
                    markdown_repr=md_table,
                )
            )

        wb.close()
        raw_text = "\n\n".join(full_text_parts).strip()
        return ParsedContent(
            raw_text=raw_text,
            page_count=len(wb.sheetnames),
            tables=extracted_tables,
            metadata={"sheet_count": len(wb.sheetnames)},
        )


class PlainTextParser(BaseDocumentParser):
    """Fallback parser for .txt, .md, and .csv text documents."""

    async def parse(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")

        return ParsedContent(raw_text=text.strip(), page_count=1)
