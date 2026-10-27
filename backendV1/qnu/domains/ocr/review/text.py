"""Only leaf text is editable; page, grid and provenance stay server-owned."""

from copy import deepcopy

from qnu.domains.ocr.review.schemas import TextChange, TextUnit
from qnu.platform.errors import Conflict


def leaf_units(document: dict) -> list[tuple[TextUnit, dict]]:
    output = []
    for page in document["pages"]:
        for block in page["blocks"]:
            base = {"page": page["page_number"], "bbox": block["bbox"]}
            table = block.get("table")
            if table is not None:
                # Unsupported raw table syntax is preserved, never edited as prose.
                if table["status"] != "parsed":
                    continue
                for row_index, row in enumerate(table["rows"]):
                    for col_index, cell in enumerate(row):
                        output.append(
                            (
                                TextUnit(
                                    **base,
                                    evidence_id=cell["evidence_id"],
                                    kind="table_cell",
                                    text=cell["text"],
                                    original_text=cell["text"],
                                    row=row_index + 1,
                                    column=col_index + 1,
                                ),
                                cell,
                            )
                        )
            elif block["type"] not in {"formula", "figure", "unknown"}:
                output.append(
                    (
                        TextUnit(
                            **base,
                            evidence_id=block["evidence_id"],
                            kind=block["type"],
                            text=block["text"],
                            original_text=block["text"],
                        ),
                        block,
                    )
                )
    return output


def apply_changes(document: dict, changes: list[TextChange]) -> dict:
    revised = deepcopy(document)
    units = {unit.evidence_id: leaf for unit, leaf in leaf_units(revised)}
    for change in changes:
        leaf = units.get(change.evidence_id)
        if leaf is None or leaf["text"] != change.before:
            raise Conflict("Đoạn văn đã thay đổi hoặc không thể sửa.", code="ocr_text_conflict")
        if change.before == change.after:
            raise Conflict("Nội dung mới trùng nội dung hiện tại.", code="ocr_text_unchanged")
        if not change.after.strip():
            raise Conflict("Không được xóa hết nội dung đoạn hoặc ô.", code="ocr_text_empty")
        if any(ord(c) < 32 and c not in "\n\t\r" for c in change.after):
            raise Conflict("Nội dung có ký tự điều khiển không hợp lệ.", code="ocr_text_invalid")
        leaf["text"] = change.after
    for page in revised["pages"]:
        for block in page["blocks"]:
            table = block.get("table")
            if table is not None and table["status"] == "parsed":
                block["text"] = "\n".join(
                    "\t".join(c["text"] for c in row) for row in table["rows"]
                )
    return revised
