"""Versioned embedding views; canonical units and their evidence stay immutable."""

import hashlib
import re
from typing import Any

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.retrieval_models import SourceUnit, UnitManifest
from app.modules.knowledge.normalization.retrieval_units import (
    manifest_digest,
    validate_manifest,
)

CHUNK_VERSION = "structure-chunks-v1"


def _protected_ranges(markdown: str) -> list[tuple[int, int, str]]:
    ranges = []
    opening = None
    offset = 0
    for line in markdown.splitlines(keepends=True):
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\n"))
        if fence:
            if opening is None:
                opening = (offset, fence[1][0], len(fence[1]))
            elif fence[1][0] == opening[1] and len(fence[1]) >= opening[2] and not fence[2].strip():
                ranges.append((opening[0], offset + len(line.rstrip("\n")), "code"))
                opening = None
        offset += len(line)
    if opening:
        raise AppException("Khối mã chưa đóng; cần kiểm tra bản sạch.", code="SOURCE_STRUCTURE_UNCLOSED", status_code=422)
    # Math inside a code fence is literal, not a second structural block.
    for match in re.finditer(r"\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]", markdown):
        if not any(start <= match.start() < end for start, end, _ in ranges):
            ranges.append((match.start(), match.end(), "formula"))
    return sorted(ranges)


def _same_scope(left: SourceUnit, right: SourceUnit) -> bool:
    return left.page_number == right.page_number and left.heading_path == right.heading_path


def _indent(markdown: str, unit: SourceUnit) -> int:
    start = markdown.rfind("\n", 0, unit.start) + 1
    return len(markdown[start:unit.start].expandtabs(4))


def _in_block(unit: SourceUnit, protected: list[tuple[int, int, str]]) -> bool:
    return any(unit.start < end and unit.end > start for start, end, _ in protected)


def _footnote_refs(group: list[SourceUnit], units: list[SourceUnit]) -> list[str]:
    refs = []
    for unit in group:
        for match in re.finditer(r"\[\^([^\]\n]+)\](?!:)", unit.text):
            definitions = [candidate for candidate in units
                           if candidate.heading_path == unit.heading_path
                           and candidate.text.startswith(f"[^{match[1]}]:")]
            if len(definitions) != 1:
                raise AppException("Chú thích thiếu hoặc trùng định danh; cần kiểm tra bản sạch.",
                                   code="SOURCE_CONTEXT_UNRESOLVED", status_code=422,
                                   details={"unit_id": unit.id, "reference": match[1]})
            refs.append(definitions[0].id)
    return refs


