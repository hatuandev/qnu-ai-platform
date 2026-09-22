"""Office Document Parser Strategies — Word (.docx), Excel (.xlsx), and Plain Text."""

from __future__ import annotations

import io
import logging
import re

from app.modules.knowledge.cleaner import clean_markdown_text
from app.modules.knowledge.parsers.base import BaseDocumentParser, ExtractedTable, ParsedContent

logger = logging.getLogger(__name__)


class DocxParser(BaseDocumentParser):
    """Word (.docx, .doc) document parser extracting headings, paragraphs, and tables sequentially."""

    async def parse(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        try:
            doc = docx.Document(io.BytesIO(file_bytes))
        except Exception as exc:
            logger.warning("Could not parse DOCX directly: %s. Falling back to empty document.", exc)
            return ParsedContent(raw_text="", page_count=1, tables=[])

        md_lines: list[str] = []
        extracted_tables: list[ExtractedTable] = []
        table_counter = 0

        for child in doc.element.body:
            if child.tag.endswith("p"):
                p = Paragraph(child, doc)
                text = p.text.strip()
                if not text:
                    continue

                style_name = (p.style.name or "").lower() if p.style else ""
                if "heading 1" in style_name or text.startswith(
                    ("I. ", "II. ", "III. ", "IV. ", "V. ", "VI. ", "VII. ", "VIII. ", "IX. ", "X. ")
                ):
                    md_lines.append(f"\n## {text}\n")
                elif "heading 2" in style_name or (text.isupper() and len(text) < 90 and not text.endswith(".")):
                    md_lines.append(f"\n### {text}\n")
                elif text.startswith(
                    ("1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. ", "10. ", "11. ", "12. ", "13. ", "14. ", "15. ")
                ):
                    md_lines.append(f"\n**{text}**\n")
                elif text.startswith(("- ", "+ ", "* ")):
                    md_lines.append(text)
                else:
                    md_lines.append(text + "\n")

            elif child.tag.endswith("tbl"):
                table = Table(child, doc)
                if not table.rows:
                    continue

                # Case A: 1-2 rows, 2 columns -> Administrative Header (National Motto / Agency)
                if len(table.rows) <= 2 and len(table.columns) == 2:
                    all_text = " ".join(c.text.strip() for r in table.rows for c in r.cells).upper()
                    if any(
                        k in all_text
                        for k in ["CỘNG HÒA", "CỘNG HOA", "ĐỘC LẬP", "QUỐC HIỆU", "TRƯỜNG ĐẠI HỌC", "BỘ GIÁO DỤC"]
                    ):
                        c0_raw = table.rows[0].cells[0].text.strip()
                        c1_raw = table.rows[0].cells[1].text.strip()

                        so_match = re.search(r"(Số\s*:\s*[^\n|*]+)", c0_raw, re.IGNORECASE)
                        so_line = f"> *{so_match.group(1).strip()}*  \n" if so_match else ""

                        c0_clean = re.sub(r"Số\s*:\s*[^\n|*]+", "", c0_raw).strip()
                        c0_clean = re.sub(r"\s+", " ", c0_clean)

                        date_match = re.search(
                            r"((?:[A-ZÀ-Ỹa-zà-ỹ\s]+,\s*)?ngày\s+\d+\s+tháng\s+\d+\s+năm\s+\d+|ngày\s+\d+\s+tháng\s+\d+\s+năm\s+\d+)",
                            c1_raw,
                            re.IGNORECASE,
                        )
                        date_str = date_match.group(1).strip() if date_match else ""

                        c1_title = re.sub(r"((?:[A-ZÀ-Ỹa-zà-ỹ\s]+,\s*)?ngày[^\n|*]+)", "", c1_raw).strip()
                        c1_title = re.sub(r"\s+", " ", c1_title)
                        if not c1_title or "CỘNG" in c1_title.upper():
                            c1_title = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM — Độc lập - Tự do - Hạnh phúc"

                        md_lines.append(f"> **{c0_clean}**  \n")
                        if so_line:
                            md_lines.append(so_line)
                        md_lines.append(f"> **{c1_title}**  \n")
                        if date_str:
                            md_lines.append(f"> *{date_str}*\n")
                        md_lines.append("\n---\n")
                        continue

                # Case A.2: Closing Signer & Recipients table
                if len(table.columns) == 2 and any("nơi nhận" in c.text.lower() for r in table.rows for c in r.cells):
                    c0_text = table.rows[0].cells[0].text.strip()
                    c1_text = table.rows[0].cells[1].text.strip()
                    if "nơi nhận" in c0_text.lower():
                        rec_text, signer_text = c0_text, c1_text
                    else:
                        rec_text, signer_text = c1_text, c0_text

                    rec_lines = [line.strip() for line in rec_text.splitlines() if line.strip()]
                    clean_rec_items = []
                    for l_str in rec_lines:
                        if not l_str.lower().startswith("nơi nhận"):
                            cleaned_item = l_str.lstrip("-*+• \t")
                            clean_rec_items.append(f"- {cleaned_item}")
                    clean_rec = "\n".join(clean_rec_items)

                    signer_lines = [
                        re.sub(r"[*_#`]", "", s_l).strip() for s_l in signer_text.splitlines() if s_l.strip()
                    ]
                    title_lines = [
                        sl
                        for sl in signer_lines
                        if re.search(
                            r"\b(?:HIỆU TRƯỞNG|GIÁM ĐỐC|TRƯỞNG|CHỦ TỊCH|KT\.|TL\.|PHÓ)\b",
                            sl,
                            re.IGNORECASE,
                        )
                        or sl.isupper()
                    ]
                    title_str = (
                        "\n".join(f"**{tl}**" for tl in title_lines)
                        if title_lines
                        else (f"**{signer_lines[0]}**" if signer_lines else "")
                    )
                    signer_name = signer_lines[-1] if len(signer_lines) > len(title_lines) else ""
                    name_str = f"\n**{signer_name}**" if signer_name else ""

                    signed_note = ""
                    if re.search(r"\bĐã ký\b", signer_text, re.IGNORECASE):
                        signed_note = "  \n*(Đã ký và đóng dấu)*"

                    md_lines.append(
                        f"\n\n---\n\n**Nơi nhận:**\n{clean_rec}\n\n{title_str}{signed_note}{name_str}\n\n"
                    )
                    continue

                # Case B: Standard / Multi-row data tables
                r0_cells = [c.text.strip().replace("\n", " ") for c in table.rows[0].cells]
                start_row = 1
                headers = r0_cells

                if len(table.rows) > 1:
                    r1_cells = [c.text.strip().replace("\n", " ") for c in table.rows[1].cells]
                    r1_first = r1_cells[0].strip() if r1_cells else ""
                    is_r1_data = (
                        r1_first.isdigit()
                        or bool(re.match(r"^\d+\b", r1_first))
                        or (len(r1_cells) > 1 and r1_cells[1].isdigit())
                    )

                    has_subheaders = False
                    if not is_r1_data:
                        has_merged_in_r0 = any(
                            r0_cells[k] == r0_cells[k + 1] and r0_cells[k] for k in range(len(r0_cells) - 1)
                        )
                        has_sub_words = any(
                            w in " ".join(r1_cells).lower()
                            for w in ["chỉ tiêu", "số lượng", "mã xét tuyển", "tổ hợp"]
                        )
                        if has_merged_in_r0 or has_sub_words:
                            has_subheaders = True

                    if has_subheaders:
                        start_row = 2
                        combined_headers = []
                        for c0, c1 in zip(r0_cells, r1_cells):
                            if c0 == c1 or not c0:
                                combined_headers.append(c1 or c0 or "")
                            elif not c1:
                                combined_headers.append(c0)
                            else:
                                combined_headers.append(f"{c1} ({c0})")
                        headers = combined_headers

                # Drop columns that are completely empty across all rows (spacing columns)
                raw_num_cols = len(table.columns)
                cols_to_keep = []
                for c_idx in range(raw_num_cols):
                    all_empty = True
                    for r in table.rows:
                        if c_idx < len(r.cells) and r.cells[c_idx].text.strip():
                            all_empty = False
                            break
                    if not all_empty:
                        cols_to_keep.append(c_idx)

                if not cols_to_keep:
                    cols_to_keep = list(range(raw_num_cols))

                headers = [headers[k] for k in cols_to_keep if k < len(headers)]
                clean_headers = [h if h.strip() else f"Cột {idx + 1}" for idx, h in enumerate(headers)]
                num_cols = len(clean_headers)

                table_lines = [
                    "| " + " | ".join(clean_headers) + " |",
                    "| "
                    + " | ".join(
                        [":---:" if idx == 0 and num_cols > 3 else ":---" for idx in range(num_cols)]
                    )
                    + " |",
                ]
                table_data_rows: list[list[str]] = []

                for row in table.rows[start_row:]:
                    row_cells_kept = [row.cells[k] for k in cols_to_keep if k < len(row.cells)]
                    clean_cell_texts = [
                        c.text.strip().replace("\n", " ") for c in row_cells_kept if c.text.strip()
                    ]
                    unique_texts = list(dict.fromkeys(clean_cell_texts))

                    is_roman_category = False
                    if unique_texts and len(row_cells_kept) > 2:
                        first_cell_txt = unique_texts[0].strip("*_# ")
                        if (
                            re.match(
                                r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|PHẦN|CHƯƠNG)\b",
                                first_cell_txt,
                                re.IGNORECASE,
                            )
                            and len(unique_texts) <= 2
                        ):
                            is_roman_category = True

                    if is_roman_category:
                        clean_cat = " — ".join(unique_texts)
                        if len(table_lines) == 2:
                            table_lines.clear()
                        else:
                            table_lines.append("\n")
                        table_lines.append(f"### {clean_cat}\n")
                        table_lines.append("| " + " | ".join(clean_headers) + " |")
                        table_lines.append(
                            "| "
                            + " | ".join(
                                [":---:" if idx == 0 and num_cols > 3 else ":---" for idx in range(num_cols)]
                            )
                            + " |"
                        )
                        continue

                    # Extract cells and handle horizontal merged cells (colspan)
                    cells = []
                    seen_tcs = set()
                    for c in row_cells_kept:
                        tc_id = id(c._tc)
                        if tc_id in seen_tcs:
                            cells.append("")
                            continue
                        seen_tcs.add(tc_id)

                        val = c.text.strip()
                        if not val:
                            cells.append("")
                            continue
                        lines = [ln.strip() for ln in val.splitlines() if ln.strip()]
                        if len(lines) > 1:
                            if all(re.match(r"^[A-D]\d{2}\b", ln) for ln in lines) or all(
                                ln.startswith(("-", "+", "*")) for ln in lines
                            ):
                                joined = "; ".join(lines)
                            else:
                                joined = "<br>".join(lines)
                        else:
                            joined = val
                        cells.append(joined.replace("|", "\\|"))

                    if len(cells) < num_cols:
                        cells += [""] * (num_cols - len(cells))
                    elif len(cells) > num_cols:
                        cells = cells[:num_cols]

                    table_lines.append("| " + " | ".join(cells) + " |")
                    table_data_rows.append(cells)

                md_table = "\n".join(table_lines)
                md_lines.append("\n\n" + md_table + "\n\n")

                table_counter += 1
                extracted_tables.append(
                    ExtractedTable(
                        page_number=table_counter,
                        headers=clean_headers,
                        rows=table_data_rows,
                        markdown_repr=md_table,
                    )
                )

        raw_result = "\n".join(md_lines).strip()
        cleaned = clean_markdown_text(raw_result)
        return ParsedContent(
            raw_text=cleaned,
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
