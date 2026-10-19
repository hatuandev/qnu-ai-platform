"""Scoped human examination, separate from raw cell state and publication authority."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.knowledge.normalization.retrieval_models import UnitManifest
from app.modules.knowledge.services.semantic_evidence import EvidenceBinding, verify_binding

PolicyMode = Literal["strict", "acknowledged_limits"]


class SourceLimitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row_unit_id: str
    column_id: str
    raw: str
    basis: Literal["source_explicit", "human_examined_scope"]
    evidence_unit_id: str
    evidence_quote: str = Field(min_length=3, max_length=5000)
    examined_unit_ids: list[str] = Field(min_length=1, max_length=2000)
    evidence_binding: EvidenceBinding | None = None
    reason: str | None = Field(None, max_length=1200)


def apply_limitations(artifact: dict, manifest: UnitManifest, limitations: list[SourceLimitation],
                      *, acknowledged: bool) -> None:
    by_id = {unit.id: unit for unit in manifest.units}
    rows = {row_id: fields for table in artifact["tables"]
            for row_id, fields in zip(table["row_unit_ids"], table["row_fields"], strict=True)}
    seen = set()
    records = []
    for item in limitations:
        key = item.row_unit_id, item.column_id
        fields = [field for field in rows.get(item.row_unit_id, []) if field["column_id"] == item.column_id]
        evidence = by_id.get(item.evidence_unit_id)
        scope = item.examined_unit_ids
        if item.evidence_binding is not None:
            verify_binding(artifact, item.evidence_binding, item.evidence_quote, item.evidence_unit_id)
        own_bound_cell = item.evidence_binding is not None and item.evidence_binding.column_id == item.column_id and item.evidence_unit_id == item.row_unit_id
        if (key in seen or len(fields) != 1 or fields[0]["raw"] != item.raw
                or fields[0]["state"] not in {"ambiguous", "blank", "not_stated"}
                or evidence is None or evidence.is_container or (not own_bound_cell and item.evidence_quote not in evidence.text)
                or len(scope) != len(set(scope)) or not set(scope).issubset(by_id)
                or item.row_unit_id not in scope or item.evidence_unit_id not in scope):
            raise ValueError("Source limitation requires exact raw, readable target, quote and examined scope")
        seen.add(key)
        # A model's failure to find a definition is only a candidate. Even an
        # explicit quote requires the dedicated human action, bound to this input.
        record = {**item.model_dump(exclude_none=True), "status": "acknowledged" if acknowledged else "candidate",
                  "usage": "description_only"}
        records.append(record)
        fields[0]["source_limitation"] = record
        fields[0]["usage"] = "description_only"
        by_id[item.row_unit_id].field_usage[item.column_id] = "description_only"
    if records:
        artifact["source_limitations"] = records


def evaluate_source_policy(artifact: dict, *, mode: PolicyMode = "strict") -> dict:
    """Evaluation only: never grants publication or changes legacy unknown counts."""
    if mode not in {"strict", "acknowledged_limits"}:
        raise ValueError("Unknown source limitation policy")
    fields = [field for table in artifact.get("tables", []) for row in table.get("row_fields", []) for field in row]
    unknown = [field for field in fields if field["state"] in {"ambiguous", "unreadable"}]
    acknowledged = [field for field in fields if (field.get("source_limitation") or {}).get("status") == "acknowledged"]
    unfinished = [field for field in unknown if field not in acknowledged]
    independent = sorted({str(issue["code"]) for issue in artifact.get("issues", [])
                          if issue.get("code") and issue["code"] != "ambiguous_cell"})
    integrity = artifact.get("content_integrity") or {}
    if integrity.get("status") in {"failed", "invalid", "incomplete"} or integrity.get("valid") is False:
        independent.append("content_integrity")
    audit = artifact.get("context_audit") or {}
    if audit.get("unresolved_count") or audit.get("status") in {"unresolved", "failed"}:
        independent.append("context_audit")
    blockers = (len(unknown) if mode == "strict" else len(unfinished)) + len(independent)
    return {"mode": mode, "semantic_unknown_count": len(unknown), "acknowledged_limit_count": len(acknowledged),
            "unfinished_count": len(unfinished), "policy_blocker_count": blockers,
            "independent_blockers": sorted(set(independent)), "eligible_for_limited_use": blockers == 0,
            "publication_enabled": False, "publication_blocker": "limited_publication_not_enabled"}
