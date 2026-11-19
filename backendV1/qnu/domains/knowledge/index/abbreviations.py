"""Deterministic, source-bound abbreviation catalog for lexical alias expansion.

Only explicit evidence is mined: parenthetical pairs already used by search-context,
and table rows whose short uppercase alias spells the initials of its whole cell pair.
No model call, no hand-written domain dictionary, no scope or answer change.
"""

from __future__ import annotations

import re
from collections import defaultdict

from qnu.domains.knowledge.index.query_scope import mentions
from qnu.domains.knowledge.publication.evidence import digest

VERSION = "qnu.index-abbreviations/v1"
MAX_ENTRIES = 256
MAX_QUERY_EXPANSIONS = 8
MAX_EXPANDED_QUERY = 8000

_PARENTHETICAL = re.compile(r"([^\n.;:!?()]{3,160})\s*\(([A-ZÀ-ỴĐ][A-ZÀ-ỴĐ0-9-]{1,15})\)")
_ALIAS = re.compile(r"[A-ZÀ-ỴĐ][A-ZÀ-ỴĐ0-9-]{1,15}")


def parenthetical(content: dict, documents: list[dict]) -> list[dict]:
    definitions = {}
    citations = content.get("citations") or content.get("index") or {}
    # Definitions must themselves be reachable through the pinned citation map.
    for document in documents:
        for page in document["pages"]:
            for block in page["blocks"]:
                citation = document["ocr_run_id"] + ":" + block["evidence_id"]
                if citation not in citations:
                    continue
                for match in _PARENTHETICAL.finditer(block["text"]):
                    expansion, alias = match.groups()
                    expansion = expansion.strip()
                    words = expansion.split()[-len(alias) :]
                    expansion = " ".join(words)
                    # Match initials exactly; never interpret a cohort code/year or
                    # consume a whole preceding sentence as an invented definition.
                    initials = "".join(w[0] for w in words).casefold()
                    if (
                        not alias.isupper()
                        or initials != alias.casefold()
                        or not 2 <= len(words) <= 12
                    ):
                        continue
                    entry = {
                        "alias": alias,
                        "expansion": expansion,
                        "citation": citation,
                        "quote": match.group(0)[match.group(0).find(words[0]) :],
                    }
                    definitions[digest(entry)] = entry
    return [definitions[key] for key in sorted(definitions)]


def _defines(alias: str, expansion: str) -> str | None:
    words = expansion.split()
    if not 2 <= len(words) <= 12:
        return None
    if "".join(word[0] for word in words).casefold() != alias.casefold():
        return None
    text = " ".join(words)
    return text if 3 <= len(text) <= 160 else None


def _table_rows(content: dict) -> list[dict]:
    definitions = {}
    citations = content.get("citations") or content.get("index") or {}
    for table in (content.get("source_tables") or content.get("tables") or []):
        body = table["table"]
        if body.get("status") != "parsed" or not body.get("rows"):
            continue
        run_id = table["citation"].split(":", 1)[0]
        for row in body["rows"]:
            cells = [
                cell for cell in row if not cell.get("header") and cell.get("text", "").strip()
            ]
            for alias_cell in cells:
                alias = alias_cell["text"].strip()
                if not _ALIAS.fullmatch(alias):
                    continue
                alias_citation = run_id + ":" + alias_cell["evidence_id"]
                if alias_citation not in citations:
                    continue
                for meaning in cells:
                    if meaning is alias_cell:
                        continue
                    expansion = _defines(alias, meaning["text"].strip())
                    if expansion is None:
                        continue
                    meaning_citation = run_id + ":" + meaning["evidence_id"]
                    if meaning_citation not in citations:
                        continue
                    entry = {
                        "alias": alias,
                        "expansion": expansion,
                        "citation": meaning_citation,
                        "quote": meaning["text"],
                    }
                    definitions[digest(entry)] = entry
    return [definitions[key] for key in sorted(definitions)]


def _catalog(entries: list[dict]) -> dict:
    unique = {}
    for entry in entries:
        unique.setdefault(digest(entry), entry)
    ordered = [unique[key] for key in sorted(unique)]
    return {
        "version": VERSION,
        "definitions": ordered[:MAX_ENTRIES],
        "truncated": len(ordered) > MAX_ENTRIES,
    }


def mine(content: dict, documents: list[dict]) -> dict:
    return _catalog([*parenthetical(content, documents), *_table_rows(content)])


def merge(catalogs) -> dict:
    entries = [
        entry
        for catalog in catalogs
        if isinstance(catalog, dict) and catalog.get("version") == VERSION
        for entry in catalog.get("definitions") or []
    ]
    return _catalog(entries)


def expand(query: str, catalog) -> tuple[str, dict]:
    """Return the original query plus alias expansions; never modify the question itself."""
    if not isinstance(catalog, dict) or catalog.get("version") != VERSION:
        return query, {}
    candidates = defaultdict(set)
    for entry in catalog.get("definitions") or []:
        alias, expansion = entry.get("alias"), entry.get("expansion")
        if isinstance(alias, str) and isinstance(expansion, str) and mentions(query, alias):
            candidates[alias].add(expansion)
    applied, ambiguous, truncated = [], [], False
    for alias in sorted(candidates):
        values = candidates[alias]
        if len(values) > 1:
            ambiguous.append(alias)
            continue
        expansion = next(iter(values))
        if mentions(query, expansion):
            continue
        used = len(query) + sum(len(item["expansion"]) + 3 for item in applied)
        if len(applied) == MAX_QUERY_EXPANSIONS or used + len(expansion) + 3 > MAX_EXPANDED_QUERY:
            truncated = True
            continue
        applied.append({"alias": alias, "expansion": expansion})
    text = query + ("\n" + " | ".join(item["expansion"] for item in applied) if applied else "")
    return text, {
        "version": VERSION,
        "applied": applied,
        "ambiguous": ambiguous,
        "truncated": truncated,
    }
