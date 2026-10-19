"""Deterministic preflight; a machine certificate is never a human issue decision."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    _digest,
    _validated_copy,
    semantic_input_hash,
)
from app.modules.knowledge.services.semantic_context_review import (
    proposal_summary,
    validate_reference_assessments,
)
from app.modules.knowledge.services.semantic_evidence import (
    EvidenceBinding,
    source_identity,
    source_text,
    verify_binding,
)

CONTRACT = "qnu-smart-approval-v1"
POLICY_VERSION = "2026-10-19.1"
POLICY_FILE = Path(__file__).with_name("policies") / "semantic_fixture_v1.json"


def fixture_policy_for(identity: dict, proposal: dict) -> dict | None:
    """Server-owned acceptance cases, never client confidence, filenames or model flags."""
    cases = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    for case in cases:
        if case["identity"] == identity and case["proposal_hash"] == proposal.get("proposal_hash"):
            return case
    return None


def _payload_hash(proposal: dict) -> str:
    return _digest({key: proposal.get(key) for key in ("annotations", "context_review", "input_hash")})


def _blocker(code: str, message: str, **target) -> dict:
    return {"reason_code": code, "message": message, **target}


def _check_evidence(artifact: dict, items: list[dict]) -> None:
    for item in items:
        binding = EvidenceBinding.model_validate(item["evidence_binding"])
        verify_binding(artifact, binding, item["evidence_quote"], binding.source_unit_id)


def _materialize_evidence(artifact: dict, item: dict) -> dict:
    """The policy pins selectors/hashes; quotations always come from the source."""
    binding = EvidenceBinding.model_validate(item["evidence_binding"])
    text = source_text(artifact, binding.source_unit_id, binding.column_id)
    result = {**item, "evidence_quote": text[binding.start:binding.end]}
    _check_evidence(artifact, [result])
    return result


def _issue_result(artifact: dict, issue: dict, proposal: dict, trusted: bool) -> dict:
    review = proposal.get("context_review") or {}
    assessment = next((a for a in review.get("reference_assessments", []) if a["issue_id"] == issue["issue_id"]), None)
    _check_evidence(artifact, issue.get("review_evidence", []))
    if issue.get("source") != source_identity(artifact) or issue.get("input_hash") != semantic_input_hash(artifact):
        raise ValueError("ISSUE_SOURCE_MISMATCH")
    related = assessment and assessment["relevance"] == "related"
    action = "related_context_reviewed" if related else "scope_confirmed"
    # Source matching only checks integrity. Scope is proven by a pinned acceptance
    # case reviewed against this exact fixture, or remains an open human question.
    eligible = trusted and issue["kind"] in {"scope_confirmation_required", "deferred_reference"}
    if issue["kind"] == "deferred_reference" and assessment is None:
        eligible = False
    if assessment and (assessment["relevance"] == "insufficient" or (related and not assessment.get("links"))):
        eligible = False
    if assessment and assessment["relevance"] == "unrelated":
        action = "not_applicable_to_target"
    return {"issue_id": issue["issue_id"], "source_id": source_identity(artifact)["document_id"],
        "revision_id": source_identity(artifact)["revision_id"], "assertion_ids": (assessment or {}).get("assertion_ids", []) or ([issue["target"]["assertion_id"]] if issue["target"].get("assertion_id") else []),
        "evidence": issue.get("review_evidence", []), "scope": issue["target"],
        "reference_assessment": assessment, "machine_action": action if eligible else None,
        "result": "AUTO_VERIFIED" if eligible else "NEEDS_REVIEW",
        "reason_code": "FIXTURE_ACCEPTANCE_CASE" if eligible else "SEMANTIC_SCOPE_NOT_PROVEN",
        "proof": "Exact versioned fixture acceptance specification and validated evidence/targets/roles" if eligible else
            "Source span integrity alone cannot prove semantic scope"}


def _cell_results(artifact: dict, policy: dict | None) -> list[dict]:
    cases = {(c["row_unit_id"], c["column_id"]): c for c in (policy or {}).get("cells", [])}
    results = []
    for table in artifact.get("tables", []):
        for rid, fields in zip(table["row_unit_ids"], table["row_fields"], strict=True):
            for field in fields:
                if field["state"] not in {"ambiguous", "unreadable"}:
                    continue
                case = cases.get((rid, field["column_id"]))
                value = {"table_id": table["id"], "row_unit_id": rid, "column_id": field["column_id"], "raw": field["raw"],
                    "classification": "UNVERIFIED_MEANING", "result": "NEEDS_REVIEW",
                    "reason_code": "CELL_MEANING_NOT_PROVEN", "message": "Ô chưa có bằng chứng xác định ý nghĩa.", "evidence": []}
                if case and case["raw"] == field["raw"]:
                    value.update(copy.deepcopy(case))
                    value["evidence"] = [_materialize_evidence(artifact, e) for e in case["evidence"]]
                    if case.get("resolution"):
                        value["resolution"] = {k: _materialize_evidence(artifact, v) for k, v in case["resolution"].items()}
                results.append(value)
    return results


def collect_quality_findings(artifact: dict, report: dict) -> None:
    units = artifact.get("retrieval_units", {}).get("units", [])
    for issue in artifact.get("issues", []):
        if issue.get("code") == "ambiguous_cell":
            continue  # represented with exact row/column in cells
        unit_id = "qnu:" + str(issue.get("block_id", ""))
        unit = next((u for u in units if u["id"] == unit_id), {})
        native_anchor = any(str(loc.get("locator", "")).startswith("word/footnotes.xml#") for loc in unit.get("source_locations", []))
        anchored = any(unit_id in u.get("context_refs", []) for u in units)
        if issue.get("code") == "page_unresolved" and native_anchor and anchored:
            report["warnings"].append({**issue, "reason_code": "NATIVE_FOOTNOTE_ANCHOR_VERIFIED",
                "message": "Chưa xác định trang preview; còn nguyên footnote và liên kết neo Word."})
        else:
            report["blockers"].append(_blocker(str(issue.get("code", "QUALITY_ISSUE_UNCLASSIFIED")),
                "Cảnh báo nguồn chưa có bằng chứng cho phép bỏ chặn.", target=issue))
    integrity = artifact.get("content_integrity") or {}
    if integrity.get("status") in {"failed", "invalid", "incomplete"} or integrity.get("valid") is False:
        report["blockers"].append(_blocker("CONTENT_INTEGRITY_FAILED", "Toàn vẹn nội dung chưa đạt."))


def evaluate_semantics(artifact: dict, *, fixture_policy: dict | None = None) -> dict:
    """Pure, non-mutating. Caller verifies the actual canonical pair before trusting it."""
    proposal = artifact.get("semantic_annotations") or {}
    review = proposal.get("context_review") or {}
    report = {"contract": CONTRACT, "policy_version": POLICY_VERSION,
        "policy_id": "standard-document-v1", "proposal_hash": proposal.get("proposal_hash"),
        "input_hash": semantic_input_hash(artifact), "issues": [], "cells": [], "blockers": [], "warnings": []}
    blockers = report["blockers"]
    collect_quality_findings(artifact, report)
    if proposal.get("status") in {"rejected", "changes_requested", "unavailable"}:
        blockers.append(_blocker("PROPOSAL_NOT_PENDING", "Đề xuất đã bị từ chối hoặc yêu cầu sửa; cần đề xuất mới trước khi duyệt."))
    try:
        trusted = bool(fixture_policy and fixture_policy["payload_sha256"] == _payload_hash(proposal))
        if trusted:
            report.update(policy_id=fixture_policy["policy_id"], fixture_policy_sha256=_digest(fixture_policy))
        if proposal.get("status") in {"proposed", "empty"} and (
                _digest({k: v for k, v in proposal.items() if k != "proposal_hash"}) != proposal.get("proposal_hash")
                or proposal.get("input_hash") != semantic_input_hash(artifact)):
            raise ValueError("PROPOSAL_STALE")
        annotations = SemanticAnnotations.model_validate(proposal.get("annotations") or {})
        validated = _validated_copy(artifact, annotations)
        validate_reference_assessments(artifact, review, annotations.notes)
        report["issues"] = [_issue_result(artifact, i, proposal, trusted) for i in review.get("issues", [])]
        if not trusted and proposal.get("status") != "verified" and (annotations.notes or annotations.cells or annotations.limitations) and not report["issues"]:
            blockers.append(_blocker("SEMANTIC_SCOPE_NOT_PROVEN", "Diễn giải chưa có quyết định đối chiếu phạm vi hợp lệ."))
        if proposal.get("status") == "verified":
            opened = set(proposal_summary(proposal)["open_issue_ids"])
            report["issues"] = [i for i in report["issues"] if i["issue_id"] in opened]
        for issue in report["issues"]:
            if issue["result"] != "AUTO_VERIFIED":
                blockers.append(_blocker(issue["reason_code"], "Quan hệ chưa đủ căn cứ xác định phạm vi.", issue_id=issue["issue_id"]))
        if review.get("packets_complete", review.get("coverage_complete", True)) is False or review.get("scope") == "selected_tables":
            blockers.append(_blocker("CONTEXT_COVERAGE_INCOMPLETE", "Chưa đối chiếu đầy đủ phạm vi tài liệu."))
        if not review.get("contract") and review.get("unresolved"):
            blockers.append(_blocker("LEGACY_CONTEXT_UNRESOLVED", "Còn ngữ cảnh chưa được giải quyết."))
        report["cells"] = _cell_results(validated if proposal.get("status") == "verified" else artifact,
            fixture_policy if trusted else None)
        resolved = annotations.model_dump()
        for cell in report["cells"]:
            if cell["classification"] == "RESOLVABLE_MEANING" and cell.get("resolution"):
                resolved["notes"].append(cell["resolution"]["note"])
                resolved["cells"].append(cell["resolution"]["cell"])
                continue
            # Limited publication remains a separate disabled policy, including
            # for trusted test fixtures. Unknown values never become numeric facts.
            code = "SOURCE_LIMITED_PUBLICATION_DISABLED" if cell["result"] == "SOURCE_LIMITATION" else cell["reason_code"]
            blockers.append(_blocker(code, cell["message"], row_unit_id=cell["row_unit_id"], column_id=cell["column_id"]))
        _validated_copy(artifact, SemanticAnnotations.model_validate(resolved))
        if resolved != annotations.model_dump():
            report["resolved_annotations"] = resolved
        if annotations.limitations or artifact.get("source_limitations"):
            blockers.append(_blocker("SOURCE_LIMITED_PUBLICATION_DISABLED", "Chính sách xuất bản có giới hạn chưa được bật."))
    except (ValueError, KeyError, TypeError) as exc:
        report["issues"] = [{"result": "INVALID", "reason_code": str(exc), "issue_id": "integrity"}]
        blockers.append(_blocker("SEMANTIC_VALIDATION_INVALID", "Bằng chứng, đề xuất hoặc đối tượng không khớp nguồn."))
    report["auto_verified_count"] = sum(i["result"] == "AUTO_VERIFIED" for i in report["issues"])
    report["source_limitation_count"] = sum(c["result"] == "SOURCE_LIMITATION" for c in report["cells"])
    report["eligible"] = not blockers
    return report


def verify_certificate(base: dict, proposal: dict, certificate: dict, identity: dict) -> None:
    artifact = {**base, "semantic_annotations": proposal}
    expected = evaluate_semantics(artifact, fixture_policy=fixture_policy_for(identity, proposal))
    if not expected["eligible"] or certificate != expected:
        raise ValueError("SMART_VALIDATION_CERTIFICATE_MISMATCH")
