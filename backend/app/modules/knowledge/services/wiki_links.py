"""Deterministic navigation over exact source mentions; never entity resolution."""

import re
import unicodedata
from collections import defaultdict, deque
from itertools import combinations

from app.core.exceptions import AppException
from app.modules.knowledge.services.wiki_compiler import digest

LINK_POLICY = "qnu-wiki-links/v1"
MAX_PAGES = 2048
MAX_LINKS = 8192
MAX_REFERENCES = 100000


def link_error(reason: str) -> AppException:
    return AppException("Liên kết tri thức không khớp bản nguồn đang xem.",
                        code="KNOWLEDGE_WIKI_LINK_BUDGET" if "budget" in reason else "KNOWLEDGE_WIKI_LINK_INVALID",
                        status_code=422 if "budget" in reason else 409,
                        details={"reason": reason})


def page_references(page: dict) -> list[dict]:
    return [ref for section in page["sections"] for ref in [*section["references"],
            *(ref for scope in section["temporal"] for ref in scope["references"])]]


def literal_mention(label: str, text: str) -> bool:
    """Match literal words/codes, including combining marks, without normalization."""
    separators = "_-/" + ("." if any(char.isdigit() for char in label) else "")

    def attached(char: str) -> bool:
        return char.isalnum() or unicodedata.category(char).startswith("M") or char in separators

    return any((match.start() == 0 or not attached(text[match.start() - 1]))
        and (match.end() == len(text) or not attached(text[match.end()]))
        for match in re.finditer(re.escape(label), text))


def build_page_links(pages: list[dict], snapshot_key: str) -> dict:
    """Inputs must already be authorized and validated against the pinned source.

    A shared label proves co-mention only if it occurs literally in evidence at
    both ends. Same code/different labels are advisory alias candidates only.
    No normalization, title similarity, or filename date can establish identity.
    """
    if len(pages) > MAX_PAGES:
        raise link_error("page_budget")
    if len({p["id"] for p in pages}) != len(pages):
        raise link_error("duplicate_page")
    if sum(len(page_references(p)) for p in pages) > MAX_REFERENCES:
        raise link_error("reference_budget")
    collections = {p.get("collection_id") or p.get("identity", {}).get("collection_id") for p in pages}
    if len(collections - {None}) > 1:
        raise link_error("collection_scope")
    nodes = {p["id"]: p for p in pages}
    edges: dict[str, dict] = {}
    edge_references = 0

    def add(left: dict, right: dict, relation: str, status: str, basis: str) -> None:
        nonlocal edge_references
        identity = [LINK_POLICY, snapshot_key, left["id"], right["id"], relation]
        eid = "wikilink_" + digest(identity)[:24]
        if eid in edges:
            return
        edge_references += len(page_references(left)) + len(page_references(right))
        if edge_references > MAX_REFERENCES:
            raise link_error("edge_reference_budget")
        edges[eid] = {"id": eid, "source": left["id"], "target": right["id"],
            "collection_id": endpoint_identity(left)["collection_id"],
            "relation": relation, "status": status, "basis": basis,
            "policy_version": LINK_POLICY, "snapshot": snapshot_key,
            "endpoints": [endpoint(left), endpoint(right)]}
        if len(edges) > MAX_LINKS:
            raise link_error("link_budget")

    sources = {p["binding_id"]: p for p in pages if p["kind"] == "source" and p.get('part', 1) == 1}
    labels: dict[tuple, list[dict]] = defaultdict(list)
    codes: dict[str, list[dict]] = defaultdict(list)
    for page in sorted(pages, key=lambda p: p["id"]):
        target = nodes.get(page.get('next_page_id'))
        if target:
            if (endpoint_identity(target) != endpoint_identity(page)
                    or target['kind'] != page['kind'] or target['title'] != page['title']):
                raise link_error('continuation_scope')
            add(page, target, 'continuation', 'structural', 'complete_source_inventory')
        if page["kind"] == "source":
            continue
        source = sources.get(page["binding_id"])
        if source and source["source_revision_id"] == page["source_revision_id"]:
            add(page, source, "source_reference", "structural", "pinned_source_units")
        labels[(page["kind"], page["title"])].append(page)
        for code in dict.fromkeys(item["code"] for item in page.get("mentions", [])):
            codes[code].append(page)
    for (_, label), group in sorted(labels.items()):
        for left, right in combinations(group, 2):
            if left["binding_id"] == right["binding_id"]:
                continue
            proved = all(any(literal_mention(label, ref["quote"]) for ref in page_references(p)) for p in (left, right))
            add(left, right, "co_mention" if proved else "same_entity",
                "structural" if proved else "candidate", label)
    for code, group in sorted(codes.items()):
        for left, right in combinations(group, 2):
            if left["binding_id"] != right["binding_id"] and left["title"] != right["title"]:
                add(left, right, "alias", "candidate", code)
    outgoing = {pid: [] for pid in nodes}
    backlinks = {pid: [] for pid in nodes}
    for edge in sorted(edges.values(), key=lambda e: e["id"]):
        outgoing[edge["source"]].append(edge["id"])
        backlinks[edge["target"]].append(edge["id"])
    result = {"version": LINK_POLICY, "snapshot": snapshot_key, "usage": "navigation_only",
              "links": sorted(edges.values(), key=lambda e: e["id"]),
              "outgoing": outgoing, "backlinks": backlinks,
              "evidence": {reference_id(page, ref): {**endpoint_identity(page), **ref,
                  **page.get("reference_locations", {}).get(ref["unit_id"], {})}
                  for page in pages for ref in page_references(page)}}
    return {**result, "sha256": digest(result)}


