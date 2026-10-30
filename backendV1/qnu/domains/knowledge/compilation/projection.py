"""Frozen snapshot projection primitives shared by every request version.

These functions define the bytes of a Compiler request. Changing them silently
would make a stored ``input_sha256`` unreproducible, so they are kept stable and
pinned by ``tests/unit/test_compiler_projection_746.py``. New request shapes are
added as a new projection version instead of editing this module.
"""

from __future__ import annotations

from qnu.platform.errors import AppException


def block_index(documents: list[dict]) -> dict[tuple[str, str], tuple[int, int, int, dict]]:
    index = {}
    for document_index, document in enumerate(documents):
        for page_index, page in enumerate(document["pages"]):
            for block_index_, block in enumerate(page["blocks"]):
                index[(document["ocr_run_id"], block["evidence_id"])] = (
                    document_index,
                    page_index,
                    block_index_,
                    block,
                )
    return index


def project_block(block: dict) -> dict:
    """Allowlist fields; never forward inline Base64 images or the evidence map."""
    payload = {
        "evidence_id": block["evidence_id"],
        "type": block["type"],
        "label": block.get("label"),
        "text": block.get("text", ""),
        "bbox": block.get("bbox"),
        "requires_review": bool(block.get("requires_review")),
    }
    if block.get("origin"):
        payload["origin"] = block["origin"]
    table = block.get("table")
    if table is not None:
        payload["table"] = {
            "evidence_id": table["evidence_id"],
            "status": table["status"],
            "reason": table.get("reason"),
            "column_count": table["column_count"],
            "row_count": table["row_count"],
            "rows": table["rows"],
        }
    return payload


def project_table_block(block: dict, rows: list[int]) -> dict:
    table = block["table"]
    payload = project_block({**block, "table": None})
    payload["table"] = {
        "evidence_id": table["evidence_id"],
        "status": table["status"],
        "reason": table.get("reason"),
        "column_count": table["column_count"],
        "row_count": table["row_count"],
        "rows": [table["rows"][index] for index in rows],
        "row_numbers": [index + 1 for index in rows],
    }
    return payload


def project_documents(
    documents: list[dict],
    owned: tuple[dict, ...] | list[dict],
    context: tuple[dict, ...] | list[dict],
) -> list[dict]:
    """Rebuild exactly the owned blocks/rows plus repeated context from the snapshot."""
    index = block_index(documents)
    selection: dict[tuple[int, int, int], dict] = {}
    for ref in [*owned, *context]:
        key = (ref["ocr_run_id"], ref["evidence_id"])
        if key not in index:
            raise AppException(
                "Phần biên soạn tham chiếu khối không có trong snapshot.",
                code="compilation_segment_manifest_mismatch",
                status_code=409,
            )
        document_index, page_index, block_index_, block = index[key]
        page = documents[document_index]["pages"][page_index]
        if page["page_number"] != ref["page"]:
            raise AppException(
                "Phần biên soạn tham chiếu sai trang nguồn.",
                code="compilation_segment_manifest_mismatch",
                status_code=409,
            )
        entry = selection.setdefault(
            (document_index, page_index, block_index_), {"block": False, "rows": set()}
        )
        if ref["kind"] == "block":
            entry["block"] = True
        else:
            rows = ref.get("rows", [])
            table = block.get("table") or {}
            source_rows = table.get("rows") or []
            if any(not isinstance(row, int) or not 0 <= row < len(source_rows) for row in rows):
                raise AppException(
                    "Phần biên soạn tham chiếu hàng bảng không hợp lệ.",
                    code="compilation_segment_manifest_mismatch",
                    status_code=409,
                )
            entry["rows"].update(rows)

    projected = []
    for document_index, document in enumerate(documents):
        pages = []
        for page_index, page in enumerate(document["pages"]):
            blocks = []
            for block_index_, block in enumerate(page["blocks"]):
                entry = selection.get((document_index, page_index, block_index_))
                if entry is None:
                    continue
                table = block.get("table")
                if entry["block"]:
                    blocks.append(project_block(block))
                elif table is not None and table.get("status") == "parsed":
                    blocks.append(project_table_block(block, sorted(entry["rows"])))
            if blocks:
                pages.append(
                    {
                        "page_number": page["page_number"],
                        "status": page["status"],
                        "blocks": blocks,
                    }
                )
        if pages:
            projected.append(
                {
                    "ocr_run_id": document["ocr_run_id"],
                    "identity": document["identity"],
                    "pages": pages,
                }
            )
    return projected


def citations_in(documents: list[dict]) -> list[str]:
    citations: list[str] = []
    seen: set[str] = set()
    for document in documents:
        run_id = document["ocr_run_id"]
        for page in document["pages"]:
            for block in page["blocks"]:
                refs = [block["evidence_id"]]
                table = block.get("table")
                if table is not None:
                    refs.append(table["evidence_id"])
                    refs.extend(cell["evidence_id"] for row in table["rows"] for cell in row)
                for evidence_id in refs:
                    ref = f"{run_id}:{evidence_id}"
                    if ref not in seen:
                        seen.add(ref)
                        citations.append(ref)
    return citations
