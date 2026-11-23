"""Direct Excel (.xlsx) extraction into canonical evidence format."""

from __future__ import annotations

import asyncio
import io
import re
import zipfile
from importlib.metadata import version

import openpyxl

from qnu.domains.ocr.artifacts.render import PageImage, RenderedDocument
from qnu.domains.ocr.layout import MAX_TABLE_COLUMNS, MAX_TABLE_ROWS, Block, Cell, PageLayout, Table
from qnu.domains.ocr.native import NativePage, NativePlan
from qnu.platform.errors import AppException

MAX_XLSX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_XLSX_ZIP_ENTRIES = 10_000
_FORMULA_TOTAL_RE = re.compile(r"^\s*=(?:SUM|TOTAL|SUBTOTAL)\b", re.IGNORECASE)


def _cell_str(val: object) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val).strip()


def _is_summary_or_formula_row(row_values: list[str]) -> bool:
    non_empty = [v for v in row_values if v]
    if not non_empty:
        return False
    # If any cell starts with =SUM or similar formula
    if any(_FORMULA_TOTAL_RE.search(v) for v in non_empty):
        return True
    # Only drop a standalone label-only summary line (1 cell); preserve 2-column metric rows
    # such as ("Tổng số tín chỉ", "120").
    first = non_empty[0].lower()
    return len(non_empty) == 1 and any(k in first for k in ("tổng cộng", "tổng số", "=sum"))


def _build_markdown_table(rows: list[list[Cell]], col_count: int) -> str:
    lines = []
    if not rows:
        return ""
    header_idx = 0
    for idx, r in enumerate(rows):
        if any(c.header for c in r):
            header_idx = idx
            break

    header_cells = [c.text.replace("\n", " ").strip() for c in rows[header_idx]]
    # Pad to col_count if needed
    while len(header_cells) < col_count:
        header_cells.append("")
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("| " + " | ".join(["---"] * col_count) + " |")

    for idx, r in enumerate(rows):
        if idx == header_idx:
            continue
        row_cells = [c.text.replace("\n", " ").strip() for c in r]
        while len(row_cells) < col_count:
            row_cells.append("")
        lines.append("| " + " | ".join(row_cells) + " |")
    return "\n".join(lines)


