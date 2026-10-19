"""Context/evidence TEST proposals; never authorize a source or real user review."""

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import tests.test_semantic_lifecycle as lifecycle
import tests.test_semantic_proposals as f
from app.core.exceptions import AppException
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.services.qnu_serving import verify_revision_pair
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    stage_semantic_annotations,
)
from app.modules.knowledge.services.semantic_binding import bind_model_proposals
from app.modules.knowledge.services.semantic_context import (
    ContextBuilder,
    SemanticContextPolicy,
    context_bytes,
)

storage = lifecycle.storage
pair = lifecycle.pair
database = lifecycle.database


@pytest.mark.asyncio
async def test_reproduce_legacy_reformatted_quote_is_rejected(pair):
    artifact = lifecycle.artifact_of(pair)
    source = next(unit for unit in artifact["retrieval_units"]["units"] if unit["id"] == "qnu:g")
    proposal = lifecycle.payload(artifact).model_dump()
    proposal["notes"][0]["evidence_quote"] = source["text"].replace(" ", "  ", 1)
    before = copy.deepcopy(artifact)
    with pytest.raises(ValueError, match="exact quote"):
        stage_semantic_annotations(artifact, SemanticAnnotations.model_validate(proposal))
    assert artifact == before


@pytest.mark.asyncio
async def test_T01_backend_binds_selected_source_without_model_copying_quote(pair):
    from app.modules.knowledge.services.qnu_serving import verify_revision_pair
    from app.modules.knowledge.services.semantic_binding import bind_model_proposals
    from app.modules.knowledge.services.semantic_context import ContextBuilder

    artifact = lifecycle.artifact_of(pair)
    builder = ContextBuilder(artifact, await verify_revision_pair(pair))
    packet = builder.packets()[0]
    evidence = next(item for item in packet["evidence"] if item["source_unit_id"] == "qnu:g")
    raw = {"context_id": packet["context_id"], "notes": [{"source_unit_id": "qnu:g",
        "evidence_id": evidence["id"], "table_id": artifact["tables"][0]["id"],
        "scope": "column", "column_ids": ["c4"], "reason": "TEST exact column condition"}]}
    annotations = bind_model_proposals(artifact, packet, raw)
    assert annotations.notes[0].evidence_quote == "Only the 2026 column has this condition."
    assert annotations.notes[0].evidence_binding.coordinate_space == "unit_codepoints"
    pending = stage_semantic_annotations(artifact, annotations)
    assert pending["status"] == "proposed" and not artifact.get("semantic_effective")


def note_payload(packet, unit_id="qnu:g", *, table_id=None, scope="column", rows=None, columns=None, contains=None):
    evidence = next(item for item in packet["evidence"] if item["source_unit_id"] == unit_id
                    and (contains is None or contains in item["text"]))
    return {"context_id": packet["context_id"], "notes": [{"source_unit_id": unit_id, "evidence_id": evidence["id"],
        "table_id": table_id or packet["tables"][0]["id"], "scope": scope, "row_unit_ids": rows or [],
        "column_ids": columns if columns is not None else ["c4"], "reason": "TEST source-supported relation; human review required"}]}


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["paraphrase", "wrong_unit", "wrong_revision", "wrong_span", "wrong_hash", "sibling"])
async def test_T02_T03_rewritten_foreign_or_stale_evidence_never_binds(pair, change):
    artifact = lifecycle.artifact_of(pair)
    packet = ContextBuilder(artifact, await verify_revision_pair(pair)).packets()[0]
    payload = note_payload(packet)
    if change == "paraphrase":
        payload["notes"][0]["evidence_quote"] = "The model rewrote this sentence"
    elif change == "wrong_unit":
        payload["notes"][0]["source_unit_id"] = "qnu:n2"
    elif change == "wrong_revision":
        packet["source"]["revision_id"] = "other-revision"
    else:
        binding = packet["_bindings"][payload["notes"][0]["evidence_id"]]
        if change == "wrong_span":
            binding["end"] += 1000
        elif change == "wrong_hash":
            binding["text_sha256"] = "0" * 64
        else:
            ev = next(item for item in packet["evidence"] if item["source_unit_id"] == "qnu:r1" and item["column_id"] == "c2")
            payload = {"context_id": packet["context_id"], "cells": [{"source_unit_id": "qnu:r1", "evidence_id": ev["id"],
                "row_unit_id": "qnu:r1", "column_id": "c7", "state": "not_stated", "reason": "TEST invalid borrowed sibling"}]}
    with pytest.raises(ValueError):
        bind_model_proposals(artifact, packet, payload)


