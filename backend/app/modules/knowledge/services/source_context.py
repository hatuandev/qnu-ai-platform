"""Human corrections are revision-bound, audited and retain extraction evidence."""

import copy
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.normalization.retrieval_models import UnitManifest
from app.modules.knowledge.normalization.retrieval_units import (
    manifest_digest,
)
from app.modules.knowledge.schemas import SourceContextEditRequest
from app.modules.knowledge.services.temporal_metadata import YEAR
from app.modules.knowledge.services.unit_annotation import approve_unit_annotations


async def create_context_revision(db: AsyncSession, collection_id: str, source_id: str, revision_id: str,
                                  request: SourceContextEditRequest, actor: AuthActor) -> KnowledgeSourceRevision:
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service

    revisions = await source_ingestion_service.get_source_revisions(db, collection_id, source_id, actor.tenant_id, actor.workspace_id)
    revision = next((item for item in revisions if item.id == revision_id), None)
    if not revision:
        raise AppException("Không tìm thấy bản nguồn.", code="SOURCE_REVISION_NOT_FOUND", status_code=404)
    return await source_ingestion_service.update_revision_content(
        db, collection_id, source_id, revision_id, revision.canonical_markdown or "",
        actor.tenant_id, actor.workspace_id, context_edits=request, actor_id=actor.actor_id,
        expected_canonical_hash=revision.canonical_hash)


def review_context_artifact(artifact: dict[str, Any], decision: str, actor_id: str, comment: str | None) -> dict[str, Any]:
    revised = copy.deepcopy(artifact)
    review = {"decision": decision, "actor_id": actor_id, "comment": comment, "at": datetime.now(UTC).isoformat()}
    revised["context_audit"]["review"] = review
    if decision == "approved":
        manifest = revised.get("retrieval_units")
        for unit in (manifest or {}).get("units", []):
            if unit["id"] in revised["context_audit"].get("unit_ids", []):
                unit["temporal"]["status"] = "verified"
        if manifest:
            revised["unit_manifest_hash"] = manifest_digest(UnitManifest.model_validate(manifest))
        for fact in revised["facts"]:
            raw = fact["raw_data"]
            if raw.get("context_review"):
                raw["context_review"] = {**raw["context_review"], "status": "verified", "review": review}
                raw["temporal_context"]["status"] = "verified"
                corrected = reviewed_human_temporal(raw)
                if corrected is not None:
                    raw["temporal_context"] = corrected
                    _reviewed_cell_scope(revised, raw, corrected)
        for field in ("issued_date", "issued_year", "subject_years"):
            evidence = revised["temporal_metadata"][field].get("evidence")
            if isinstance(evidence, dict) and evidence.get("actor_id"):
                revised["temporal_metadata"][field]["status"] = "verified"
    revised["fact_set_hash"] = fact_set_hash(revised["facts"])
    if decision == "approved":
        approve_unit_annotations(revised)
    return revised


