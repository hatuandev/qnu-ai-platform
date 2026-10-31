"""Exact source retention checks, never OCR verification or semantic approval."""

from collections import Counter


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
