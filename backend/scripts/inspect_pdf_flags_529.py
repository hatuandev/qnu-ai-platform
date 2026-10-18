"""Read-only survey of QNU RAG Markdown quality flags for the 5 PDF revisions.

Prints aggregated flag evidence (code, pages, block types, sample detail) so classification can be
done against real artifacts instead of the journal numbers. Writes no DB rows and no storage files.
"""

import argparse
import asyncio
import json
from collections import Counter

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.core.storage import storage_service
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.normalization.qnu_markdown import QnuStructuredDocument
from app.modules.knowledge.parsers.pdf_evidence import intersection_fraction

_MAX_DETAIL = 180


def _area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def evidence_pages(evidence: dict) -> list[dict]:
    """Compact per-page shape metrics: what the builder saw, not the raw payload."""
    rows = []
    for page in evidence.get("pages", []):
        native = page.get("native") or {}
        width, height = native.get("width") or 1, native.get("height") or 1
        page_area = width * height
        tables = native.get("tables") or []
        table_boxes = [table["bbox"] for table in tables]
        drawings = native.get("drawings") or []
        boxes = [d.get("rect") for d in drawings if isinstance(d.get("rect"), list)]
        valid = [b for b in boxes if b[2] > b[0] and b[3] > b[1]]
        inside = [b for b in valid if any(intersection_fraction(b, t) >= 0.9 for t in table_boxes)]
        images = native.get("images") or []
        cells = [box for table in tables for row in table.get("cell_boxes") or [] for box in row]
        rows.append({
            "page": page.get("page"),
            "engine": page.get("engine_used"),
            "ocr_selected": bool(page.get("ocr_selected")),
            "raw_ocr_available": bool(page.get("raw_ocr_available")),
            "text_blocks": sum(1 for block in (native.get("layout") or {}).get("blocks", []) if block.get("lines")),
            "native_tables": [
                {"rows": len(t.get("matrix") or []), "cols": max((len(r) for r in t.get("matrix") or []), default=0),
                 "null_cell_boxes": sum(1 for box in (c for row in t.get("cell_boxes") or [] for c in row) if box is None),
                 "header_depth": t.get("proposed_header_depth"),
                 "external_header": bool((t.get("header") or {}).get("external")),
                 "names": len((t.get("header") or {}).get("names") or []),
                 "area_pct": round(_area(t["bbox"]) / page_area * 100, 1)}
                for t in tables
            ],
            "images": len(images),
            "image_area_pct": round(sum(_area(i["bbox"]) for i in images) / page_area * 100, 1),
            "drawings": len(drawings),
            "drawings_degenerate": len([b for b in boxes if not (b[2] > b[0] and b[3] > b[1])]),
            "drawings_in_table": len(inside),
            "drawing_figure_candidates": len(valid) - len(inside),
            "cell_boxes": len(cells),
            "header_rescue": sorted((page.get("header_rescue") or {}).keys()),
        })
    return rows


def _truncate(value: str) -> str:
    return " ".join(value.split())[:_MAX_DETAIL]


def summarize(document: QnuStructuredDocument) -> dict:
    flags: dict[str, dict] = {}
    for block in document.blocks:
        for flag in block.quality_flags:
            entry = flags.setdefault(
                flag.code,
                {"count": 0, "statuses": Counter(), "block_types": Counter(), "pages": Counter(),
                 "field_ids": 0, "details": Counter()},
            )
            entry["count"] += 1
            entry["statuses"][flag.status] += 1
            entry["block_types"][block.type] += 1
            for location in block.source_locations:
                entry["pages"][str(location.page)] += 1
            if flag.field_id:
                entry["field_ids"] += 1
            entry["details"][_truncate(flag.detail)] += 1
    out = {}
    for code, entry in sorted(flags.items(), key=lambda item: -item[1]["count"]):
        out[code] = {
            "count": entry["count"],
            "statuses": dict(entry["statuses"]),
            "block_types": dict(entry["block_types"]),
            "pages_with_flag": sorted(entry["pages"], key=lambda p: (p == "None", p)),
            "flagged_fields": entry["field_ids"],
            "sample_details": [text for text, _ in entry["details"].most_common(3)],
        }
    field_states: Counter[str] = Counter()
    for block in document.blocks:
        fields = block.attributes.get("fields")
        if isinstance(fields, dict):
            for value in fields.values():
                if isinstance(value, dict):
                    field_states[str(value.get("state"))] += 1
    return {
        "title": document.title,
        "source": document.source.model_dump(mode="json"),
        "page_mapping": document.document_meta.get("page_mapping"),
        "stats": document.stats,
        "block_types": dict(Counter(block.type for block in document.blocks)),
        "table_representations": dict(
            Counter(str(block.attributes.get("representation")) for block in document.blocks if block.type == "table")
        ),
        "field_states": dict(field_states),
        "flagged_block_ids": {
            code: [block.id for block in document.blocks if any(f.code == code for f in block.quality_flags)][:8]
            for code in out
        },
        "flags": out,
    }