def test_T04_original_unicode_whitespace_and_emoji_offsets_are_preserved():
    document = f.fixture.fixture_document()
    document.blocks[-1].body = "Nguồn  A\u0301\nGiữ 🚀 nguyên văn; không sửa dấu."
    _, artifact = project_document(document, f.fixture.reference(), {})
    packet = ContextBuilder(artifact, document).packets()[0]
    raw = note_payload(packet, scope="table", columns=[])
    annotation = bind_model_proposals(artifact, packet, raw).notes[0]
    assert annotation.evidence_quote == document.blocks[-1].body
    assert "A\u0301" in annotation.evidence_quote and "🚀" in annotation.evidence_quote
    assert annotation.evidence_binding.end == len(document.blocks[-1].body)
    assert annotation.evidence_binding.end != len(document.blocks[-1].body.encode())


@pytest.fixture(scope="module")
async def actual_document():
    from app.modules.knowledge.parsers.docling_office_parser import DoclingOfficeParser
    from app.modules.knowledge.parsers.docling_structure import build_qnu_structured_document

    path = Path(__file__).resolve().parents[2] / "docs/tai_lieu/tuyen_sinh/tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx"
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    assert sha == "58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274"
    parsed = await DoclingOfficeParser("docx").parse(raw, path.name)
    return build_qnu_structured_document(parsed.docling_document, filename=path.name, sha256=sha,
        header_evidence=parsed.docx_header_evidence, source_evidence=parsed.docx_source_evidence)


@pytest.mark.parametrize("marker,scope", [("(TB1)", "table"), ("(C-2027)", "column"), ("(D-AM-0007)", "row"), ("(N-II)", "group")])
def test_T05_T06_T07_T08_actual_docx_scopes_remain_exact(actual_document, marker, scope):
    _, artifact = project_document(actual_document, f.fixture.reference(), {})
    builder = ContextBuilder(artifact, actual_document)
    packets = builder.packets()
    target = artifact["tables"][1 if scope == "group" else 0]
    unit = next(unit for unit in builder.manifest.units if marker in unit.text and not unit.is_container)
    packet = next(packet for packet in packets if any(table["id"] == target["id"] for table in packet["tables"])
                  and any(ev["source_unit_id"] == unit.id for ev in packet["evidence"]))
    rows = [rid for rid, values in zip(target["row_unit_ids"], target["rows"], strict=True)
            if ("AM-0007" in values if scope == "row" else any(f"NV-{n:02}" in values for n in range(16, 31)))] if scope in {"row", "group"} else []
    columns = [column["id"] for column in target["columns"] if any("2027" in part for part in column["header_path"])] if scope == "column" else []
    payload = note_payload(packet, unit.id, table_id=target["id"], scope=scope, rows=rows, columns=columns)
    if scope in {"row", "column"}:
        payload["notes"][0]["evidence_id"] = next(ev["id"] for ev in packet["evidence"] if ev["source_unit_id"] == unit.id
            and (("AM-0007" in ev["text"] and "AM-0070" not in ev["text"]) if scope == "row"
                 else ("2027" in ev["text"] and "2025" not in ev["text"])))
    review_issues = []
    proposal = bind_model_proposals(artifact, packet, payload, review_issues=review_issues)
    assert proposal.notes[0].evidence_quote in unit.text
    pending = stage_semantic_annotations(artifact, proposal, context_review={"coverage_complete": True, "scope": "document", "issues": review_issues})
    from app.modules.knowledge.normalization.retrieval_units import UnitManifest
    from app.modules.knowledge.services.semantic_annotations import apply_reviewed_semantics
    from app.modules.knowledge.services.source_links import unit_context_ids

    decisions = [{"issue_id": issue["issue_id"], "target": issue["target"], "action": "scope_confirmed",
                  **issue["review_evidence"][0], "reason": "TEST complete source and exact columns checked"} for issue in review_issues]
    approved = apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST-reviewer547", "TEST ONLY known fixture scope", context_decisions=decisions)
    manifest = UnitManifest.model_validate(approved["retrieval_units"])
    for rid in target["row_unit_ids"]:
        for column in target["columns"]:
            expected = (rid in rows if rows else True) and (column["id"] in columns if columns else True)
            assert (unit.id in unit_context_ids(manifest, rid, column["id"])) == expected


