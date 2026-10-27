"""PDF native/OCR evidence → QNU model, independent of the serving Markdown projection."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from itertools import pairwise
from typing import Any

from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuQualityFlag,
    QnuSourceInfo,
    QnuSourceLocation,
    QnuStructuredDocument,
)
from app.modules.knowledge.parsers.pdf_continuations import (
    aligned_columns,
    inherit_headers,
    retain_native_projections,
)
from app.modules.knowledge.parsers.pdf_evidence import intersection_fraction, reading_order
from app.modules.knowledge.parsers.pdf_headings import heading_decisions
from app.modules.knowledge.parsers.pdf_reconciliation import (
    footnote_marker,
    furniture_locators,
    join_code_lines,
    text_background,
    visible_items,
)
from app.modules.knowledge.parsers.pdf_tables import (
    native_table,
    ocr_table,
    table_blocks,
)

PDF_STRUCTURE_VERSION = "pdf-evidence-structure/v6"
# Anything no thicker than this carries a rule, not readable content, whatever painted it.
_HAIRLINE_POINT = 2.0


def _compact(text: str) -> str:
    return " ".join(text.split()).casefold()


def _percent(box: list[float], width: float, height: float) -> list[float]:
    return [box[0] / width * 100, box[1] / height * 100, box[2] / width * 100, box[3] / height * 100]


def _valid_box(box: Any) -> bool:
    return (isinstance(box, (list, tuple)) and len(box) == 4
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in box)
            and box[2] > box[0] and box[3] > box[1])


def _is_grid_furniture(drawing: dict[str, Any], page_width: float, page_height: float) -> bool:
    """Ruling strokes and sub-point junction dots carry no letters; a readable image region does."""
    box = drawing["rect"]
    short, long_side = min(box[2] - box[0], box[3] - box[1]), max(box[2] - box[0], box[3] - box[1])
    stroke = drawing.get("width")
    # A filled rectangle has no stroke width, so its own short side is the thickness.
    limit = max(2.0 * stroke, _HAIRLINE_POINT) if isinstance(stroke, (int, float)) and stroke > 0 else _HAIRLINE_POINT
    dot = long_side <= max(limit, 0.002 * min(page_width, page_height))
    ruling = short <= limit and long_side >= 10 * max(short, 0.1) and long_side <= 2 * max(page_width, page_height)
    return dot or ruling


def _count_rulings(pages: list[dict[str, Any]]) -> int:
    """Meta count of ruling strokes; the raw evidence JSON still keeps every drawing."""
    return sum(1 for page in pages for drawing in (page["native"].get("drawings") or [])
               if _valid_box(drawing.get("rect")) and "rect" in drawing
               and _is_grid_furniture(drawing, page["native"]["width"], page["native"]["height"]))


def _native_spans(page: dict[str, Any]) -> list[tuple[str, list[float]]]:
    """Blocks of the digital text layer as (compacted text, percent box); used to cross-check OCR structure."""
    width, height = page["width"], page["height"]
    spans = []
    for block in page.get("layout", {}).get("blocks", []):
        text = "\n".join("".join(span.get("text", "") for span in line.get("spans", [])) for line in block.get("lines", []))
        if text.strip() and _valid_box(block.get("bbox")):
            spans.append((_compact(text), _percent(list(block["bbox"]), width, height)))
    return spans


def _native_items(page: dict[str, Any]) -> list[dict[str, Any]]:
    width, height = page["width"], page["height"]
    items = []
    tables = page.get("tables") or []
    for index, raw in enumerate(tables):
        items.append({"kind": "table", "table": native_table(raw), "bbox": _percent(raw["bbox"], width, height),
                      "source_bbox": raw["bbox"], "space": page["bbox_space"], "engine": "native",
                      "locator": f"pdf:page:{page['page']}/native/table/{index}", "raw": raw})
    for index, block in enumerate(page.get("layout", {}).get("blocks", [])):
        lines = ["".join(span.get("text", "") for span in line.get("spans", [])) for line in block.get("lines", [])]
        text = "\n".join(lines)
        if not text.strip():
            continue
        box = list(block["bbox"])
        # Suppress only a spatially contained, identical table projection. Raw layout stays intact.
        if any(intersection_fraction(box, table["bbox"]) >= 0.9 and _compact(text).replace(" ", "") in
               _compact(" ".join(str(cell or "") for row in (table.get("glyph_matrix") or table["matrix"]) for cell in row)).replace(" ", "")
               for table in tables):
            continue
        spans = [span for line in block.get("lines", []) for span in line.get("spans", [])]
        items.append({"kind": "text", "text": text, "bbox": _percent(box, width, height),
                      "source_bbox": box, "space": page["bbox_space"], "engine": "native", "raw": block,
                      "font_size": max((span.get("size", 0) for span in spans), default=0),
                      "monospaced": bool(spans) and all(span.get("flags", 0) & 8 for span in spans if span.get("text", "").strip()),
                      "locator": f"pdf:page:{page['page']}/native/block/{index}"})
    for index, image in enumerate(page.get("images", [])):
        items.append({"kind": "figure", "text": "", "bbox": _percent(image["bbox"], width, height),
                      "source_bbox": image["bbox"], "space": page["bbox_space"], "engine": "native", "raw": image,
                      "locator": f"pdf:page:{page['page']}/native/image/{index}",
                      "resource": {"sha256": image["sha256"]} if image.get("sha256") else None})
    for index, drawing in enumerate(page.get("drawings", [])):
        box = drawing.get("rect")
        if not _valid_box(box) or _is_grid_furniture(drawing, width, height) or _is_table_border(drawing, tables) or (
                page.get("visible_text_verified") and text_background(drawing, page.get("layout", {}), page.get("drawings", []))) or any(
                intersection_fraction(box, t["bbox"]) >= 0.9 for t in tables):
            continue
        items.append({"kind": "figure", "text": "", "bbox": _percent(box, width, height),
                      "source_bbox": box, "space": page["bbox_space"], "engine": "native", "raw": drawing,
                      "locator": f"pdf:page:{page['page']}/native/drawing/{index}"})
    return join_code_lines(items)


def _is_table_border(drawing: dict[str, Any], tables: list[dict[str, Any]]) -> bool:
    """Short filled border fragments are furniture when aligned to a detected table edge."""
    box = drawing["rect"]
    if drawing.get("type") != "f" or not drawing.get("items") or any(i[0] != "re" for i in drawing["items"]):
        return False
    width, height = box[2] - box[0], box[3] - box[1]
    if min(width, height) > _HAIRLINE_POINT:
        return False
    for table in tables:
        left, top, right, bottom = table["bbox"]
        if not (left - 2 <= box[0] <= box[2] <= right + 2 and top - 2 <= box[1] <= box[3] <= bottom + 2):
            continue
        if width <= height and min(abs((box[0] + box[2]) / 2 - x) for x in (left, right)) <= 2:
            return True
        if height <= width and min(abs((box[1] + box[3]) / 2 - y) for y in (top, bottom)) <= 2:
            return True
    return False


def _ocr_items(page: dict[str, Any]) -> list[dict[str, Any]]:
    raw = page.get("ocr_raw_page") or {}
    pruned = raw.get("prunedResult") or raw.get("layout_pruned") or {}
    blocks = pruned.get("parsing_res_list") or raw.get("blocks") or []
    dimensions = page.get("ocr_dimensions") or {}
    width, height = pruned.get("width") or dimensions.get("width"), pruned.get("height") or dimensions.get("height")
    items = []
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        text = block.get("block_content", block.get("text", ""))
        if not isinstance(text, str):
            continue
        label = block.get("block_label", block.get("type", "text"))
        coordinates = block.get("coordinates") or {}
        box = block.get("block_bbox")
        if _valid_box(box) and isinstance(width, (int, float)) and isinstance(height, (int, float)) and width > 0 and height > 0:
            box = _percent(box, width, height)
        elif coordinates.get("is_valid") and all(k in coordinates for k in ("left", "top", "width", "height")):
            box = [coordinates["left"], coordinates["top"], coordinates["left"] + coordinates["width"],
                   coordinates["top"] + coordinates["height"]]
        else:
            box = None
        if not _valid_box(box):
            box = None
        table = ocr_table(text) if label == "table" else None
        items.append({"kind": "table" if table else label, "table": table, "text": text, "bbox": box,
                      "source_bbox": box, "space": "normalized_percent" if box else None,
                      "engine": page["engine_used"], "raw": block, "order": block.get("block_order", block.get("order")),
                      "locator": f"pdf:page:{page['page']}/ocr/block/{index}"})
    if not items and page.get("ocr_text", "").strip():
        items.append({"kind": "text", "text": page["ocr_text"], "bbox": None, "source_bbox": None,
                      "space": None, "engine": page["engine_used"], "raw": raw, "unstructured": True,
                      "locator": f"pdf:page:{page['page']}/ocr/page"})
    return items


def _item_text(item: dict[str, Any]) -> str:
    if item.get("table"):
        return " ".join(cell["raw"] for row in item["table"]["grid"] for cell in row)
    return item.get("text", "")


def _overlap_ratio(a: list[float], b: list[float]) -> float:
    """Symmetric intersection over union; containment alone cannot compare boxes of very different size."""
    inter = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _completeness(item: dict[str, Any]) -> float:
    """Rank two reconstructions of one region by evidence carried, never by source order or engine."""
    grid = item["table"]["grid"]
    cells = [cell for row in grid for cell in row]
    if not cells:
        return 0.0
    filled = sum(1 for cell in cells if cell["raw"].strip()) / len(cells)
    geometry = sum(1 for cell in cells if not cell.get("unresolved")) / len(cells)
    return (filled + geometry) / 2


def _select_items(native: list[dict[str, Any]], ocr: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not ocr:
        return native
    chosen = list(ocr)
    for item in native:
        if item.get("table") and item.get("bbox"):
            rivals = [(index, other) for index, other in enumerate(chosen)
                      if other.get("table") and other.get("bbox") and _overlap_ratio(item["bbox"], other["bbox"]) >= 0.3]
            if rivals:
                index, rival = max(rivals, key=lambda pair: _overlap_ratio(item["bbox"], pair[1]["bbox"]))
                if _completeness(item) > _completeness(rival):
                    item.setdefault("alternatives", []).append(rival)
                    chosen[index] = item
                else:
                    rival.setdefault("alternatives", []).append(item)
                continue
        matches = [other for other in ocr if item.get("bbox") and other.get("bbox") and
                   intersection_fraction(item["bbox"], other["bbox"]) >= 0.8]
        if matches:
            primary = max(matches, key=lambda other: intersection_fraction(item["bbox"], other["bbox"]))
            if _compact(_item_text(item)) != _compact(_item_text(primary)) and item["kind"] != "figure":
                primary.setdefault("alternatives", []).append(item)
            continue
        # Without geometry, a complete OCR page cannot establish which native span duplicates it.
        if any(other.get("unstructured") for other in ocr):
            ocr[0].setdefault("alternatives", []).append(item)
        else:
            chosen.append(item)
    return chosen


def _location(item: dict[str, Any], page: dict[str, Any]) -> QnuSourceLocation:
    return QnuSourceLocation(page=page["page"], page_label=page.get("page_label"), locator=item["locator"],
                             bbox=item.get("source_bbox"), bbox_space=item.get("space"))


def _flags(item: dict[str, Any]) -> list[QnuQualityFlag]:
    flags = []
    if item.get("bbox") is None:
        flags.append(QnuQualityFlag(code="source_geometry_unavailable", detail="Có trang và locator, chưa có tọa độ vùng đáng tin cậy."))
    if item.get("unmatched_ocr") or item.get("alternatives") and item.get("reconciliation", {}).get("status") != "verified":
        flags.append(QnuQualityFlag(code="native_ocr_conflict", detail="Hai bản trích xuất không khớp; giữ đối chiếu trong JSON."))
    if item.get("unstructured"):
        flags.append(QnuQualityFlag(code="ocr_structure_unavailable", detail="OCR chỉ có văn bản trang; chưa xác minh cấu trúc."))
    if item.get("kind") == "table" and not item.get("table"):
        flags.append(QnuQualityFlag(code="table_structure_unresolved", detail="Giữ nguyên nội dung bảng OCR để đối soát."))
    return flags


def _propose_header(item: dict[str, Any], spans: list[tuple[str, list[float]]]) -> None:
    """Propose headers for an OCR table when corroborated by the digital text layer, for reviewer inspection."""
    table, box = item.get("table"), item.get("bbox")
    if not table or not box or table["header_depth"] or table.get("external_headers") or not table.get("raw_html"):
        return
    if len(table["grid"]) < 2:
        return
    labels = [cell["raw"] for cell in table["grid"][0] if cell["raw"].strip()]
    if len(labels) < 2:
        return
    band = [box[0], box[1], box[2], box[1] + (box[3] - box[1]) * 0.2]
    in_band = [text for text, span in spans if intersection_fraction(span, band) >= 0.5]
    if len([label for label in labels if any(_compact(label) in text for text in in_band)]) != len(labels):
        return
    # Text agreement corroborates the OCR transcription: retain proposal for reviewer inspection.
    # But text agreement alone is NOT proof of semantic header role; do not consume an unverified row.
    table["header_proposal"] = {"basis": "native_text_layer_corroboration", "labels": labels}


_SYMBOL_LEGEND = re.compile(r"[\"“”»']\s*(?P<symbol>[^\s\"“”»']{1,3})\s*[\"“”»']\s*[:–—-]\s*(?P<definition>\S.{7,})")


def _collect_page_legends(items: list[dict[str, Any]], page: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect candidate symbol definitions for a page with locator and bounding box."""
    page_no = page["native"].get("page") or page.get("page", 1)
    legends: list[dict[str, Any]] = []

    # 1. Collect from selected items
    for item in items:
        if item.get("table"):
            continue
        text = item.get("text", "")
        box = item.get("bbox")
        locator = item.get("locator")
        for line in text.splitlines():
            match = _SYMBOL_LEGEND.search(line)
            if not match:
                continue
            symbol = match["symbol"]
            if any(character.isalnum() for character in symbol):
                continue
            meaning = unicodedata.normalize("NFC", match["definition"].strip().lower())
            legends.append({
                "symbol": symbol, "page": page_no, "line": line.strip(),
                "meaning": meaning, "bbox": box, "locator": locator,
            })

    # 2. Also collect from native layout blocks if not already captured
    native_blocks = page.get("native", {}).get("layout", {}).get("blocks", [])
    native_w = page.get("native", {}).get("width") or page.get("native", {}).get("layout", {}).get("width") or 100.0
    native_h = page.get("native", {}).get("height") or page.get("native", {}).get("layout", {}).get("height") or 100.0
    for idx, block in enumerate(native_blocks):
        lines = ["".join(span.get("text", "") for span in line.get("spans", [])) for line in block.get("lines", [])]
        text = "\n".join(lines)
        box = block.get("bbox")
        norm_box = _percent(box, native_w, native_h) if _valid_box(box) and native_w > 0 and native_h > 0 else box
        for line in text.splitlines():
            match = _SYMBOL_LEGEND.search(line)
            if not match:
                continue
            symbol = match["symbol"]
            if any(character.isalnum() for character in symbol):
                continue
            meaning = unicodedata.normalize("NFC", match["definition"].strip().lower())
            locator = f"pdf:page:{page_no}/native/block/{idx}"
            if not any(l["line"] == line.strip() and l["page"] == page_no
                       and l["locator"] == locator for l in legends):
                legends.append({
                    "symbol": symbol, "page": page_no, "line": line.strip(),
                    "meaning": meaning, "bbox": norm_box,
                    "locator": locator,
                })

    return legends


