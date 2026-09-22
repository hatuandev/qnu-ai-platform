"""PyMuPDF Document Parser Strategy — High-speed text, layout & table extraction."""

from __future__ import annotations

import logging
import re

import pymupdf as fitz

from app.modules.knowledge.normalization.markdown_renderer import (
    render_canonical_document_markdown,
    render_canonical_table_markdown,
)
from app.modules.knowledge.normalization.models import (
    BlockType,
    CanonicalBlock,
    CanonicalCell,
    CanonicalDocument,
    CanonicalRow,
    CanonicalTable,
    SourceSpan,
)
from app.modules.knowledge.normalization.table_reconstructor import (
    _is_phantom_header,
    reconstruct_multi_page_tables,
    table_schema_key,
)
from app.modules.knowledge.parsers.base import BaseDocumentParser, ExtractedTable, ParsedContent
from app.modules.knowledge.parsers.blocks import (
    extract_page_blocks,
    find_page_tables,
    suppress_nested_tables,
)

logger = logging.getLogger(__name__)


def _intersection_ratio(r1: fitz.Rect, r2: fitz.Rect) -> float:
    """Calculate intersection over r1 area."""
    inter = r1 & r2
    if inter.is_empty or r1.get_area() <= 0:
        return 0.0
    return inter.get_area() / r1.get_area()


def _is_table_text(text_rect: fitz.Rect, table_rects: list[fitz.Rect]) -> bool:
    """Return True if text_rect falls significantly inside any table bounding box (including side-by-side tables)."""
    if not table_rects or text_rect.is_empty or text_rect.get_area() <= 0:
        return False
    total_inter = 0.0
    for tr in table_rects:
        # Buffer margin of 6pt horizontally and 10pt vertically to capture rows hugging borders/footer
        buffered_tr = fitz.Rect(tr.x0 - 6.0, tr.y0 - 4.0, tr.x1 + 6.0, tr.y1 + 10.0)
        inter = text_rect & buffered_tr
        if not inter.is_empty:
            total_inter += inter.get_area()
        center_pt = fitz.Point(
            (text_rect.x0 + text_rect.x1) / 2.0,
            (text_rect.y0 + text_rect.y1) / 2.0,
        )
        if buffered_tr.contains(center_pt):
            return True
        # If top edge of text rect starts inside table vertically and horizontally
        if tr.y0 <= text_rect.y0 <= (tr.y1 + 6.0) and (tr.x0 - 10.0) <= center_pt.x <= (tr.x1 + 10.0):
            return True
    return (total_inter / text_rect.get_area()) >= 0.35


class _RawTableItem:
    """Container for raw extracted table matrix and bounding box before canonicalization."""

    def __init__(self, bbox: tuple[float, float, float, float], rows: list[list[str]]):
        self.bbox = bbox
        self.rows = rows


