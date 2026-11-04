"""Source-backed reading scopes, independent of compiler part/page boundaries.

These scopes describe available structural coverage, not semantic truth or an
exhaustive search of the collection. Source text is never interpreted as commands.
"""

import re
import unicodedata

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.domains.knowledge.index.schemas import SearchHit
from qnu.domains.knowledge.publication.evidence import VersionBundle
from qnu.domains.knowledge.source_sections import source_sections

VERSION = "qnu.rag.structure/v2"
_ARTICLE = re.compile(r"^(?:điều|article|section)\s+(\d+[a-zđ]?)\s*[.:]\s*\S", re.IGNORECASE)
_CHAPTER = re.compile(
    r"^(?:chương|chapter|phần|part|phụ\s+lục|appendix|annex)\s+(?:[IVXLCDM]+|\d+|[A-Z])\b",
    re.IGNORECASE,
)
_ENUMERATION = re.compile(
    r"\b(?:những|các|liệt kê|bao gồm|gồm|toàn bộ|tất cả|"
    r"list|requirements|conditions|steps|all)\b",
    re.IGNORECASE,
)
_REFERENCE = re.compile(r"\b(?:điều|article|section)\s+(\d+[a-zđ]?)\b", re.IGNORECASE)
_POINT = re.compile(r"^(?:[a-zđ]\)|\d+[.)])\s+\S", re.IGNORECASE)
_BULLET = re.compile(r"^[+•●▪–—-]\s+\S")
_TOPIC_REQUEST = re.compile(
    r"^(?:(?:xin|vui lòng)\s+)?(?:cho\s+(?:(?:tôi|em|mình)\s+)?biết|tra cứu|tìm hiểu)\s+",
    re.IGNORECASE,
)


def needs_structure(question: str) -> bool:
    return bool(
        _ENUMERATION.search(question)
        or _REFERENCE.search(question)
        or _TOPIC_REQUEST.match(question.strip())
    )


def enumeration_requested(question: str) -> bool:
    return bool(_ENUMERATION.search(question))


def unresolved_references(question: str, groups: list[dict]) -> list[str]:
    return sorted(
        {r.casefold() for r in _REFERENCE.findall(question)}
        - {g["reference"] for g in groups if g.get("reference")}
    )


def _owners(rows: list[IndexChunk], input_id: str, document: dict) -> dict[str, list[str]]:
    owners = {}
    for row in rows:
        if row.input_id != input_id:
            continue
        for ref, locator in row.citations.items():
            if locator.get("run_id") != document["ocr_run_id"]:
                continue
            if (
                document.get("canonical_sha256")
                and locator.get("canonical_sha256") != document["canonical_sha256"]
            ):
                continue
            if (
                document.get("identity", {}).get("revision_id")
                and locator.get("revision_id") != document["identity"]["revision_id"]
            ):
                continue
            owners.setdefault(ref, []).append(row.id)
    return owners


def _terms(text: str) -> set[str]:
    # Linguistic stopwords only; no corpus titles, majors, years or answer keywords.
    ignored = {
        "theo",
        "quy",
        "chế",
        "những",
        "các",
        "gì",
        "nào",
        "năm",
        "của",
        "và",
        "là",
        "phải",
        "được",
        "cho",
        "the",
        "of",
        "and",
        "what",
        "which",
    }
    return {
        t
        for t in re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", text).casefold())
        if t not in ignored
    }


def _records(document: dict, owners: dict) -> list[dict]:
    records = []
    run = document["ocr_run_id"]
    sections = source_sections([document])
    for page in document["pages"]:
        for block in page["blocks"]:
            text = (block.get("text") or "").strip()
            ref = run + ":" + block["evidence_id"]
            is_table = bool(block.get("table")) or block.get("type") == "table"
            if not is_table and (not text or text.isdecimal()):
                continue
            records.append(
                {
                    "text": text,
                    "ref": ref,
                    "ids": owners.get(ref, []),
                    "section": sections[ref].citation,
                    "is_table": is_table,
                }
            )
    return records


def _bullet_group(records: list[dict], start: int) -> list[dict]:
    heading = records[start]
    if heading["ref"] != heading["section"]:
        return []
    group = [heading]
    bullets = 0
    for record in records[start + 1 :]:
        if (
            record["section"] != heading["ref"]
            or record["is_table"]
            or _POINT.match(record["text"])
        ):
            break
        if _BULLET.match(record["text"]):
            bullets += 1
        elif not bullets:
            break
        group.append(record)
    return group if bullets >= 2 else []


