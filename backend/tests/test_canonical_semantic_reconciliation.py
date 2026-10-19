"""Exact structural lineage, fresh bindings and fail-closed offline reconciliation."""

import copy

import pytest

import tests.test_review536_findings as fixture
import tests.test_semantic_lifecycle as lifecycle
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    stage_semantic_annotations,
)
from tests.test_semantic_scope_assertions import assertion

storage, database = lifecycle.storage, lifecycle.database


def inputs():
    old = fixture.fixture_document()
    for i, block in enumerate(old.blocks):
        for location in block.source_locations:
            location.locator = f"word/document.xml/block/{i}"
    old.blocks[-1].body = "Equipment dossier for group A in 2027 only; never student quantities."
    new = old.model_copy(deep=True)
    new.blocks[-1].id = "g_canonical"
    new.title = "Canonical title"
    _, before = project_document(old, fixture.reference("offline", "draft"), {})
    ref = fixture.reference("canonical", "revision") | {
        "sha256": "c" * 64,
        "structured_sha256": "d" * 64,
    }
    _, after = project_document(new, ref, {})
    note = assertion(before, old.blocks[-1].body, scope="group", rows=["qnu:r1"])
    note.update(context_kind="workflow", context_label="Equipment dossier context")
    staged = copy.deepcopy(before)
    proposal = stage_semantic_annotations(staged, SemanticAnnotations(notes=[note]))
    return old, new, before, after, proposal


def reconcile(values):
    from scripts.reconcile_semantic_checkpoint import reconcile_proposal

    return reconcile_proposal(*values)


def test_T03_T06_T09_T10_reconciliation_rebuilds_source_ids_and_hash_without_weakening_importer():
    values = inputs()
    _old, _new, before, after, proposal = values
    result = reconcile(values)
    assert result["status"] == "PREPARED_NOT_STAGED"
    pending = result["proposal"]
    note = pending["annotations"]["notes"][0]
    assert note["note_unit_id"] == "qnu:g_canonical"
    assert note["evidence_binding"]["source_identity"] == {
        k: after["qnu_input"][k]
        for k in ["document_id", "revision_id", "sha256", "structured_sha256"]
    }
    assert (
        note["evidence_binding"]["evidence_id"]
        != proposal["annotations"]["notes"][0]["evidence_binding"]["evidence_id"]
    )
    assert note["context_kind"] == "workflow" and note["column_ids"] == []
    assert pending["proposal_hash"] != proposal["proposal_hash"]
    assert before["tables"] == after["tables"] and "semantic_effective" not in after
    assert proposal["annotations"]["notes"][0]["note_unit_id"] == "qnu:g"


@pytest.mark.parametrize("change", ["missing", "text", "locator", "role", "duplicate"])
def test_T06_T07_missing_ambiguous_or_changed_source_blocks_only_its_candidate(change):
    old, new, before, after, proposal = inputs()
    note = new.blocks[-1]
    if change == "missing":
        new.blocks.pop()
    elif change == "text":
        note.body += " Extra exception."
    elif change == "locator":
        note.source_locations[0].locator = "different/source/location"
    elif change == "role":
        note.type = "section"
    else:
        new.blocks.append(note.model_copy(deep=True, update={"id": "duplicate"}))
    _, after = project_document(new, after["qnu_input"], {})
    result = reconcile((old, new, before, after, proposal))
    assert result["status"] == "RECONCILIATION_BLOCKED" and result["proposal"] is None
    assert result["assertions"][0]["status"] == "BLOCKED"


def test_T06_identical_text_in_different_location_does_not_steal_binding():
    old, new, before, after, proposal = inputs()
    clone = new.blocks[-1].model_copy(deep=True, update={"id": "same_words"})
    clone.source_locations[0].locator = "another/physical/location"
    new.blocks.append(clone)
    _, after = project_document(new, after["qnu_input"], {})
    result = reconcile((old, new, before, after, proposal))
    assert result["proposal"]["annotations"]["notes"][0]["note_unit_id"] == "qnu:g_canonical"