def test_T06_T07_wrong_year_or_identifier_is_rejected(actual_document):
    _, artifact = project_document(actual_document, f.fixture.reference(), {})
    builder = ContextBuilder(artifact, actual_document)
    target = artifact["tables"][0]
    packet = next(packet for packet in builder.packets() if packet["tables"] and packet["tables"][0]["id"] == target["id"])
    column_note = next(unit for unit in builder.manifest.units if "(C-2027)" in unit.text)
    # Select just the positive-scope sentence; other years occur in its exclusion.
    ev = next(ev for ev in packet["evidence"] if ev["source_unit_id"] == column_note.id and "2027" in ev["text"] and "2025" not in ev["text"])
    wrong_col = next(col["id"] for col in target["columns"] if any("2026" in part for part in col["header_path"]))
    payload = note_payload(packet, column_note.id, columns=[wrong_col])
    payload["notes"][0]["evidence_id"] = ev["id"]
    # Full source includes several years and exclusions. Exact binding may stage
    # only with a scope issue; a generic approval cannot accept the wrong column.
    issues = []
    proposal = bind_model_proposals(artifact, packet, payload, review_issues=issues)
    pending = stage_semantic_annotations(artifact, proposal, context_review={"coverage_complete": True, "issues": issues})
    from app.modules.knowledge.services.semantic_annotations import apply_reviewed_semantics
    with pytest.raises(AppException) as error:
        apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST", "Generic comment")
    assert error.value.code == "SEMANTIC_CONTEXT_REVIEW_REQUIRED"
    row_note = next(unit for unit in builder.manifest.units if "(D-AM-0007)" in unit.text)
    ev = next(ev for ev in packet["evidence"] if ev["source_unit_id"] == row_note.id and "AM-0007" in ev["text"] and "AM-0070" not in ev["text"])
    wrong_row = next(rid for rid, values in zip(target["row_unit_ids"], target["rows"], strict=True) if "AM-0070" in values)
    payload = note_payload(packet, row_note.id, scope="row", rows=[wrong_row], columns=[])
    payload["notes"][0]["evidence_id"] = ev["id"]
    with pytest.raises(ValueError, match="ROW_CONFLICT"):
        bind_model_proposals(artifact, packet, payload)


def test_T12_explicit_far_reference_and_ambiguous_label_are_traced():
    from app.modules.knowledge.normalization.qnu_markdown import QnuBlock

    document = f.fixture.fixture_document()
    document.blocks[-1].body = "Read Clause 9 for the condition."
    document.blocks.append(QnuBlock(id="far", type="section", body="# Clause 9 Conditions"))
    document.blocks.append(QnuBlock(id="term", parent_id="far", type="text", body="Exact remote condition."))
    document.blocks.append(QnuBlock(id="extra", type="section", body="# Unrelated appendix"))
    document.blocks.append(QnuBlock(id="extra-term", parent_id="extra", type="text", body="Additional source context."))
    _, artifact = project_document(document, f.fixture.reference(), {})
    builder = ContextBuilder(artifact, document)
    packet = builder.packets()[0]
    assert "qnu:far" in packet["_unit_ids"]
    assert "qnu:term" in packet["_unit_ids"]
    expanded = builder.expand(packet, ["qnu:extra"])
    assert "qnu:extra-term" in expanded["_unit_ids"]
    with pytest.raises(ValueError, match="NO_NEW"):
        builder.expand(expanded, ["qnu:extra"])
    document.blocks.append(QnuBlock(id="duplicate", type="section", body="# Clause 9 Other conditions"))
    _, artifact = project_document(document, f.fixture.reference(), {})
    builder = ContextBuilder(artifact, document)
    builder.packets()
    assert any(item["reason"] == "ambiguous_exact_reference" for item in builder.trace)


