"""Authenticated one-click source approval inside the existing source lock/transaction."""
from __future__ import annotations

import asyncio
import copy
import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.schemas import SmartApprovalRequest
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    _digest,
    _validated_copy,
)
from app.modules.knowledge.services.semantic_store import (
    identity,
    proposal_base,
    record_bulk_decision,
)
from app.modules.knowledge.services.smart_approval import (
    CONTRACT,
    POLICY_VERSION,
    collect_quality_findings,
    evaluate_semantics,
    fixture_policy_for,
)


def _require_current(revision: KnowledgeSourceRevision, artifact: dict, request: SmartApprovalRequest) -> None:
    if (request.expected_canonical_hash != revision.canonical_hash
            or request.expected_semantic_proposal_hash != (artifact.get("semantic_annotations") or {}).get("proposal_hash")
            or request.policy_version != POLICY_VERSION):
        raise AppException("Nội dung, đề xuất hoặc chính sách đã thay đổi; hãy tải lại trước khi duyệt.",
            code="SMART_APPROVAL_STALE", status_code=409)


def _quality_gate(revision: KnowledgeSourceRevision, artifact: dict, validation: dict) -> list[dict]:
    """Run the real approval guard on detached copies before any Storage/DB write."""
    from types import SimpleNamespace

    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service

    try:
        proposal = artifact.get("semantic_annotations") or {}
        if proposal.get("status") == "proposed" and validation["eligible"]:
            artifact = _validated_copy(artifact, SemanticAnnotations.model_validate(
                validation.get("resolved_annotations", proposal["annotations"])))
            artifact["semantic_annotations"] = {**proposal, "status": "verified", "review": {
                "action": "bulk_acceptance_v1", "actor_id": "preflight-only", "at": "preflight-only",
                "machine_validation": validation}}
        # These are detached values, never an ORM instance/commit or a human audit.
        detached = SimpleNamespace(**{c.key: copy.deepcopy(getattr(revision, c.key)) for c in revision.__table__.columns})
        source_ingestion_service._apply_review_decision(SimpleNamespace(status="pending"), detached,
            artifact, "approved", "Bulk approval preflight", "preflight-only", proposal.get("proposal_hash"))
    except AppException as exc:
        return [{"reason_code": exc.code, "message": exc.message}]
    return []


def _verify_cached_cells(artifact: dict, base: dict) -> None:
    def cells(value: dict) -> list:
        return [(t["id"], rid, [(f["column_id"], f["raw"], f["state"]) for f in fields])
            for t in value.get("tables", []) for rid, fields in zip(t["row_unit_ids"], t["row_fields"], strict=True)]
    # Existing effective annotations are separately replay-verified. Pending
    # annotations confer no authority to alter the canonical cells beforehand.
    if not artifact.get("semantic_effective") and cells(artifact) != cells(base):
        raise AppException("Ô dữ liệu dẫn xuất không khớp bản chuẩn; cần đối soát lại.",
            code="SMART_APPROVAL_PROJECTION_MISMATCH", status_code=409)


async def _verify_origin(revision: KnowledgeSourceRevision) -> None:
    data = await storage_service.get(revision.snapshot_storage_path)
    if data is None or hashlib.sha256(data).hexdigest() != revision.origin_file_hash:
        raise AppException("Tệp nguồn không còn khớp hash của phiên bản; cần đối soát lại.",
            code="SMART_APPROVAL_SOURCE_MISMATCH", status_code=409)


