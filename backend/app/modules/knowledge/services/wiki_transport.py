"""Short request-local evidence handles; immutable source IDs remain server-owned."""

from functools import reduce
from operator import or_
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, Field, Tag, create_model

from app.core.exceptions import AppException
from app.modules.knowledge.wiki_schemas import (
    WIKI_MAX_REFERENCES,
    WikiAnalysis,
    WikiContract,
    WikiDraftPage,
    WikiDraftSection,
    WikiDraftTemporal,
    WikiOutline,
    WikiPacketGeneration,
    WikiPacketRepair,
    WikiSectionPatch,
    WikiSelection,
    WikiSelectionOutline,
)


def prepare_transport(contract: type[BaseModel], payload: dict) -> tuple[type[BaseModel], dict, dict[str, str]]:
    """Constrain each page to its offered handles, without adding source evidence."""
    if contract not in {WikiAnalysis, WikiSelection, WikiPacketGeneration, WikiPacketRepair} or not payload.get("units"):
        return contract, payload, {}
    handles = payload.get("_request_handles") or {unit["id"]: f"u{index}" for index, unit in enumerate(payload["units"])}
    wire = {**{key: value for key, value in payload.items() if key != "_request_handles"}, "units": [{**unit, "id": handles[unit["id"]],
        **({"context_ids": [handles[uid] for uid in unit["context_ids"]]} if "context_ids" in unit else {})}
        for unit in payload["units"]]}
    reverse = {handle: uid for uid, handle in handles.items()}
    if contract in {WikiAnalysis, WikiSelection}:
        fields = {"unit_ids": (list[Literal[tuple(reverse)]], Field(min_length=1, max_length=100))}
        if contract is WikiSelection:
            temporal = create_model("OfferedSelectionScope", __base__=WikiDraftTemporal,
                references=(list[Literal[tuple(reverse)]], Field(min_length=1, max_length=WIKI_MAX_REFERENCES)))
            fields["temporal"] = (list[temporal], Field(default_factory=list, max_length=8))
        outline = create_model("OfferedWikiOutline", __base__=WikiSelectionOutline if contract is WikiSelection else WikiOutline,
            **fields)
        bound = create_model("OfferedWikiAnalysis", __base__=contract,
            pages=(list[outline], Field(min_length=1, max_length=3)))
        return bound, wire, reverse
    outlines = payload["analysis"]["pages"]
    wire["analysis"] = {"pages": [{**page, "unit_ids": [handles[uid] for uid in page["unit_ids"]]} for page in outlines]}
    if feedback := payload.get("validation_feedback"):
        wire["validation_feedback"] = {**feedback,
            "supporting_unit_candidates": {token: [handles[uid] for uid in ids]
                for token, ids in feedback.get("supporting_unit_candidates", {}).items()},
            "invalid_unit_ids": [handles.get(uid, uid) for uid in feedback.get("invalid_unit_ids", [])],
            "validation_findings": [{**finding, **({"invalid_unit_ids": [handles.get(uid, uid)
                for uid in finding["invalid_unit_ids"]]} if "invalid_unit_ids" in finding else {})}
                for finding in feedback.get("validation_findings", [])]}
    page_types, section_types = [], {}
    for index, page in enumerate(wire["analysis"]["pages"]):
        offered = Literal[tuple(page["unit_ids"])]
        temporal = create_model(f"WikiScope{index}", __base__=WikiDraftTemporal,
            references=(list[offered], Field(min_length=1, max_length=WIKI_MAX_REFERENCES)))
        section = create_model(f"WikiSection{index}", __base__=WikiDraftSection,
            references=(list[offered], Field(min_length=1, max_length=WIKI_MAX_REFERENCES)),
            temporal=(list[temporal], Field(default_factory=list, max_length=8)))
        section_types[(page["kind"], page["title"])] = section
        page_types.append(create_model(f"WikiPage{index}", __base__=WikiDraftPage,
            kind=(Literal[page["kind"]], ...), title=(Literal[page["title"]], ...),
            sections=(list[section], Field(min_length=1, max_length=3))))
    if contract is WikiPacketRepair:
        targets = payload["repair_targets"]
        wire["repair_targets"] = [{**target, "section": map_section_ids(target["section"], handles, mark_unoffered=True)} for target in targets]
        patch_types = [create_model(f"WikiPatch{index}", __base__=WikiSectionPatch,
            target_id=(Literal[target["target_id"]], ...),
            section=(section_types[(target["kind"], target["title"])], ...)) for index, target in enumerate(targets)]
        def select_target(value):
            return value.get("target_id") if isinstance(value, dict) else value.target_id
        patch_type = patch_types[0] if len(patch_types) == 1 else Annotated[
            reduce(or_, [Annotated[model, Tag(target["target_id"])] for model, target in zip(patch_types, targets, strict=True)]),
            Discriminator(select_target)]
        bound = create_model("OfferedWikiRepair", __base__=WikiContract,
            patches=(list[patch_type], Field(min_length=1, max_length=9)))
        return bound, wire, reverse
    identities = {(page["kind"], page["title"]): f"page{index}" for index, page in enumerate(outlines)}
    def select_page(value):
        data = value if isinstance(value, dict) else value.model_dump()
        return identities.get((data.get("kind"), data.get("title")))
    page_type = page_types[0] if len(page_types) == 1 else Annotated[
        reduce(or_, [Annotated[model, Tag(f"page{index}")] for index, model in enumerate(page_types)]),
        Discriminator(select_page)]
    bound = create_model("OfferedWikiGeneration", __base__=WikiContract,
        pages=(list[page_type], Field(min_length=1, max_length=3)))
    return bound, wire, reverse


def restore_source_ids(contract: type[BaseModel], output: BaseModel, reverse: dict[str, str]) -> BaseModel:
    try:
        return _restore_source_ids(contract, output, reverse)
    except KeyError:
        raise AppException("Tham chiếu không thuộc gói nguồn đã cấp.", code="KNOWLEDGE_WIKI_INVALID",
            status_code=422, details={"reason": "quote_binding"}) from None


def _restore_source_ids(contract: type[BaseModel], output: BaseModel, reverse: dict[str, str]) -> BaseModel:
    if not reverse:
        return output
    data = output.model_dump()
    if contract is WikiPacketRepair:
        for patch in data["patches"]:
            patch["section"] = map_section_ids(patch["section"], reverse)
        return contract.model_validate(data)
    for page in data["pages"]:
        if "unit_ids" in page:
            page["unit_ids"] = [reverse[handle] for handle in page["unit_ids"]]
        for scope in page.get("temporal", []):
            scope["references"] = [reverse[handle] for handle in scope["references"]]
        for section in page.get("sections", []):
            section["references"] = [reverse[handle] for handle in section["references"]]
            for scope in section.get("temporal", []):
                scope["references"] = [reverse[handle] for handle in scope["references"]]
    return contract.model_validate(data)


def map_section_ids(section: dict, mapping: dict[str, str], *, mark_unoffered: bool = False) -> dict:
    def resolve(uid):
        if mark_unoffered and uid not in mapping:
            return "[outside_outline]"  # Invalid draft input only; output enums never allow this marker.
        return mapping[uid]
    return {**section, "references": [resolve(uid) for uid in section["references"]],
        "temporal": [{**scope, "references": [resolve(uid) for uid in scope["references"]]}
                     for scope in section.get("temporal", [])]}