def _fuse_side_by_side_tables(tables: list[_RawTableItem]) -> list[_RawTableItem]:
    """Fuse horizontally adjacent tables that share the same vertical Y-span (e.g. IELTS and VSTEP)."""
    if len(tables) < 2:
        return tables

    sorted_tables = sorted(tables, key=lambda t: t.bbox[0])
    fused: list[_RawTableItem] = []
    skip_indices: set[int] = set()

    for i in range(len(sorted_tables)):
        if i in skip_indices:
            continue
        t1 = sorted_tables[i]
        matched_j = None

        for j in range(i + 1, len(sorted_tables)):
            if j in skip_indices:
                continue
            t2 = sorted_tables[j]

            y0_1, y1_1 = t1.bbox[1], t1.bbox[3]
            y0_2, y1_2 = t2.bbox[1], t2.bbox[3]
            h1 = max(1.0, y1_1 - y0_1)
            h2 = max(1.0, y1_2 - y0_2)
            v_overlap = max(0.0, min(y1_1, y1_2) - max(y0_1, y0_2))
            overlap_ratio = v_overlap / min(h1, h2)

            x1_1 = t1.bbox[2]
            x0_2 = t2.bbox[0]
            is_horiz_adjacent = (x0_2 >= t1.bbox[0]) and (x1_1 <= x0_2 + 35.0)

            if overlap_ratio >= 0.70 and is_horiz_adjacent:
                matched_j = j
                break

        if matched_j is not None:
            t2 = sorted_tables[matched_j]
            skip_indices.add(matched_j)

            max_r = max(len(t1.rows), len(t2.rows))
            cols1 = max((len(r) for r in t1.rows), default=0)
            cols2 = max((len(r) for r in t2.rows), default=0)
            new_rows: list[list[str]] = []
            for r_idx in range(max_r):
                r1 = t1.rows[r_idx] if r_idx < len(t1.rows) else [""] * cols1
                r2 = t2.rows[r_idx] if r_idx < len(t2.rows) else [""] * cols2
                r1_padded = r1 + [""] * max(0, cols1 - len(r1))
                r2_padded = r2 + [""] * max(0, cols2 - len(r2))
                new_rows.append(r1_padded + r2_padded)

            # Disambiguate duplicate header names across fused tables (e.g. "Điểm quy đổi" -> "Điểm quy đổi IELTS")
            if new_rows:
                h1_names = [new_rows[0][c] for c in range(cols1)]
                h2_names = [new_rows[0][cols1 + c] for c in range(cols2)]
                for c in range(cols2):
                    h2_val = h2_names[c].strip()
                    if h2_val and h2_val in h1_names:
                        ctx1 = next((w for w in h1_names if any(k in w.lower() for k in ["ielts", "toefl", "pt1"])), "")
                        ctx2 = next((w for w in h2_names if any(k in w.lower() for k in ["vstep", "đgnl", "pt2"])), "")
                        if "ielts" in ctx1.lower() or "vstep" in ctx2.lower():
                            h1_idx = h1_names.index(h2_val)
                            new_rows[0][h1_idx] = f"{h2_val} IELTS"
                            new_rows[0][cols1 + c] = f"{h2_val} VSTEP"
                        elif ctx1 or ctx2:
                            h1_idx = h1_names.index(h2_val)
                            new_rows[0][h1_idx] = f"{h2_val} ({ctx1})"
                            new_rows[0][cols1 + c] = f"{h2_val} ({ctx2})"

            new_bbox = (
                min(t1.bbox[0], t2.bbox[0]),
                min(t1.bbox[1], t2.bbox[1]),
                max(t1.bbox[2], t2.bbox[2]),
                max(t1.bbox[3], t2.bbox[3]),
            )
            fused.append(_RawTableItem(bbox=new_bbox, rows=new_rows))
        else:
            fused.append(t1)

    return fused