def extract_xlsx(payload: bytes, max_rows: int | None = None) -> tuple[RenderedDocument, NativePlan]:
    """Parse an .xlsx payload directly using openpyxl, preserving sheets, headers, and cells."""
    if not payload:
        raise AppException("Tệp Excel rỗng.", code="xlsx_empty", status_code=422)

    if max_rows is None:
        try:
            from qnu.platform.config import get_settings

            effective_max_rows = get_settings().XLSX_MAX_ROWS
        except Exception:
            effective_max_rows = 500
    else:
        effective_max_rows = max_rows

    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_XLSX_ZIP_ENTRIES or sum(i.file_size for i in infos) > MAX_XLSX_EXPANDED_BYTES:
                raise AppException(
                    "Tệp Excel vượt giới hạn dung lượng giải nén cho phép.",
                    code="xlsx_expanded_limit_exceeded",
                    status_code=422,
                )
    except AppException:
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        raise AppException(
            f"Không thể đọc tệp Excel: {exc}",
            code="xlsx_read_failed",
            status_code=422,
        ) from exc

    try:
        wb = openpyxl.load_workbook(io.BytesIO(payload), data_only=True)
    except Exception as exc:
        raise AppException(
            f"Không thể đọc tệp Excel: {exc}",
            code="xlsx_read_failed",
            status_code=422,
        ) from exc

    pages: list[NativePage] = []
    rendered_pages: list[PageImage] = []
    page_number = 0

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]

        # Gather merged cell ranges
        merged_slots: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        # (row, col) -> (start_row, start_col, row_span, col_span)
        for rng in ws.merged_cells.ranges:
            min_r, min_c, max_r, max_c = rng.min_row, rng.min_col, rng.max_row, rng.max_col
            r_span = max_r - min_r + 1
            c_span = max_c - min_c + 1
            for r in range(min_r, max_r + 1):
                for c in range(min_c, max_c + 1):
                    merged_slots[(r, c)] = (min_r, min_c, r_span, c_span)

        # Read all raw rows to find bounding box of content
        raw_rows: list[list[tuple[int, int, object]]] = []
        for r_idx, row in enumerate(ws.iter_rows(values_only=False), start=1):
            cell_items = []
            for c_idx, cell in enumerate(row, start=1):
                cell_items.append((r_idx, c_idx, cell.value))
            raw_rows.append(cell_items)

        # Determine non-empty row bounds
        valid_rows = []
        for row in raw_rows:
            has_val = any(_cell_str(val) for _, _, val in row)
            if has_val:
                valid_rows.append(row)

        if not valid_rows:
            # Empty sheet, skip
            continue

        # Find min and max columns that have content
        min_c = min(
            (c_idx for row in valid_rows for _, c_idx, val in row if _cell_str(val)),
            default=1,
        )
        max_c = max(
            (c_idx for row in valid_rows for _, c_idx, val in row if _cell_str(val)),
            default=1,
        )
        col_count = max_c - min_c + 1

        if col_count > MAX_TABLE_COLUMNS:
            col_count = MAX_TABLE_COLUMNS
            max_c = min_c + MAX_TABLE_COLUMNS - 1

        blocks: list[Block] = []
        warnings: list[str] = []
        order = 1

        # Check for sheet-level Title in the first non-empty row
        first_row = valid_rows[0]
        first_row_non_empty = [
            (c_idx, _cell_str(val))
            for _, c_idx, val in first_row
            if min_c <= c_idx <= max_c and _cell_str(val)
        ]

        data_start_row_idx = 0
        if len(first_row_non_empty) == 1 and len(valid_rows) > 1:
            # First row is likely a standalone title banner (e.g. "DANH MỤC PHÒNG ĐỌC MỞ...")
            title_text = first_row_non_empty[0][1]
            blocks.append(
                Block(
                    order=order,
                    label="Title",
                    kind="title",
                    text=f"# {title_text}",
                    bbox=None,
                    requires_review=False,
                    origin="native",
                    source_locator={"format": "xlsx", "sheet": sheet_name, "row": first_row[0][0]},
                )
            )
            order += 1
            data_start_row_idx = 1

        # Process the tabular rows
        table_rows: list[list[Cell]] = []
        candidate_rows = valid_rows[data_start_row_idx:]

        # Filter out formula summary rows
        non_summary_rows = [
            r_row
            for r_row in candidate_rows
            if not _is_summary_or_formula_row(
                [_cell_str(val) for _, c_idx, val in r_row if min_c <= c_idx <= max_c]
            )
        ]

        if not non_summary_rows:
            continue

        # Data rows (excluding the header row)
        data_rows = non_summary_rows[1:]

        if len(data_rows) > effective_max_rows:
            raise AppException(
                f"Bảng tính '{sheet_name}' chứa {len(data_rows)} dòng dữ liệu, vượt quá giới hạn tối đa cho phép "
                f"({effective_max_rows} dòng). Vui lòng tách nhỏ tệp Excel hoặc cấu hình tăng biến XLSX_MAX_ROWS.",
                code="xlsx_row_limit_exceeded",
                status_code=422,
            )

        # Keep columns that have non-empty content in at least one data row,
        # plus any merged partner columns, to prevent bloat from empty template columns.
        if data_rows:
            active_col_set = {
                c_idx
                for c_idx in range(min_c, max_c + 1)
                if any(_cell_str(next((x[2] for x in r if x[1] == c_idx), None)) for r in data_rows)
            }
            for rng in ws.merged_cells.ranges:
                for c in range(rng.min_col, rng.max_col + 1):
                    if c in active_col_set:
                        active_col_set.update(range(rng.min_col, rng.max_col + 1))
                        break
            active_cols = sorted(active_col_set) if active_col_set else list(range(min_c, max_c + 1))
        else:
            active_cols = list(range(min_c, max_c + 1))

        if len(active_cols) > MAX_TABLE_COLUMNS:
            active_cols = active_cols[:MAX_TABLE_COLUMNS]

        col_count = len(active_cols)
        header_determined = False
        kept_row_nums = [r[0][0] for r in non_summary_rows]
        kept_row_set = set(kept_row_nums)

        for r_row in non_summary_rows:
            is_header = not header_determined
            header_determined = True

            curr_row_cells: list[Cell] = []
            col_pos = 0
            while col_pos < len(active_cols):
                c_idx = active_cols[col_pos]
                cell_tuple = next((x for x in r_row if x[1] == c_idx), None)
                val = cell_tuple[2] if cell_tuple else None
                text = _cell_str(val)

                r_span = 1
                c_span = 1
                r_num = r_row[0][0]
                if (r_num, c_idx) in merged_slots:
                    start_r, start_c, span_r, span_c = merged_slots[(r_num, c_idx)]
                    effective_start_r = (
                        start_r
                        if start_r in kept_row_set
                        else next(
                            (rn for rn in kept_row_nums if start_r <= rn < start_r + span_r),
                            r_num,
                        )
                    )
                    if (r_num, c_idx) == (effective_start_r, start_c):
                        # Top-left of surviving merged range
                        active_span_c = sum(1 for ac in active_cols[col_pos:] if ac < start_c + span_c)
                        c_span = max(1, active_span_c)
                        active_span_r = sum(
                            1 for rn in kept_row_nums if effective_start_r <= rn < start_r + span_r
                        )
                        r_span = max(1, active_span_r)
                        curr_row_cells.append(
                            Cell(text=text, row_span=r_span, col_span=c_span, header=is_header)
                        )
                        col_pos += c_span
                        continue
                    else:
                        col_pos += 1
                        continue

                curr_row_cells.append(
                    Cell(text=text, row_span=r_span, col_span=c_span, header=is_header)
                )
                col_pos += 1

            if curr_row_cells:
                table_rows.append(curr_row_cells)

        if table_rows:
            # Enforce layout limits without silent truncation
            if len(table_rows) > MAX_TABLE_ROWS:
                raise AppException(
                    f"Bảng tính '{sheet_name}' chứa {len(table_rows)} hàng, vượt quá giới hạn cấu trúc bảng hệ thống ({MAX_TABLE_ROWS} hàng). "
                    f"Vui lòng tách nhỏ trang tính.",
                    code="xlsx_table_exceeds_layout_limit",
                    status_code=422,
                )

            table_obj = Table(
                status="parsed",
                rows=tuple(tuple(r) for r in table_rows),
                column_count=col_count,
                source_mapping={
                    "format": "xlsx",
                    "sheet": sheet_name,
                    "title": f"Sheet: {sheet_name}",
                    "rows": len(table_rows),
                },
            )
            md_table = _build_markdown_table(table_rows, col_count)
            table_intro = f"### Bảng dữ liệu: {sheet_name}\n\n{md_table}"
            blocks.append(
                Block(
                    order=order,
                    label="Table",
                    kind="table",
                    text=table_intro,
                    bbox=None,
                    requires_review=False,
                    table=table_obj,
                    origin="native",
                    source_locator={"format": "xlsx", "sheet": sheet_name},
                )
            )
            order += 1

        if not blocks:
            continue

        page_number += 1
        page_layout = PageLayout(blocks=tuple(blocks), warnings=tuple(warnings))
        pages.append(
            NativePage(
                page_number=page_number,
                layout=page_layout,
                images=(),
                needs_ocr=False,
                native_text=True,
            )
        )
        rendered_pages.append(
            PageImage(page_number, None, None, None, None, False, None)
        )

    if not pages:
        raise AppException(
            "Tệp Excel không chứa dữ liệu hợp lệ để xử lý.",
            code="xlsx_empty_content",
            status_code=422,
        )

    rendered = RenderedDocument(
        extension=".xlsx",
        renderer={
            "name": "openpyxl",
            "version": version("openpyxl"),
            "pagination": "sheets",
        },
        pages=tuple(rendered_pages),
    )
    return rendered, NativePlan(tuple(pages), "source_revision")


async def extract_xlsx_async(
    payload: bytes, max_rows: int | None = None
) -> tuple[RenderedDocument, NativePlan]:
    return await asyncio.to_thread(extract_xlsx, payload, max_rows)
