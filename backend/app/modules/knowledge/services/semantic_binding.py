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


class ModelSemanticProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    context_id: str
    notes: list[NoteSelection] = Field(default_factory=list, max_length=128)
    cells: list[CellSelection] = Field(default_factory=list, max_length=256)
    limitations: list[LimitSelection] = Field(default_factory=list, max_length=256)
    needs_context: list[str] = Field(default_factory=list, max_length=32)
    unresolved: list[UnresolvedRelation] = Field(default_factory=list, max_length=64)


def _evidence(artifact: dict, packet: dict, selection: Selection) -> tuple[EvidenceBinding, str]:
    record = packet["_bindings"].get(selection.evidence_id)
    if record is None:
        raise ValueError("EVIDENCE_ID_NOT_IN_CONTEXT")
    binding = EvidenceBinding.model_validate(record)
    text = source_text(artifact, binding.source_unit_id, binding.column_id)
    quote = text[binding.start:binding.end]
    verify_binding(artifact, binding, quote, selection.source_unit_id)
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


def scope_guard(artifact: dict, note: NoteSelection, quote: str) -> None:
    """Reject verifiable contradictions, never certify arbitrary natural language."""
    table = next(table for table in artifact["tables"] if table["id"] == note.table_id)
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", quote))
    if note.scope == "column" and len(years) > 1:
        raise ValueError("EVIDENCE_SCOPE_YEAR_AMBIGUOUS_SELECT_NARROWER_SPAN")
    if note.scope == "column" and len(years) == 1:
        for column in table["columns"]:
            target_years = set(re.findall(r"\b(?:19|20)\d{2}\b", " / ".join(column["header_path"])))
            if column["id"] in note.column_ids and target_years and not target_years.issubset(years):
                raise ValueError("EVIDENCE_SCOPE_YEAR_CONFLICT")
    if note.scope not in {"row", "group"}:
        return
    # Generic identifiers, independent of column vocabulary and fixture labels.
    codes = {rid: {field["raw"] for field in fields if re.fullmatch(r"[^\W\d_]+(?:[-_.][^\W_]+)+", field["raw"])}
             for rid, fields in zip(table["row_unit_ids"], table["row_fields"], strict=True)}
    mentioned = {code for values in codes.values() for code in values
                 if re.search(r"(?<!\w)" + re.escape(code) + r"(?!\w)", quote)}
    ranges = list(re.finditer(r"(?P<prefix>[^\W\d_]+(?:-[^\W\d_]+)*-)(?P<start>\d+)\s+(?:đến|tới|to|through)\s+(?P=prefix)(?P<end>\d+)", quote))
    if note.scope == "row" and len(mentioned) > 1:
        raise ValueError("EVIDENCE_SCOPE_ROW_AMBIGUOUS_SELECT_NARROWER_SPAN")
    if len(ranges) == 1:
        interval = ranges[0]
        start, end = int(interval["start"]), int(interval["end"])
        if start <= end and len(interval["start"]) == len(interval["end"]):
            mentioned = {code for values in codes.values() for code in values
                         if (match := re.fullmatch(re.escape(interval["prefix"]) + r"(\d+)", code))
                         and len(match[1]) == len(interval["start"]) and start <= int(match[1]) <= end}
    if mentioned and any(codes.get(row) and not codes[row].intersection(mentioned) for row in note.row_unit_ids):
        raise ValueError("EVIDENCE_SCOPE_ROW_CONFLICT")


def bind_model_proposals(artifact: dict, packet: dict, payload: dict | ModelSemanticProposal):
    from app.modules.knowledge.services.semantic_annotations import (
        SemanticAnnotations,
        _validated_copy,
    )

    proposal = payload if isinstance(payload, ModelSemanticProposal) else ModelSemanticProposal.model_validate(payload)
    if proposal.context_id != packet["context_id"] or packet["source"] != source_identity(artifact):
        raise ValueError("EVIDENCE_CONTEXT_OR_REVISION_MISMATCH")
    result = {"notes": [], "cells": [], "limitations": []}
    for category, entries in result.items():
        for selection in getattr(proposal, category):
            binding, quote = _evidence(artifact, packet, selection)
            item = {"evidence_quote": quote, "evidence_binding": binding.model_dump(), "reason": selection.reason}
            if category == "notes":
                allowed = [table for table in packet["tables"] if table["id"] == selection.table_id]
                if len(allowed) != 1 or not set(selection.row_unit_ids).issubset({row["id"] for row in allowed[0]["row_directory"]}):
                    raise ValueError("SEMANTIC_SCOPE_OUTSIDE_CONTEXT")
                if binding.column_id is not None:
                    raise ValueError("NOTE_EVIDENCE_REQUIRES_PROSE")
                scope_guard(artifact, selection, quote)
                item.update(selection.model_dump(exclude={"evidence_id", "source_unit_id", "reason"}), note_unit_id=binding.source_unit_id)
            else:
                target = _row_field(artifact, packet, selection.row_unit_id, selection.column_id)
                item.update(selection.model_dump(exclude={"evidence_id", "source_unit_id", "reason"}),
                            raw=target["raw"], evidence_unit_id=binding.source_unit_id)
                if category == "limitations" and not set(selection.examined_unit_ids).issubset({u["id"] for u in packet["units"]} | {r["id"] for t in packet["tables"] for r in t["rows"]}):
                    raise ValueError("LIMIT_SCOPE_NOT_EXAMINED")
            entries.append(item)
    annotations = SemanticAnnotations.model_validate(result)
    _validated_copy(artifact, annotations)
    return annotations
