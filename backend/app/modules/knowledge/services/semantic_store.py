"""Revision-owned immutable annotation snapshots; projections are disposable derivatives."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import re
from typing import Any

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.knowledge.normalization.qnu_projection import VERSION, project_document
from app.modules.knowledge.normalization.retrieval_models import UnitManifest
from app.modules.knowledge.normalization.retrieval_units import manifest_digest
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    _digest,
    _refresh,
    _validated_copy,
    apply_reviewed_semantics,
    semantic_input_hash,
)

SCHEMA = "qnu-semantic-v1"
STORE = "semantic_store"


def invalid(reason: str, code: str = "SEMANTIC_SNAPSHOT_INVALID") -> AppException:
    return AppException("Annotation không khớp nguồn hoặc quyết định duyệt; cần đối soát lại.",
                        code=code, status_code=409, details={"reason": reason})


def identity(revision: Any) -> dict:
    from app.modules.knowledge.services.qnu_serving import input_reference, standard_reference

    return {"binding_id": revision.binding_id, "revision_id": revision.id,
            "origin_file_hash": revision.origin_file_hash,
            "qnu_input": input_reference(standard_reference(revision)), "projection_version": VERSION,
            # Global application scope: legacy tenant/workspace are NOT authorization partitions.
            "data_scope": "application_shared"}


def _enrichment(base: dict, current: dict) -> dict:
    """Pin pre-review temporal enrichment only, never copy arbitrary graph/fields."""
    original = UnitManifest.model_validate(base["retrieval_units"])
    actual = UnitManifest.model_validate(current["retrieval_units"])
    if len(original.units) != len(actual.units):
        raise invalid("enrichment_units")
    changes = {}
    for old, new in zip(original.units, actual.units, strict=True):
        if old.model_dump(exclude={"temporal"}) != new.model_dump(exclude={"temporal"}):
            raise invalid("enrichment_structure")
        if old.temporal != new.temporal:
            changes[old.id] = new.temporal.model_dump()
    return {"temporals": changes, "unit_annotation": copy.deepcopy(current.get("unit_annotation"))}


def _restore_enrichment(base: dict, recipe: dict) -> dict:
    restored = copy.deepcopy(base)
    manifest = UnitManifest.model_validate(restored["retrieval_units"])
    by_id = {unit.id: unit for unit in manifest.units}
    for unit_id, temporal in recipe["temporals"].items():
        if unit_id not in by_id:
            raise invalid("enrichment_target")
        by_id[unit_id].temporal = type(by_id[unit_id].temporal).model_validate(temporal)
    restored.update(retrieval_units=manifest.model_dump(), unit_manifest_hash=manifest_digest(manifest))
    if recipe.get("unit_annotation") is not None:
        restored["unit_annotation"] = recipe["unit_annotation"]
    return restored


async def base_projection(revision: Any, document: Any = None) -> tuple[str, dict]:
    from app.modules.knowledge.services.qnu_serving import (
        input_reference,
        standard_reference,
        verify_revision_pair,
    )

    document = document or await verify_revision_pair(revision)
    return await asyncio.to_thread(project_document, document, input_reference(standard_reference(revision)),
                                   revision.citation_metadata or {})


def semantic_fingerprint(artifact: dict) -> str:
    """Independent of audit timestamps and subsequent temporal-scope approval."""
    return _digest({"units": [{**{key: unit.get(key) for key in ("id", "context_refs", "field_context_refs")},
                              "field_usage": unit.get("field_usage") or {}}
                              for unit in artifact["retrieval_units"]["units"]],
        "fields": [[[{key: field.get(key) for key in ("raw", "state", "normalized", "state_source", "state_evidence", "usage", "source_limitation")}
                     for field in row] for row in table["row_fields"]] for table in artifact["tables"]],
        "facts": [{"id": fact["id"], "context": fact["raw_data"].get("context_unit_ids"),
                   "column": fact["raw_data"].get("column_id"), "state": fact["raw_data"].get("field_state")}
                  for fact in artifact["facts"]], "source_limitations": artifact.get("source_limitations"),
        "source_policy": artifact.get("source_policy")})


def _proposal(snapshot: dict) -> dict:
    proposal, review = snapshot["proposal"], snapshot["review"]
    if (proposal.get("status") not in {"proposed", "empty"}
            or proposal.get("proposal_hash") != _digest({k: v for k, v in proposal.items() if k != "proposal_hash"})
            or review.get("decision") not in {"approved", "rejected", "changes_requested"}
            or not all(isinstance(review.get(k), str) and review[k].strip() for k in ("actor_id", "comment", "at"))):
        raise invalid("approval_or_proposal")
    return proposal


def _semantic_hash(snapshot: dict) -> str:
    payload = {"schema": snapshot["schema"], "identity": snapshot["identity"],
                    "enrichment": snapshot["enrichment"], "input_hash": snapshot["proposal"]["input_hash"],
                    "annotations": snapshot["proposal"]["annotations"]}
    if "policy_mode" in snapshot:
        payload["policy_mode"] = snapshot["policy_mode"]
    return _digest(payload)


def _apply_snapshot(base: dict, snapshot: dict, reference: dict) -> dict:
    proposal = _proposal(snapshot)
    if snapshot["review"]["decision"] != "approved":
        raise invalid("active_not_approved")
    enriched = _restore_enrichment(base, snapshot["enrichment"])
    if semantic_input_hash(enriched) != proposal["input_hash"]:
        raise invalid("input_fingerprint", "SEMANTIC_SOURCE_MISMATCH")
    semantic_hash = _semantic_hash(snapshot)
    if snapshot.get("semantic_hash") != semantic_hash:
        raise invalid("semantic_hash")
    annotations = SemanticAnnotations.model_validate(proposal["annotations"])
    acknowledged = snapshot["review"].get("action") == "acknowledged_limits"
    if annotations.limitations and not acknowledged:
        raise invalid("limitation_not_acknowledged")
    result = _validated_copy(enriched, annotations, acknowledged_limits=acknowledged)
    if annotations.limitations:
        from app.modules.knowledge.services.source_limitations import evaluate_source_policy

        result["source_policy"] = evaluate_source_policy(result, mode=snapshot.get("policy_mode", "strict"))
    manifest = UnitManifest.model_validate(result["retrieval_units"])
    manifest.semantic_annotation_hash = semantic_hash
    _refresh(result, manifest)
    result["semantic_effective"] = {"semantic_hash": semantic_hash, "snapshot_sha256": reference["sha256"],
                                    "proposal_hash": proposal["proposal_hash"]}
    result["semantic_annotations"] = {**proposal, "status": "verified", "review": snapshot["review"]}
    return result


async def _read(revision: Any, reference: dict) -> dict:
    checksum = reference.get("sha256")
    path = f"{revision.snapshot_storage_path}.{checksum}.qnu-semantic-v1.json"
    if (not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum)
            or reference.get("path") != path):
        raise invalid("snapshot_path")
    data = await storage_service.get(path)
    if data is None:
        raise invalid("snapshot_missing", "SEMANTIC_SNAPSHOT_MISSING")
    if hashlib.sha256(data).hexdigest() != checksum:
        raise invalid("snapshot_checksum")
    try:
        snapshot = json.loads(data)
        if snapshot["schema"] != SCHEMA or snapshot["identity"] != identity(revision):
            raise invalid("snapshot_identity", "SEMANTIC_SOURCE_MISMATCH")
        _proposal(snapshot)
    except (ValueError, KeyError, TypeError) as exc:
        raise invalid("snapshot_shape") from exc
    return snapshot


async def effective_snapshot(revision: Any) -> tuple[dict | None, dict | None]:
    store = (revision.parse_provenance or {}).get(STORE)
    if store is None:
        return None, None
    if (not isinstance(store, dict) or store.get("schema") != SCHEMA
            or not isinstance(store.get("history"), list)
            or any(not isinstance(item, dict) for item in store["history"])):
        raise invalid("store_shape")
    active = store.get("active")
    if active is None:
        return None, None
    if active not in store["history"]:
        raise invalid("active_history")
    return active, await _read(revision, active)


async def rebuild_projection(revision: Any, document: Any = None) -> tuple[str, dict]:
    """Internal recovery: only server-owned revision references confer authority."""
    canonical, base = await base_projection(revision, document)
    reference, snapshot = await effective_snapshot(revision)
    if snapshot is not None:
        try:
            result = _apply_snapshot(base, snapshot, reference)
        except (ValueError, KeyError, TypeError) as exc:
            raise invalid("snapshot_evidence", "SEMANTIC_SOURCE_MISMATCH") from exc
        return canonical, result
    old = ((revision.parse_provenance or {}).get("structured_artifact") or {}).get("semantic_annotations") or {}
    if old.get("status") == "verified":
        from app.modules.knowledge.services.qnu_serving import validate_projection_binding

        validate_projection_binding(revision, revision.parse_provenance["structured_artifact"])
        # Old code mutated status/review AFTER hashing the proposal. Recover only
        # when its original proposal and exact base input can still be proven.
        original = {k: v for k, v in old.items() if k not in {"review", "status", "proposal_hash"}}
        original["status"] = "proposed"
        if _digest(original) != old.get("proposal_hash") or semantic_input_hash(base) != old.get("input_hash"):
            raise invalid("legacy_input_or_proposal", "SEMANTIC_LEGACY_REVIEW_REQUIRED")
        review = old.get("review") or {}
        _proposal({"proposal": {**original, "proposal_hash": old["proposal_hash"]}, "review": review})
        if review["decision"] != "approved":
            raise invalid("legacy_review", "SEMANTIC_LEGACY_REVIEW_REQUIRED")
        base["semantic_annotations"] = {**original, "proposal_hash": old["proposal_hash"]}
        restored = apply_reviewed_semantics(base, old["proposal_hash"], review["actor_id"], review["comment"])
        restored["semantic_annotations"]["review"] = copy.deepcopy(review)
        return canonical, restored
    if ((revision.parse_provenance or {}).get("structured_artifact") or {}).get("semantic_effective"):
        raise invalid("effective_reference_missing")
    return canonical, base


async def proposal_base(revision: Any, current: dict, document: Any = None) -> dict:
    _, base = await base_projection(revision, document)
    _, active = await effective_snapshot(revision)
    if active:
        return _restore_enrichment(base, active["enrichment"])
    if (current.get("semantic_annotations") or {}).get("status") == "verified":
        # Legacy verified decisions are checked before any replacement.
        await rebuild_projection(revision, document)
        return base
    return _restore_enrichment(base, _enrichment(base, current))


async def record_decision(revision: Any, artifact: dict, expected_hash: str, actor_id: str,
                          comment: str, decision: str, document: Any = None, *, policy_mode: str = "strict") -> dict:
    """Storage first, read-back verified; mutate DB pointer only inside caller's transaction."""
    if (revision.status != "review_required" or decision not in {"approved", "acknowledged_limits", "rejected", "changes_requested"}
            or policy_mode not in {"strict", "acknowledged_limits"}
            or (policy_mode != "strict" and decision != "acknowledged_limits")):
        raise invalid("draft_or_decision")
    _, base = await base_projection(revision, document)
    enriched = await proposal_base(revision, artifact, document)
    proposal = copy.deepcopy(artifact.get("semantic_annotations") or {})
    enriched["semantic_annotations"] = proposal
    # Exact pending payload + input checks, even for rejection.
    checked = apply_reviewed_semantics(enriched, expected_hash, actor_id, comment,
                                      acknowledged_limits=decision != "approved")
    if proposal.get("status") != "proposed":
        raise invalid("not_pending", "SEMANTIC_PROPOSAL_NOT_PENDING")
    snapshot = {"schema": SCHEMA, "identity": identity(revision), "enrichment": _enrichment(base, enriched),
                "proposal": proposal, "review": checked["semantic_annotations"]["review"]}
    snapshot["review"]["decision"] = "approved" if decision == "acknowledged_limits" else decision
    if decision == "acknowledged_limits":
        if not proposal["annotations"].get("limitations"):
            raise invalid("no_limits_to_acknowledge")
        snapshot["review"]["action"] = decision
        snapshot["policy_mode"] = policy_mode
    snapshot["semantic_hash"] = _semantic_hash(snapshot)
    return await _persist_snapshot(revision, base, artifact, snapshot)


