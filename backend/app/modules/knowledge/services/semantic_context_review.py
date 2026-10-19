"""Versioned context issues and source-bound human intent; never model approval."""
import copy
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.exceptions import AppException
from app.modules.knowledge.services.semantic_evidence import (
    EvidenceBinding,
    digest,
    make_binding,
    source_identity,
    source_text,
    verify_binding,
)

CONTRACT = "qnu-context-review-v2"


class ContextDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issue_id: str
    target: dict[str, str | list[str]]
    action: Literal["scope_confirmed", "not_applicable_to_target"]
    evidence_binding: EvidenceBinding
    evidence_quote: str = Field(min_length=3, max_length=10000)
    reason: str = Field(min_length=3, max_length=2000)


def make_issue(artifact: dict, kind: str, unit_ids: list[str], target: dict, reason: str) -> dict:
    from app.modules.knowledge.services.semantic_annotations import semantic_input_hash

    canonical = {key: sorted(set(value)) if isinstance(value, list) else value for key, value in target.items()}
    identity = {"contract": CONTRACT, "source": source_identity(artifact), "input_hash": semantic_input_hash(artifact),
        "kind": kind, "unit_ids": sorted(set(unit_ids)), "target": canonical}
    evidence = []
    if kind in {"scope_confirmation_required", "deferred_reference"}:
        for unit_id in identity["unit_ids"]:
            text = source_text(artifact, unit_id)
            if 3 <= len(text) <= 10000:
                evidence.append({"evidence_binding": make_binding(artifact, unit_id, 0, len(text)).model_dump(), "evidence_quote": text})
    return {"issue_id": "ctxissue:" + digest(identity), **identity, "reason": reason, "review_evidence": evidence}


def normalize_review(artifact: dict, review: dict | None, previous: dict | None = None) -> dict | None:
    if review is None:
        return copy.deepcopy(previous)
    result = copy.deepcopy(review)
    issues = {}
    for item in review.get("issues", []):
        issue = make_issue(artifact, item["kind"], item["unit_ids"], item["target"], item["reason"])
        if item.get("issue_id") not in {None, issue["issue_id"]}:
            raise ValueError("CONTEXT_ISSUE_ID_MISMATCH")
        issues[issue["issue_id"]] = issue
    for item in review.get("unresolved", []):
        target = {"scope": review.get("scope", "document"), "table_ids": review.get("target_table_ids") or []}
        issue = make_issue(artifact, "missing_context", item["unit_ids"], target, item["reason"])
        issues[issue["issue_id"]] = issue
    # Silence in a new response is not a resolution of prior source-bound issues.
    if previous and not previous.get("contract"):
        previous = normalize_review(artifact, previous)
    replacements = {item["old_issue_id"]: item for item in review.get("reprocessed_issues", [])}
    for item in (previous or {}).get("issues", []):
        if item.get("source") != source_identity(artifact):
            raise ValueError("CONTEXT_PRIOR_SOURCE_MISMATCH")
        from app.modules.knowledge.services.semantic_annotations import semantic_input_hash
        if item.get("input_hash") != semantic_input_hash(artifact):
            raise ValueError("CONTEXT_PRIOR_INPUT_CHANGED_REVIEW_REQUIRED")
        replacement = replacements.get(item["issue_id"])
        if replacement:
            new = issues.get(replacement["new_issue_id"])
            if (item["kind"] != "missing_context" or new is None or new["kind"] != "scope_confirmation_required"
                    or new["target"] != item["target"] or not set(new["unit_ids"]) - set(item["unit_ids"])):
                raise ValueError("CONTEXT_REPROCESSING_INVALID")
            for evidence in new["review_evidence"]:
                binding = EvidenceBinding.model_validate(evidence["evidence_binding"])
                verify_binding(artifact, binding, evidence["evidence_quote"], binding.source_unit_id)
            issues.pop(item["issue_id"], None)
        else:
            issues.setdefault(item["issue_id"], copy.deepcopy(item))
    result.update(contract=CONTRACT, issues=list(issues.values()),
        reconciliation={"retained_issue_ids": [item["issue_id"] for item in (previous or {}).get("issues", []) if item["issue_id"] not in replacements],
                        "reprocessed": list(replacements.values()), "prior_issues": (previous or {}).get("issues", []),
                        "reason": "An omitted model issue remains open until source-bound reprocessing or a valid specific decision."},
        packets_complete=review.get("packets_complete", review.get("coverage_complete", True)))
    return result


