"""Source-backed reading scopes, independent of compiler part/page boundaries.

These scopes describe available structural coverage, not semantic truth or an
exhaustive search of the collection. Source text is never interpreted as commands.
"""

import re
import unicodedata

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.domains.knowledge.index.schemas import SearchHit
from qnu.domains.knowledge.metadata import matches_metadata
from qnu.domains.knowledge.publication.evidence import VersionBundle
from qnu.domains.knowledge.source_sections import source_sections

VERSION = "qnu.rag.structure/v6"
FURNITURE_TYPES = {"header", "footer"}
FURNITURE_LABELS = {"header", "page-header", "page_header", "footer", "page-footer", "page_footer"}
FURNITURE_MAX_CHARS = 240
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
_NUMBERED = re.compile(r"^(\d{1,2})[.)]\s+\S")
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
            if not isinstance(locator, dict):
                continue
            if locator.get("run_id") != document.get("ocr_run_id"):
                continue
            if (
                document.get("canonical_sha256")
                and locator.get("canonical_sha256") != document["canonical_sha256"]
            ):
                continue
            doc_identity = document.get("identity") or {}
            rev_id = doc_identity.get("revision_id")
            if rev_id and locator.get("revision_id") != rev_id:
                continue
            owners.setdefault(ref, []).append(row.id)
    return owners


def content_terms(text: str) -> set[str]:
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
            is_table = bool(block.get("table")) or block.get("type") in {"table", "figure"}
            if not is_table and (not text or text.isdecimal()):
                continue
            furniture = not is_table and (
                (block.get("type") or "").casefold() in FURNITURE_TYPES
                or (block.get("label") or "").casefold() in FURNITURE_LABELS
            )
            records.append(
                {
                    "text": text,
                    "ref": ref,
                    "ids": owners.get(ref, []),
                    "section": sections[ref].citation,
                    "is_table": is_table,
                    "page": page["page_number"],
                    "furniture": furniture,
                }
            )
    _mark_repeats(records)
    return records


def _record_key(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split()).casefold()


def _mark_repeats(records: list[dict]) -> None:
    """Map an exact repeated page header/footer to its first copy; content text never merges."""
    first: dict[str, dict] = {}
    for record in records:
        if not record["furniture"] or len(record["text"]) > FURNITURE_MAX_CHARS:
            continue
        key = _record_key(record["text"])
        seen = first.get(key)
        if seen is None:
            first[key] = record
        elif seen["page"] != record["page"]:
            record["repeat_of"] = seen["ref"]


def _kept_records(records: list[dict], anchors: set[str]) -> tuple[list[dict], list[dict]]:
    """Drop repeated page furniture, but never the copy that carries a retrieved anchor."""
    kept, compressed = [], []
    for record in records:
        if record.get("repeat_of") and not set(record["ids"]) & anchors:
            compressed.append({"ref": record["ref"], "same_as": record["repeat_of"]})
            continue
        kept.append(record)
    return kept, compressed


_SUBHEADING = re.compile(r"^(?:[IVXLCDM]+|[A-Z])[.)]\s+\S")


