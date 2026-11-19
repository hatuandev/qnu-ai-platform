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

CHUNKER_VERSION = "qnu.published-chunks/v6"
READABLE_CHUNKER_VERSIONS = {
    "qnu.published-chunks/v3",
    "qnu.published-chunks/v4",
    "qnu.published-chunks/v5",
    CHUNKER_VERSION,
}


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


def _covering_rows(rows: list[list[dict]], group: list[int], part: list[int]) -> list[int]:
    """Earlier rows of the same group whose rowspan still labels this part."""
    first = part[0]
    return [
        anchor
        for anchor in group
        if anchor < first
        and any(
            cell.get("row_span", 1) > 1 and anchor + cell["row_span"] > first
            for cell in rows[anchor]
        )
    ]


def _split_group(group: list[int], fits: Callable[[list[int]], bool]) -> list[list[int]]:
    """Last resort for a group over budget: contiguous parts, each row must fit alone."""
    parts, start = [], 0
    while start < len(group):
        end = start + 1
        if not fits(group[start:end]):
            raise _too_large("index_table_group_too_large")
        while end < len(group) and fits(group[start : end + 1]):
            end += 1
        parts.append(group[start:end])
        start = end
    return parts


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

    def fragment(
        body_rows: list[int],
        context_rows: list[int] = (),
        split: tuple[list[int], int, int] | None = None,
    ) -> Chunk:
        selected = sorted(set(headers + list(context_rows) + body_rows))
        structure = {
            "source_table_citation": entry["citation"],
            "original_row_count": table["row_count"],
            "original_column_count": table["column_count"],
            "row_indices": selected,
            "rows": [rows[i] for i in selected],
            "page_notes": notes,
        }
        if split is not None:
            group, part_index, part_count = split
            structure["rowspan_split"] = {
                "group_start_row": group[0],
                "group_end_row": group[-1],
                "part": part_index,
                "parts": part_count,
            }
        text = prefix + json.dumps(structure, ensure_ascii=False, sort_keys=True)
        refs = [entry["citation"], *note_refs] + [
            run_id + ":" + cell["evidence_id"] for i in selected for cell in rows[i]
        ]
        return prepare(Chunk("table", text, {r: index[r] for r in refs}, structure), len(chunks))

    def part_fragment(group: list[int], part: list[int], part_index: int, part_count: int) -> Chunk:
        return fragment(part, _covering_rows(rows, group, part), (group, part_index, part_count))

    chunks, pending = [], []
    for group in groups:
        if size(fragment(group)) > maximum:
            if pending:
                chunks.append(fragment(pending))
                pending = []
            group_rows = group
            parts = _split_group(
                group_rows,
                lambda part, group=group_rows: (
                    size(
                        fragment(
                            part,
                            _covering_rows(rows, group, part),
                            # Worst-case marker width, so the final chunk stays under budget.
                            (group, len(group), len(group)),
                        )
                    )
                    <= maximum
                ),
            )
            for part_index, part in enumerate(parts):
                chunks.append(part_fragment(group, part, part_index, len(parts)))
            continue
        candidate = fragment(pending + group)
        if size(candidate) > maximum:
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
    index = content.get("citations") or content.get("index") or {}
    annotations = annotations or []
    relations = {ref: link for doc in documents for ref, link in dependencies(doc).items()}
    source_outline = source_sections(documents)
    source_copy = content.get("validation", {}).get("source_copy") == "retained"
    source_tables = content.get("source_tables") or content.get("tables") or []
    table_copies = _table_text_copies(source_tables)
    title = content.get("title") or ""
    chunks = []
    for section_no, section in enumerate(content.get("sections") or []):
        for paragraph_no, paragraph in enumerate(section.get("paragraphs") or []):
            citations = paragraph.get("citations") or []
            refs = {r: index[r] for r in citations if r in index}
            target = f"paragraph:{section_no}:{paragraph_no}"
            source = shared_section(citations, source_outline)
            targets = {target}
            if source and source.citation:
                targets.add(f"section:{source.citation}")
            metadata = chunk_metadata(annotations, targets)
            if (
                len(citations) == 1
                and paragraph.get("text", "") in table_copies.get(citations[0], ())
                and not any(item["target"] == target for item in metadata)
            ):
                continue
            heading_text = section.get("heading") or ""
            fallback = (
                ""
                if source_copy and heading_text.startswith("Nguồn ")
                else heading_text
            )
            heading = (source.heading if source else "") or fallback
            structure = {
                "context": {
                    "parent": f"section:{section_no}",
                    "position": paragraph_no,
                    "part": 0,
                    "title": title,
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

            prefix = f"{title}\n{heading}\n"
            p_text = paragraph.get("text") or ""
            if heading != fallback and any(
                text_size(prefix + word) > maximum
                for word in re.findall(r"\S+\s*", p_text)
            ):
                prefix = f"{title}\n{fallback}\n"
            chunks += [
                Chunk(
                    "paragraph",
                    t,
                    refs,
                    {**structure, "context": {**structure["context"], "part": part}},
                )
                for part, t in enumerate(_split_text(prefix, p_text, maximum, text_size))
            ]
    for table in source_tables:
        source = source_outline.get(table.get("citation", ""))

        def prepare(
            fragment: Chunk,
            part: int,
            *,
            table: dict = table,
            source: SourceSection | None = source,
        ) -> Chunk:
            cit = table.get("citation", "")
            parent = "table:" + cit
            structure = fragment.structure
            tbl_info = table.get("table") or {}
            col_count = tbl_info.get("column_count", 0)
            targets = {f"{parent}:row:{r}" for r in structure.get("row_indices", [])}
            targets.update(
                f"{parent}:row:{r}:column:{c}"
                for r in structure.get("row_indices", [])
                for c in range(col_count)
            )
            targets.update(f"{parent}:column:{c}" for c in range(col_count))
            structure["context"] = {
                "parent": parent,
                "position": part,
                "part": 0,
                "title": title,
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
            if cit in relations:
                structure["source_dependencies"] = relations[cit]
            return fragment

        chunks += _table_chunks(title, table, documents, index, maximum, prepare, size)
    if not chunks:
        raise AppException(
            "Bản xuất bản không có chunk.", code="index_chunks_empty", status_code=422
        )
    for chunk in chunks:
        for annotation in (chunk.structure or {}).get("retrieval_metadata", []):
            for proof in annotation.get("evidence", []):
                proof_cit = proof.get("citation")
                if proof_cit and proof_cit in index:
                    chunk.citations[proof_cit] = index[proof_cit]
    return chunks
