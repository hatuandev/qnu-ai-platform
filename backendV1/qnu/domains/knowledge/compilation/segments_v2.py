"""Frozen v2 request shape for parts planned before the v3 planner.

A run created with ``qnu.compiler.plan/v2`` stored ``input_sha256`` over exactly
these bytes. Resuming such a run must rebuild the same request, so this module is
never edited: new behaviour lives in ``segments.py`` under a new version. The
pinning test in ``tests/unit/test_compiler_projection_746.py`` fails if any byte of
the v2 payload or prompt changes.
"""

from __future__ import annotations

import json

from qnu.domains.knowledge.compilation.drafting import SYSTEM_PROMPT
from qnu.domains.knowledge.compilation.projection import citations_in, project_documents
from qnu.domains.knowledge.compilation.schemas import SegmentDraftContent
from qnu.domains.knowledge.compilation.units import Unit, owned_refs, ref_key
from qnu.ports.chat_model import ChatMessage

PROMPT_VERSION = "qnu.compiler.segment.prompt/v2"
PLANNER_VERSION = "qnu.compiler.plan/v2"
MANIFEST_VERSION = "qnu.compiler.segment-manifest/v1"
TARGET_RATIO = 0.6
OUTPUT_CONTENT_RATIO = 0.25
CONTEXT_TYPES = {"title", "header", "caption", "footnote"}


def header_row_indexes(rows: list[list[dict]]) -> tuple[int, ...]:
    leading = 0
    for row in rows:
        if not row or not all(cell.get("header") for cell in row):
            break
        leading += 1
    if leading == len(rows):
        return ()
    return tuple(range(leading))


def _adjacent_context(documents: list[dict], unit: Unit) -> list[dict]:
    page = documents[unit.document_index]["pages"][unit.page_index]
    refs = []
    for offset in (-2, -1, 1, 2):
        index = unit.block_index + offset
        if not 0 <= index < len(page["blocks"]):
            continue
        block = page["blocks"][index]
        if block.get("table") is not None or block.get("type") not in CONTEXT_TYPES:
            continue
        refs.append(
            {
                "kind": "block",
                "ocr_run_id": unit.ocr_run_id,
                "page": unit.page_number,
                "evidence_id": block["evidence_id"],
            }
        )
    return refs


def structural_context(documents: list[dict], unit: Unit) -> list[dict]:
    """Preserve document headings/notes and candidate headers without guessing joins."""
    document = documents[unit.document_index]
    has_tables = any(b.get("table") for p in document["pages"] for b in p["blocks"])
    refs = []
    heading = None
    for page in document["pages"]:
        for block in page["blocks"]:
            table = block.get("table")
            base = {
                "ocr_run_id": unit.ocr_run_id,
                "page": page["page_number"],
                "evidence_id": block["evidence_id"],
            }
            if table and table.get("status") == "parsed":
                rows = header_row_indexes(table.get("rows") or [])
                if rows:
                    refs.append({**base, "kind": "table_header_rows", "rows": list(rows)})
            elif has_tables or block.get("type") in {"caption", "footnote"}:
                refs.append({**base, "kind": "block"})
            if block.get("type") in {"title", "header"}:
                heading = {**base, "kind": "block"}
            if block["evidence_id"] == unit.evidence_id and heading:
                refs.append(heading)
    return refs


def context_refs(documents: list[dict], units: list[Unit]) -> tuple[dict, ...]:
    """Repeat table headers and nearby title/caption/footnote blocks as context only."""
    owned = {ref_key(ref) for ref in owned_refs(units)}
    refs: list[dict] = []
    seen: set[tuple] = set()
    for unit in units:
        candidates = []
        if unit.kind == "table_row" and unit.header_rows:
            candidates.append(
                {
                    "kind": "table_header_rows",
                    "ocr_run_id": unit.ocr_run_id,
                    "page": unit.page_number,
                    "evidence_id": unit.evidence_id,
                    "rows": list(unit.header_rows),
                }
            )
        candidates.extend(_adjacent_context(documents, unit))
        candidates.extend(structural_context(documents, unit))
        for ref in candidates:
            key = ref_key(ref)
            if key in owned or key in seen:
                continue
            seen.add(key)
            refs.append(ref)
    return tuple(refs)