def _normalize_raw_table_rows(
    table_rows: list[list[str]],
) -> tuple[str | None, list[str], list[list[str]]]:
    """Extract appendix/table title if captured as row 0, and merge multi-line header rows."""
    if not table_rows:
        return None, [], []
    rows = list(table_rows)
    title_text = None
    first_non_empty = [c.strip() for c in rows[0] if c.strip()]
    if len(first_non_empty) == 1 and re.match(
        r"^\s*(?:PHỤ\s+LỤC|BẢNG|DANH\s+MỤC)\b", first_non_empty[0], re.IGNORECASE
    ):
        title_text = first_non_empty[0]
        rows = rows[1:]

    if not rows:
        return title_text, [], []

    def _is_hdr(r_cells: list[str], is_first_header: bool = False) -> bool:
        non_empty = [
            str(c or "").strip()
            for c in r_cells
            if str(c or "").strip() and not _is_phantom_header(str(c or ""))
        ]
        if not non_empty:
            return False
        if is_first_header and len(non_empty) < 2:
            return False

        first = non_empty[0]
        # Check 1: Primary data sequence keys (STT, task code, Roman numeral, or program code)
        if (
            re.fullmatch(r"^\d+$", first)
            or re.fullmatch(r"^\d+(?:\.\d+)+$", first)
            or re.fullmatch(r"^[IVXLCDM]+$", first)
            or re.fullmatch(r"^\d{7}[A-Za-z]*$", first)
        ):
            return False

        # Check 2: Paragraph descriptions, bullet points or multi-sentence content
        if any(
            len(c) > 45
            or c.startswith(("- ", "+ ", "• ", "* "))
            or (c.endswith((".", "...")) and len(c) > 10)
            or ";" in c
            or re.search(r"[\.;]\s+[A-ZÀ-Ỹ]", c)
            for c in non_empty
        ):
            return False

        # Check 2b: Sub-headers (level 2+) single cell must be short labels
        if not is_first_header and len(non_empty) == 1 and len(non_empty[0]) > 25:
            return False

        # Check 3: Numeric / date density (headers are predominantly text labels)
        data_re = re.compile(r"\d+[/\-]\d+|\d+%\b|\btháng\s+\d|\bnăm\s+\d", re.IGNORECASE)
        data_count = sum(1 for c in non_empty if data_re.search(c))
        if (data_count / len(non_empty)) > 0.20:
            return False

        # Check 4: Check if any cell has a distinct program or task code
        if any(
            re.fullmatch(r"^\d{7}[A-Za-z]*$", c) or re.fullmatch(r"^\d+\.\d+$", c)
            for c in non_empty
        ):
            return False

        # Check 5: Every meaningful header cell must contain alphabetic characters
        return all(re.search(r"[a-zA-Zà-ỹÀ-Ỹ]", c) for c in non_empty)

    h_count = 0
    while h_count < min(3, len(rows)) and _is_hdr(rows[h_count], is_first_header=(h_count == 0)):
        h_count += 1

    if h_count > 1:
        cols = len(rows[0])
        merged_hdr = [""] * cols
        for r in rows[:h_count]:
            for i, c in enumerate(r):
                val = c.strip()
                if val:
                    merged_hdr[i] = (f"{merged_hdr[i]} {val}").strip() if merged_hdr[i] else val
        return title_text, merged_hdr, rows[h_count:]

    return title_text, rows[0], rows[1:]


