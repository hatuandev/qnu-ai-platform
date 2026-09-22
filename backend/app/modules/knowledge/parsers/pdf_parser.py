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
        inter = text_rect & tr
        if not inter.is_empty:
            total_inter += inter.get_area()
        center_pt = fitz.Point(
            (text_rect.x0 + text_rect.x1) / 2.0,
            (text_rect.y0 + text_rect.y1) / 2.0,
        )
        if tr.contains(center_pt):
            return True
    return (total_inter / text_rect.get_area()) >= 0.40


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
            table_rects: list[fitz.Rect] = []

            for t_idx, tab in enumerate(page_tables):
                extracted = tab.extract()
                if not extracted or len(extracted) < 2:
                    continue

                t_rect = fitz.Rect(tab.bbox)
                table_rects.append(t_rect)

                headers = [str(c or "").strip() for c in extracted[0]]
                schema_key = table_schema_key(headers)
                canonical_rows: list[CanonicalRow] = []

                for r_idx, r_cells in enumerate(extracted[1:]):
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