def test_T09_identical_actual_notes_keep_distinct_source_and_table(actual_document):
    _, artifact = project_document(actual_document, f.fixture.reference(), {})
    builder = ContextBuilder(artifact, actual_document)
    packets = builder.packets()
    quotes, evidence_ids = [], []
    for index, source in [(6, "qnu:p080"), (7, "qnu:p082")]:
        table = artifact["tables"][index]
        packet = next(p for p in packets if any(t["id"] == table["id"] for t in p["tables"]))
        note = bind_model_proposals(artifact, packet, note_payload(packet, source, scope="table", columns=[])).notes[0]
        assert note.table_id == table["id"] and note.note_unit_id == source
        quotes.append(note.evidence_quote)
        evidence_ids.append(note.evidence_binding.evidence_id)
    assert quotes[0] == quotes[1] and evidence_ids[0] != evidence_ids[1]


def test_T10_T11_actual_scoped_legend_preserves_unknown_slash(actual_document):
    from app.modules.knowledge.services.semantic_annotations import apply_reviewed_semantics

    _, artifact = project_document(actual_document, f.fixture.reference(), {})
    builder = ContextBuilder(artifact, actual_document)
    table = artifact["tables"][4]
    packet = next(p for p in builder.packets() if any(t["id"] == table["id"] for t in p["tables"]))
    row = next(rid for rid, values in zip(table["row_unit_ids"], table["rows"], strict=True) if "CT-05" in values)
    slash = next(rid for rid, values in zip(table["row_unit_ids"], table["rows"], strict=True) if "CT-06" in values)
    payload = note_payload(packet, "qnu:p072", scope="row", rows=[row], columns=[])
    payload["notes"][0]["evidence_id"] = next(e["id"] for e in packet["evidence"]
        if e["source_unit_id"] == "qnu:p072" and "CT-05" in e["text"] and "CT-06" not in e["text"])
    proposal = bind_model_proposals(artifact, packet, payload)
    before = copy.deepcopy(artifact["tables"][4]["row_fields"])
    pending = stage_semantic_annotations(artifact, proposal)
    applied = apply_reviewed_semantics(artifact, pending["proposal_hash"], "TEST-reviewer547", "TEST scoped legend")
    assert applied["tables"][4]["row_fields"] == before
    units = {u["id"]: u for u in applied["retrieval_units"]["units"]}
    assert "qnu:p072" in units[row]["context_refs"] and "qnu:p072" not in units[slash]["context_refs"]
    assert any(field["raw"] == "/" and field["state"] == "ambiguous" for field in before[table["row_unit_ids"].index(slash)])


@pytest.mark.asyncio
async def test_incomplete_budget_and_unverified_document_make_no_model_call(pair):
    from app.modules.knowledge.services.semantic_annotations import propose_source_semantics

    artifact = lifecycle.artifact_of(pair)
    document = await verify_revision_pair(pair)
    before = copy.deepcopy(artifact)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock()) as generate:
        with pytest.raises(AppException):
            await propose_source_semantics(AsyncMock(), artifact, "TEST", "TEST-model", "TEST-provider",
                document=document, context_policy={"max_packet_bytes": 2000})
        with pytest.raises(AppException) as error:
            await propose_source_semantics(AsyncMock(), artifact, "TEST", "TEST-model", "TEST-provider",
                document=document, context_policy={"max_total_bytes": 2000})
        assert error.value.code == "SEMANTIC_CONTEXT_INCOMPLETE"
        generate.assert_not_awaited()
    assert artifact == before
    artifact["retrieval_units"]["units"][0]["text"] += " tampered"
    with pytest.raises(ValueError):
        ContextBuilder(artifact, document)