def proposal_summary(proposal: dict) -> dict:
    review = proposal.get("context_review") or {}
    issues = review.get("issues", [])
    decisions = (proposal.get("review") or {}).get("context_decisions", [])
    # Only snapshot/verified review envelopes can confer a decision. Pending model
    # payloads cannot carry "resolved" flags that bypass application checks.
    cleared = {item["issue_id"] for item in decisions if item.get("proposal_hash") == proposal.get("proposal_hash")
               and item.get("actor_id") and item.get("at")} if proposal.get("status") == "verified" else set()
    opened = [item["issue_id"] for item in issues if item["issue_id"] not in cleared]
    legacy = review.get("unresolved", []) if not review.get("contract") else []
    opened.extend("legacy:" + digest(item) for item in legacy)
    packets = review.get("packets_complete", review.get("coverage_complete", True))
    if packets is False:
        opened.append("coverage:incomplete")
    missing = packets is False or bool(legacy) or any(item["issue_id"] in opened and item["kind"] not in {"scope_confirmation_required", "deferred_reference"} for item in issues)
    return {"contract": CONTRACT, "packets_complete": packets, "scope": review.get("scope", "legacy"),
        "issue_count": len(issues) + len(legacy), "open_issue_ids": sorted(set(opened)),
        "context_blocker_count": len(set(opened)), "application_blocked": bool(opened),
        "semantic_complete": packets and not opened,
        "requires_more_context": missing,
        "publication_blocked": bool(opened) or review.get("scope") == "selected_tables"}


def checked_decisions(artifact: dict, proposal: dict, requests: list, actor_id: str) -> list[dict]:
    issues = {item["issue_id"]: item for item in (proposal.get("context_review") or {}).get("issues", [])}
    actions = {"scope_confirmation_required": "scope_confirmed", "deferred_reference": "not_applicable_to_target"}
    checked, seen = [], set()
    for raw in requests:
        intent = ContextDecision.model_validate(raw)
        issue = issues.get(intent.issue_id)
        if (issue is None or issue.get("input_hash") != proposal.get("input_hash") or issue.get("source") != source_identity(artifact)
                or intent.issue_id in seen or intent.target != issue["target"]
                or intent.action != actions.get(issue["kind"]) or not actor_id):
            raise ValueError("CONTEXT_DECISION_TARGET_OR_ACTION_INVALID")
        binding = intent.evidence_binding
        verify_binding(artifact, binding, intent.evidence_quote, binding.source_unit_id)
        text = source_text(artifact, binding.source_unit_id, binding.column_id)
        if (binding.source_unit_id not in issue["unit_ids"] or binding.column_id is not None
                or binding.start != 0 or binding.end != len(text)):
            raise ValueError("CONTEXT_DECISION_REQUIRES_FULL_CANONICAL_UNIT")
        seen.add(intent.issue_id)
        checked.append({**intent.model_dump(), "actor_id": actor_id, "at": datetime.now(UTC).isoformat(),
            "proposal_hash": proposal["proposal_hash"]})
    return checked


def guard_application(artifact: dict, proposal: dict, requests: list, actor_id: str) -> list[dict]:
    checked = checked_decisions(artifact, proposal, requests, actor_id)
    candidate = {**proposal, "status": "verified", "review": {"context_decisions": checked}}
    if proposal_summary(candidate)["application_blocked"]:
        raise AppException("Cần xử lý từng vấn đề ngữ cảnh và phạm vi trước khi áp dụng.",
            code="SEMANTIC_CONTEXT_REVIEW_REQUIRED", status_code=409, details=proposal_summary(candidate))
    return checked


def refresh_policy(artifact: dict, mode: str = "strict") -> None:
    from app.modules.knowledge.services.source_limitations import evaluate_source_policy

    proposal = artifact.get("semantic_annotations") or {}
    if proposal.get("context_review") or artifact.get("source_limitations"):
        artifact["source_policy"] = evaluate_source_policy(artifact, mode=mode)