def _is_table_geometrically_applicable(
    t: dict[str, Any],
    cand: dict[str, Any],
    page_tables: list[dict[str, Any]],
) -> bool:
    t_box = t.get("bbox")
    c_box = cand.get("bbox")
    if not t_box or len(t_box) < 4 or not c_box or len(c_box) < 4:
        return False
    t_x0, _t_y0, t_x1, t_y1 = t_box
    c_x0, c_y0, c_x1, _c_y1 = c_box

    # 1. Legend must be situated immediately below the table
    # Vertical gap: legend top is at or below table bottom (allowing minor 2% rounding / subpixel overlap, up to 25% of page)
    if not (t_y1 - 2.0 <= c_y0 <= t_y1 + 25.0):
        return False

    # 2. Horizontal overlap
    h_overlap = min(t_x1, c_x1) - max(t_x0, c_x0)
    if h_overlap <= 0:
        return False

    # 3. No intervening table between table t and candidate legend
    for other in page_tables:
        if other is t:
            continue
        o_box = other.get("bbox")
        if not o_box or len(o_box) < 4:
            continue
        corridor_left, corridor_right = max(t_x0, c_x0), min(t_x1, c_x1)
        if (t_y1 - 2.0 <= o_box[1] < c_y0
                and min(o_box[2], corridor_right) > max(o_box[0], corridor_left)):
            return False

    return True


