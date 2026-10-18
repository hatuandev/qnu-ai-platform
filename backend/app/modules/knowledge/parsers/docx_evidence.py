"""Original OOXML note anchors and embedded resources, separate from engine output."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any
from zipfile import ZipFile

from lxml import etree
from PIL import Image

from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuQualityFlag,
    QnuSourceLocation,
    QnuStructuredDocument,
)

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS = {"w": _W, "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def _xml(archive: ZipFile, path: str) -> Any:
    return etree.fromstring(
        archive.read(path), etree.XMLParser(resolve_entities=False, no_network=True)
    )


def _text(element: Any) -> str:
    return "".join(
        "\n"
        if node.tag == f"{{{_W}}}br"
        else "\t"
        if node.tag == f"{{{_W}}}tab"
        else node.text or ""
        for node in element.iter()
        if node.tag in {f"{{{_W}}}t", f"{{{_W}}}br", f"{{{_W}}}tab"}
    )


def _normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def _pixel_key(image: Any) -> tuple:
    rgba = image.convert("RGBA")
    return rgba.size, hashlib.sha256(rgba.tobytes()).hexdigest()


def read_docx_evidence(content: bytes, document: Any) -> dict[str, Any]:
    """Never follow external relationships; keep original bytes out of JSON metadata."""
    with ZipFile(BytesIO(content)) as archive:
        root = _xml(archive, "word/document.xml")
        top_tables = root.findall(f"{{{_W}}}body/{{{_W}}}tbl")
        paragraphs = []
        for index, paragraph in enumerate(root.xpath("//w:body//w:p", namespaces=_NS), 1):
            table = next((a for a in paragraph.iterancestors() if a.tag == f"{{{_W}}}tbl"), None)
            table_position = None
            if table is not None and table in top_tables:
                row = next(a for a in paragraph.iterancestors() if a.tag == f"{{{_W}}}tr")
                cell = next(a for a in paragraph.iterancestors() if a.tag == f"{{{_W}}}tc")
                col = sum(
                    int(c.find(f"{{{_W}}}tcPr/{{{_W}}}gridSpan").get(f"{{{_W}}}val"))
                    if c.find(f"{{{_W}}}tcPr/{{{_W}}}gridSpan") is not None
                    else 1
                    for c in row.findall(f"{{{_W}}}tc")[
                        : list(row.findall(f"{{{_W}}}tc")).index(cell)
                    ]
                )
                before = row.find(f"{{{_W}}}trPr/{{{_W}}}gridBefore")
                table_position = {
                    "table": top_tables.index(table) + 1,
                    "row": list(table.findall(f"{{{_W}}}tr")).index(row) + 1,
                    "column": col
                    + (int(before.get(f"{{{_W}}}val")) if before is not None else 0)
                    + 1,
                }
            paragraphs.append(
                {
                    "locator": f"word/document.xml#p{index}",
                    "text": _text(paragraph),
                    "style": paragraph.xpath("./w:pPr/w:pStyle/@w:val", namespaces=_NS),
                    "table": table_position,
                    "notes": [
                        {"part": part, "id": ref.get(f"{{{_W}}}id")}
                        for part in ("footnote", "endnote")
                        for ref in paragraph.iter(f"{{{_W}}}{part}Reference")
                    ],
                }
            )
        notes = []
        for kind in ("footnote", "endnote"):
            path = f"word/{kind}s.xml"
            if path not in archive.namelist():
                continue
            for note in _xml(archive, path):
                if note.get(f"{{{_W}}}type") in {"separator", "continuationSeparator"}:
                    continue
                notes.append(
                    {
                        "part": kind,
                        "id": note.get(f"{{{_W}}}id"),
                        "text": "\n\n".join(_text(child) for child in note),
                        "complex_structure": any(child.tag != f"{{{_W}}}p" for child in note)
                        or bool(note.xpath(".//w:drawing|.//w:object", namespaces=_NS)),
                        "locator": f"{path}#id={note.get(f'{{{_W}}}id')}",
                    }
                )
        resources = _resources(archive, root, document)
    return {
        "paragraphs": paragraphs,
        "notes": notes,
        "resources": resources,
        "image_anchor_count": len(root.xpath("//a:blip", namespaces=_NS)),
    }


def _resources(archive: ZipFile, root: Any, document: Any) -> list[dict]:
    path = "word/_rels/document.xml.rels"
    relationships = (
        {r.get("Id"): r for r in _xml(archive, path)} if path in archive.namelist() else {}
    )
    assets = defaultdict(dict)
    for blip in root.xpath("//a:blip", namespaces=_NS):
        relation = relationships.get(blip.get(f"{{{_R}}}embed"))
        if relation is None or relation.get("TargetMode") == "External":
            continue
        target = PurePosixPath("word") / relation.get("Target", "")
        if target.is_absolute() or ".." in target.parts or str(target) not in archive.namelist():
            continue
        payload = archive.read(str(target))
        try:
            with Image.open(BytesIO(payload)) as image:
                key = _pixel_key(image)
                mime = Image.MIME.get(image.format, "application/octet-stream")
        except (OSError, ValueError):
            continue  # Unsupported formats remain in the source package and inventory.
        checksum = hashlib.sha256(payload).hexdigest()
        assets[key][checksum] = {
            "member": str(target),
            "sha256": checksum,
            "media_type": mime,
            "extension": target.suffix.lower(),
            "data": payload,
        }
    resources = []
    for picture in getattr(document, "pictures", []):
        image_ref = getattr(picture, "image", None)
        image = getattr(image_ref, "pil_image", None) if image_ref is not None else None
        matches = assets.get(_pixel_key(image), {}) if image is not None else {}
        if len(matches) == 1:
            resources.append({**next(iter(matches.values())), "source_ref": picture.self_ref})
    return resources


def preview_image_locations(preview: bytes, resources: list[dict]) -> dict[str, dict]:
    """Locate only a unique, pixel-identical source image in the PDF preview."""
    import pymupdf

    if not resources:
        return {}
    assets = defaultdict(list)
    for resource in resources:
        with Image.open(BytesIO(resource["data"])) as image:
            assets[_pixel_key(image)].append(resource["source_ref"])
    positions = defaultdict(dict)
    try:
        document = pymupdf.open(stream=preview, filetype="pdf")
    except (ValueError, RuntimeError):
        return {}
    with document:
        for number, page in enumerate(document, 1):
            for entry in page.get_images(full=True):
                xref = entry[0]
                try:
                    payload = document.extract_image(xref)["image"]
                    with Image.open(BytesIO(payload)) as image:
                        refs = assets.get(_pixel_key(image), [])
                    if len(refs) != 1:
                        continue
                    for rect in page.get_image_rects(xref):
                        positions[refs[0]][(number, *rect)] = {
                            "page": number, "bbox": list(rect), "bbox_space": "points",
                            "basis": "exact_render_image_pixels",
                        }
                except (OSError, ValueError, RuntimeError):
                    continue  # No proof: retain the DOCX locator and unresolved page.
    return {ref: next(iter(items.values())) for ref, items in positions.items() if len(items) == 1}


def apply_docx_evidence(model: QnuStructuredDocument, evidence: dict[str, Any]) -> None:
    """Only source-owned note IDs create dependencies; prose proximity is not scope."""
    if not evidence:
        return
    paragraphs = evidence.get("paragraphs", [])
    by_text = defaultdict(list)
    for paragraph in paragraphs:
        if paragraph["text"].strip():
            by_text[_normalized(paragraph["text"])].append(paragraph)
    for block in model.blocks:
        body = re.sub(r"^#{1,6}\s+", "", block.body)
        matches = by_text.get(_normalized(body), [])
        if len(matches) == 1:
            block.attributes["source_paragraph"] = {k: matches[0][k] for k in ("locator", "style")}
    counts = Counter((n["part"], n["id"]) for n in evidence.get("notes", []))
    anchor_counts = Counter((r["part"], r["id"]) for p in paragraphs for r in p["notes"])
    unresolved = 0
    note_blocks = []
    for index, note in enumerate(evidence.get("notes", []), 1):
        key = note["part"], note["id"]
        anchors = [p for p in paragraphs if any((r["part"], r["id"]) == key for r in p["notes"])]
        note_id = f"docx_{note['part']}_{index}"
        while any(b.id == note_id for b in [*model.blocks, *note_blocks]):
            note_id += "_source"
        linked = []
        for anchor in anchors:
            targets = _anchor_targets(model, anchor)
            if counts[key] == 1 and len(targets) == 1:
                target = targets[0]
                target.context_refs = list(dict.fromkeys([*target.context_refs, note_id]))
                linked.append(
                    {"block_id": target.id, "locator": anchor["locator"], "table": anchor["table"]}
                )
            else:
                unresolved += 1
        flags = []
        if len(linked) != len(anchors) or not anchors or not note["text"].strip():
            flags.append(
                QnuQualityFlag(
                    code="source_note_unresolved",
                    detail="Giữ chú thích nguồn; liên kết anchor chưa duy nhất hoặc thiếu nội dung.",
                )
            )
        if note.get("complex_structure"):
            flags.append(
                QnuQualityFlag(
                    code="source_note_structure_unresolved",
                    detail="Chú thích có cấu trúc ngoài đoạn văn; giữ text và locator, cần đối soát bố cục nguồn.",
                )
            )
        text = _normalized(note["text"])
        page_matches = [
            page
            for page, rendered in evidence.get("render_pages", {}).items()
            if text and text in _normalized(rendered)
        ]
        pages = page_matches if len(page_matches) == 1 else [None]
        if evidence.get("render_pages") and pages == [None]:
            flags.append(
                QnuQualityFlag(
                    code="page_unresolved",
                    detail="Chú thích giữ locator nguồn; chưa định vị được trang render duy nhất.",
                )
            )
            model.document_meta["page_mapping"]["status"] = "partial"
        note_blocks.append(
            QnuBlock(
                id=note_id,
                type="note",
                source_label=note["id"],
                source_locations=[
                    QnuSourceLocation(page=page, locator=note["locator"]) for page in pages
                ],
                attributes={
                    "role": note["part"],
                    "source_note_id": note["id"],
                    "source_anchors": linked,
                },
                quality_flags=flags,
                body=note["text"] or "[Chú thích nguồn chưa đọc được]",
            )
        )
    missing = sorted(f"{part}:{key}" for part, key in anchor_counts if (part, key) not in counts)
    for block in model.blocks:
        if missing:
            block.quality_flags.append(
                QnuQualityFlag(
                    code="source_note_missing",
                    detail="DOCX có anchor thiếu note target: " + ", ".join(missing),
                )
            )
            break
    model.blocks.extend(note_blocks)
    resources = {r["source_ref"]: r for r in evidence.get("resources", [])}
    for block in model.blocks:
        ref = (block.attributes.get("resource") or {}).get("ref")
        if block.type == "figure" and ref in resources:
            resource = resources[ref]
            block.attributes["resource"].update(
                {k: resource[k] for k in ("member", "sha256", "media_type")}
            )
            position = evidence.get("preview_images", {}).get(ref)
            if position:
                block.source_locations = [QnuSourceLocation(
                    page=position["page"], bbox=position["bbox"], bbox_space=position["bbox_space"],
                    locator=block.source_locations[0].locator if block.source_locations else None)]
                block.attributes["page_mapping_basis"] = position["basis"]
                block.quality_flags = [f for f in block.quality_flags if f.code != "page_unresolved"]
            block.quality_flags = [f for f in block.quality_flags if f.code != "missing_content"]
            block.quality_flags.append(
                QnuQualityFlag(
                    code="figure_content_unverified",
                    detail="Giữ bytes ảnh gốc; chưa phiên âm/kiểm chứng nội dung trong ảnh.",
                )
            )
    if evidence.get("image_anchor_count", 0) > len(resources) and model.blocks:
        model.blocks[0].quality_flags.append(
            QnuQualityFlag(
                code="source_resource_unresolved",
                detail="Inventory ảnh nguồn chưa được ánh xạ đầy đủ tới resource; giữ nguyên package DOCX để đối soát.",
            )
        )
    model.document_meta["source_inventory"] = {
        "note_count": len(evidence.get("notes", [])),
        "note_blocks": len(note_blocks),
        "note_anchor_count": sum(anchor_counts.values()),
        "linked_anchors": sum(len(b.attributes["source_anchors"]) for b in note_blocks),
        "unresolved_anchors": unresolved,
        "missing_note_ids": missing,
        "image_anchor_count": evidence.get("image_anchor_count", 0),
        "image_resources": len(resources),
    }
    model.stats.update(
        block_count=len(model.blocks), type_counts=dict(Counter(b.type for b in model.blocks))
    )


def _anchor_targets(model: QnuStructuredDocument, anchor: dict) -> list[QnuBlock]:
    position = anchor["table"]
    if position:
        tables = [
            b
            for b in model.blocks
            if b.type == "table"
            and (b.source_data or {}).get("header_evidence", {}).get("locator")
            == f"word/document.xml/table/{position['table']}"
        ]
        if len(tables) != 1:
            return []
        table = tables[0]
        header_rows = (table.source_data or {}).get("header_rows", 0)
        if position["row"] <= header_rows:
            return [table]
        return [
            b
            for b in model.blocks
            if b.parent_id == table.id
            and b.type == "table_row"
            and b.source_label == str(position["row"])
        ]
    text = _normalized(anchor["text"])
    targets = []
    for block in model.blocks:
        if block.type in {"table", "table_row", "figure", "note"}:
            continue
        body = re.sub(r"^#{1,6}\s+", "", block.body)
        lines = [re.sub(r"^\s*(?:[-*+] |\d+[.)] )", "", line) for line in body.splitlines()]
        if (
            _normalized(body) == text
            or block.type == "list"
            and any(_normalized(line) == text for line in lines)
        ):
            targets.append(block)
    return targets
