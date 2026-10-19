"""One authenticated intent, deterministic validation, no shared-data writes."""
import copy

import pytest

from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_context_review import proposal_summary
from app.modules.knowledge.services.smart_approval import evaluate_semantics
from tests.test_semantic_scope_assertions import assertion
from tests.test_semantic_selector_v2 import case


def test_exact_source_binding_does_not_prove_semantic_scope():
    artifact, _ = case("Only one group, subject to conditions. Never the whole table.")
    pending = stage_semantic_annotations(artifact, SemanticAnnotations(notes=[
        assertion(artifact, "Only one group, subject to conditions.", scope="table")]))
    before = copy.deepcopy(artifact)
    report = evaluate_semantics(artifact, fixture_policy=None)
    assert report["issues"][0]["result"] == "NEEDS_REVIEW"
    assert report["issues"][0]["reason_code"] == "SEMANTIC_SCOPE_NOT_PROVEN"
    assert report["auto_verified_count"] == 0
    assert artifact == before
    assert proposal_summary(pending)["application_blocked"]


@pytest.mark.parametrize("status", ["rejected", "changes_requested", "unavailable"])
def test_machine_validation_cannot_reopen_a_previous_decision(status):
    artifact, _ = case("TEST scope.")
    stage_semantic_annotations(artifact, SemanticAnnotations())
    artifact["semantic_annotations"]["status"] = status
    report = evaluate_semantics(artifact, fixture_policy=None)
    assert any(b["reason_code"] == "PROPOSAL_NOT_PENDING" for b in report["blockers"])


def test_legacy_approval_error_preserves_context_blocker():
    from types import SimpleNamespace

    from app.core.exceptions import AppException
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service

    artifact, _ = case("Only one row; not a general table condition.")
    stage_semantic_annotations(artifact, SemanticAnnotations(notes=[
        assertion(artifact, "Only one row; not a general table condition.", rows=["qnu:r1"])]))
    with pytest.raises(AppException) as error:
        source_ingestion_service._apply_review_decision(SimpleNamespace(), SimpleNamespace(), artifact,
            "approved", "TEST bulk", "TEST actor")
    assert error.value.code == "SEMANTIC_CONTEXT_REVIEW_REQUIRED"
    assert str(error.value.message) == "Còn vấn đề ngữ cảnh cần đối chiếu trước khi duyệt nguồn."


def test_changed_semantic_payload_cannot_inherit_fixture_acceptance():
    from app.modules.knowledge.services.semantic_annotations import _digest
    from app.modules.knowledge.services.smart_approval import _payload_hash

    artifact, _ = case("Only this one row. Never all rows.")
    proposal = stage_semantic_annotations(artifact, SemanticAnnotations(notes=[
        assertion(artifact, "Only this one row.", rows=["qnu:r1"])]))
    policy = {"policy_id": "TEST", "payload_sha256": _payload_hash(proposal), "cells": []}
    assert evaluate_semantics(artifact, fixture_policy=policy)["auto_verified_count"] == 1
    proposal["annotations"]["notes"][0]["row_unit_ids"] = ["qnu:r2"]
    proposal["proposal_hash"] = _digest({k:v for k,v in proposal.items() if k != "proposal_hash"})
    result = evaluate_semantics(artifact, fixture_policy=policy)
    assert result["auto_verified_count"] == 0 and not result["eligible"]


def test_allowlist_requires_exact_revision_provenance_not_test_filename():
    import json

    from app.modules.knowledge.services.smart_approval import POLICY_FILE, fixture_policy_for

    policy = json.loads(POLICY_FILE.read_text("utf-8"))[0]
    proposal = {"proposal_hash": policy["proposal_hash"]}
    assert fixture_policy_for(policy["identity"], proposal) == policy
    for field in ["binding_id", "revision_id", "origin_file_hash"]:
        forged = {**policy["identity"], field: "[KIEM THU]"}
        assert fixture_policy_for(forged, proposal) is None
    assert fixture_policy_for(policy["identity"], {"proposal_hash": "0" * 64}) is None


def test_only_exact_native_footnote_anchor_can_make_unknown_page_a_warning():
    artifact, _ = case("TEST native source.")
    artifact["issues"] = [{"code": "page_unresolved", "block_id": "footnote"}]
    artifact["retrieval_units"]["units"].extend([
        {"id": "qnu:footnote", "source_locations": [{"locator": "word/footnotes.xml#footnote:3"}]},
        {"id": "anchor", "context_refs": ["qnu:footnote"]}])
    from app.modules.knowledge.services.smart_approval import collect_quality_findings
    report = {"blockers": [], "warnings": []}
    collect_quality_findings(artifact, report)
    assert len(report["warnings"]) == 1 and not report["blockers"]
    artifact["retrieval_units"]["units"][-1]["context_refs"] = []
    report = {"blockers": [], "warnings": []}
    collect_quality_findings(artifact, report)
    assert not report["warnings"] and report["blockers"]