def test_T13_large_catalog_is_partitioned_and_missing_budget_is_explicit():
    document = f.fixture.fixture_document()
    originals = [block for block in document.blocks if block.type == "table_row"]
    for index in range(120):
        row = originals[index % 2].model_copy(deep=True)
        row.id = "large-row-" + str(index)
        document.blocks.insert(-1, row)
    _, artifact = project_document(document, f.fixture.reference(), {})
    policy = SemanticContextPolicy(max_packet_bytes=18000, max_units=30, max_packets=64, max_calls=64)
    builder = ContextBuilder(artifact, document, policy)
    packets = builder.packets()
    assert len(packets) > 1
    assert not builder.unexamined
    assert all(context_bytes(packet) <= policy.max_packet_bytes for packet in packets)
    assert {rid for packet in packets for table in packet["tables"] for rid in table["visible_row_ids"]} == set(artifact["tables"][0]["row_unit_ids"])
    missing_row = next(rid for rid in artifact["tables"][0]["row_unit_ids"] if rid not in packets[0]["tables"][0]["visible_row_ids"])
    builder.policy = policy.model_copy(update={"max_packet_bytes": 100000, "max_units": 1000})
    expanded = builder.expand(packets[0], [missing_row])
    assert missing_row in expanded["tables"][0]["visible_row_ids"]
    assert any(row["id"] == missing_row and row["fields"] for row in expanded["tables"][0]["rows"])
    limited = ContextBuilder(artifact, document, policy.model_copy(update={"max_packets": 1}))
    assert len(limited.packets()) == 1 and limited.unexamined


@pytest.mark.asyncio
async def test_T14_failed_later_packet_never_mutates_effective_data(pair):
    from app.modules.knowledge.services.semantic_annotations import propose_source_semantics

    document = await verify_revision_pair(pair)
    artifact = lifecycle.artifact_of(pair)
    before = copy.deepcopy(artifact)
    async def reply(_db, request):
        return SimpleNamespace(content=json.dumps({"context_id": "wrong"}), provider="TEST", model="TEST", is_fallback=False,
                               prompt_tokens=1, completion_tokens=1, cost_usd=None)
    with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=reply)), pytest.raises(AppException):
        await propose_source_semantics(AsyncMock(), artifact, "TEST", "TEST-model", "TEST-provider", document=document)
    assert artifact == before


@pytest.mark.asyncio
async def test_T15_bound_evidence_survives_real_db_storage_and_rebuild(database):
    from app.modules.knowledge.models import KnowledgeSourceRevision
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    from app.modules.knowledge.normalization.structure_chunks import structure_chunks
    from app.modules.knowledge.services.semantic_store import rebuild_projection, record_decision

    _col, _binding, revision = database.ids
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, revision)
        artifact = copy.deepcopy(lifecycle.artifact_of(rev))
        packet = ContextBuilder(artifact, await verify_revision_pair(rev)).packets()[0]
        annotations = bind_model_proposals(artifact, packet, note_payload(packet))
        pending = stage_semantic_annotations(artifact, annotations)
        rev.parse_provenance = {**rev.parse_provenance, "structured_artifact": artifact}
        await record_decision(rev, artifact, pending["proposal_hash"], "TEST-reviewer547", "TEST exact selector only", "approved")
        await db.commit()
    async with database.factory() as db:
        loaded = await db.get(KnowledgeSourceRevision, revision)
        with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=AssertionError("No model on replay"))):
            canonical, restored = await rebuild_projection(loaded)
        note = restored["semantic_annotations"]["annotations"]["notes"][0]
        assert note["evidence_binding"]["source_identity"]["revision_id"] == revision
        manifest = resolve_unit_manifest(canonical, restored)
        chunks = structure_chunks(canonical, manifest, context_graph=restored["context_graph"])
        assert any("Only the 2026" in chunk["content"] for chunk in chunks)
        assert loaded.status == "review_required"
