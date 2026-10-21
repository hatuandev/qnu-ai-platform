"""Source-visible text wins OCR proposals; decorative fills never invent visual facts."""

from __future__ import annotations

from app.modules.knowledge.parsers.pdf_evidence import intersection_fraction


def text_background(drawing: dict, layout: dict, drawings: list[dict]) -> bool:
    """Only a fill-only line-height rectangle behind independently captured glyphs."""
    box = drawing.get("rect")
    if not box or drawing.get("type") != "f" or not drawing.get("fill") or not drawing.get("items"):
        return False
    if any(item[0] != "re" for item in drawing["items"]):
        return False
    spans = [
        s
        for b in layout.get("blocks", [])
        for line in b.get("lines", [])
        for s in line.get("spans", [])
        if s.get("text", "").strip()
        and s.get("bbox")
        and intersection_fraction(s["bbox"], box) >= 0.8
    ]
    # A solitary bar with a value is still artwork. Code backgrounds repeat at
    # the same line width behind monospaced glyphs; keep all other fills.
    adjacent = any(
        other is not drawing
        and other.get("type") == "f"
        and other.get("fill") == drawing["fill"]
        and other.get("rect")
        and abs(other["rect"][0] - box[0]) < 0.15
        and abs(other["rect"][2] - box[2]) < 0.15
        and min(abs(other["rect"][1] - box[3]), abs(other["rect"][3] - box[1])) < 3
        for other in drawings
    )
    return (
        bool(spans)
        and adjacent
        and all(s.get("flags", 0) & 8 for s in spans)
        and box[3] - box[1] <= 2 * max(s.get("size", 0) for s in spans)
    )


def visible_items(native: list[dict], ocr: list[dict]) -> list[dict]:
    """Called only for verified visible native text. Preserve every competing raw result.

    Unmatched OCR is retained and blocking; OCR is still needed for image content.
    No OCR transcription is treated as a verified image interpretation.
    """
    result = list(native)
    for proposal in ocr:
        box = proposal.get("bbox")
        candidates = []
        if box:
            for item in native:
                other = item.get("bbox")
                if not other:
                    continue
                same_role = bool(item.get("table")) == bool(proposal.get("table")) and (
                    item["kind"] == "figure"
                ) == (proposal["kind"] in {"figure", "image", "chart"})
                if item["kind"] == "figure" and intersection_fraction(box, other) >= 0.9:
                    same_role = (
                        True  # OCR text inside an image remains an unverified image proposal.
                    )
                if (
                    same_role
                    and max(intersection_fraction(box, other), intersection_fraction(other, box))
                    >= 0.65
                ):
                    candidates.append(item)
        if candidates:
            for item in candidates:
                item.setdefault("alternatives", []).append(proposal)
                item["reconciliation"] = {
                    "status": "verified",
                    "basis": "visible_native_glyphs_and_region",
                }
        else:
            proposal["unmatched_ocr"] = True
            result.append(proposal)
    return result


def join_code_lines(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        prior = result[-1] if result else None
        if (
            prior
            and prior.get("monospaced")
            and item.get("monospaced")
            and 0 <= item["source_bbox"][1] - prior["source_bbox"][3] <= item["font_size"]
            and abs(item["source_bbox"][0] - prior["source_bbox"][0]) <= item["font_size"]
        ):
            prior["text"] += "\n" + item["text"]
            prior["raw"] = {
                "raw_blocks": [*prior["raw"].get("raw_blocks", [prior["raw"]]), item["raw"]],
                "lines": [*prior["raw"].get("lines", []), *item["raw"].get("lines", [])],
            }
            for key in ("bbox", "source_bbox"):
                a, b = prior[key], item[key]
                prior[key] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
        else:
            result.append(item)
    return result


def furniture_locators(pages: list[list[dict]]) -> set[str]:
    import re
    from collections import Counter

    def signature(item):
        return re.sub(r"\d+", "#", " ".join(item.get("text", "").split()))

    bands = [
        [
            i
            for i in page
            if i.get("text") and i.get("bbox") and (i["bbox"][3] > 94 or i["bbox"][1] < 4)
        ]
        for page in pages
    ]
    counts = Counter(key for page in bands for key in {signature(i) for i in page})
    return {
        i["locator"]
        for index, page in enumerate(bands, 1)
        for i in page
        if counts[signature(i)] >= 2
        and (not re.findall(r"\d+", i["text"]) or re.findall(r"\d+", i["text"]) == [str(index)])
    }


def footnote_marker(item: dict, page: dict) -> str | None:
    """A numbered note under a short separator, not merely small text near a table."""
    import re

    box = item.get("source_bbox")
    lines = [line.strip() for line in item.get("text", "").splitlines() if line.strip()]
    if (
        not box
        or len(lines) < 2
        or not re.fullmatch(r"\d{1,3}|[*†‡]+", lines[0])
        or box[1] < page["height"] * 0.8
    ):
        return None
    spans = [
        s
        for line in item.get("raw", {}).get("lines", [])
        for s in line.get("spans", [])
        if s.get("text", "").strip()
    ]
    first = spans[0].get("bbox") if spans else None
    if not first:
        return None
    for drawing in page.get("drawings", []):
        rule = drawing.get("rect")
        if (
            rule
            and rule[3] - rule[1] <= 2
            and page["width"] * 0.1 <= rule[2] - rule[0] <= page["width"] * 0.5
            and 0 <= first[1] - rule[3] <= 20
            and abs(first[0] - rule[0]) <= 4
        ):
            return lines[0]
    return None


def literal_table(table: dict) -> bool:
    """A complete tiled grid is evidence of literal preservation, never column meaning."""
    raw = table.get("raw_native") or {}
    if (
        not raw.get("visible_text_verified")
        or raw.get("geometry", {}).get("status") == "unresolved"
    ):
        return False
    grid = table["grid"]
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        return False
    box = raw["bbox"]
    cells = {tuple(c["bbox"]) for row in grid for c in row if c.get("bbox")}
    if any(c.get("unresolved") or not c.get("bbox") for row in grid for c in row):
        return False
    xs = sorted({c[i] for c in cells for i in (0, 2)})
    ys = sorted({c[i] for c in cells for i in (1, 3)})
    if len(xs) != len(grid[0]) + 1 or len(ys) != len(grid) + 1 or len(grid) * len(grid[0]) > 100000:
        return False
    x_index, y_index = {x: i for i, x in enumerate(xs)}, {y: i for i, y in enumerate(ys)}
    occupied = {}
    for a in cells:
        if any(a[i] < box[i] - 0.1 for i in (0, 1)) or any(a[i] > box[i] + 0.1 for i in (2, 3)):
            return False
        for r in range(y_index[a[1]], y_index[a[3]]):
            for c in range(x_index[a[0]], x_index[a[2]]):
                if (r, c) in occupied:
                    return False
                occupied[r, c] = a
    return (
        abs(xs[0] - box[0]) < 0.1
        and abs(xs[-1] - box[2]) < 0.1
        and abs(ys[0] - box[1]) < 0.1
        and abs(ys[-1] - box[3]) < 0.1
        and all(
            occupied.get((r, c)) == tuple(cell["bbox"])
            for r, row in enumerate(grid)
            for c, cell in enumerate(row)
        )
    )