def document_structure(documents: list[dict]) -> dict:
    """Small structural outline only: counts, table shapes and heading text."""
    payload = []
    for document in documents:
        pages = []
        outline = []
        for page in document["pages"]:
            tables = []
            for block in page["blocks"]:
                if block.get("type") in {"title", "header"} and block.get("text"):
                    outline.append({"page": page["page_number"], "text": block["text"][:300]})
                table = block.get("table")
                if table is not None:
                    tables.append(
                        {
                            "page": page["page_number"],
                            "evidence_id": block["evidence_id"],
                            "status": table["status"],
                            "row_count": table["row_count"],
                            "column_count": table["column_count"],
                        }
                    )
            pages.append(
                {
                    "page": page["page_number"],
                    "status": page["status"],
                    "block_count": len(page["blocks"]),
                    "tables": tables,
                }
            )
        payload.append(
            {
                "ocr_run_id": document["ocr_run_id"],
                "identity": document["identity"],
                "page_count": len(document["pages"]),
                "pages": pages,
                "outline": outline[:80],
            }
        )
    return {"documents": payload}


def build_projection(
    topic: str,
    documents: list[dict],
    owned: tuple[dict, ...] | list[dict],
    context: tuple[dict, ...] | list[dict],
    index: int,
) -> tuple[dict, list[str]]:
    projected = project_documents(documents, owned, context)
    citations = citations_in(projected)
    payload = {
        "topic": topic,
        "segment": {
            "index": index,
            "has_previous": index > 1,
            "owned": list(owned),
            "context_only": list(context),
            "note": (
                "Chỉ biên soạn các refs trong owned; context_only chỉ dùng đối chiếu "
                "điều kiện/header, không biên soạn lại. rows của refs bắt đầu từ 0; "
                "row_numbers trong bảng bắt đầu từ 1. Không suy nội dung phần khác."
            ),
        },
        "structure": document_structure(documents),
        "documents": projected,
        "allowed_citations": citations,
    }
    return payload, citations


def segment_system(index: int, total: int) -> str:
    return SYSTEM_PROMPT + (
        f"\nĐây là phần {index}/{total} của một tài liệu dài. Chỉ trả nội dung thuộc phần "
        "này; giữ tiêu đề mục ngắn và không lặp lại nội dung đã viết ở phần khác. "
        "Nếu phần này không đủ căn cứ, trả sections rỗng và ghi unknowns. "
        "Tuyệt đối không tạo lại bảng và không trích dẫn ID ngoài allowed_citations. "
        "Hệ thống ghép đủ hàng/ô bảng nguyên gốc ở cuối; không diễn giải tuần tự "
        "mọi ô thành đoạn văn. Chỉ viết ghi chú cần thiết về phạm vi, điều kiện, "
        "ngoại lệ của owned; chỉ dùng context_only khi cần xác định các ghi chú đó. "
        "Không cần soạn cả tài liệu hoặc kiểm kê toàn bộ citation trong phản hồi."
    )


def segment_schema(citations: list[str]) -> dict:
    schema = SegmentDraftContent.model_json_schema()
    schema["$defs"]["DraftParagraph"]["properties"]["citations"]["items"]["enum"] = citations
    return schema


def segment_messages(payload: dict, index: int, total: int) -> list[ChatMessage]:
    return [
        ChatMessage("system", segment_system(index, total)),
        ChatMessage("user", json.dumps(payload, ensure_ascii=False, sort_keys=True)),
    ]


def estimate_output_size(documents: list[dict], units: list[Unit]) -> int:
    """UTF-8 copy-size proxy for owned content plus JSON and citation overhead."""
    size = 256
    for unit in units:
        block = documents[unit.document_index]["pages"][unit.page_index]["blocks"][
            unit.block_index
        ]
        cells = block["table"]["rows"][unit.row_index] if unit.kind == "table_row" else [block]
        size += 96  # Paragraph/section JSON framing.
        for cell in cells:
            text = cell.get("text") or ""
            citation = f"{unit.ocr_run_id}:{cell['evidence_id']}"
            size += len(json.dumps([text, citation], ensure_ascii=False).encode("utf-8"))
    return size