def endpoint_identity(page: dict) -> dict:
    return {"collection_id": page.get("collection_id") or page.get("identity", {}).get("collection_id"),
            **{key: page.get(key) for key in
               ("binding_id", "source_revision_id", "index_revision_id", "canonical_hash")}}


def reference_id(page: dict, ref: dict) -> str:
    return "wikiref_" + digest([endpoint_identity(page), ref])[:24]


def endpoint(page: dict) -> dict:
    return {"page_id": page["id"], **endpoint_identity(page),
        "sections": [{"reference_ids": [reference_id(page, ref) for ref in section["references"]],
            "temporal": [{"role": scope["role"], "years": scope["years"],
                "reference_ids": [reference_id(page, ref) for ref in scope["references"]]}
                for scope in section["temporal"]],
            "conditions": section["conditions"], "exceptions": section["exceptions"]}
            for section in page["sections"]]}


def validate_page_links(graph: dict, pages: list[dict], snapshot_key: str) -> None:
    if graph != build_page_links(pages, snapshot_key):
        raise link_error("graph_changed_or_stale")


def expand_linked_pages(selected: list[dict], pages: list[dict], graph: dict, *,
                        max_depth: int, max_nodes: int, max_edges: int) -> list[dict]:
    """BFS over structural cross-source co-mentions; no extra model/tool calls.

    The caller supplies only query-compatible pages and enforces character/time
    budgets. Canonical closure and final verification still own answer evidence.
    """
    by_id = {p["id"]: p for p in pages}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for link in graph["links"]:
        if link["status"] == "structural" and link["relation"] == "co_mention":
            if link["source"] not in by_id or link["target"] not in by_id:
                raise link_error("missing_endpoint")
            adjacency[link["source"]].append(link["target"])
            adjacency[link["target"]].append(link["source"])
    result = list({p["id"]: p for p in selected}.values())
    if len(result) > max_nodes:
        return []  # Reject the whole selection; never slice away a source's closure.
    seen = {p["id"] for p in result}
    pending = deque((p["id"], 0) for p in result)
    visited_edges = 0
    while pending and len(result) < max_nodes:
        pid, depth = pending.popleft()
        if depth >= max_depth:
            continue
        for target in sorted(adjacency[pid]):
            if visited_edges >= max_edges or len(result) >= max_nodes:
                return result
            visited_edges += 1
            if target not in seen:
                seen.add(target)
                result.append(by_id[target])
                pending.append((target, depth + 1))
    return result
