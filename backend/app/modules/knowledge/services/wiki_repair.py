"""Section-local repair plans never let the model replace validated sections."""

from collections.abc import Callable

from pydantic import BaseModel

from app.core.exceptions import AppException
from app.modules.knowledge.wiki_schemas import WikiGeneration, WikiPacketRepair


def repair_targets(candidate: WikiGeneration, locations: list[dict]) -> list[dict]:
    result = []
    for index, location in enumerate(locations):
        page = candidate.pages[location["page_index"] - 1]
        section = page.sections[location["section_index"] - 1].model_dump()
        section["references"] = [ref["unit_id"] for ref in section["references"]]
        for scope in section["temporal"]:
            scope["references"] = [ref["unit_id"] for ref in scope["references"]]
        result.append({"target_id": f"repair{index}", **location, "kind": page.kind,
            "title": page.title, "section": section})
    return result


def repair_context(payload: dict, targets: list[dict]) -> dict:
    keys = {(target["kind"], target["title"]) for target in targets}
    pages = [page for page in payload["analysis"]["pages"] if (page["kind"], page["title"]) in keys]
    ids = {uid for page in pages for uid in page["unit_ids"]}
    units = [unit for unit in payload["units"] if unit["id"] in ids]
    scopes = {unit["scope_id"] for unit in units}
    handles = payload.get("_request_handles") or {unit["id"]: f"u{index}" for index, unit in enumerate(payload["units"])}
    return {**payload, "analysis": {"pages": pages}, "units": units,
        "scopes": {key: value for key, value in payload["scopes"].items() if key in scopes},
        "repair_targets": targets, "_request_handles": {unit["id"]: handles[unit["id"]] for unit in units}}


def merge_section_patches(candidate: WikiGeneration, patches: WikiPacketRepair, targets: list[dict],
                          bind: Callable[[BaseModel], WikiGeneration]) -> WikiGeneration:
    offered = {target["target_id"]: target for target in targets}
    selected = [patch.target_id for patch in patches.patches]
    if len(selected) != len(set(selected)) or set(selected) != set(offered):
        raise AppException("Bản sửa phải khớp đúng các phần được cấp.", code="KNOWLEDGE_WIKI_INVALID",
            status_code=422, details={"reason": "repair_target_identity"})
    result = candidate.model_copy(deep=True)
    from app.modules.knowledge.wiki_schemas import WikiPacketGeneration
    for patch in patches.patches:
        target = offered[patch.target_id]
        # Binding expands only the selected IDs. The full generation validator
        # still checks this section against its exact original page outline.
        page = WikiPacketGeneration(pages=[{"kind": target["kind"], "title": target["title"],
            "sections": [patch.section.model_dump()]}])
        section_type = type(result.pages[target["page_index"] - 1].sections[target["section_index"] - 1])
        replacement = section_type.model_validate(bind(page).pages[0].sections[0].model_dump())
        result.pages[target["page_index"] - 1].sections[target["section_index"] - 1] = replacement
    return result
