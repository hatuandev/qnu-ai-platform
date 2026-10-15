"""Source-preserving document hierarchy, no domain dictionary or generated facts."""

import hashlib
import json
import re
from itertools import pairwise
from typing import Any

from app.core.exceptions import AppException
from app.modules.knowledge.chunker import BaseChunker
from app.modules.knowledge.normalization.retrieval_models import (
    SourceUnit,
    TemporalScope,
    UnitManifest,
)

YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

PAGE = re.compile(r"<!--\s*(?:Trang|Page)\s+(\d+)\s*-->", re.IGNORECASE)
PARAGRAPH = re.compile(r"\S[\s\S]*?(?=\n\s*\n|\Z)")
HEADING = re.compile(r"(#{1,6})\s+([^\n]+)")
LIST = re.compile(r"(?m)^\s*(?:[-+*]|\d+[.)]|[a-z][.)])\s+")
TABLE_SEPARATOR = re.compile(r"^\s*\|[\s|:\-]+\|\s*$")


def structural_spans(markdown: str, begin: int, finish: int) -> list[tuple[int, int]]:
    spans = []
    for paragraph in PARAGRAPH.finditer(markdown, begin, finish):
        points = {paragraph.start(), paragraph.end()}
        is_table = False
        for line in re.finditer(r"[^\n]+(?:\n|$)", markdown[paragraph.start():paragraph.end()]):
            text = line.group().strip()
            start = paragraph.start() + line.start()
            end = paragraph.start() + line.end()
            table_line = text.startswith("|")
            if table_line != is_table:
                points.add(start)
            if not table_line and (HEADING.fullmatch(text) or LIST.match(text)):
                points.add(start)
            if HEADING.fullmatch(text):
                points.add(end)
            is_table = table_line
        ordered = sorted(points)
        for start, end in pairwise(ordered):
            text = markdown[start:end]
            left = len(text) - len(text.lstrip())
            if text.strip():
                spans.append((start + left, start + len(text.rstrip())))
    return spans


def build_unit_manifest(markdown: str, temporal_metadata: dict[str, Any] | None = None) -> UnitManifest:
    markers = list(PAGE.finditer(markdown))
    ranges = [(0, markers[0].start(), None)] if markers and markers[0].start() else []
    ranges += [(marker.end(), markers[i + 1].start() if i + 1 < len(markers) else len(markdown), int(marker[1]))
               for i, marker in enumerate(markers)]
    if not markers:
        ranges = [(0, len(markdown), None)]
    issued = ((temporal_metadata or {}).get("issued_date") or {}).get("value")
    headings: list[tuple[int, SourceUnit]] = []
    units = []
    for begin, finish, page in ranges:
        for start, end in structural_spans(markdown, begin, finish):
            text = markdown[start:end]
            heading = HEADING.fullmatch(text)
            if heading:
                depth = len(heading[1])
                headings = [(level, unit) for level, unit in headings if level < depth]
            kind = "heading" if heading else "table" if re.search(r"(?m)^\s*\|", text) else "list" if LIST.match(text) else "paragraph"
            unit = SourceUnit(id=f"span:{start}:{end}", kind=kind,
                start=start, end=end, text=text, page_number=page,
                parent_id=headings[-1][1].id if headings else None,
                heading_path=[parent.text for _, parent in headings] + ([text] if heading else []),
                temporal=TemporalScope(issued_date=issued,
                    mentioned_years=sorted({int(year) for year in YEAR.findall(text)}),
                    heading_years=sorted({int(year) for _, parent in headings for year in YEAR.findall(parent.text)})))
            # A numeric year mention may be a citation, an event or historical
            # data. Do not silently promote it to verified data applicability.
            unit.temporal.status = "proposed" if unit.temporal.mentioned_years or unit.temporal.heading_years else "unknown"
            units.append(unit)
            if kind == "table":
                units.extend(table_children(unit))
            if heading:
                headings.append((len(heading[1]), unit))
    return UnitManifest(canonical_hash=hashlib.sha256(markdown.encode("utf-8")).hexdigest(), units=units)


def table_children(parent: SourceUnit) -> list[SourceUnit]:
    """Retain a table container and exact row spans with source header context."""
    # Reuse the existing structural header tree; keep raw lines for citations.
    # Import at runtime to avoid a normalization/service initialization cycle.
    from app.modules.knowledge.services.table_context import extract_context_tables

    lines = list(re.finditer(r"[^\n]+", parent.text))
    separator = next((i for i, line in enumerate(lines) if TABLE_SEPARATOR.fullmatch(line.group())), None)
    if separator is None or separator == len(lines) - 1:
        return []
    tables = extract_context_tables(parent.text, 1)
    header_levels = len(tables[0]["header_rows"]) if tables else 1
    header_last = min(separator + header_levels - 1, len(lines) - 1)
    if header_last == len(lines) - 1:
        return []
    parent.is_container = True
    header_end = lines[header_last].end()
    header = parent.text[:header_end]
    result = []
    # Header is independently citable, never only an embedding-only prefix.
    spans = [(0, header_end), *[(line.start(), line.end()) for line in lines[header_last + 1:]]]
    for start, end in spans:
        text = parent.text[start:end]
        result.append(SourceUnit(id=f"span:{parent.start + start}:{parent.start + end}",
            parent_id=parent.id, kind="table", text=text, start=parent.start + start,
            end=parent.start + end, page_number=parent.page_number, heading_path=parent.heading_path,
            header_context=header,
            temporal=parent.temporal.model_copy(update={"mentioned_years": sorted({int(y) for y in YEAR.findall(text)})})))
    return result