def fact_set_hash(facts: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(facts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def reviewed_human_temporal(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Adapt the server's audited correction contract, including older year-only facts.

    This is review evidence, not a fabricated quote from the source. Projection
    never copies this audit structure from document metadata.
    """
    temporal, audit = raw.get("temporal_context"), raw.get("context_review")
    if not isinstance(temporal, dict) or not isinstance(audit, dict):
        return None
    review = audit.get("review")
    if (temporal.get("evidence") != "human_correction" or temporal.get("status") != "verified"
            or audit.get("status") != "verified" or not isinstance(review, dict)
            or review.get("decision") != "approved"
            or any(not isinstance(value, str) or not value.strip()
                   for value in (audit.get("actor_id"), audit.get("reason"), audit.get("at"),
                                 review.get("actor_id"), review.get("at")))):
        return None
    year = temporal.get("year")
    if year is not None and (not isinstance(year, int) or isinstance(year, bool) or not 1900 <= year <= 2099):
        return None
    if temporal.get("type") != ("year" if year is not None else "unknown"):
        return None
    return {**temporal, "years": [year] if year is not None else [],
            "role": "data" if year is not None else "unknown", "scope_level": "field",
            "review_basis": "human_review"}


def fact_temporal_context(raw: dict[str, Any]) -> dict[str, Any]:
    temporal = dict(raw.get("temporal_context") or {})
    if temporal.get("evidence") != "human_correction":
        return temporal
    return reviewed_human_temporal(raw) or {**temporal, "status": "ambiguous", "role": "unknown", "years": []}


def _reviewed_cell_scope(artifact: dict[str, Any], raw: dict[str, Any], scope: dict[str, Any]) -> None:
    """Keep row-answer coordinates on the same reviewed fact scope as evidence."""
    for table in artifact.get("tables") or []:
        if table.get("id") != raw.get("table_id"):
            continue
        row, column = raw.get("row_index"), raw.get("column_index")
        rows, ids = table.get("row_fields") or [], table.get("row_unit_ids") or []
        if (not isinstance(row, int) or not isinstance(column, int) or not 0 <= row < len(rows)
                or not 0 <= column < len(rows[row]) or row >= len(ids)
                or ids[row] != raw.get("source_unit_id")):
            return
        field = rows[row][column]
        if field.get("column_index") != column:
            return
        field["temporal"] = {**scope, "data_years": list(scope["years"])}
        return


def query_projection(raw: dict[str, Any]) -> dict[str, Any]:
    temporal, qualifiers = fact_temporal_context(raw), raw.get("qualifiers") or {}
    year = temporal.get("year")
    # Only a review-verified data year is an applicability constraint. A header
    # mention or proposed declaration must not silently filter other years.
    verified = temporal.get("status") == "verified" and temporal.get("role", "data") == "data"
    return {"entity_code": raw.get("entity_code"), "attribute_code": raw.get("attribute_code"),
            "applicability_year": year if verified and temporal.get("type") == "year"
            and isinstance(year, int) and not isinstance(year, bool) else None,
            "temporal_type": temporal.get("type"), "admission_method": qualifiers.get("method"), "unit": qualifiers.get("unit")}


def apply_context_edits(artifact: dict[str, Any], request: SourceContextEditRequest, actor_id: str,
                        base_artifact: dict[str, Any] | None = None) -> dict[str, Any]:
    if request.expected_unit_manifest_hash and (base_artifact or artifact).get("unit_manifest_hash") != request.expected_unit_manifest_hash:
        raise AppException("Bộ đơn vị nguồn đã thay đổi; hãy tải lại trước khi hiệu đính.", code="SOURCE_UNITS_CHANGED", status_code=409)
    revised = copy.deepcopy(artifact)
    audit = {"actor_id": actor_id, "reason": request.reason, "at": datetime.now(UTC).isoformat(),
             "base_fact_set_hash": request.expected_fact_set_hash, "status": "proposed"}
    facts = {fact["id"]: fact for fact in revised["facts"]}
    if len({edit.fact_id for edit in request.facts}) != len(request.facts):
        raise AppException("Một fact bị sửa nhiều lần trong cùng yêu cầu.", code="DUPLICATE_FACT_CONTEXT", status_code=422)
    for edit in request.facts:
        fact = facts.get(edit.fact_id)
        if not fact and base_artifact:
            original = next((item for item in base_artifact["facts"] if item["id"] == edit.fact_id), None)
            if original:
                keys = ("page_number", "table_id", "row_index", "column_index", "header_path", "raw_value")
                candidates = [item for item in facts.values() if item["entity_name"] == original["entity_name"]
                              and item["attribute_value"] == original["attribute_value"]
                              and all(item["raw_data"].get(key) == original["raw_data"].get(key) for key in keys)]
                fact = candidates[0] if len(candidates) == 1 else None
        if not fact:
            raise AppException("Fact không thuộc bản đang hiệu đính; hãy nâng ngữ cảnh và tải lại trước.", code="FACT_CONTEXT_NOT_FOUND", status_code=409)
        raw = fact["raw_data"]
        raw["extracted_context"] = copy.deepcopy(raw.get("extracted_context") or
                                                 {key: raw.get(key) for key in ("temporal_context", "qualifiers")})
        changes = edit.model_dump(exclude_unset=True)
        if "year" in changes:
            year = changes["year"]
            raw["temporal_context"] = {"type": "year" if year else "unknown", "year": year,
                                       "years": [year] if year is not None else [],
                                       "role": "data" if year is not None else "unknown", "scope_level": "field",
                                       "status": "proposed", "evidence": "human_correction"}
            raw["year"] = str(year) if year else None
        raw["qualifiers"] = {**raw.get("qualifiers", {}),
                             **{key: changes[key] for key in ("method", "unit") if key in changes}}
        raw["context_review"] = {**audit, "original_fact_id": edit.fact_id}
        if raw.get("context_ambiguous") and edit.method:
            raw["context_ambiguous"] = False
    temporal = revised["temporal_metadata"]
    revised["extracted_temporal_metadata"] = copy.deepcopy(artifact.get("extracted_temporal_metadata") or temporal)
    changes = request.model_dump(exclude_unset=True)
    if "issued_date" in changes:
        value = request.issued_date.isoformat() if request.issued_date else None
        temporal["issued_date"] = {"value": value, "status": "proposed", "precision": "day" if value else None,
                                   "evidence": audit}
        temporal["issued_year"] = {"value": request.issued_date.year if request.issued_date else None,
                                   "status": "proposed", "evidence": audit}
    if "issued_year" in changes:
        if request.issued_date and request.issued_year != request.issued_date.year:
            raise AppException("Ngày và năm ban hành mâu thuẫn.", code="DOCUMENT_DATE_YEAR_CONFLICT", status_code=422)
        temporal["issued_year"] = {"value": request.issued_year, "status": "proposed", "evidence": audit}
    issued_date = temporal["issued_date"].get("value")
    if issued_date and temporal["issued_year"].get("value") != int(issued_date[:4]):
        raise AppException("Ngày và năm ban hành mâu thuẫn; hãy sửa hoặc xóa ngày đầy đủ.", code="DOCUMENT_DATE_YEAR_CONFLICT", status_code=422)
    if "subject_years" in changes:
        temporal["subject_years"] = {"values": request.subject_years or [], "status": "proposed", "evidence": audit}
    manifest = resolve_unit_manifest_from_revision(revised)
    previous_units = {unit["id"]: unit for unit in (base_artifact or {}).get("retrieval_units", {}).get("units", [])}
    for unit in manifest.units:
        previous = previous_units.get(unit.id)
        if previous and previous["text"] == unit.text:
            from app.modules.knowledge.normalization.retrieval_models import TemporalScope

            unit.temporal = TemporalScope.model_validate(previous["temporal"])
    if request.units:
        by_id = {unit.id: unit for unit in manifest.units}
        if len({edit.unit_id for edit in request.units}) != len(request.units):
            raise AppException("Một đơn vị nguồn bị sửa nhiều lần.", code="DUPLICATE_UNIT_CONTEXT", status_code=422)
        for edit in request.units:
            unit = by_id.get(edit.unit_id)
            if not unit or edit.evidence_quote not in unit.text or not set(edit.data_years).issubset(
                    {int(year) for year in YEAR.findall(edit.evidence_quote)}):
                raise AppException("Ngữ cảnh phải có trích đoạn khớp đúng đơn vị nguồn.", code="UNIT_CONTEXT_INVALID", status_code=422)
            unit.temporal.data_years = edit.data_years
            unit.temporal.role = edit.role
            unit.temporal.evidence_quote = edit.evidence_quote
            unit.temporal.status = "proposed"
        audit["unit_ids"] = [edit.unit_id for edit in request.units]
    revised["retrieval_units"] = manifest.model_dump()
    revised["unit_manifest_hash"] = manifest_digest(manifest)
    revised["context_audit"] = audit
    revised["review"] = {"status": "required"}
    revised["fact_set_hash"] = fact_set_hash(revised["facts"])
    return revised


def resolve_unit_manifest_from_revision(artifact: dict[str, Any]) -> UnitManifest:
    """Stored units are already bound to the artifact content hash."""
    # Legacy artifacts can have no units; callers materialize the new revision
    # before corrections. Do not reconstruct lost source spans from prose here.
    return UnitManifest.model_validate(artifact["retrieval_units"]) if artifact.get("retrieval_units") else UnitManifest(
        canonical_hash=artifact.get("content_hash", ""))