def structure_chunks(markdown: str, manifest: UnitManifest, *, max_chars: int = 6000,
                     chunker: Any = None, chunk_config: dict | None = None,
                     context_graph: dict | None = None) -> list[dict]:
    """Rows retain headers/notes; lists retain parents; fenced formulae stay whole.

    Structural groups override a strategy's preferred size, never its hard budget.
    Oversize dependencies need review rather than truncation or guessed semantics.
    """
    validate_manifest(manifest, markdown)
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars <= 0:
        raise AppException("Giới hạn đoạn phải là số nguyên dương.", code="INVALID_CHUNK_BUDGET", status_code=422)
    if context_graph:
        from app.modules.knowledge.services.source_links import validate_context_graph

        validate_context_graph(context_graph, manifest)
    units = [unit for unit in manifest.units if not unit.is_container]
    by_id = {unit.id: unit for unit in manifest.units}
    protected = _protected_ranges(markdown)
    # Older unit manifests may classify a literal '# heading' inside a fence as
    # document structure. Keep that manifest intact, but not in embedding context.
    headings = []
    paths = {}
    for unit in units:
        inside = any(start <= unit.start < end for start, end, _ in protected)
        if unit.kind == "heading" and not inside:
            depth = len(unit.text) - len(unit.text.lstrip("#"))
            headings = [(level, heading) for level, heading in headings if level < depth]
            headings.append((depth, unit))
        paths[unit.id] = unit.heading_path if unit.qnu_block_id else [heading.text for _, heading in headings]
    digest = manifest_digest(manifest)
    result = []
    index = 0
    while index < len(units):
        first = units[index]
        finish = index + 1
        kind = first.kind
        refs = []
        block = next((block for block in protected if first.start < block[1] and first.end > block[0]), None)
        if block:
            kind = block[2]
            while finish < len(units) and units[finish].start < block[1]:
                finish += 1
            if kind == "formula":
                # A following paragraph and its definition list are retained as
                # context, without deciding whether their semantics are correct.
                if (finish < len(units) and units[finish].kind == "paragraph"
                        and _same_scope(first, units[finish]) and not _in_block(units[finish], protected)):
                    finish += 1
                while (finish < len(units) and units[finish].kind == "list" and _same_scope(first, units[finish])
                       and not _in_block(units[finish], protected)):
                    finish += 1
        elif first.kind == "list":
            while (finish < len(units) and units[finish].kind == "list"
                   and _same_scope(first, units[finish]) and _indent(markdown, units[finish]) > _indent(markdown, first)):
                finish += 1
        if kind in {"list", "formula"} and index > 0:
            previous = units[index - 1]
            if (previous.kind == "paragraph" and _same_scope(first, previous) and not _in_block(previous, protected)
                    and (kind == "formula" or previous.text.rstrip().endswith(":"))):
                refs.append(previous.id)
            if kind == "list":
                # All ancestors, not merely the preceding sibling.
                depth = _indent(markdown, first)
                cursor = index - 1
                while cursor >= 0 and units[cursor].kind == "list" and _same_scope(first, units[cursor]):
                    if _indent(markdown, units[cursor]) < depth:
                        refs.insert(0, units[cursor].id)
                        depth = _indent(markdown, units[cursor])
                    cursor -= 1
                if cursor >= 0 and units[cursor].kind == "paragraph" and _same_scope(first, units[cursor]) and units[cursor].text.endswith(":"):
                    refs.insert(0, units[cursor].id)
        group = units[index:finish]
        for unit in group:
            refs.extend((context_graph or {}).get("links", {}).get(unit.id, []))
        if kind != "code":
            refs.extend(_footnote_refs([*group, *[by_id[ref] for ref in refs]], units))
        refs = list(dict.fromkeys(refs))
        # Use exact source slice, retaining nested indentation and blank lines.
        start, end = first.start, group[-1].end
        view = markdown[start:end]
        views = [(view, start, end)]
        if kind == "paragraph" and len(group) == 1 and chunker is not None:
            views = []
            covered = 0
            for draft in chunker.chunk(view, **(chunk_config or {})):
                part = draft.content
                at = view.find(part, max(0, covered - len(part))) if part else -1
                if at < 0 or view[covered:at].strip():
                    raise AppException("Chiến lược làm đổi hoặc bỏ nội dung nguồn.", code="CHUNK_SOURCE_MISMATCH", status_code=422)
                covered = max(covered, at + len(part))
                views.append((part, start + at, start + at + len(part)))
            if not views or view[covered:].strip():
                raise AppException("Chiến lược bỏ nội dung nguồn.", code="CHUNK_SOURCE_MISMATCH", status_code=422)
        for text, span_start, span_end in views:
            projection = (context_graph or {}).get("row_projections", {}).get(first.id, "")
            parts = [*paths[first.id], first.header_context, *[by_id[ref].text for ref in refs], text, projection]
            content = "\n\n".join(dict.fromkeys(part for part in parts if part)).strip()
            if len(content) > max_chars:
                raise AppException("Cấu trúc kèm điều kiện quá dài; cần duyệt cách chia trước khi nạp vector.",
                                   code="SOURCE_UNIT_TOO_LARGE", status_code=422,
                                   details={"unit_id": first.id, "kind": kind, "characters": len(content), "max_chars": max_chars})
            metadata = {"source_unit_version": manifest.version, "source_unit_id": first.id,
                        "source_unit": first.model_dump(), "unit_manifest_hash": digest,
                        "chunk_structure_version": CHUNK_VERSION, "structure_kind": kind,
                        "source_unit_ids": [unit.id for unit in group],
                        "source_units": [unit.model_dump() for unit in group],
                        "source_span": {"start": span_start, "end": span_end}, "context_unit_ids": refs}
            if context_graph:
                metadata["context_graph_hash"] = context_graph["digest"]
            if manifest.semantic_annotation_hash:
                metadata["semantic_annotation_hash"] = manifest.semantic_annotation_hash
            result.append({"index": len(result), "content": content,
                           "chunk_hash": hashlib.sha256(content.encode()).hexdigest(),
                           "token_count": max(1, len(content) // 3), "section": " / ".join(paths[first.id]),
                           "page_number": first.page_number, "metadata": metadata})
        index = finish
    return result