def manifest_digest(manifest: UnitManifest) -> str:
    return hashlib.sha256(json.dumps(manifest.model_dump(), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def validate_manifest(manifest: UnitManifest, markdown: str) -> None:
    if manifest.canonical_hash != hashlib.sha256(markdown.encode("utf-8")).hexdigest():
        raise ValueError("Source unit manifest has a different canonical hash")
    ids = {unit.id for unit in manifest.units}
    by_id = {unit.id: unit for unit in manifest.units}
    if len(ids) != len(manifest.units):
        raise ValueError("Duplicate source unit ID")
    for unit in manifest.units:
        if unit.end <= unit.start or markdown[unit.start:unit.end] != unit.text:
            raise ValueError("Source unit does not match its original span")
        if unit.parent_id and unit.parent_id not in ids:
            raise ValueError("Source unit parent is missing")
        if unit.parent_id:
            parent = by_id[unit.parent_id]
            heading_parent = parent.kind == "heading" and parent.start < unit.start
            table_parent = parent.kind == "table" and parent.is_container and parent.start <= unit.start and parent.end >= unit.end
            if unit.parent_id == unit.id or not (heading_parent or table_parent):
                raise ValueError("Source unit parent is not a containing structural node")
        scope = unit.temporal
        if scope.status == "verified" and (not scope.evidence_quote or scope.evidence_quote not in unit.text
                or not set(scope.data_years).issubset({int(year) for year in YEAR.findall(scope.evidence_quote)})):
            raise ValueError("Verified temporal scope lacks exact same-unit evidence")


def resolve_unit_manifest(markdown: str, artifact: dict[str, Any]) -> UnitManifest:
    stored = artifact.get("retrieval_units")
    manifest = UnitManifest.model_validate(stored) if stored else build_unit_manifest(markdown, artifact.get("temporal_metadata"))
    validate_manifest(manifest, markdown)
    if stored and artifact.get("unit_manifest_hash") != manifest_digest(manifest):
        raise ValueError("Source unit manifest digest mismatch")
    return manifest


def unit_chunks(manifest: UnitManifest, max_chars: int = 6000, *, chunker: BaseChunker | None = None,
                chunk_config: dict[str, Any] | None = None,
                context_graph: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Preserve atomic structure; oversize units need review, never silent truncation."""
    result = []
    digest = manifest_digest(manifest)
    if context_graph:
        from app.modules.knowledge.services.source_links import validate_context_graph

        validate_context_graph(context_graph, manifest)
    for unit in manifest.units:
        if unit.is_container:
            continue
        metadata = {"source_unit_version": manifest.version, "source_unit_id": unit.id,
            "source_unit": unit.model_dump(), "unit_manifest_hash": digest}
        projection = ""
        if context_graph:
            metadata.update(context_graph_hash=context_graph["digest"],
                            context_unit_ids=context_graph["links"].get(unit.id, []))
            projection = context_graph["row_projections"].get(unit.id, "")
        views = [unit.text]
        if chunker is not None and unit.kind == "paragraph":
            views = [view.content for view in chunker.chunk(unit.text, **(chunk_config or {}))]
            if not views:
                raise AppException("Chiến lược cắt đoạn không trả nội dung.", code="CHUNKER_RETURNED_ZERO", status_code=422)
        for view in views:
            content = "\n".join(dict.fromkeys([*unit.heading_path, unit.header_context, view, projection])).strip()
            if len(content) > max_chars:
                raise AppException("Đơn vị nguồn quá dài; cần chia theo cấu trúc trước khi nạp vector.",
                    code="SOURCE_UNIT_TOO_LARGE", status_code=422, details={"unit_id": unit.id})
            result.append({"index": len(result), "content": content,
                "chunk_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "token_count": max(1, len(content) // 3), "section": " / ".join(unit.heading_path),
                "page_number": unit.page_number, "metadata": metadata})
    return result


def refresh_unit_metadata(markdown: str, artifact: dict[str, Any]) -> None:
    """Update document metadata without losing revision-bound unit corrections."""
    manifest = resolve_unit_manifest(markdown, artifact)
    issued = (artifact.get("temporal_metadata", {}).get("issued_date") or {}).get("value")
    for unit in manifest.units:
        unit.temporal.issued_date = issued
    artifact["retrieval_units"] = manifest.model_dump()
    artifact["unit_manifest_hash"] = manifest_digest(manifest)