def drawings_profile(evidence: dict) -> list[dict]:
    """Classify the drawing items the builder turned into figure blocks: hairline furniture vs real graphic."""
    rows = []
    for page in evidence.get("pages", []):
        native = page.get("native") or {}
        tables = [table["bbox"] for table in native.get("tables") or []]
        width, height = native.get("width") or 1, native.get("height") or 1
        buckets: Counter[str] = Counter()
        samples: dict[str, list[str]] = {}
        for drawing in native.get("drawings") or []:
            box = drawing.get("rect")
            if not (isinstance(box, list) and box[2] > box[0] and box[3] > box[1]):
                continue
            if any(intersection_fraction(box, target) >= 0.9 for target in tables):
                continue
            w, h = box[2] - box[0], box[3] - box[1]
            thickness, length = min(w, h), max(w, h)
            overlap = max((intersection_fraction(box, target) for target in tables), default=0.0)
            kind = "fill" if drawing.get("fill") else "stroke"
            if thickness <= 1.5 and length >= 0.2 * min(width, height):
                bucket = f"hairline_rule_{kind}"
            elif thickness <= 3 and length >= 0.2 * min(width, height):
                bucket = f"thin_line_{kind}"
            elif overlap >= 0.3:
                bucket = f"overlaps_table_{kind}"
            else:
                bucket = f"graphic_{kind}"
            buckets[bucket] += 1
            samples.setdefault(bucket, []).append(
                f"[{box[0]:.0f},{box[1]:.0f},{box[2]:.0f},{box[3]:.0f}] w={w:.1f} h={h:.1f} items={len(drawing.get('items') or [])} ov={overlap:.2f}"
            )
        rows.append({
            "page": page.get("page"),
            "buckets": dict(buckets),
            "samples": {key: value[:3] for key, value in samples.items()},
        })
    return rows


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--revision", action="append", default=[])
    parser.add_argument("--code", help="Chỉ in cờ này, kèm chi tiết từng block.")
    parser.add_argument("--evidence", action="store_true", help="In metric cấu trúc native/OCR từng trang.")
    parser.add_argument("--drawings", action="store_true", help="Phân loại drawing thành figure block.")
    args = parser.parse_args()

    async with AsyncSessionFactory() as db:
        query = (
            select(KnowledgeSourceRevision)
            .join(KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id)
            .where(KnowledgeBinding.collection_id == args.collection)
        )
        revisions = list((await db.scalars(query)).all())

    for revision in sorted(revisions, key=lambda row: row.id):
        if args.revision and revision.id not in args.revision:
            continue
        artifact = (revision.snapshot_metadata or {}).get("qnu_markdown") or {}
        path = artifact.get("structured_path")
        if artifact.get("status") != "ready" or not path:
            print(json.dumps({"revision_id": revision.id, "status": artifact.get("status")}, ensure_ascii=False))
            continue
        content = await storage_service.get(path)
        document = QnuStructuredDocument.model_validate_json(content)
        if args.evidence or args.drawings:
            reference = document.document_meta.get("raw_evidence") or {}
            raw = await storage_service.get(reference["path"]) if reference.get("path") else None
            evidence = json.loads(raw) if raw else {}
            rows = drawings_profile(evidence) if args.drawings else evidence_pages(evidence)
            for row in rows:
                print(json.dumps({"revision_id": revision.id, **row}, ensure_ascii=False))
            continue
        if args.code:
            for block in document.blocks:
                for flag in block.quality_flags:
                    if flag.code == args.code:
                        print(
                            json.dumps(
                                {
                                    "revision_id": revision.id,
                                    "block_id": block.id,
                                    "type": block.type,
                                    "parent_id": block.parent_id,
                                    "locations": [
                                        {"page": loc.page, "locator": loc.locator} for loc in block.source_locations
                                    ],
                                    "section_path": block.section_path,
                                    "status": flag.status,
                                    "field_id": flag.field_id,
                                    "related_block_ids": flag.related_block_ids,
                                    "detail": _truncate(flag.detail),
                                    "body": _truncate(block.body),
                                },
                                ensure_ascii=False,
                            )
                        )
            continue
        print(json.dumps({"revision_id": revision.id, **summarize(document)}, ensure_ascii=False))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
