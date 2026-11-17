"""Exact source retention checks, never OCR verification or semantic approval."""

from collections import Counter, defaultdict

from qnu.domains.knowledge.compilation.schemas import DRAFT_PARAGRAPH_TEXT_LIMIT
from qnu.domains.knowledge.compilation.source_first import build_source_draft
from qnu.platform.errors import AppException


def retained_sections(material: dict, run_id: str) -> list[dict]:
    draft = material["draft"]
    if (draft.get("validation") or {}).get("source_copy") != "retained":
        return []
    try:
        rebuilt = build_source_draft(material["topic"], material["documents"], run_id)
    except AppException:
        return []  # An older snapshot may not be reproducible by today's source assembler.
    return rebuilt["sections"] if rebuilt["sections"] == draft["sections"] else []


def assess_source_headings(material: dict, sections: list[dict]) -> tuple[dict, ...]:
    refs = {unit["id"]: unit["id"] for unit in material["source_units"]}
    for unit in material["source_units"]:
        if unit.get("table_id"):
            refs.setdefault(unit["table_id"], unit["id"])
    checks = []
    for index, section in enumerate(sections, start=1):
        reference = next(
            (
                refs[ref]
                for paragraph in section["paragraphs"]
                for ref in paragraph["citations"]
                if ref in refs
            ),
            None,
        )
        if reference:
            checks.append(
                {
                    "draft_id": f"section:{index}:heading",
                    "status": "supported",
                    "source_ids": [reference],
                    "explanation": "Tiêu đề phân đoạn do QNU tạo, khớp cấu trúc dựng lại từ nguồn đã ghim.",
                    "suggested_action": "",
                }
            )
    return tuple(checks)


def assess_table_text_copies(material: dict) -> tuple[dict, ...]:
    """Verify literal copies of table blocks without asking a model to reread their cells."""
    paragraphs = defaultdict(list)
    for unit in material["draft_units"]:
        citations = unit.get("citations", ())
        if unit["kind"] == "paragraph" and len(citations) == 1:
            paragraphs[citations[0]].append(unit)
    table_copies = {
        entry["citation"]: entry["table"] for entry in material["draft"]["source_tables"]
    }
    anchors = {}
    for unit in material["source_units"]:
        if unit.get("table_id") and unit["text"].strip():
            anchors.setdefault(unit["table_id"], unit["id"])
    checks = []
    for doc in material["documents"]:
        for page in doc["pages"]:
            for block in page["blocks"]:
                ref = f"{doc['ocr_run_id']}:{block['evidence_id']}"
                anchor = anchors.get(ref)
                table = block.get("table") or {}
                if (
                    not anchor
                    or block.get("requires_review")
                    or table.get("status") != "parsed"
                    or table != table_copies.get(ref)
                ):
                    continue
                checks.extend(_table_text_checks(block["text"], paragraphs.get(ref, ()), anchor))
    return tuple(checks)


def _table_text_checks(text: str, paragraphs: list | tuple, anchor: str) -> list[dict]:
    if not text.strip():
        return []
    expected = [
        text[offset : offset + DRAFT_PARAGRAPH_TEXT_LIMIT]
        for offset in range(0, len(text), DRAFT_PARAGRAPH_TEXT_LIMIT)
    ]
    if [unit["text"] for unit in paragraphs] != expected:
        return []
    return [
        {
            "draft_id": unit["id"],
            "status": "supported",
            "source_ids": [anchor],
            "explanation": "Đoạn chép nguyên văn khối bảng. Các ô nguồn được kiểm riêng.",
            "suggested_action": "",
        }
        for unit in paragraphs
    ]