async def smart_approve(db: AsyncSession, collection_id: str, source_id: str, revision_id: str,
                        request: SmartApprovalRequest, actor: AuthActor) -> dict:
    from app.modules.knowledge.services.qnu_serving import verify_approval_pair
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
    from app.modules.knowledge.services.source_reparse import ensure_source_idle, lock_source

    if not actor.authenticated or not actor.actor_id or not actor.has_permission("ai.knowledge.update"):
        raise AppException("Bạn chưa có quyền duyệt nguồn.", code="FORBIDDEN", status_code=403)
    try:
        await lock_source(db, source_id)
        await ensure_source_idle(db, source_id)
        binding = await source_ingestion_service.get_source(db, collection_id, source_id, actor.tenant_id, actor.workspace_id)
        await db.refresh(binding)
        rev = (await db.scalars(select(KnowledgeSourceRevision).where(
            KnowledgeSourceRevision.id == revision_id, KnowledgeSourceRevision.binding_id == source_id
        ).execution_options(populate_existing=True))).one_or_none()
        if rev is None:
            raise AppException("Không tìm thấy phiên bản nguồn.", code="SOURCE_REVISION_NOT_FOUND", status_code=404)
        artifact = (rev.parse_provenance or {}).get("structured_artifact") or {}
        _require_current(rev, artifact, request)
        await _verify_origin(rev)
        request_hash = _digest({"collection_id": collection_id, "source_id": source_id, "revision_id": revision_id,
            "actor_id": actor.actor_id, "canonical_hash": request.expected_canonical_hash,
            "proposal_hash": request.expected_semantic_proposal_hash, "policy_version": request.policy_version,
            "comment": request.comment})
        receipt = (rev.parse_provenance or {}).get("smart_approval")
        if receipt:
            if receipt["request_hash"] != request_hash or rev.status != "ready" or binding.active_source_revision_id != rev.id:
                raise AppException("Quyết định đã thay đổi; hãy tải lại phiên bản.", code="SMART_APPROVAL_CONFLICT", status_code=409)
            await verify_approval_pair(rev, "approved")
            await db.rollback()
            return {**receipt["result"], "idempotent": True}
        binding, rev, artifact = await source_ingestion_service._get_review_target(
            db, collection_id, source_id, revision_id, actor.tenant_id, actor.workspace_id, actor.actor_id)
        await verify_approval_pair(rev, "approved")
        base = await proposal_base(rev, artifact) if artifact.get("input_format") == "qnu-rag-projection/v1" else artifact
        _verify_cached_cells(artifact, base)
        base["semantic_annotations"] = copy.deepcopy(artifact.get("semantic_annotations"))
        policy = await asyncio.to_thread(fixture_policy_for, identity(rev), base.get("semantic_annotations") or {})
        validation = await asyncio.to_thread(evaluate_semantics, base, fixture_policy=policy)
        blockers = list(validation["blockers"])
        current_quality = {"blockers": [], "warnings": []}
        collect_quality_findings(artifact, current_quality)
        blockers.extend(b for b in current_quality["blockers"] if b not in blockers)
        # No warning category is globally exempted. Keep all independent quality failures.
        quality = rev.quality_report or {}
        if quality.get("overall_status") in {"failed", "error"} or quality.get("status") in {"failed", "invalid"}:
            blockers.append({"reason_code": "QUALITY_GATE_FAILED", "message": "Bản bóc tách chưa đạt kiểm tra chất lượng."})
        for flag in quality.get("warning_flags", []):
            if flag in {"tables_detected_but_missing_in_markdown", "critically_low_text_density", "mojibake_or_font_corruption_detected"}:
                blockers.append({"reason_code": flag, "message": "Có dấu hiệu mất bảng, mất nội dung hoặc lỗi ký tự; cần đối chiếu nguồn."})
        for issue in quality.get("issues", []):
            if issue.get("severity") in {"error", "critical", "blocking"}:
                blockers.append({"reason_code": issue["code"], "message": issue.get("message", "Kiểm tra chất lượng không đạt.")})
        if not blockers:
            blockers.extend(_quality_gate(rev, copy.deepcopy(artifact), validation))
        result = {"contract": CONTRACT, "source_id": source_id, "revision_id": revision_id,
            "approved": False, "idempotent": False, "validation": validation, "blockers": blockers,
            "message": f"Chưa thể chấp thuận: {len(blockers)} vấn đề cần kiểm tra." if blockers else "Kiểm tra đạt; chưa ghi quyết định."}
        if blockers or request.dry_run:
            await db.rollback()
            return result
        comment = request.comment or "Chấp thuận hàng loạt sau kiểm tra tự động; không xác nhận đã đọc từng vấn đề."
        if (artifact.get("semantic_annotations") or {}).get("status") == "proposed":
            artifact = await record_bulk_decision(rev, artifact, validation, actor.actor_id, comment)
        source_ingestion_service._apply_review_decision(binding, rev, artifact, "approved", comment,
            actor.actor_id, request.expected_semantic_proposal_hash)
        result.update(approved=True, message="Đã chấp thuận tài liệu thành công.")
        receipt = {"contract": CONTRACT, "actor_id": actor.actor_id, "action": "bulk_acceptance_v1",
            "at": datetime.now(UTC).isoformat(), "request_hash": request_hash,
            "idempotency_key": request.idempotency_key, "canonical_hash": rev.canonical_hash,
            "origin_file_hash": rev.origin_file_hash,
            "proposal_hash": request.expected_semantic_proposal_hash, "policy_version": POLICY_VERSION,
            "transaction_result": "committed", "result": result}
        rev.parse_provenance = {**rev.parse_provenance, "smart_approval": receipt}
        await db.commit()
        return result
    except BaseException:
        await db.rollback()
        raise
