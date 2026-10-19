"""Model selects source IDs, backend supplies quotes, existing validators decide."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.knowledge.services.semantic_evidence import (
    EvidenceBinding,
    source_identity,
    source_text,
    verify_binding,
)


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_unit_id: str
    evidence_id: str
    reason: str = Field(min_length=3, max_length=1200)


class NoteSelection(Selection):
    table_id: str
    scope: Literal["table", "row", "group", "column"]
    row_unit_ids: list[str] = Field(default_factory=list, max_length=300)
    column_ids: list[str] = Field(default_factory=list, max_length=100)


class CellSelection(Selection):
    row_unit_id: str
    column_id: str
    state: Literal["not_stated", "not_applicable", "ambiguous", "unreadable"]


class LimitSelection(Selection):
    row_unit_id: str
    column_id: str
    basis: Literal["source_explicit", "human_examined_scope"]
    examined_unit_ids: list[str] = Field(min_length=1, max_length=2000)


class UnresolvedRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    unit_ids: list[str] = Field(default_factory=list, max_length=100)
    reason: str = Field(min_length=3, max_length=1200)


class ContextFollowup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issue_id: str
    evidence_ids: list[str] = Field(min_length=1, max_length=16)
    reason: str = Field(min_length=3, max_length=1200)


class ModelSemanticProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    context_id: str
    notes: list[NoteSelection] = Field(default_factory=list, max_length=128)
    cells: list[CellSelection] = Field(default_factory=list, max_length=256)
    limitations: list[LimitSelection] = Field(default_factory=list, max_length=256)
    needs_context: list[str] = Field(default_factory=list, max_length=32)
    unresolved: list[UnresolvedRelation] = Field(default_factory=list, max_length=64)
    context_followups: list[ContextFollowup] = Field(default_factory=list, max_length=64)


class SelectionV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    reason: str = Field(min_length=3, max_length=1200)


class NoteSelectionV2(SelectionV2):
    table_id: str
    scope: Literal["table", "row", "group", "column"]
    row_unit_ids: list[str] = Field(default_factory=list, max_length=300)
    column_ids: list[str] = Field(default_factory=list, max_length=100)


class CellSelectionV2(SelectionV2):
    row_unit_id: str
    column_id: str
    state: Literal["not_stated", "not_applicable", "ambiguous", "unreadable"]


class LimitSelectionV2(SelectionV2):
    row_unit_id: str
    column_id: str
    basis: Literal["source_explicit", "human_examined_scope"]
    examined_unit_ids: list[str] = Field(min_length=1, max_length=2000)


class ModelSemanticProposalV2(ModelSemanticProposal):
    notes: list[NoteSelectionV2] = Field(default_factory=list, max_length=128)
    cells: list[CellSelectionV2] = Field(default_factory=list, max_length=256)
    limitations: list[LimitSelectionV2] = Field(default_factory=list, max_length=256)


def selector_type(contract: str):
    if contract == "qnu_semantic_selector_v1":
        return ModelSemanticProposal
    if contract == "qnu_semantic_selector_v2":
        return ModelSemanticProposalV2
    raise ValueError("SELECTOR_CONTRACT_UNKNOWN")


class BindingSelectionError(ValueError):
    def __init__(self, reason: str, diagnostics: dict):
        super().__init__(reason)
        self.diagnostics = diagnostics


def _evidence(artifact: dict, packet: dict, selection: Selection | SelectionV2) -> tuple[EvidenceBinding, str]:
    record = packet["_bindings"].get(selection.evidence_id)
    if record is None:
        raise ValueError("EVIDENCE_ID_NOT_IN_CONTEXT")
    offered = [item for item in packet["evidence"] if item["id"] == selection.evidence_id]
    if len(offered) != 1:
        raise ValueError("EVIDENCE_ID_NOT_OFFERED_IN_PACKET")
    binding = EvidenceBinding.model_validate(record)
    if binding.evidence_id != selection.evidence_id:
        raise ValueError("EVIDENCE_REGISTRY_KEY_MISMATCH")
    text = source_text(artifact, binding.source_unit_id, binding.column_id)
    quote = text[binding.start:binding.end]
    if (offered[0]["source_unit_id"] != binding.source_unit_id or offered[0].get("column_id") != binding.column_id
            or offered[0]["text"] != quote):
        raise ValueError("EVIDENCE_PUBLIC_RECORD_MISMATCH")
    owner = selection.source_unit_id if isinstance(selection, Selection) else binding.source_unit_id
    verify_binding(artifact, binding, quote, owner)
    return binding, quote


def _row_field(artifact: dict, packet: dict, row_id: str, column_id: str) -> dict:
    visible = {row["id"] for table in packet["tables"] for row in table["rows"]}
    if row_id not in visible:
        raise ValueError("SEMANTIC_TARGET_OUTSIDE_CONTEXT")
    fields = [field for table in artifact["tables"]
              for rid, row in zip(table["row_unit_ids"], table["row_fields"], strict=True) if rid == row_id
              for field in row if field["column_id"] == column_id]
    if len(fields) != 1:
        raise ValueError("SEMANTIC_TARGET_INVALID")
    return fields[0]


def scope_guard(artifact: dict, note: NoteSelection, quote: str, full_text: str, issues: list | None) -> None:
    """Reject verifiable contradictions, never certify arbitrary natural language."""
    table = next(table for table in artifact["tables"] if table["id"] == note.table_id)
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", quote))
    full_years = set(re.findall(r"\b(?:19|20)\d{2}\b", full_text))
    selected = [column for column in table["columns"] if column["id"] in note.column_ids]
    header_years = [set(re.findall(r"\b(?:19|20)\d{2}\b", " / ".join(column["header_path"]))) for column in selected]
    # Code occurrence, numeric ranges and a selected clause cannot prove the
    # meaning of exclusions. Every row/group relation needs exact human scope.
    needs_review = note.scope in {"row", "group"} or (note.scope == "column" and (
        len(full_years) > 1 or any(len(value) != 1 for value in header_years)))
    if needs_review:
        if issues is None:
            raise ValueError("SEMANTIC_SCOPE_REVIEW_COLLECTOR_REQUIRED")
        from app.modules.knowledge.services.semantic_context_review import make_issue
        issue = make_issue(artifact, "scope_confirmation_required", [note.source_unit_id],
            {"table_id": note.table_id, "row_unit_ids": note.row_unit_ids, "column_ids": note.column_ids},
            "Đọc toàn đơn vị nguồn, các năm và điều kiện loại trừ; xác nhận đúng tập cột/dòng.")
        if not issue["review_evidence"] or issue["review_evidence"][0]["evidence_quote"] != full_text:
            raise ValueError("SEMANTIC_FULL_SOURCE_REVIEW_UNAVAILABLE")
        issues.append(issue)
    if note.scope == "column" and len(years) == 1 and not needs_review:
        for column in table["columns"]:
            target_years = set(re.findall(r"\b(?:19|20)\d{2}\b", " / ".join(column["header_path"])))
            if column["id"] in note.column_ids and target_years and not target_years.issubset(years):
                raise ValueError("EVIDENCE_SCOPE_YEAR_CONFLICT")


def _bound_selection(artifact: dict, packet: dict, category: str, selection, review_issues: list | None) -> dict:
    binding, quote = _evidence(artifact, packet, selection)
    if isinstance(selection, SelectionV2):
        internal = {"notes": NoteSelection, "cells": CellSelection, "limitations": LimitSelection}[category]
        selection = internal(**selection.model_dump(), source_unit_id=binding.source_unit_id)
    item = {"evidence_quote": quote, "evidence_binding": binding.model_dump(), "reason": selection.reason}
    if category == "notes":
        allowed = [table for table in packet["tables"] if table["id"] == selection.table_id]
        if len(allowed) != 1 or not set(selection.row_unit_ids).issubset({row["id"] for row in allowed[0]["row_directory"]}):
            raise ValueError("SEMANTIC_SCOPE_OUTSIDE_CONTEXT")
        if binding.column_id is not None:
            raise ValueError("NOTE_EVIDENCE_REQUIRES_PROSE")
        scope_guard(artifact, selection, quote, source_text(artifact, binding.source_unit_id), review_issues)
        item.update(selection.model_dump(exclude={"evidence_id", "source_unit_id", "reason"}), note_unit_id=binding.source_unit_id)
    else:
        target = _row_field(artifact, packet, selection.row_unit_id, selection.column_id)
        item.update(selection.model_dump(exclude={"evidence_id", "source_unit_id", "reason"}),
                    raw=target["raw"], evidence_unit_id=binding.source_unit_id)
        if category == "limitations" and not set(selection.examined_unit_ids).issubset({u["id"] for u in packet["units"]} | {r["id"] for t in packet["tables"] for r in t["rows"]}):
            raise ValueError("LIMIT_SCOPE_NOT_EXAMINED")
    return item


def _selection_diagnostic(packet: dict, category: str, index: int, selection) -> dict:
    record = packet["_bindings"].get(selection.evidence_id, {})
    return {"category": category, "index": index, "evidence_id": selection.evidence_id,
        "registry_owner": record.get("source_unit_id") if isinstance(record, dict) else None,
        "declared_owner": getattr(selection, "source_unit_id", None),
        "target": selection.model_dump(exclude={"reason", "source_unit_id", "evidence_id"})}


def bind_model_proposals(artifact: dict, packet: dict, payload: dict | ModelSemanticProposal, *, review_issues: list | None = None,
                         selector_contract: str = "qnu_semantic_selector_v1"):
    from app.modules.knowledge.services.semantic_annotations import (
        SemanticAnnotations,
        _validated_copy,
    )

    expected = selector_type(selector_contract)
    proposal = payload if type(payload) is expected else expected.model_validate(payload.model_dump() if isinstance(payload, BaseModel) else payload)
    if proposal.context_id != packet["context_id"] or packet["source"] != source_identity(artifact):
        raise ValueError("EVIDENCE_CONTEXT_OR_REVISION_MISMATCH")
    result = {"notes": [], "cells": [], "limitations": []}
    candidates = []
    for category, entries in result.items():
        for index, selection in enumerate(getattr(proposal, category)):
            diagnostic = _selection_diagnostic(packet, category, index, selection)
            candidates.append(diagnostic)
            try:
                entries.append(_bound_selection(artifact, packet, category, selection, review_issues))
            except ValueError as exc:
                raise BindingSelectionError(str(exc) if type(exc) is ValueError else "EVIDENCE_RECORD_INVALID", diagnostic) from exc
    annotations = SemanticAnnotations.model_validate(result)
    try:
        _validated_copy(artifact, annotations)
    except ValueError as exc:
        raise BindingSelectionError(str(exc) if type(exc) is ValueError else "ANNOTATION_INVALID", {"candidates": candidates}) from exc
    return annotations
