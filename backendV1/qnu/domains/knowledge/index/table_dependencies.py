"""Derived native table boundaries; never change canonical evidence."""

import re
import unicodedata

from qnu.domains.knowledge.index.table_layout import layout

BASIS = "native_numbered_table_boundary/v1"
TYPED_BASIS = "native_typed_columns/v1"
MULTITIER_BASIS = "native_multitier_header/v1"
ADMINISTRATIVE_BASIS = "native_administrative_header/v1"

_ADMIN_HEADER_KEYWORDS = (
    "tt",
    "stt",
    "số tt",
    "số thứ tự",
    "mã",
    "mã việc",
    "mã số",
    "mã ct",
    "mã ngành",
    "nội dung",
    "nhiệm vụ",
    "công việc",
    "hoạt động",
    "hạng mục",
    "tiêu chí",
    "chỉ tiêu",
    "chủ trì",
    "đơn vị chủ trì",
    "phối hợp",
    "đơn vị phối hợp",
    "thời gian",
    "thời hạn",
    "tiến độ",
    "sản phẩm",
    "kết quả",
    "đầu ra",
    "minh chứng",
    "ghi chú",
    "kinh phí",
    "nguồn kinh phí",
    "điều kiện",
    "nghiệm thu",
    "trách nhiệm",
)


def administrative_header(table: dict) -> bool:
    """Detect header row for administrative tables where OCR did not flag cells as headers.

    Matches column label keywords (TT/STT, Nội dung, Thời gian, Chủ trì, Phối hợp,
    Sản phẩm, Ghi chú, etc.) on Row 0. Requires at least 2 distinct administrative
    keywords and text-based cells, preserving headerless data tables as raw rows.
    """
    rows = table.get("rows", [])
    columns = table.get("column_count", 0)
    if len(rows) < 2 or columns < 2 or not rows[0]:
        return False
    if len(rows[0]) != columns:
        return False
    if any(c.get("row_span", 1) != 1 or c.get("col_span", 1) != 1 for c in rows[0]):
        return False

    cell_texts = [
        unicodedata.normalize("NFC", c.get("text", "").strip().lower())
        for c in rows[0]
    ]
    if not all(t and any(ch.isalpha() for ch in t) for t in cell_texts):
        return False
    if any(t.isdecimal() for t in cell_texts):
        return False

    matched_keywords = set()
    for text in cell_texts:
        for kw in _ADMIN_HEADER_KEYWORDS:
            if kw == text or re.search(r"\b" + re.escape(kw) + r"\b", text):
                matched_keywords.add(kw)
                break
    return len(matched_keywords) >= 2


def typed_header(table: dict) -> bool:
    """Single native header proven by repeated column type contrast, not vocabulary.

    Cross-page joins still require the numbered boundary proof below. This rule
    labels row zero of one complete rectangular table or a table whose body merges
    resolve cleanly via layout.
    """
    rows, columns = table.get("rows", []), table.get("column_count", 0)
    if len(rows) < 3 or columns < 2 or not rows[0]:
        return False
    if len(rows[0]) != columns or any(
        c.get("row_span", 1) != 1 or c.get("col_span", 1) != 1 for c in rows[0]
    ):
        return False
    if not all(
        c["text"].strip()
        and any(ch.isalpha() for ch in c["text"])
        and not any(ch.isdigit() for ch in c["text"])
        for c in rows[0]
    ):
        return False

    is_simple = not any(
        len(row) != columns or any(c.get("row_span", 1) != 1 or c.get("col_span", 1) != 1 for c in row)
        for row in rows[1:]
    )
    if is_simple:
        return any(
            all(
                any(ch.isdigit() for ch in row[col]["text"])
                and not any(ch.isalpha() for ch in row[col]["text"])
                for row in rows[1:]
            )
            for col in range(columns)
        )

    from qnu.domains.knowledge.index.table_layout import layout, table_structure

    structure = table if "row_indices" in table else table_structure(table)
    positions, errors = layout(structure)
    if errors:
        return False
    for col in range(columns):
        col_data = [p.cell for p in positions if p.row > 0 and p.column == col]
        if col_data and all(
            any(ch.isdigit() for ch in c["text"])
            and not any(ch.isalpha() for ch in c["text"])
            for c in col_data
            if c["text"].strip()
        ):
            return True
    return False


def _horizontal_metric_tier(rows: list[list[dict]], identity_width: int) -> bool:
    top, second = rows[:2]
    return (
        len(top) > 1
        and all(cell.get("header") and cell["row_span"] == 1 for cell in top)
        and all(cell["col_span"] >= 2 for cell in top[1:])
        and len(second) > identity_width
        and all(cell["row_span"] == cell["col_span"] == 1 for cell in second)
        and all(not cell["text"].strip() for cell in second[:identity_width])
        and all(any(ch.isalpha() for ch in cell["text"]) for cell in second[identity_width:])
    )


