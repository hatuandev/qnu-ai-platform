"""Structure-aware chunks: paragraphs retain headings; tables retain headers, spans and notes."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, replace

from qnu.domains.knowledge.compilation.schemas import DRAFT_PARAGRAPH_TEXT_LIMIT
from qnu.domains.knowledge.index.table_dependencies import dependencies
from qnu.domains.knowledge.index.table_layout import quality
from qnu.domains.knowledge.metadata import chunk_metadata
from qnu.domains.knowledge.source_sections import SourceSection, shared_section, source_sections
from qnu.platform.errors import AppException

CHUNKER_VERSION = "qnu.published-chunks/v5"
READABLE_CHUNKER_VERSIONS = {"qnu.published-chunks/v3", "qnu.published-chunks/v4", CHUNKER_VERSION}


@dataclass(frozen=True, slots=True)
class Chunk:
    kind: str
    text: str
    citations: dict
    structure: dict | None = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def _too_large(code: str = "index_chunk_too_large") -> AppException:
    return AppException(
        "Một đơn vị cấu trúc vượt ngân sách chunk; cần điều chỉnh cấu hình/nguồn.",
        code=code,
        status_code=422,
    )


def _text_size(text: str) -> int:
    return len(text.encode("utf-8"))


def _chunk_size(chunk: Chunk) -> int:
    return _text_size(chunk.text)


def _split_text(
    prefix: str, text: str, maximum: int, size: Callable[[str], int] = _text_size
) -> list[str]:
    if size(prefix + text) <= maximum:
        return [prefix + text]
    pieces, current = [], ""
    for word in re.findall(r"\S+\s*", text):
        if size(prefix + word) > maximum:
            raise _too_large()
        if current and size(prefix + current + word) > maximum:
            pieces.append(prefix + current.rstrip())
            current = ""
        current += word
    if current:
        pieces.append(prefix + current.rstrip())
    return pieces


def _table_context(entry: dict, documents: list[dict]) -> tuple[list[dict], str]:
    run_id, evidence_id = entry["citation"].split(":", 1)
    doc = next(d for d in documents if d["ocr_run_id"] == run_id)
    page = next(p for p in doc["pages"] if p["page_number"] == entry["page_number"])
    notes = [
        b
        for b in page["blocks"]
        if b.get("label", "").casefold()
        in {
            "footnote",
            "caption",
            "title",
            "section-header",
            "page-header",
        }
    ]
    block = next(b for b in page["blocks"] if b["evidence_id"] == evidence_id)
    return [{"citation": run_id + ":" + b["evidence_id"], "text": b["text"]} for b in notes], block[
        "text"
    ]


def _row_groups(rows: list[list[dict]], header_indices: list[int]) -> list[list[int]]:
    """Rows linked by rowspan stay in one connected group; no numeric/text guessing."""
    result, start = [], 0
    while start < len(rows):
        end, cursor = start + 1, start
        while cursor < min(end, len(rows)):
            end = max([end, *[cursor + max(1, c["row_span"]) for c in rows[cursor]]])
            cursor += 1
        group = [i for i in range(start, min(end, len(rows))) if i not in header_indices]
        if group:
            result.append(group)
        start = max(start + 1, end)
    return result


def _table_chunks(
    title: str,
    entry: dict,
    documents: list[dict],
    index: dict,
    maximum: int,
    prepare: Callable[[Chunk, int], Chunk],
    size: Callable[[Chunk], int],
) -> list[Chunk]:
    table = entry["table"]
    notes, raw_text = _table_context(entry, documents)
    prefix = title + "\n" + "\n".join(n["text"] for n in notes) + "\n"
    note_refs = [n["citation"] for n in notes]
    if table["status"] != "parsed" or not table["rows"]:
        text = prefix + raw_text
        refs = [entry["citation"], *note_refs]
        chunk = prepare(
            Chunk("table", text, {r: index[r] for r in refs}, {"table_status": table["status"]}), 0
        )
        if size(chunk) > maximum:
            raise _too_large("index_table_group_too_large")
        return [chunk]
    rows = table["rows"]
    headers = []
    for i, row in enumerate(rows):
        if not any(c["header"] for c in row) or not all(c["header"] or not c["text"] for c in row):
            break
        headers.append(i)
    groups = _row_groups(rows, headers) or [[]]
    run_id = entry["citation"].split(":", 1)[0]

    def fragment(body_rows: list[int]) -> Chunk:
        selected = sorted(set(headers + body_rows))
        structure = {
            "source_table_citation": entry["citation"],
            "original_row_count": table["row_count"],
            "original_column_count": table["column_count"],
            "row_indices": selected,
            "rows": [rows[i] for i in selected],
            "page_notes": notes,
        }
        text = prefix + json.dumps(structure, ensure_ascii=False, sort_keys=True)
        refs = [entry["citation"], *note_refs] + [
            run_id + ":" + cell["evidence_id"] for i in selected for cell in rows[i]
        ]
        return prepare(Chunk("table", text, {r: index[r] for r in refs}, structure), len(chunks))

    chunks, pending = [], []
    for group in groups:
        candidate = fragment(pending + group)
        if size(candidate) > maximum:
            if not pending or size(fragment(group)) > maximum:
                raise _too_large("index_table_group_too_large")
            chunks.append(fragment(pending))
            pending = []
        pending += group
    if pending or not chunks:
        chunks.append(fragment(pending))
    return chunks


def _table_text_copies(tables: list[dict]) -> dict[str, set[str]]:
    """Recognize literal copies of parsed rows, including split draft paragraphs."""
    copies = {}
    for entry in tables:
        table = entry["table"]
        if table["status"] != "parsed" or not table["rows"]:
            continue
        text = "\n".join(" | ".join(cell["text"] for cell in row) for row in table["rows"])
        copies[entry["citation"]] = {
            text[offset : offset + DRAFT_PARAGRAPH_TEXT_LIMIT]
            for offset in range(0, len(text), DRAFT_PARAGRAPH_TEXT_LIMIT)
        }
    return copies


def build_chunks(
    content: dict,
    documents: list[dict],
    maximum: int,
    annotations: list[dict] | None = None,
    *,
    size: Callable[[Chunk], int] = _chunk_size,
) -> list[Chunk]:
    index = content["citations"]
    annotations = annotations or []
    relations = {ref: link for doc in documents for ref, link in dependencies(doc).items()}
    source_outline = source_sections(documents)
    source_copy = content.get("validation", {}).get("source_copy") == "retained"
    table_copies = _table_text_copies(content["source_tables"])
    chunks = []
    for section_no, section in enumerate(content["sections"]):
        for paragraph_no, paragraph in enumerate(section["paragraphs"]):
            citations = paragraph["citations"]
            refs = {r: index[r] for r in citations}
            target = f"paragraph:{section_no}:{paragraph_no}"
            source = shared_section(citations, source_outline)
            targets = {target}
            if source and source.citation:
                targets.add(f"section:{source.citation}")
            metadata = chunk_metadata(annotations, targets)
            if (
                len(citations) == 1
                and paragraph["text"] in table_copies.get(citations[0], ())
                and not any(item["target"] == target for item in metadata)
            ):
                continue
            fallback = (
                ""
                if source_copy and section["heading"].startswith("Nguồn ")
                else section["heading"]
            )
            heading = (source.heading if source else "") or fallback
            structure = {
                "context": {
                    "parent": f"section:{section_no}",
                    "position": paragraph_no,
                    "part": 0,
                    "title": content["title"],
                    "heading": heading,
                    **(
                        {"source_heading_citation": source.citation}
                        if source and source.heading
                        else {}
                    ),
                },
                "retrieval_metadata": metadata,
            }

            def text_size(text: str, *, refs: dict = refs, structure: dict = structure) -> int:
                return size(Chunk("paragraph", text, refs, structure))

            prefix = f"{content['title']}\n{heading}\n"
            if heading != fallback and any(
                text_size(prefix + word) > maximum
                for word in re.findall(r"\S+\s*", paragraph["text"])
            ):
                prefix = f"{content['title']}\n{fallback}\n"
            chunks += [
                Chunk(
                    "paragraph",
                    t,
                    refs,
                    {**structure, "context": {**structure["context"], "part": part}},
                )
                for part, t in enumerate(_split_text(prefix, paragraph["text"], maximum, text_size))
            ]
    for table in content["source_tables"]:
        source = source_outline.get(table["citation"])

        def prepare(
            fragment: Chunk,
            part: int,
            *,
            table: dict = table,
            source: SourceSection | None = source,
        ) -> Chunk:
            parent = "table:" + table["citation"]
            structure = fragment.structure
            targets = {f"{parent}:row:{r}" for r in structure.get("row_indices", [])}
            targets.update(
                f"{parent}:row:{r}:column:{c}"
                for r in structure.get("row_indices", [])
                for c in range(table["table"]["column_count"])
            )
            structure["context"] = {
                "parent": parent,
                "position": part,
                "part": 0,
                "title": content["title"],
            }
            if source and source.citation:
                targets.add(f"section:{source.citation}")
            structure["retrieval_metadata"] = chunk_metadata(annotations, targets)
            if source and source.heading:
                structure["context"].update(
                    heading=source.heading, source_heading_citation=source.citation
                )
                prefix = source.heading + "\n"
                if size(replace(fragment, text=prefix + fragment.text)) <= maximum:
                    fragment = replace(fragment, text=prefix + fragment.text)
            structure["reading_quality"] = quality(structure)
            if table["citation"] in relations:
                structure["source_dependencies"] = relations[table["citation"]]
            return fragment

        chunks += _table_chunks(content["title"], table, documents, index, maximum, prepare, size)
    if not chunks:
        raise AppException(
            "Bản xuất bản không có chunk.", code="index_chunks_empty", status_code=422
        )
    for chunk in chunks:
        for annotation in (chunk.structure or {}).get("retrieval_metadata", []):
            for proof in annotation.get("evidence", []):
                chunk.citations[proof["citation"]] = index[proof["citation"]]
    return chunks