class PyMuPdfParser(BaseDocumentParser):
    """Fast PDF parser preserving page numbers, structure and non-duplicated tables."""

    async def parse(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = len(doc)
        geometry_blocks: list[dict] = []
        raw_canonical_tables: list[CanonicalTable] = []
        canonical_blocks: list[CanonicalBlock] = []

        for page_idx in range(page_count):
            page = doc[page_idx]
            page_num = page_idx + 1

            # 0. Extract real geometry blocks (for studio bounding boxes UI)
            for block in extract_page_blocks(page):
                geometry_blocks.append({"page_number": page_num, **block})

            # 1. Detect native tables on current page (suppressing nested sub-tables)
            raw_tab_list = list(getattr(find_page_tables(page), "tables", []) or [])
            page_tables = suppress_nested_tables(raw_tab_list)

            # Convert to _RawTableItem and apply horizontal side-by-side fusion
            raw_table_items: list[_RawTableItem] = []
            for tab in page_tables:
                extracted = tab.extract() or []
                cleaned_rows = [
                    [str(c or "").strip() for c in r]
                    for r in extracted
                    if any(str(c or "").strip() for c in r)
                ]
                if cleaned_rows:
                    raw_table_items.append(_RawTableItem(bbox=tab.bbox, rows=cleaned_rows))

            fused_table_items = _fuse_side_by_side_tables(raw_table_items)
            table_rects: list[fitz.Rect] = []
            page_table_words: set[str] = set()

            for t_idx, item in enumerate(fused_table_items):
                t_rect = fitz.Rect(item.bbox)
                table_rects.append(t_rect)

                title_text, headers, data_rows = _normalize_raw_table_rows(item.rows)
                if title_text:
                    canonical_blocks.append(
                        CanonicalBlock(
                            block_id=f"heading_p{page_num}_{t_idx+1}",
                            type=BlockType.HEADING,
                            text=title_text,
                            source_span=SourceSpan(
                                page_number=page_num,
                                bbox=(t_rect.x0, t_rect.y0, t_rect.x1, t_rect.y0 + 20.0),
                            ),
                        )
                    )

                schema_key = table_schema_key(headers)
                canonical_rows: list[CanonicalRow] = []

                # Index table cell words for content deduplication
                for r in data_rows:
                    for c in r:
                        for word in str(c or "").strip().lower().split():
                            if len(word) >= 3:
                                page_table_words.add(word)

                for r_idx, r_cells in enumerate(data_rows):
                    cells = [
                        CanonicalCell(
                            raw_value=str(c or "").strip(),
                            normalized_value=str(c or "").strip() if str(c or "").strip() else None,
                            source_span=SourceSpan(
                                page_number=page_num,
                                bbox=(t_rect.x0, t_rect.y0, t_rect.x1, t_rect.y1),
                            ),
                        )
                        for c in r_cells
                    ]
                    canonical_rows.append(
                        CanonicalRow(
                            row_id=f"p{page_num}_t{t_idx+1}_r{r_idx+1}",
                            cells=cells,
                            source_pages=[page_num],
                        )
                    )

                raw_canonical_tables.append(
                    CanonicalTable(
                        table_id=f"table_p{page_num}_{t_idx+1}",
                        schema_key=schema_key,
                        headers=headers,
                        rows=canonical_rows,
                        source_pages=[page_num],
                        bbox=(t_rect.x0, t_rect.y0, t_rect.x1, t_rect.y1),
                    )
                )

            # 2. Extract non-table text blocks (P0.1: Suppress table text from paragraph stream)
            raw_blocks = page.get_text("blocks") or []
            for b_idx, b in enumerate(raw_blocks):
                # b = (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 7 and b[6] != 0:
                    continue  # Skip image blocks
                txt = str(b[4] or "").strip()
                if not txt:
                    continue

                b_rect = fitz.Rect(b[0], b[1], b[2], b[3])
                if _is_table_text(b_rect, table_rects):
                    # Text belongs to a table -> suppress to avoid duplication!
                    continue

                # Filter out standalone page numbers (header <= 8% from page 2 onward, or footer >= 88%)
                is_page_num = bool(
                    re.fullmatch(r"(?:Trang\s+)?\d{1,3}(?:\s*/\s*\d{1,3})?", txt, re.IGNORECASE)
                )
                if is_page_num:
                    if b_rect.y0 > page.rect.height * 0.88:
                        continue
                    if page_num > 1 and b_rect.y1 < page.rect.height * 0.08:
                        continue

                # Xử lý khối văn bản cắt ngang biên giới bảng (ví dụ: chân bảng nối với Nơi nhận / Chữ ký)
                if table_rects:
                    bx0, by0, bx1, by1 = b_rect.x0, b_rect.y0, b_rect.x1, b_rect.y1
                    for tr in table_rects:
                        inter = b_rect & tr
                        if not inter.is_empty:
                            if tr.y0 <= by0 < tr.y1 < by1:
                                clip_rect = fitz.Rect(bx0, tr.y1, bx1, by1)
                                clipped_txt = page.get_text("text", clip=clip_rect).strip()
                                if clipped_txt:
                                    txt = clipped_txt
                                    by0 = tr.y1
                                    b_rect = fitz.Rect(bx0, by0, bx1, by1)
                                else:
                                    txt = ""
                                break
                            elif by0 < tr.y0 < by1 <= tr.y1:
                                clip_rect = fitz.Rect(bx0, by0, bx1, tr.y0)
                                clipped_txt = page.get_text("text", clip=clip_rect).strip()
                                if clipped_txt:
                                    txt = clipped_txt
                                    by1 = tr.y0
                                    b_rect = fitz.Rect(bx0, by0, bx1, by1)
                                else:
                                    txt = ""
                                break

                if not txt:
                    continue

                # Content-level anti-leakage: if text block heavily overlaps table cells on this page
                is_heading = bool(
                    re.match(
                        r"^\s*(?:\d+[\.\)]|[IVXLCDM]+[\.\)]|#+|\bĐiều\b|\bMục\b|\bChương\b|\bPhần\b|\bPhụ lục\b)",
                        txt,
                    )
                )
                is_admin_bullet = txt.startswith(("- ", "+ ", "• "))
                if not is_heading and not is_admin_bullet and page_table_words:
                    b_words = [w for w in txt.lower().split() if len(w) >= 3]
                    if len(b_words) >= 4:
                        overlap = sum(1 for w in b_words if w in page_table_words)
                        if (overlap / len(b_words)) >= 0.40 and any(char.isdigit() for char in txt):
                            # Table data leakage detected outside table bounding box -> suppress!
                            continue

                b_type = (
                    BlockType.HEADING
                    if txt.startswith("#") or txt.upper().startswith("PHỤ LỤC")
                    else BlockType.PARAGRAPH
                )

                canonical_blocks.append(
                    CanonicalBlock(
                        block_id=f"block_p{page_num}_{b_idx+1}",
                        type=b_type,
                        text=txt,
                        source_span=SourceSpan(
                            page_number=page_num,
                            bbox=(b_rect.x0, b_rect.y0, b_rect.x1, b_rect.y1),
                        ),
                    )
                )

        # 3. P0.2: Reconstruct multi-page tables across the entire document
        reconstructed_tables = reconstruct_multi_page_tables(raw_canonical_tables)

        # 4. Build the CanonicalDocument
        canonical_doc = CanonicalDocument(
            document_id=file_name,
            page_count=page_count,
            blocks=canonical_blocks,
            tables=reconstructed_tables,
            metadata={
                "title": doc.metadata.get("title") or file_name,
                "author": doc.metadata.get("author") or "",
                "page_count": page_count,
                "table_count": len(reconstructed_tables),
            },
        )

        # 5. Render clean, unified Markdown (Duplicate-free, single-line table rows)
        clean_markdown = render_canonical_document_markdown(canonical_doc)

        # 6. Backward-compatible ExtractedTable list for downstream consumers
        extracted_tables: list[ExtractedTable] = []
        for tbl in reconstructed_tables:
            p_num = min(tbl.source_pages) if tbl.source_pages else 1
            headers = tbl.headers
            rows = [[c.raw_value for c in r.cells] for r in tbl.rows]
            tbl_md = render_canonical_table_markdown(tbl)
            extracted_tables.append(
                ExtractedTable(
                    page_number=p_num,
                    headers=headers,
                    rows=rows,
                    markdown_repr=tbl_md,
                )
            )

        # 7. Run Firecrawl Rust-based PDF Inspector for smart classification and OCR routing
        from app.modules.knowledge.parsers.pdf_inspector import PDFInspector

        inspection = PDFInspector.inspect_bytes(file_bytes)

        # If native canonical markdown is empty but inspector recovered text, use it as fallback
        final_markdown = clean_markdown
        if (not final_markdown or not final_markdown.strip()) and inspection.markdown and inspection.markdown.strip():
            final_markdown = inspection.markdown

        metadata = {
            "title": doc.metadata.get("title") or file_name,
            "author": doc.metadata.get("author") or "",
            "page_count": page_count,
            "table_count": len(extracted_tables),
            "pdf_type": inspection.pdf_type,
            "confidence": inspection.confidence,
            "pages_needing_ocr": inspection.pages_needing_ocr,
            "has_encoding_issues": inspection.has_encoding_issues,
            "is_complex_layout": inspection.is_complex_layout,
            "pages_with_tables": inspection.pages_with_tables,
            "inspector_engine": inspection.inspector_engine,
            "inspection_time_ms": inspection.processing_time_ms,
        }
        doc.close()

        return ParsedContent(
            raw_text=final_markdown,
            page_count=page_count,
            tables=extracted_tables,
            metadata=metadata,
            blocks=geometry_blocks,
            canonical_document=canonical_doc,
        )