def test_T06_targeted_column_requires_exact_header_role_even_with_same_grid():
    old, new, before, after, _ = inputs()
    note = assertion(before, old.blocks[-1].body, scope="column", columns=["c4"])
    staged = copy.deepcopy(before)
    proposal = stage_semantic_annotations(staged, SemanticAnnotations(notes=[note]))
    table = next(b for b in new.blocks if b.type == "table")
    next(c for c in table.attributes["columns"] if c["id"] == "c4")["header_path"] = [
        "Different metric",
        "2035",
    ]
    _, after = project_document(new, after["qnu_input"], {})
    assert reconcile((old, new, before, after, proposal))["status"] == "RECONCILIATION_BLOCKED"


@pytest.mark.parametrize("change", ["docx", "proposal_hash", "manifest", "row_value"])
def test_T01_T05_T08_wrong_lineage_tampering_or_changed_target_is_not_accepted(change):
    old, new, before, after, proposal = inputs()
    if change == "docx":
        new.source.sha256 = "f" * 64
    elif change == "proposal_hash":
        proposal["proposal_hash"] = "0" * 64
    elif change == "manifest":
        after["retrieval_units"]["units"][0]["text"] += "forged"
    else:
        next(b for b in new.blocks if b.id == "r1").attributes["fields"]["c1"]["raw"] = "9999999"
        _, after = project_document(new, after["qnu_input"], {})
    if change == "row_value":
        assert reconcile((old, new, before, after, proposal))["status"] == "RECONCILIATION_BLOCKED"
    else:
        with pytest.raises(ValueError):
            reconcile((old, new, before, after, proposal))


async def test_T12_T14_T15_reconciled_proposal_stages_then_reloads_pending_without_approval(
    database,
):
    from app.modules.knowledge.models import KnowledgeSourceRevision
    from app.modules.knowledge.schemas import SemanticCheckpointImportRequest
    from app.modules.knowledge.services.qnu_docx_artifacts import save_qnu_document
    from app.modules.knowledge.services.qnu_serving import input_reference, verify_revision_pair
    from app.modules.knowledge.services.semantic_checkpoint import import_semantic_checkpoint
    from app.modules.knowledge.services.semantic_evidence import make_binding
    from app.modules.knowledge.services.semantic_store import rebuild_projection

    col, binding, rid = database.ids
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rid)
        document = await verify_revision_pair(rev)
        base = copy.deepcopy(lifecycle.artifact_of(rev))
        old_doc = document.model_copy(deep=True)
        old_note = next(b for b in old_doc.blocks if b.id == "g")
        old_note.id = "legacy_g"
        ref = await save_qnu_document(
            old_doc,
            document_id="offline-test",
            revision_id="draft-test",
            snapshot_path="offline556/source.docx",
        )
        _, old = project_document(old_doc, input_reference(ref), {})
        text = old_note.body
        note = {
            "note_unit_id": "qnu:legacy_g",
            "evidence_quote": text,
            "evidence_binding": make_binding(old, "qnu:legacy_g", 0, len(text)).model_dump(),
            "table_id": base["tables"][0]["id"],
            "scope": "group",
            "row_unit_ids": ["qnu:r1"],
            "column_ids": [],
            "assertion_version": 1,
            "context_kind": "workflow",
            "context_label": "TEST dossier only",
        }
        pending = stage_semantic_annotations(copy.deepcopy(old), SemanticAnnotations(notes=[note]))
        result = reconcile((old_doc, document, old, base, pending))
        assert result["status"] == "PREPARED_NOT_STAGED"
        upload = {
            "contract": "qnu-semantic-checkpoint-v1",
            "source_artifact": base,
            "proposal": result["proposal"],
        }
        await import_semantic_checkpoint(
            db,
            col,
            binding,
            rid,
            SemanticCheckpointImportRequest(
                checkpoint=upload, comment="TEST canonical source reconciled"
            ),
            lifecycle.actor(),
        )
        stored = copy.deepcopy(lifecycle.artifact_of(rev)["semantic_annotations"])
        assert not rev.parse_provenance.get("semantic_store", {}).get("active")
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, rid)
        restored = (await rebuild_projection(rev))[1]
        assert restored["semantic_annotations"] == stored and stored["status"] == "proposed"
        assert not restored.get("semantic_effective") and restored["tables"] == base["tables"]