async def _persist_snapshot(revision: Any, base: dict, artifact: dict, snapshot: dict) -> dict:
    data = (json.dumps(snapshot, sort_keys=True, ensure_ascii=False) + "\n").encode()
    checksum = hashlib.sha256(data).hexdigest()
    reference = {"path": f"{revision.snapshot_storage_path}.{checksum}.qnu-semantic-v1.json", "sha256": checksum}
    try:
        await storage_service.save(reference["path"], data)
    except OSError as exc:
        raise invalid("snapshot_write_failed", "SEMANTIC_STORAGE_UNAVAILABLE") from exc
    await _read(revision, reference)
    store = copy.deepcopy((revision.parse_provenance or {}).get(STORE) or {"schema": SCHEMA, "active": None, "history": []})
    store["history"].append(reference)
    if snapshot["review"]["decision"] == "approved":
        store["active"] = reference
        revised = _apply_snapshot(base, snapshot, reference)
    else:
        revised = copy.deepcopy(artifact)
        revised["semantic_annotations"] = {**snapshot["proposal"], "status": snapshot["review"]["decision"], "review": snapshot["review"]}
    revision.parse_provenance = {**revision.parse_provenance, STORE: store, "structured_artifact": revised}
    return revised


async def backfill_verified_semantics(revision: Any, document: Any = None) -> dict:
    """On-demand, locked draft migration of a provable legacy approval; no bulk writes."""
    if revision.status != "review_required":
        raise invalid("legacy_backfill_requires_draft")
    if STORE in revision.parse_provenance:
        return revision.parse_provenance["structured_artifact"]
    _, restored = await rebuild_projection(revision, document)
    if (restored.get("semantic_annotations") or {}).get("status") != "verified":
        return restored
    _, base = await base_projection(revision, document)
    old = restored["semantic_annotations"]
    proposal = {k: v for k, v in old.items() if k not in {"review", "status"}}
    proposal["status"] = "proposed"
    snapshot = {"schema": SCHEMA, "identity": identity(revision), "enrichment": _enrichment(base, base),
                "proposal": proposal, "review": old["review"]}
    snapshot["semantic_hash"] = _semantic_hash(snapshot)
    return await _persist_snapshot(revision, base, restored, snapshot)


async def verify_effective_projection(revision: Any, artifact: dict, document: Any = None) -> None:
    """Check saved decisions before using cached derivatives; never silently upgrade them."""
    provenance = revision.parse_provenance or {}
    if STORE not in provenance and (artifact.get("semantic_annotations") or {}).get("status") != "verified":
        if artifact.get("semantic_effective"):
            raise invalid("effective_reference_missing")
        return
    _, expected = await rebuild_projection(revision, document)
    if semantic_fingerprint(expected) != semantic_fingerprint(artifact) or expected.get("semantic_effective") != artifact.get("semantic_effective"):
        raise invalid("derived_projection_mismatch")
    if artifact.get("semantic_effective") and artifact["retrieval_units"].get("semantic_annotation_hash") != artifact["semantic_effective"]["semantic_hash"]:
        raise invalid("manifest_annotation_hash")
