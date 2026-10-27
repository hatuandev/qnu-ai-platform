"""Structure-aware chunks: paragraphs retain headings; tables retain headers, spans and notes."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from qnu.domains.knowledge.metadata import chunk_metadata
from qnu.platform.errors import AppException

CHUNKER_VERSION = "qnu.published-chunks/v2"


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


def _split_text(prefix: str, text: str, maximum: int) -> list[str]:
    if len((prefix + text).encode("utf-8")) <= maximum:
        return [prefix + text]
    pieces, current = [], ""
    for word in re.findall(r"\S+\s*", text):
        if len((prefix + word).encode("utf-8")) > maximum:
            raise _too_large()
        if current and len((prefix + current + word).encode("utf-8")) > maximum:
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
    title: str, entry: dict, documents: list[dict], index: dict, maximum: int
) -> list[Chunk]:
    table = entry["table"]
    notes, raw_text = _table_context(entry, documents)
    prefix = title + "\n" + "\n".join(n["text"] for n in notes) + "\n"
    note_refs = [n["citation"] for n in notes]
    if table["status"] != "parsed" or not table["rows"]:
        text = prefix + raw_text
        if len(text.encode("utf-8")) > maximum:
            raise _too_large("index_table_group_too_large")
        refs = [entry["citation"], *note_refs]
        return [
            Chunk("table", text, {r: index[r] for r in refs}, {"table_status": table["status"]})
        ]
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
        return Chunk("table", text, {r: index[r] for r in refs}, structure)

    chunks, pending = [], []
    for group in groups:
        candidate = fragment(pending + group)
        if len(candidate.text.encode("utf-8")) > maximum:
            if not pending or len(fragment(group).text.encode("utf-8")) > maximum:
                raise _too_large("index_table_group_too_large")
            chunks.append(fragment(pending))
            pending = []
        pending += group
    if pending or not chunks:
        chunks.append(fragment(pending))
    return chunks


def build_chunks(
    content: dict, documents: list[dict], maximum: int, annotations: list[dict] | None = None
) -> list[Chunk]:
    index = content["citations"]
    annotations = annotations or []
    chunks = []
    for section_no, section in enumerate(content["sections"]):
        prefix = content["title"] + "\n" + section["heading"] + "\n"
        for paragraph_no, paragraph in enumerate(section["paragraphs"]):
            refs = {r: index[r] for r in paragraph["citations"]}
            target = f"paragraph:{section_no}:{paragraph_no}"
            chunks += [
                Chunk(
                    "paragraph",
                    t,
                    refs,
                    {
                        "context": {
                            "parent": f"section:{section_no}",
                            "position": paragraph_no,
                            "part": part,
                            "title": content["title"],
                            "heading": section["heading"],
                        },
                        "retrieval_metadata": chunk_metadata(annotations, {target}),
                    },
                )
                for part, t in enumerate(_split_text(prefix, paragraph["text"], maximum))
            ]
    for table in content["source_tables"]:
        fragments = _table_chunks(content["title"], table, documents, index, maximum)
        for part, fragment in enumerate(fragments):
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
            structure["retrieval_metadata"] = chunk_metadata(annotations, targets)
        chunks += fragments
    if not chunks:
        raise AppException(
            "Bản xuất bản không có chunk.", code="index_chunks_empty", status_code=422
        )
    for chunk in chunks:
        for annotation in (chunk.structure or {}).get("retrieval_metadata", []):
            for proof in annotation.get("evidence", []):
                chunk.citations[proof["citation"]] = index[proof["citation"]]
    return chunks
