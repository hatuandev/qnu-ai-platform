"""Untrusted offline proposals enter the existing draft lifecycle, never approval."""
from __future__ import annotations

import asyncio
import copy

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.normalization.qnu_markdown import QnuStructuredDocument
from app.modules.knowledge.schemas import SemanticCheckpointImportRequest
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    _digest,
    _validated_copy,
    semantic_input_hash,
    stage_semantic_annotations,
    verify_pending_envelope,
)
from app.modules.knowledge.services.semantic_assertions import assertion_identity
from app.modules.knowledge.services.semantic_context_review import (
    CONTRACT,
    make_issue,
    validate_reference_assessments,
)
from app.modules.knowledge.services.semantic_evidence import (
    EvidenceBinding,
    make_binding,
    source_identity,
    source_text,
    verify_source_document,
)

CONTRACT_IMPORT = "qnu-semantic-checkpoint-v1"


def rebind_checkpoint(upload: dict, base: dict, document: QnuStructuredDocument) -> tuple[SemanticAnnotations, dict, dict]:
    """Exact pair hashes AND complete projection identity; never match by filename."""
    if set(upload) != {"contract", "source_artifact", "proposal"} or upload["contract"] != CONTRACT_IMPORT:
        raise ValueError("CHECKPOINT_CONTRACT_UNSUPPORTED")
    source, proposal = upload["source_artifact"], upload["proposal"]
    if (proposal.get("status") not in {"proposed", "empty"} or "review" in proposal
            or proposal.get("proposal_hash") != _digest({k:v for k,v in proposal.items() if k != "proposal_hash"})
            or proposal.get("input_hash") != semantic_input_hash(source)):
        raise ValueError("CHECKPOINT_PENDING_ENVELOPE_INVALID")
    for key in ("sha256", "structured_sha256"):
        if not source_identity(source).get(key) or source_identity(source)[key] != source_identity(base).get(key):
            raise ValueError("CHECKPOINT_SOURCE_PAIR_MISMATCH")
    manifest = verify_source_document(source, document)
    if (manifest.model_dump() != base["retrieval_units"] or source["tables"] != base["tables"]
            or source["content_hash"] != base["content_hash"]):
        raise ValueError("CHECKPOINT_EXACT_PROJECTION_REQUIRED")
    annotations = SemanticAnnotations.model_validate(proposal["annotations"])
    if (any(note.assertion_version != 1 for note in annotations.notes)
            or any(item.evidence_binding is None for items in (annotations.notes, annotations.cells, annotations.limitations) for item in items)):
        raise ValueError("CHECKPOINT_REQUIRES_VERSIONED_BOUND_ANNOTATIONS")
    if (proposal.get("model") or {}).get("selector_contract"):
        from app.modules.knowledge.services.semantic_binding import selector_type
        selector_type(proposal["model"]["selector_contract"])
    _validated_copy(source, annotations)
    original_review = proposal.get("context_review") or {}
    if original_review.get("contract") not in {None, CONTRACT}:
        raise ValueError("CHECKPOINT_CONTEXT_CONTRACT_UNSUPPORTED")
    validate_reference_assessments(source, original_review, annotations.notes)

    def binding(raw):
        old = EvidenceBinding.model_validate(raw)
        text = source_text(source, old.source_unit_id, old.column_id)
        from app.modules.knowledge.services.semantic_evidence import verify_binding
        verify_binding(source, old, text[old.start:old.end], old.source_unit_id)
        return make_binding(base, old.source_unit_id, old.start, old.end, old.column_id).model_dump()

    def bindings(value):
        if isinstance(value, list):
            return [bindings(item) for item in value]
        if isinstance(value, dict):
            if "coordinate_space" in value and "evidence_id" in value:
                return binding(value)
            return {key: bindings(item) for key, item in value.items()}
        return value

    rebound = SemanticAnnotations.model_validate(bindings(annotations.model_dump()))
    ids = {assertion_identity(old): assertion_identity(new)
        for old, new in zip(annotations.notes, rebound.notes, strict=True) if old.assertion_version == 1}
    review = {key: copy.deepcopy(original_review[key]) for key in (
        "scope", "target_table_ids", "coverage_complete", "packets_complete", "unresolved") if key in original_review}
    issues, issue_ids = [], {}
    for old in original_review.get("issues", []):
        checked = make_issue(source, old["kind"], old["unit_ids"], old["target"], old["reason"])
        if old["issue_id"] != checked["issue_id"]:
            raise ValueError("CHECKPOINT_ISSUE_ID_INVALID")
        target = copy.deepcopy(old["target"])
        if "assertion_id" in target:
            if target["assertion_id"] not in ids:
                raise ValueError("CHECKPOINT_ASSERTION_TARGET_INVALID")
            target["assertion_id"] = ids[target["assertion_id"]]
        new = make_issue(base, old["kind"], old["unit_ids"], target, old["reason"])
        issue_ids[old["issue_id"]] = new["issue_id"]
        issues.append(new)
    review["issues"] = issues
    review["reference_assessments"] = bindings(original_review.get("reference_assessments", []))
    for item in review["reference_assessments"]:
        item["issue_id"] = issue_ids[item["issue_id"]]
        item["assertion_ids"] = [ids[uid] for uid in item["assertion_ids"]]
        for link in item.get("links", []):
            link["assertion_id"] = ids[link["assertion_id"]]
    labels = original_review.get("display_labels") or {}
    review["display_labels"] = {"assertions": {ids[k]:v for k,v in labels.get("assertions", {}).items() if k in ids},
        "issues": {issue_ids[k]:v for k,v in labels.get("issues", {}).items() if k in issue_ids}}
    audit = {"origin": "offline_checkpoint_import", "offline_proposal_hash": proposal["proposal_hash"],
        "offline_source": source_identity(source), "issue_id_map": issue_ids, "assertion_id_map": ids,
        "new_model_calls": 0}
    return rebound, review, audit