def _bullet_group(records: list[dict], start: int) -> list[dict]:
    heading = records[start]
    if heading["is_table"] or _BULLET.match(heading["text"]):
        return []
    owner_section = heading["section"]
    group = [heading]
    bullets = 0
    trailing_prose = 0
    for record in records[start + 1 :]:
        text = record["text"]
        if (
            record["section"] != owner_section
            or record["is_table"]
            or _POINT.match(text)
            or _ARTICLE.match(text)
            or _CHAPTER.match(text)
            or _SUBHEADING.match(text)
            or text.endswith(":")
        ):
            break
        if _BULLET.match(text):
            bullets += 1
            trailing_prose = 0
            group.append(record)
        elif not bullets:
            break
        else:
            # Allow at most one continuation/note line directly after a bullet;
            # stop before swallowing subsequent unrelated prose paragraphs.
            trailing_prose += 1
            if trailing_prose > 1:
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
    all_ids = list(dict.fromkeys(key for record in group for key in record["ids"]))
    title = group[0]["text"]
    article = _ARTICLE.match(title)
    explicit = bool(article and article[1].casefold() in references)
    anchors = primary.keys() & set(all_ids)
    if not anchors and not explicit:
        return None
    if explicit and not anchors:
        anchors = {hit.chunk_id}
    kept, compressed = _kept_records(group, anchors)
    ids = list(dict.fromkeys(key for record in kept for key in record["ids"]))
    terms = content_terms(question)
    title_terms = content_terms(title)
    overlap = len(terms & title_terms)
    asks_list = enumeration_requested(question)
    if kind == "bullet_list":
        topic = _TOPIC_REQUEST.sub("", question.strip())
        exact_topic = content_terms(topic) == title_terms
        if not title_terms or (not exact_topic and not (asks_list and title_terms <= terms)):
            return None
    elif not asks_list and not references:
        return None
    if (
        kind == "article"
        and not explicit
        and (overlap < 2 or overlap / max(1, len(content_terms(title))) < 0.6)
    ):
        return None
    if kind == "list" and (not overlap or overlap / max(1, len(content_terms(title))) < 0.5):
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
            for r in kept[1:]
            if kind == "bullet_list" or asks_list
        ],
        "unindexed_refs": [r["ref"] for r in kept if not r["ids"]],
        "compressed_refs": compressed,
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


def _continues(left: dict, right: dict) -> bool:
    previous, following = left["text"].rstrip(), right["text"].lstrip()
    if (
        not previous
        or not following
        or left["is_table"]
        or right["is_table"]
        or previous.rstrip("\"”’')]} ").endswith((".", "!", "?", ";", ":", "：", "…"))
        or right["ref"] == right["section"]
        or _POINT.match(following)
        or _ARTICLE.match(following)
        or _CHAPTER.match(following)
        or _BULLET.match(following)
    ):
        return False
    return following[0].isalpha() or following[0].isdigit()


CONTINUATION_RECORDS = 6
CONTINUATION_CHARS = 6000


def _anchor_positions(records: list[dict], anchor_ids: set[str]) -> list[int]:
    return [index for index, record in enumerate(records) if set(record["ids"]) & anchor_ids]


def _continuation_window(records: list[dict], positions: list[int]) -> tuple[int, int] | None:
    first, last = positions[0], positions[-1]
    starts = first > 0 and _continues(records[first - 1], records[first])
    ends = last + 1 < len(records) and _continues(records[last], records[last + 1])
    if not starts and not ends:
        return None
    lo, hi = first, last
    chars = sum(len(record["text"]) for record in records[lo : hi + 1])
    backward = 3 if starts else 0
    forward = 3 if ends else 0
    while backward and lo > 0 and hi - lo + 1 < CONTINUATION_RECORDS:
        size = len(records[lo - 1]["text"])
        if chars + size > CONTINUATION_CHARS:
            break
        lo, chars, backward = lo - 1, chars + size, backward - 1
    while forward and hi + 1 < len(records) and hi - lo + 1 < CONTINUATION_RECORDS:
        size = len(records[hi + 1]["text"])
        if chars + size > CONTINUATION_CHARS:
            break
        hi, chars, forward = hi + 1, chars + size, forward - 1
    return lo, hi