def multitier_header(table: dict) -> list[int] | None:
    """Prove header tiers from merged geometry and type contrast within one block.

    Accept a vertically merged identity label or a marked top row of horizontal
    groups over a separate metric row with an empty identity slot.
    """
    rows, columns = table["rows"], table["column_count"]
    if len(rows) < 4 or columns < 2 or not rows[0]:
        return None
    first = rows[0][0]
    height, identity_width = first.get("row_span"), first.get("col_span")
    if (
        type(height) is not int
        or type(identity_width) is not int
        or height < 1
        or identity_width < 1
        or identity_width >= columns
        or len(rows) - height < 2
    ):
        return None
    if height == 1:
        if not _horizontal_metric_tier(rows, identity_width):
            return None
        height = 2
    if not first["text"].strip() or not any(ch.isalpha() for ch in first["text"]):
        return None
    positions, errors = layout(
        {
            "rows": rows,
            "row_indices": list(range(len(rows))),
            "original_row_count": len(rows),
            "original_column_count": columns,
        }
    )
    if errors:
        return None
    for p in positions:
        if p.row >= height or p.column < identity_width:
            continue
        text = p.cell["text"]
        label = any(ch.isalpha() for ch in text)
        group = any(ch.isdigit() for ch in text) and p.cell["col_span"] > 1
        if not text.strip() or not (label or group):
            return None
    for col in range(identity_width, columns):
        data = [
            p
            for p in positions
            if p.row >= height and p.column <= col < p.column + p.cell["col_span"]
        ]
        if data and all(
            p.cell["col_span"] == 1
            and p.cell["row_span"] == 1
            and any(ch.isdigit() for ch in p.cell["text"])
            and not any(ch.isalpha() for ch in p.cell["text"])
            for p in data
        ):
            return list(range(height))
    return None


def sequence(table: dict) -> list[int] | None:
    values = []
    for i, row in enumerate(table["rows"]):
        if any(c["row_span"] != 1 or c["col_span"] != 1 for c in row):
            return None
        if len(row) != table["column_count"]:
            return None
        text = row[0]["text"].strip()
        if not text and i == 0:
            continue  # A possible carried row, never a standalone identity proof.
        if not text.isascii() or not text.isdecimal():
            return None
        values.append(int(text))
    if len(values) < 2 or values != list(range(values[0], values[0] + len(values))):
        return None
    return values


def header_row(table: dict) -> bool:
    rows = table["rows"]
    return (
        len(rows) >= 3
        and len(rows[0]) == table["column_count"]
        and all(c["row_span"] == c["col_span"] == 1 for c in rows[0])
        and all(c["text"].strip() and not any(ch.isdigit() for ch in c["text"]) for c in rows[0])
        and sequence({**table, "rows": rows[1:]}) is not None
    )


def adjoining(left: dict, right: dict) -> bool:
    a, b = left["block"]["bbox"], right["block"]["bbox"]
    return (
        right["page"] == left["page"] + 1
        and a.get("units") == b.get("units") == "normalized_0_1"
        # Bottom margins vary even between pages of the same numbered table.
        # The page edge is only a gate alongside geometry and consecutive IDs.
        and a["y1"] >= 0.88
        and b["y0"] <= 0.12
        and abs(a["x0"] - b["x0"]) <= 0.005
        and abs(a["x1"] - b["x1"]) <= 0.005
        and left["last_on_page"]
        and right["first_on_page"]
        and left["block"]["table"]["column_count"] == right["block"]["table"]["column_count"]
        and right["numbers"][0] == left["numbers"][-1] + 1
    )


def dependencies(document: dict) -> dict[str, dict]:
    result, previous, header, chain = {}, None, None, []
    run = document.get("ocr_run_id") or document.get("identity", {}).get("run_id") or ""
    for page in document["pages"]:
        blocks = page["blocks"]
        tables = [b for b in blocks if b.get("table")]
        for block in tables:
            table = block["table"]
            page_method = page.get("extraction_method")
            native_page = page_method == "native"
            native_block = native_page or (
                page_method == "hybrid" and block.get("origin") == "native"
            )
            if (
                not native_block
                or block.get("requires_review")
                or table.get("status") != "parsed"
            ):
                previous, header, chain = None, None, []
                continue
            ref = run + ":" + block["evidence_id"]
            if (
                block.get("bbox")
                and not header_row(table)
                and (typed_header(table) or administrative_header(table))
            ):
                result[ref] = {
                    "basis": TYPED_BASIS if typed_header(table) else ADMINISTRATIVE_BASIS,
                    "header": ref,
                    "chain": [ref],
                    "previous": None,
                }
                previous, header, chain = None, None, []
                continue
            tiers = multitier_header(table)
            if tiers is not None:
                result[ref] = {
                    "basis": MULTITIER_BASIS,
                    "header": ref,
                    "chain": [ref],
                    "previous": None,
                    "header_rows": tiers,
                }
                previous, header, chain = None, None, []
                continue
            if not native_page or not block.get("bbox"):
                # Same-block merged tiers use logical cell coordinates. Page
                # continuations below still need a native page and placement.
                previous, header, chain = None, None, []
                continue
            start = 1 if header_row(table) else 0
            numbers = sequence({**table, "rows": table["rows"][start:]})
            if numbers is None:
                previous, header, chain = None, None, []
                continue
            current = {
                "block": block,
                "page": page["page_number"],
                "numbers": numbers,
                "first_on_page": block == blocks[0],
                "last_on_page": block == blocks[-1],
            }
            if start:
                header, chain = ref, [ref]
            elif previous and header and adjoining(previous, current):
                chain = [*chain, ref]
            else:
                header, chain = None, []
            if header:
                first = table["rows"][0]
                identity_width = 1 if len(first) == 2 else 2
                carried = (
                    start == 0
                    and not any(c["text"].strip() for c in first[:identity_width])
                    and any(c["text"].strip() for c in first[identity_width:])
                )
                result[ref] = {
                    "basis": BASIS,
                    "header": header,
                    "chain": chain,
                    "previous": chain[-2] if carried and len(chain) > 1 else None,
                }
            previous = current
    return result