def source_prose_pairs(material: dict) -> dict[str, str]:
    """Map exact one-to-one paragraphs, with no other draft claim citing the same block."""
    sources = {unit["id"]: unit for unit in material["source_units"]}
    refs = Counter(ref for unit in material["draft_units"] for ref in unit.get("citations", ()))
    pairs = {}
    for unit in material["draft_units"]:
        citations = unit.get("citations", ())
        if unit["kind"] != "paragraph" or len(citations) != 1:
            continue
        ref = citations[0]
        original = sources.get(ref)
        if (
            original is not None
            and original["kind"]
            in {"text", "paragraph", "title", "heading", "section_header", "footer", "page_footer"}
            and refs[ref] == 1
            and not original.get("requires_review")
            and original["text"]
            and original["text"] == unit["text"]
        ):
            pairs[unit["id"]] = ref
    return pairs


def assess_source_prose(material: dict, payload: dict) -> dict | None:
    pairs = source_prose_pairs(material)
    drafts = [unit["id"] for unit in payload["draft_units"]]
    if not drafts or not set(drafts) <= pairs.keys():
        return None
    matched = {pairs[key]: key for key in drafts}
    if matched.keys() != {unit["id"] for unit in payload["source_units"]}:
        return None
    explanation = "Văn bản khớp nguyên văn với khối nguồn đã ghim. Chưa đối chiếu với ảnh gốc."
    return {
        "source_assessments": [
            {
                "source_id": ref,
                "status": "covered",
                "draft_ids": [key],
                "explanation": explanation,
                "suggested_action": "",
            }
            for ref, key in matched.items()
        ],
        "draft_assessments": [
            {
                "draft_id": key,
                "status": "supported",
                "source_ids": [pairs[key]],
                "explanation": explanation,
                "suggested_action": "",
            }
            for key in drafts
        ],
    }


def assess(material: dict, payload: dict) -> dict | None:
    sources = {unit["id"]: unit for unit in material["source_units"]}
    drafts = material["draft_units"]
    if len(sources) != len(material["source_units"]):
        return None
    counts = Counter(unit.get("source_id") for unit in drafts)
    matched = {}
    tables = material.get("draft", {}).get("source_tables", [])
    for unit in drafts:
        source = sources.get(unit.get("source_id"))
        if unit.get("kind") != "table_cell" or source is None or source.get("kind") != "table_cell":
            continue
        try:
            identity = unit["id"].split(":")
            if len(identity) != 6 or identity[::2] != ["table", "row", "cell"]:
                continue
            table_index = int(identity[1]) - 1
            if table_index < 0 or (int(identity[3]), int(identity[5])) != (
                unit["row"],
                unit["column"],
            ):
                continue
            table = tables[table_index]
        except (ValueError, IndexError, KeyError, TypeError):
            continue
        if counts[unit["source_id"]] != 1 or table.get("citation") != source.get("table_id"):
            continue
        if all(
            unit.get(key) == source.get(key)
            for key in (
                "text",
                "row",
                "column",
                "header",
                "row_span",
                "col_span",
            )
        ):
            matched[unit["id"]] = unit["source_id"]
    owned_source = {unit["id"] for unit in payload["source_units"]}
    owned_draft = {unit["id"] for unit in payload["draft_units"]}
    allowed_source = set(payload.get("allowed_source_ids", owned_source))
    allowed_draft = set(payload.get("allowed_draft_ids", owned_draft))
    reverse = {source: draft for draft, source in matched.items() if draft in allowed_draft}
    if not owned_source.issubset(reverse) or not owned_draft.issubset(matched):
        return None
    if any(matched[key] not in allowed_source for key in owned_draft):
        return None
    explanation = (
        "Giữ nguyên ô nguồn theo ID, bảng, vị trí, văn bản và span; không xác minh OCR với ảnh."
    )
    return {
        "source_assessments": [
            {
                "source_id": key,
                "status": "covered",
                "draft_ids": [reverse[key]],
                "explanation": explanation,
                "suggested_action": "",
            }
            for key in sorted(owned_source)
        ],
        "draft_assessments": [
            {
                "draft_id": key,
                "status": "supported",
                "source_ids": [matched[key]],
                "explanation": explanation,
                "suggested_action": "",
            }
            for key in sorted(owned_draft)
        ],
    }