async def import_semantic_checkpoint(db: AsyncSession, collection_id: str, source_id: str, revision_id: str,
        payload: SemanticCheckpointImportRequest, actor: AuthActor) -> KnowledgeSourceRevision:
    from app.modules.knowledge.services.qnu_serving import (
        validate_projection_binding,
        verify_revision_pair,
    )
    from app.modules.knowledge.services.semantic_store import (
        proposal_base,
        verify_effective_projection,
    )
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
    from app.modules.knowledge.services.source_reparse import ensure_source_idle, lock_source

    if not actor.authenticated or not actor.actor_id or not actor.has_permission("ai.knowledge.update"):
        raise AppException("Cần tài khoản có quyền hiệu đính nguồn.", code="PERMISSION_DENIED", status_code=403)
    await lock_source(db, source_id)
    await ensure_source_idle(db, source_id)
    _, revision, artifact = await source_ingestion_service._get_review_target(
        db, collection_id, source_id, revision_id, actor.tenant_id, actor.workspace_id, actor.actor_id)
    if revision.status != "review_required":
        raise AppException("Cần revision nháp chưa xuất bản.", code="SEMANTIC_DRAFT_REQUIRED", status_code=409)
    before = copy.deepcopy(revision.parse_provenance)
    try:
        document = await verify_revision_pair(revision)
        validate_projection_binding(revision, artifact)
        await verify_effective_projection(revision, artifact, document)
        base = await proposal_base(revision, artifact, document)
        annotations, review, audit = rebind_checkpoint(payload.checkpoint, base, document)
        current = artifact.get("semantic_annotations") or {}
        if current.get("status") in {"proposed", "empty"}:
            if (current.get("model") or {}).get("offline_proposal_hash") == audit["offline_proposal_hash"]:
                verify_pending_envelope(base | {"semantic_annotations": current}, current["proposal_hash"], actor.actor_id, payload.comment)
                return revision
            raise AppException("Hãy yêu cầu sửa hoặc từ chối đề xuất hiện tại trước.", code="SEMANTIC_PROPOSAL_EXISTS", status_code=409)
        if current and (current.get("status") == "verified" or payload.expected_semantic_proposal_hash != current.get("proposal_hash")):
            raise AppException("Đề xuất hiện tại đã thay đổi hoặc đã áp dụng.", code="SEMANTIC_PROPOSAL_STALE", status_code=409)
        revised = copy.deepcopy(artifact)
        stage_semantic_annotations(revised, annotations, base_artifact=base, context_review=review,
            model={**audit, "staged_by": actor.actor_id, "comment": payload.comment})
        revision.parse_provenance = {**before, "structured_artifact": revised}
        await db.commit()
    except (ValueError, KeyError, TypeError) as exc:
        await db.rollback()
        raise AppException("Checkpoint không khớp nguồn, revision hoặc bằng chứng. Chưa tạo pending proposal.",
            code="SEMANTIC_CHECKPOINT_INVALID", status_code=422) from exc
    except (Exception, asyncio.CancelledError):
        await db.rollback()
        raise
    await db.refresh(revision)
    return revision
