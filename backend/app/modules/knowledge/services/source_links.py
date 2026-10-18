"""Context-only, source-bound table relations; never infer data-year applicability."""

import hashlib
import json
import re
from typing import Any

from app.modules.knowledge.normalization.retrieval_models import SourceUnit, UnitManifest
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.table_context import extract_context_tables

VERSION = "source-context-v1"


def graph_digest(graph: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps({key: value for key, value in graph.items() if key != "digest"},
                                    sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _ordinal(unit: SourceUnit) -> int | None:
    first = _split_gfm_row(unit.text)[0].strip()
    return int(first.rstrip(".)")) if re.fullmatch(r"\d+[.)]?", first) else None


def _same_family(previous: list[SourceUnit], current: list[SourceUnit], between: list[SourceUnit]) -> bool:
    return bool(not between and previous and current and previous[0].page_number is not None
        and current[0].page_number == previous[-1].page_number + 1
        and previous[0].header_context == current[0].header_context
        and _ordinal(previous[-1]) is not None and _ordinal(current[-1]) is not None
        and len(current) > 1 and _ordinal(current[1]) == _ordinal(previous[-1]) + 1)


def build_context_graph(manifest: UnitManifest) -> dict[str, Any]:
    units = manifest.units
    if any(unit.qnu_block_id for unit in units):
        by_id = {unit.id: unit for unit in units}
        links = {}
        for unit in units:
            pending, seen = list(unit.context_refs), set()
            while pending:
                ref = pending.pop()
                if ref not in by_id or ref == unit.id:
                    raise ValueError("Invalid or cyclic standard context reference")
                if ref in seen:
                    continue
                seen.add(ref)
                pending.extend(by_id[ref].context_refs)
            links[unit.id] = sorted(seen, key=lambda ref: by_id[ref].start)
        graph = {"version": VERSION, "canonical_hash": manifest.canonical_hash, "status": "context_only",
                 "links": links, "row_projections": {}}
        graph["digest"] = graph_digest(graph)
        return graph
    containers = [unit for unit in units if unit.is_container and unit.kind == "table"]
    families: list[list[SourceUnit]] = []
    for container in containers:
        children = [unit for unit in units if unit.parent_id == container.id]
        if not children:
            continue
        prior = families[-1] if families else []
        between = [unit for unit in units if prior and prior[-1].end <= unit.start < container.start
                   and not unit.is_container and unit not in prior]
        if _same_family(prior, children, between):
            prior.extend(children)
        else:
            families.append(children)
    links, projections = {}, {}
    for family in families:
        first, last = family[0], family[-1]
        preceding = [unit for unit in units if unit.end <= first.start and unit.kind != "table"]
        # A new structural heading bounds scope. Context is a hint, never an authority override.
        boundary = max([0, *(unit.start for unit in preceding if unit.kind == "heading"),
                        *(unit.end for unit in containers if unit.end <= first.start)])
        intro = [unit.id for unit in preceding if unit.start >= boundary][-3:]
        next_table = min((unit.start for unit in containers if unit.start > last.end), default=float("inf"))
        following = [unit for unit in units if last.end <= unit.start < next_table
                     and unit.kind != "table" and not unit.is_container]
        notes = []
        caption = bool(following and len(following[0].text) <= 120 and following[0].text.rstrip().endswith(":"))
        numbered = bool(following and following[0].kind == "list" and re.match(r"^\s*1[.)]\s", following[0].text))
        if caption or numbered:
            for unit in following:
                letters = [char for char in unit.text if char.isalpha()]
                upper_heading = len(unit.text) <= 120 and letters and all(char.isupper() for char in letters)
                next_caption = bool(notes and len(unit.text) <= 120 and unit.text.rstrip().endswith(":"))
                if (unit.kind == "heading" or upper_heading or next_caption
                        or sum(len(item.text) for item in notes) + len(unit.text) > 8000):
                    break
                notes.append(unit)
        for member in family:
            headers = [unit for unit in family if unit.text == member.header_context
                       and (unit.parent_id == member.parent_id or unit.id == family[0].id)]
            links[member.id] = list(dict.fromkeys(ref for ref in [*intro, *(unit.id for unit in headers),
                                                   *(unit.id for unit in notes)] if ref != member.id))
            cells = _split_gfm_row(member.text)
            parsed = extract_context_tables(member.header_context, 1)
            labels = parsed[0]["headers"] if parsed else _split_gfm_row(member.header_context.splitlines()[0])
            if len(cells) == len(labels) and member.text != member.header_context:
                projections[member.id] = " | ".join(f"{label}: {value}" for label, value in
                    zip(labels, cells, strict=True) if label.strip() and value.strip())
    graph = {"version": VERSION, "canonical_hash": manifest.canonical_hash, "status": "context_only",
             "links": links, "row_projections": projections}
    graph["digest"] = graph_digest(graph)
    return graph


def attach_fact_context(facts: list[dict[str, Any]], manifest: UnitManifest, graph: dict[str, Any]) -> None:
    rows: dict[tuple, list[SourceUnit]] = {}
    for unit in manifest.units:
        if unit.kind == "table" and not unit.is_container and unit.text != unit.header_context:
            rows.setdefault((unit.page_number, tuple(_split_gfm_row(unit.text))), []).append(unit)
    for fact in facts:
        raw = fact["raw_data"]
        matches = rows.get((raw["page_number"], tuple(raw["row_values"])),
                           rows.get((None, tuple(raw["row_values"])), []))
        # Identical rows in unrelated tables cannot be assigned by last-write-wins.
        if len(matches) == 1:
            unit = matches[0]
            raw["source_unit_id"] = unit.id
            raw["context_unit_ids"] = graph["links"].get(unit.id, [])
            raw["context_graph_hash"] = graph["digest"]


def validate_context_graph(graph: dict[str, Any], manifest: UnitManifest) -> None:
    if not isinstance(graph, dict):
        raise TypeError("Context graph must be an object")
    if (graph.get("version") != VERSION or graph.get("canonical_hash") != manifest.canonical_hash
            or graph.get("status") != "context_only" or graph.get("digest") != graph_digest(graph)):
        raise ValueError("Context graph does not match source/hash/version")
    by_id = {unit.id: unit for unit in manifest.units}
    if any(unit_id not in by_id or any(ref not in by_id for ref in refs)
           for unit_id, refs in graph.get("links", {}).items()):
        raise ValueError("Context graph references an unknown source unit")
    # Rebuild from exact units: an altered projection/link must not become citable source text.
    if graph != build_context_graph(manifest):
        raise ValueError("Context graph is not the deterministic source projection")
