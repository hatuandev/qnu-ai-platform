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
from app.modules.knowledge.schemas import SourceContextEditRequest


async def create_context_revision(db: AsyncSession, collection_id: str, source_id: str, revision_id: str,
                                  request: SourceContextEditRequest, actor: AuthActor) -> KnowledgeSourceRevision:
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service

    revisions = await source_ingestion_service.get_source_revisions(db, collection_id, source_id, actor.tenant_id, actor.workspace_id)
    revision = next((item for item in revisions if item.id == revision_id), None)
    if not revision:
        raise AppException("Không tìm thấy bản nguồn.", code="SOURCE_REVISION_NOT_FOUND", status_code=404)
    return await source_ingestion_service.update_revision_content(
        db, collection_id, source_id, revision_id, revision.canonical_markdown or "",
        actor.tenant_id, actor.workspace_id, context_edits=request, actor_id=actor.actor_id)


def review_context_artifact(artifact: dict[str, Any], decision: str, actor_id: str, comment: str | None) -> dict[str, Any]:
    revised = copy.deepcopy(artifact)
    review = {"decision": decision, "actor_id": actor_id, "comment": comment, "at": datetime.now(UTC).isoformat()}
    revised["context_audit"]["review"] = review
    if decision == "approved":
        for fact in revised["facts"]:
            raw = fact["raw_data"]
            if raw.get("context_review"):
                raw["context_review"] = {**raw["context_review"], "status": "verified", "review": review}
                raw["temporal_context"]["status"] = "verified"
        for field in ("issued_date", "issued_year", "subject_years"):
            evidence = revised["temporal_metadata"][field].get("evidence")
            if isinstance(evidence, dict) and evidence.get("actor_id"):
                revised["temporal_metadata"][field]["status"] = "verified"
    revised["fact_set_hash"] = fact_set_hash(revised["facts"])
    return revised


def fact_set_hash(facts: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(facts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def query_projection(raw: dict[str, Any]) -> dict[str, Any]:
    temporal, qualifiers = raw.get("temporal_context") or {}, raw.get("qualifiers") or {}
    year = temporal.get("year")
    return {"entity_code": raw.get("entity_code"), "attribute_code": raw.get("attribute_code"),
            "applicability_year": year if temporal.get("type") == "year" and isinstance(year, int) else None,
            "temporal_type": temporal.get("type"), "admission_method": qualifiers.get("method"), "unit": qualifiers.get("unit")}


def apply_context_edits(artifact: dict[str, Any], request: SourceContextEditRequest, actor_id: str,
                        base_artifact: dict[str, Any] | None = None) -> dict[str, Any]:
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
                                       "status": "proposed", "evidence": "human_correction"}
            raw["year"] = str(year) if year else None
        raw["qualifiers"] = {**raw.get("qualifiers", {}),
                             **{key: changes[key] for key in ("method", "unit") if key in changes}}
        raw["context_review"] = {**audit, "original_fact_id": edit.fact_id}
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
    revised["context_audit"] = audit
    revised["review"] = {"status": "required"}
    revised["fact_set_hash"] = fact_set_hash(revised["facts"])
    return revised