def _groups(records: list[dict]) -> list[tuple[str, list[dict]]]:
    groups = []
    for index, record in enumerate(records):
        text = record["text"]
        if _ARTICLE.match(text):
            stop = next(
                (
                    j
                    for j in range(index + 1, len(records))
                    if _ARTICLE.match(records[j]["text"]) or _CHAPTER.match(records[j]["text"])
                ),
                len(records),
            )
            groups.append(("article", records[index:stop]))
        if text.endswith(":"):
            bullets = _bullet_group(records, index)
            if bullets:
                groups.append(("bullet_list", bullets))
            stop = index + 1
            numbered = stop < len(records) and records[stop]["text"][:1].isdigit()
            while (
                stop < len(records)
                and _POINT.match(records[stop]["text"])
                and (records[stop]["text"][0].isdigit() == numbered)
            ):
                stop += 1
            if stop >= index + 3:
                groups.append(("list", records[index:stop]))
    return groups


def _candidate(kind, group, input_id, hit, primary, references, question):
    ids = list(dict.fromkeys(key for record in group for key in record["ids"]))
    title = group[0]["text"]
    article = _ARTICLE.match(title)
    explicit = bool(article and article[1].casefold() in references)
    anchors = primary.keys() & set(ids)
    if not anchors and not explicit:
        return None
    if explicit and not anchors:
        anchors = {hit.chunk_id}
    terms = _terms(question)
    title_terms = _terms(title)
    overlap = len(terms & title_terms)
    asks_list = enumeration_requested(question)
    if kind == "bullet_list":
        topic = _TOPIC_REQUEST.sub("", question.strip())
        exact_topic = _terms(topic) == title_terms
        if not title_terms or (not exact_topic and not (asks_list and title_terms <= terms)):
            return None
    elif not asks_list and not references:
        return None
    if (
        kind == "article"
        and not explicit
        and (overlap < 2 or overlap / max(1, len(_terms(title))) < 0.6)
    ):
        return None
    if kind == "list" and (not overlap or overlap / max(1, len(_terms(title))) < 0.5):
        return None
    if references and not explicit:
        return None
    priority = (
        0 if explicit else 1 if kind == "bullet_list" else 2,
        0 if kind == "article" else 1,
        min(primary[key] for key in anchors),
        -overlap,
    )
    return priority, {
        "kind": kind,
        "reference": article[1].casefold() if article else None,
        "label": title,
        "input_id": input_id,
        "primary_chunk_id": min(anchors, key=primary.get),
        "required_ids": ids,
        "units": [
            {"ref": r["ref"], "chunk_ids": r["ids"]}
            for r in group[1:]
            if kind == "bullet_list" or (asks_list and not r["text"].endswith((":", "：")))
        ],
        "unindexed_refs": [r["ref"] for r in group if not r["ids"]],
    }


def _candidates(rows, hits, bundles, question, references):
    primary = {hit.chunk_id: rank for rank, hit in enumerate(hits)}
    by_id = {row.id: row for row in rows}
    candidates = []
    visited = set()
    for hit in hits:
        input_id = by_id[hit.chunk_id].input_id
        identity = (input_id, hit.version_id)
        if identity in visited:
            continue
        visited.add(identity)
        for document in bundles[hit.version_id].documents:
            owners = _owners(rows, input_id, document)
            for kind, group in _groups(_records(document, owners)):
                candidate = _candidate(kind, group, input_id, hit, primary, references, question)
                if candidate is not None:
                    candidates.append(candidate)
    return candidates


def select_groups(
    rows: list[IndexChunk], hits: list[SearchHit], bundles: dict[str, VersionBundle], question: str
) -> list[dict]:
    """Resolve only within the authorized, pinned inputs which already produced hits."""
    references = {r.casefold() for r in _REFERENCE.findall(question)}
    candidates = _candidates(rows, hits, bundles, question, references)
    if not candidates:
        return []
    if references:
        return [
            min(
                (c for c in candidates if c[1]["reference"] == reference), key=lambda pair: pair[0]
            )[1]
            for reference in sorted(references)
            if any(c[1]["reference"] == reference for c in candidates)
        ]
    # One anchored scope, not a claim that other sources/chapters do not exist.
    return [min(candidates, key=lambda pair: pair[0])[1]]
