"""Derived native table boundaries; never change canonical evidence."""

from qnu.domains.knowledge.index.table_layout import layout

BASIS = "native_numbered_table_boundary/v1"
TYPED_BASIS = "native_typed_columns/v1"
MULTITIER_BASIS = "native_multitier_header/v1"


def typed_header(table: dict) -> bool:
    """Single native header proven by repeated column type contrast, not vocabulary.

    Cross-page joins still require the numbered boundary proof below. This rule
    only labels row zero of one complete, rectangular, unmerged source table.
    """
    rows, columns = table["rows"], table["column_count"]
    if (
        len(rows) < 3
        or columns < 2
        or any(
            len(row) != columns or any(c["row_span"] != 1 or c["col_span"] != 1 for c in row)
            for row in rows
        )
    ):
        return False
    if not all(
        c["text"].strip()
        and any(ch.isalpha() for ch in c["text"])
        and not any(ch.isdigit() for ch in c["text"])
        for c in rows[0]
    ):
        return False
    # At least one column has repeated numeric observations where row zero is a label.
    return any(
        all(
            any(ch.isdigit() for ch in row[col]["text"])
            and not any(ch.isalpha() for ch in row[col]["text"])
            for row in rows[1:]
        )
        for col in range(columns)
    )


def multitier_header(table: dict) -> list[int] | None:
    """Header tiers proven by a merged identity label above numeric columns.

    One complete native block whose top-left label spans several rows and the
    identity columns; every other header cell is a label or a merged numeric
    group (e.g. a year), and at least one data column is purely numeric.
    Geometry and type contrast only — no vocabulary, no cross-page join.
    """
    rows, columns = table["rows"], table["column_count"]
    if len(rows) < 4 or columns < 2 or not rows[0]:
        return None
    first = rows[0][0]
    height, identity_width = first.get("row_span"), first.get("col_span")
    if (
        type(height) is not int
        or type(identity_width) is not int
        or height < 2
        or identity_width < 1
        or identity_width >= columns
        or len(rows) - height < 2
    ):
        return None
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
    run = document["ocr_run_id"]
    for page in document["pages"]:
        blocks = page["blocks"]
        tables = [b for b in blocks if b.get("table")]
        for block in tables:
            table = block["table"]
            if (
                page.get("extraction_method") != "native"
                or block.get("requires_review")
                or not block.get("bbox")
                or table.get("status") != "parsed"
            ):
                previous, header, chain = None, None, []
                continue
            ref = run + ":" + block["evidence_id"]
            if not header_row(table) and typed_header(table):
                result[ref] = {
                    "basis": TYPED_BASIS,
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