def continuation_groups(rows: list[IndexChunk], hits: list[SearchHit], bundles: dict) -> list[dict]:
    """Complete only the clipped edge of an anchored sentence.

    A retrieved fragment inside a long unpunctuated OCR chain must not turn the
    whole chain into required evidence. The group is optional and bounded so
    packing can drop it instead of failing the request.
    """
    by_id = {row.id: row for row in rows}
    anchors = {hit.chunk_id: rank for rank, hit in enumerate(hits)}
    visited, groups = set(), []
    for hit in hits:
        identity = (by_id[hit.chunk_id].input_id, hit.version_id)
        bundle = bundles.get(hit.version_id)
        if identity in visited or bundle is None:
            continue
        visited.add(identity)
        anchor_ids = {key for key in anchors if by_id[key].input_id == identity[0]}
        for document in bundle.documents:
            records = _records(document, _owners(rows, identity[0], document))
            start = 0
            while start < len(records):
                stop = start + 1
                while stop < len(records) and _continues(records[stop - 1], records[stop]):
                    stop += 1
                chain = records[start:stop]
                positions = _anchor_positions(chain, anchor_ids)
                window = _continuation_window(chain, positions) if positions else None
                if window is None:
                    start = stop
                    continue
                lo, hi = window
                fragment = chain[lo : hi + 1]
                fragment_ids = list(
                    dict.fromkeys(key for record in fragment for key in record["ids"])
                )
                primary = anchors.keys() & set(fragment_ids)
                kept, compressed = _kept_records(fragment, primary)
                ids = list(dict.fromkeys(key for record in kept for key in record["ids"]))
                if len(fragment) > 1 and primary:
                    groups.append(
                        {
                            "kind": "continuation",
                            "label": fragment[0]["text"],
                            "input_id": identity[0],
                            "primary_chunk_id": min(primary, key=anchors.get),
                            "required_ids": ids,
                            "units": [{"ref": r["ref"], "chunk_ids": r["ids"]} for r in kept],
                            "unindexed_refs": [r["ref"] for r in kept if not r["ids"]],
                            "compressed_refs": compressed,
                            "optional": True,
                            "chain_records": len(chain),
                            "truncated": len(fragment) < len(chain),
                        }
                    )
                start = stop
    return groups


NUMBERED_RECORDS = 10
NUMBERED_CHARS = 6000


def _numbered_runs(records: list[dict]) -> list[list[dict]]:
    """Maximal runs of strictly consecutive numbered items and their continuation lines."""
    runs, index = [], 0
    while index < len(records):
        item = None if records[index]["is_table"] else _NUMBERED.match(records[index]["text"])
        if item is None:
            index += 1
            continue
        expected, stop = int(item[1]) + 1, index + 1
        while stop < len(records):
            record = records[stop]
            number = None if record["is_table"] else _NUMBERED.match(record["text"])
            if number is not None:
                if int(number[1]) != expected:
                    break
                expected, stop = expected + 1, stop + 1
                continue
            if (
                record["is_table"]
                or record["ref"] == record["section"]
                or _ARTICLE.match(record["text"])
                or _CHAPTER.match(record["text"])
                or _BULLET.match(record["text"])
                or not _continues(records[stop - 1], record)
            ):
                break
            stop += 1
        runs.append(records[index:stop])
        index = stop
    return runs