def _find_table_legends(
    table_item: dict[str, Any],
    page_tables: list[dict[str, Any]],
    page_legends: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Resolve symbol legends specifically to a table based on proven unique spatial adjacency."""
    table_box = table_item.get("bbox")
    if not table_box or len(table_box) < 4:
        return {}

    candidate_matches: dict[str, list[dict[str, Any]]] = {}

    for cand in page_legends:
        c_box = cand.get("bbox")
        if not c_box or len(c_box) < 4:
            continue

        if not _is_table_geometrically_applicable(table_item, cand, page_tables):
            continue

        # Find all geometrically applicable tables for this candidate
        applicable_tables = [
            t for t in page_tables
            if _is_table_geometrically_applicable(t, cand, page_tables)
        ]

        if not applicable_tables:
            continue

        # Compute vertical distance from each applicable table bottom to candidate top
        distances = [
            abs(cand["bbox"][1] - t["bbox"][3])
            for t in applicable_tables
        ]
        min_dist = min(distances)

        # Tables achieving the minimum distance within 0.5 tolerance
        closest = [
            t for t, d in zip(applicable_tables, distances, strict=False)
            if abs(d - min_dist) < 0.5
        ]

        # Require a unique winning association among geometrically applicable tables; ties must abstain.
        if len(closest) == 1 and closest[0] is table_item:
            candidate_matches.setdefault(cand["symbol"], []).append(cand)

    applicable: dict[str, dict[str, Any]] = {}
    for sym, matches in candidate_matches.items():
        distinct_meanings = {m["meaning"] for m in matches}
        if len(distinct_meanings) == 1:
            applicable[sym] = matches[0]

    return applicable


def _link_symbol_legends(blocks: list[QnuBlock]) -> None:
    """Point every legend-defined cell at the canonical block that carries the defining sentence."""
    for block in blocks:
        defs = block.attributes.get("symbol_definitions") or {}
        to_remove = []
        for field_id, entry in list(defs.items()):
            matches = [other for other in blocks if other.id != block.id and other.type in {"text", "note", "list"}
                       and any(loc.page == entry["page"]
                               and (not entry.get("locator") or loc.locator == entry["locator"])
                               for loc in other.source_locations)
                       and _compact(entry["line"]) in _compact(other.body)]
            legend = matches[0] if len(matches) == 1 else None
            if legend is None:
                to_remove.append(field_id)
                block.attributes.setdefault("symbol_definition_candidates", {})[field_id] = entry
                if "fields" in block.attributes and field_id in block.attributes["fields"]:
                    block.attributes["fields"][field_id]["state"] = "ambiguous"
                block.quality_flags = [f for f in block.quality_flags if not (f.code == "cell_symbol_defined" and f.field_id == field_id)]
                block.quality_flags.append(QnuQualityFlag(
                    code="ambiguous_cell", field_id=field_id,
                    detail=f"Ký hiệu \"{entry['symbol']}\" không tìm thấy block định nghĩa chuẩn xác trong tài liệu."
                ))
                continue
            if legend.id not in block.context_refs:
                block.context_refs.append(legend.id)
            for flag in block.quality_flags:
                if flag.code == "cell_symbol_defined" and flag.field_id == field_id and legend.id not in flag.related_block_ids:
                    flag.related_block_ids.append(legend.id)
        for field_id in to_remove:
            defs.pop(field_id, None)


def _link_continuations(blocks: list[QnuBlock]) -> None:
    """Propose links using page adjacency and geometry; never silently merge header schemas."""
    tables = [block for block in blocks if block.type == "table"]
    for previous, current in pairwise(tables):
        a, b = previous.source_locations[0], current.source_locations[0]
        if a.page is None or b.page != a.page + 1:
            continue
        left, right = previous.attributes.get("comparison_bbox"), current.attributes.get("comparison_bbox")
        if not left or not right or left[3] < 80 or right[1] > 25:
            continue
        if abs(left[0] - right[0]) > 2 or abs(left[2] - right[2]) > 2:
            continue
        if len(previous.attributes["columns"]) != len(current.attributes["columns"]):
            continue
        current.attributes["continuation_candidate"] = {"block_id": previous.id, "basis": "inferred_geometry"}
        same_headers = previous.attributes["columns"] == current.attributes["columns"] and all(
            c["header_path"] for c in current.attributes["columns"])
        # Distinct captions/headings between tables prevent a geometric match
        # from establishing continuation. Keep each physical fragment intact.
        between = blocks[blocks.index(previous) + 1:blocks.index(current)]
        intervening = [b for b in between if b.type != "table_row" and b.body.strip()
                       and b.attributes.get("source_role") not in {"header", "footer"}]
        aligned = aligned_columns(previous, current)
        if (same_headers and aligned and not intervening and previous.attributes.get("native_literal_coverage")
                and current.attributes.get("native_literal_coverage")):
            current.attributes["continuation"] = {"block_id":previous.id,
                "basis": current.attributes.get('inherited_header', {}).get('basis',
                    'adjacent_page_aligned_grid_identical_verified_headers'), "status":"verified"}
            current.context_refs.append(previous.id)
            before = [b for b in blocks if b.type == "table_row" and b.parent_id == previous.id]
            after = [b for b in blocks if b.type == "table_row" and b.parent_id == current.id]
            if before and after and left[3] >= 90 and right[1] <= 15:
                first, last = after[0], before[-1]
                fields = first.attributes["fields"]
                occupied = [key for key,value in fields.items() if value["raw"].strip()]
                if (len(occupied) == 1 and occupied[0] != next(iter(fields))
                        and last.attributes["fields"][occupied[0]]["raw"].strip()
                        and last.attributes.get("row_role") != "source_merged_literal"):
                    # Keep the two source cells separate. The link ensures the
                    # truncated record carries its continuation through retrieval.
                    first.attributes.update(interpretation="literal_only", row_role="source_row_fragment",
                        continuation_of={"block_id":last.id, "column_id":occupied[0], "basis":"aligned_page_break_fragment"})
                    for field in fields.values():
                        if field["state"] == "present":
                            field["state"] = "ambiguous"
                    last.context_refs.append(first.id)
            continue
        current.quality_flags.append(QnuQualityFlag(code="table_continuation_needs_review",
            detail="Bảng ở biên hai trang có bố cục tương thích; chưa gộp hoặc kế thừa header khi chưa duyệt.",
            related_block_ids=[previous.id]))


def _link_explicit_notes(blocks: list[QnuBlock]) -> None:
    for note in (block for block in blocks if block.type == "note"):
        marker = re.match(r"^\s*(\[\d+\]|\[\*+\]|[†‡])", note.body)
        if not marker:
            continue
        same_notes = [other for other in blocks if other.type == "note" and other.body.lstrip().startswith(marker[1])
                      and other.source_locations[0].page == note.source_locations[0].page]
        if len(same_notes) != 1:
            continue
        for block in blocks:
            if block.type != "note" and block.source_locations[0].page == note.source_locations[0].page and marker[1] in block.body:
                block.context_refs.append(note.id)


def build_pdf_document(evidence: dict[str, Any], *, filename: str, sha256: str,
                       legacy_v5: bool = False) -> QnuStructuredDocument:
    pages = evidence["pages"]
    if any(page["native"].get("capture_error") for page in pages):
        raise ValueError("Native evidence capture incomplete")
    result = QnuStructuredDocument(title=filename, source=QnuSourceInfo(filename=filename, sha256=sha256,
                                      page_count=len(pages)), language="und", document_meta={"builder_version": PDF_STRUCTURE_VERSION,
                                      "source_format": "pdf",
                                      "page_mapping": {"kind": "physical_pdf", "status": "direct"}})
    font_counts: Counter[float] = Counter()
    for page in pages:
        for item in _native_items(page["native"]):
            if item.get("text") and item["bbox"][1] < 80:
                font_counts[item.get("font_size", 0)] += len(item["text"])
    body_size = font_counts.most_common(1)[0][0] if font_counts else 0
    decisions = heading_decisions([reading_order(_native_items(page['native'])) for page in pages], body_size)
    furniture = furniture_locators([_native_items(page['native']) for page in pages])
    sections: list[tuple[int, str, str]] = []
    all_legends: set[str] = set()

    for page in pages:
        native = _native_items(page["native"])
        for item in native:
            if item["locator"] in furniture:
                item["kind"] = "footer" if item["bbox"][3] > 94 else "header"
            elif marker := footnote_marker(item, page["native"]):
                item["kind"], item["footnote_marker"] = "footnote", marker
        spans = _native_spans(page["native"])
        ocr = _ocr_items(page) if page.get("ocr_selected") else []
        verified = page["native"].get("visible_text_verified", False)
        items = visible_items(native, ocr) if verified else _select_items(native, ocr)
        ordered = reading_order(items)
        page_tables = [it for it in ordered if it.get("table") and it.get("bbox")]
        page_legends = _collect_page_legends(ordered, page)
        all_legends.update(cand["symbol"] for cand in page_legends)
        for index, item in enumerate(ordered):
            block_id = f"p{page['page']:04d}_b{index + 1:04d}"
            location, flags = _location(item, page), _flags(item)
            path, parent = [s[1] for s in sections], sections[-1][2] if sections else None
            if item.get("table"):
                _propose_header(item, spans)
                applicable_legends = _find_table_legends(item, page_tables, page_legends)
                emitted = table_blocks(item["table"], block_id=block_id, parent_id=parent,
                    location=location, section_path=path, engine=item["engine"], symbol_definitions=applicable_legends)
                if emitted:
                    emitted[0].quality_flags.extend(flags)
                    emitted[0].attributes["comparison_bbox"] = item.get("bbox")
                    emitted[0].source_data = {"table": item["table"], "alternatives": item.get("alternatives", [])}
                result.blocks.extend(emitted)
                continue
            text, kind = item.get("text", ""), "text"
            if item["kind"] == "table" and not item.get("table"):
                fence = "`" * max(3, max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
                text = f"{fence}text\n{text}\n{fence}"
            size = item.get("font_size", 0)
            heading = decisions.get(item['locator'], {})
            if heading.get('status') == 'inferred':
                text = text.strip()  # Presentation only; the untouched glyph stream stays in source_data.raw.
                level = heading['level']
                while sections and sections[-1][0] >= level:
                    sections.pop()
                parent = sections[-1][2] if sections else None
                sections.append((level, text, block_id))
                path, kind = [s[1] for s in sections], "section"
                text = f"{'#' * min(level + 1, 6)} {text}"
                flags.append(QnuQualityFlag(code="heading_inferred_typography", status="confirmed" if verified else "unresolved",
                    detail="Bảo toàn chữ hiển thị; cấp mục là cấu trúc trình bày suy từ kiểu chữ, không xác nhận quan hệ ngữ nghĩa."))
            elif item["kind"] in {"title", "section_header"}:
                flags.append(QnuQualityFlag(code="heading_level_unresolved", detail="OCR có tiêu đề nhưng chưa xác định cấp mục."))
            elif item["kind"] in {"figure", "image", "chart"}:
                kind = "figure"
                flags.append(QnuQualityFlag(code="visual_content_untranscribed", detail="Giữ vùng hình; không suy số liệu từ hình."))
            elif item["kind"] in {"formula", "equation"} and text.strip():
                kind = "formula"
            elif item.get("monospaced") and text.strip():
                kind = "code"
                fence = "`" * max(3, max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
                text = f"{fence}\n{text}\n{fence}"
            elif item["kind"] in {"footnote", "header", "footer", "signature", "stamp"}:
                kind = "note"
            elif size and size < body_size and item.get("bbox") and item["bbox"][1] > 80:
                kind = "note"
                flags.append(QnuQualityFlag(code="footnote_needs_review", status="confirmed" if verified else "unresolved",
                    detail="Giữ nguyên chữ chú thích cuối trang; chưa gán phạm vi khi thiếu neo duy nhất."))
            elif re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", text):
                kind = "list"
            if not text.strip() and kind != "figure":
                continue
            result.blocks.append(QnuBlock(id=block_id, parent_id=parent, type=kind, source_locations=[location],
                source_label=heading.get('source_label'), section_path=path,
                attributes={"engine_used": item["engine"], "source_role": item["kind"],
                    **({"resource":item["resource"]} if item.get("resource") else {}),
                    **({"footnote_marker":item["footnote_marker"], "scope_status":"unassigned"} if item.get("footnote_marker") else {}),
                    **({'heading_evidence': heading} if heading else {})},
                quality_flags=flags, body=text, source_data={"raw": item["raw"], "alternatives": item.get("alternatives", []),
                    **({"reconciliation":item["reconciliation"]} if item.get("reconciliation") else {})}))
        if page["native"].get("table_errors"):
            result.document_meta.setdefault("extraction_warnings", []).append({"page": page["page"], "code": "native_tables_unavailable"})
        if page.get("ocr_selected") and not page.get("raw_ocr_available"):
            result.document_meta.setdefault("extraction_warnings", []).append({"page": page["page"], "code": "raw_ocr_unavailable"})
        rescue = page.get("header_rescue") or {}
        audit = rescue.get("audit") or {}
        if audit.get("accepted_lines"):
            result.blocks.append(QnuBlock(id=f"p{page['page']:04d}_header_rescue", type="note",
                source_locations=[QnuSourceLocation(page=page["page"], locator=f"pdf:page:{page['page']}/header-rescue",
                    bbox=audit.get("bbox"), bbox_space="pymupdf_render_crop_points")],
                attributes={"source_role": "header_rescue_proposal", "engine_used": audit.get("engine"),
                            "location_precision": "crop_region"},
                quality_flags=[QnuQualityFlag(code="header_rescue_needs_review",
                    detail="Dòng số/ngày được OCR vùng đầu đề xuất; JSON giữ raw và phép biến đổi, chưa xác nhận đúng.")],
                source_data=rescue, body="\n\n".join(audit["accepted_lines"])))
    if not legacy_v5:
        retain_native_projections(result.blocks)
        inherit_headers(result.blocks)
    _link_continuations(result.blocks)
    _link_explicit_notes(result.blocks)
    _link_symbol_legends(result.blocks)
    result.stats = {"pages": len(pages), "blocks": len(result.blocks),
                    "quality_flags": sum(len(block.quality_flags) for block in result.blocks)}
    result.document_meta["visual_classification"] = {
        "ruling_strokes_in_source": _count_rulings(pages),
        "visual_regions_retained": sum(1 for block in result.blocks if block.type == "figure"),
        "symbol_legend_definitions": len(all_legends)}
    result.document_meta["content_status"] = "needs_review" if result.stats["quality_flags"] or result.document_meta.get("extraction_warnings") else "unreviewed"
    return result