def numbered_groups(rows: list[IndexChunk], hits: list[SearchHit], bundles: dict) -> list[dict]:
    """Read an anchored numbered list whole, item by item.

    Only source-numbered items that increment by one belong to the run, so an
    unrelated paragraph cannot be pulled in as an item. The group is optional
    and bounded so packing can drop it instead of failing the request.
    """
    by_id = {row.id: row for row in rows}
    anchors = {hit.chunk_id: rank for rank, hit in enumerate(hits)}
    visited, groups = set(), []
    for hit in hits:
        identity = (by_id[hit.chunk_id].input_id, hit.version_id)
        bundle = bundles.get(hit.version_id)
        if identity in visited or bundle is None:
            continue
        visited.add(identity)
        anchor_ids = {key for key in anchors if by_id[key].input_id == identity[0]}
        for document in bundle.documents:
            records = _records(document, _owners(rows, identity[0], document))
            for run in _numbered_runs(records):
                if sum(_NUMBERED.match(record["text"]) is not None for record in run) < 2:
                    continue
                positions = _anchor_positions(run, anchor_ids)
                if not positions:
                    continue
                primary = anchor_ids & {key for record in run for key in record["ids"]}
                if not primary:
                    continue
                lo, hi = positions[0], positions[-1]
                chars = sum(len(record["text"]) for record in run[lo : hi + 1])
                while lo > 0 and hi - lo + 1 < NUMBERED_RECORDS:
                    size = len(run[lo - 1]["text"])
                    if chars + size > NUMBERED_CHARS:
                        break
                    lo, chars = lo - 1, chars + size
                while hi + 1 < len(run) and hi - lo + 1 < NUMBERED_RECORDS:
                    size = len(run[hi + 1]["text"])
                    if chars + size > NUMBERED_CHARS:
                        break
                    hi, chars = hi + 1, chars + size
                kept, compressed = _kept_records(run[lo : hi + 1], primary)
                units, current = [], []
                for record in kept:
                    if current and _NUMBERED.match(record["text"]):
                        units.append(current)
                        current = []
                    current.append(record)
                if current:
                    units.append(current)
                groups.append(
                    {
                        "kind": "continuation",
                        "basis": "numbered_list",
                        "label": run[0]["text"],
                        "input_id": identity[0],
                        "primary_chunk_id": min(primary, key=anchors.get),
                        "required_ids": list(
                            dict.fromkeys(key for record in kept for key in record["ids"])
                        ),
                        "units": [
                            {
                                "ref": unit[0]["ref"],
                                "chunk_ids": [key for record in unit for key in record["ids"]],
                            }
                            for unit in units
                        ],
                        "unindexed_refs": [r["ref"] for r in kept if not r["ids"]],
                        "compressed_refs": compressed,
                        "optional": True,
                        "list_items": len(units),
                        "truncated": len(kept) < len(run) or lo > 0 or hi + 1 < len(run),
                    }
                )
    return groups


MAX_TABLE_FAMILY_CHUNKS = 8


def _family_label(structure: dict) -> str:
    rows = structure.get("rows") or []
    header = [cell.get("text", "").strip() for cell in (rows[0] if rows else [])]
    label = " | ".join(text for text in header if text)
    return label[:120] or (structure.get("context") or {}).get("title") or "table"


def _family_order(row) -> tuple:
    indices = (row.structure or {}).get("row_indices") or []
    return (min(indices) if indices else 10**9, row.ordinal)


def table_family_groups(rows: list[IndexChunk], hits: list[SearchHit], scopes) -> list[dict]:
    """Every indexed chunk of the retrieved physical table, for enumeration/count reading.

    The family is the same published input and table citation under an allowed
    scope. Chunks are the atomic retrieval unit, so a family above the bound is
    left untouched instead of claiming a partial table as the whole parent.
    """
    by_id = {row.id: row for row in rows}
    rank = {hit.chunk_id: position for position, hit in enumerate(hits)}
    anchors = {}
    for hit in hits:
        row = by_id.get(hit.chunk_id)
        structure = (row.structure or {}) if row is not None else {}
        citation = structure.get("source_table_citation")
        if row is None or row.kind != "table" or not citation:
            continue
        anchors.setdefault((row.input_id, citation), []).append(hit.chunk_id)
    groups = []
    for (input_id, citation), anchor_ids in anchors.items():
        family = [
            row
            for row in rows
            if row.input_id == input_id
            and row.kind == "table"
            and (row.structure or {}).get("source_table_citation") == citation
            and any(matches_metadata(row.structure, scope) for scope in scopes)
        ]
        available = [key for key in anchor_ids if any(row.id == key for row in family)]
        if len(family) < 2 or not available or len(family) > MAX_TABLE_FAMILY_CHUNKS:
            continue
        family.sort(key=_family_order)
        groups.append(
            {
                "kind": "table_family",
                "label": _family_label(family[0].structure),
                "input_id": input_id,
                "primary_chunk_id": min(available, key=lambda key: rank.get(key, len(rank))),
                "required_ids": [row.id for row in family],
                "units": [{"ref": citation, "chunk_ids": [row.id]} for row in family],
                "family_chunks": len(family),
                "unindexed_refs": [],
                "compressed_refs": [],
                "truncated": False,
            }
        )
    return groups
