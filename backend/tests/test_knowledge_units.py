"""Shared source units and temporal scopes across domains, never FAQ seeds."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.knowledge.normalization.retrieval_units import (
    build_unit_manifest,
    manifest_digest,
    resolve_unit_manifest,
    unit_chunks,
    validate_manifest,
)
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.rag.evidence_blocks import load_published_blocks, rank_blocks, split_source_blocks
from app.modules.rag.evidence_facts import reviewed_fact_blocks
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


@pytest.mark.asyncio
async def test_annotation_default_model_preserves_explicit_provider():
    from types import SimpleNamespace
    from unittest.mock import patch

    from app.modules.knowledge.services.unit_annotation import propose_unit_annotations

    manifest = build_unit_manifest("Historical data from 2023: 17 items.")
    content = '{"annotations": []}'
    defaults = SimpleNamespace(defaults=SimpleNamespace(default_chat_model="configured-model", default_chat_provider_id="default-provider"))
    with (patch("app.modules.modelops.services.model_catalog_service.model_catalog_service.get_system_model_defaults", AsyncMock(return_value=defaults)),
          patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(return_value=SimpleNamespace(content=content))) as generate):
        await propose_unit_annotations(AsyncMock(), manifest, "tenant", provider_id="operator-provider")
    request = generate.call_args.args[1]
    assert request.preferred_provider_id == "operator-provider"
    assert request.preferred_model_name == "configured-model"


@pytest.mark.asyncio
async def test_anchor_filter_receives_data_year_not_document_or_event_year():
    from unittest.mock import patch

    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_retrieval import retrieve_anchors

    with patch("app.modules.rag.evidence_retrieval.hybrid_retriever.retrieve", AsyncMock(return_value=[])) as retrieve:
        await retrieve_anchors(AskRequest(question="Report 2026 about data 2023 and event 2024", collection_id="c"),
            RetrievalSnapshot(snapshot_id="s", collection_id="c"), "Report 2026 data 2023 event 2024",
            EvidencePolicy(), False, data_years=[2023])
    assert retrieve.call_args.kwargs["data_years"] == [2023]


def test_structure_spans_preserve_hierarchy_lists_and_unknown_pages():
    text = "# Report 2026\nParagraph with a cited regulation 2020.\n\n## Statistics\n- Data from 2022.\n- Data from 2023.\n\n<!-- Page 7 -->\nContinuation."
    manifest = build_unit_manifest(text)
    validate_manifest(manifest, text)
    assert [u.kind for u in manifest.units] == ["heading", "paragraph", "heading", "list", "list", "paragraph"]
    assert all(text[u.start:u.end] == u.text for u in manifest.units)
    assert manifest.units[-1].page_number == 7
    assert manifest.units[0].page_number is None
    assert manifest.units[1].temporal.mentioned_years == [2020]
    assert manifest.units[1].temporal.data_years == []  # citation is not applicability
    assert manifest.units[-1].parent_id == manifest.units[2].id


def test_manifest_rejects_tampered_span_digest_and_parent():
    text = "# Policy 2026\n\nRecords from 2023."
    manifest = build_unit_manifest(text)
    artifact = {"retrieval_units": manifest.model_dump(), "unit_manifest_hash": manifest_digest(manifest)}
    assert resolve_unit_manifest(text, artifact) == manifest
    artifact["unit_manifest_hash"] = "0" * 64
    with pytest.raises(ValueError):
        resolve_unit_manifest(text, artifact)
    manifest.units[1].parent_id = manifest.units[1].id
    with pytest.raises(ValueError):
        validate_manifest(manifest, text)


def test_projection_enriches_search_but_never_changes_source_quote():
    text = "# Policy 2026\n\n## Support\n\nHistorical data from 2023: 17 records."
    manifest = build_unit_manifest(text)
    chunk = unit_chunks(manifest)[-1]
    unit = chunk["metadata"]["source_unit"]
    assert chunk["content"].startswith("# Policy 2026\n## Support")
    assert unit["text"] == text[unit["start"]:unit["end"]]
    assert unit["temporal"]["mentioned_years"] == [2023]
    assert unit["temporal"]["heading_years"] == [2026]


def test_oversize_structural_unit_does_not_silently_drop_content():
    from app.core.exceptions import AppException

    with pytest.raises(AppException) as error:
        unit_chunks(build_unit_manifest("A complete indivisible condition."), max_chars=10)
    assert error.value.code == "SOURCE_UNIT_TOO_LARGE"


def test_multilevel_table_projection_carries_all_evidenced_header_levels():
    text = "| Entity | 2023 | | 2024 | |\n| --- | --- | --- | --- | --- |\n| | Round A | Round B | Round A | Round B |\n| Department A | 17 | 18 | 19 | 20 |"
    manifest = build_unit_manifest(text)
    validate_manifest(manifest, text)
    rows = [unit for unit in manifest.units if not unit.is_container]
    assert len(rows) == 2  # one complete header tree and one data row
    row = rows[-1]
    assert "Round A" in row.header_context and "2023" in row.header_context
    assert row.header_context == rows[0].text
    assert "Round B" in unit_chunks(manifest)[-1]["content"]
    assert text[row.start:row.end] == row.text


def test_large_table_uses_exact_rows_with_headers_not_arbitrary_character_cuts():
    text = "# Archive 2026\n\n| Entity | 2022 | 2023 |\n| --- | --- | --- |\n" + "\n".join(
        f"| Department {i} | 17 | 18 |" for i in range(350))
    manifest = build_unit_manifest(text)
    validate_manifest(manifest, text)
    assert any(u.is_container for u in manifest.units)
    chunks = unit_chunks(manifest, max_chars=200)
    assert len(chunks) == 352  # title, header, 350 complete data rows
    assert all("| Entity | 2022 | 2023 |" in c["content"] for c in chunks[1:])
    assert all(text[c["metadata"]["source_unit"]["start"]:c["metadata"]["source_unit"]["end"]]
               == c["metadata"]["source_unit"]["text"] for c in chunks)


def test_merged_year_header_tree_keeps_distinct_contexts():
    text = "| Entity | 2023 | | 2024 | |\n| --- | --- | --- | --- | --- |\n| | Round A | Round B | Round A | Round B |\n| Department A | 17 | 18 | 19 | 20 |"
    artifact = build_source_artifact(text, 0, {})
    assert not artifact["issues"]
    assert [f["attribute_name"] for f in artifact["facts"]] == ["2023 / Round A", "2023 / Round B", "2024 / Round A", "2024 / Round B"]


def test_verified_data_scope_cannot_be_overridden_by_a_newer_document_heading():
    from app.modules.rag.evidence_validation import temporal_references_supported
    claim = {"references": [{"temporal_scope": {"data_years": [2023], "role": "data", "status": "verified"}},
                            {"temporal_scope": {"heading_years": [2026], "status": "proposed"}}]}
    assert temporal_references_supported(claim, [2023])
    assert not temporal_references_supported(claim, [2026])


def test_semantic_annotation_requires_exact_source_and_never_auto_verifies():
    from app.modules.knowledge.services.unit_annotation import (
        UnitAnnotations,
        apply_annotations,
        approve_unit_annotations,
    )
    artifact = build_source_artifact("# Report 2026\n\nDepartment A recorded 17 items in 2023.", 0, {})
    manifest = resolve_unit_manifest("# Report 2026\n\nDepartment A recorded 17 items in 2023.", artifact)
    unit = manifest.units[-1]
    proposal = UnitAnnotations(annotations=[{"unit_id": unit.id, "role": "data", "data_years": [2023], "evidence_quote": unit.text}])
    assert apply_annotations(manifest, proposal) == [unit.id]
    assert unit.temporal.status == "proposed"
    artifact["retrieval_units"] = manifest.model_dump()
    artifact["unit_annotation"] = {"status": "proposed", "unit_ids": [unit.id]}
    approve_unit_annotations(artifact)
    assert artifact["retrieval_units"]["units"][-1]["temporal"]["status"] == "verified"
    proposal.annotations[0].data_years = [2026]
    with pytest.raises(ValueError):
        apply_annotations(manifest, proposal)


@pytest.mark.asyncio
async def test_annotation_provider_failure_is_observable_unknown_not_fake_scope():
    from unittest.mock import patch

    from app.core.exceptions import AppException
    from app.modules.knowledge.services.unit_annotation import enrich_source_units
    text = "Department A recorded 17 items in 2023."
    artifact = build_source_artifact(text, 0, {})
    previous = artifact["unit_manifest_hash"]
    with patch("app.modules.knowledge.services.unit_annotation.propose_unit_annotations", AsyncMock(
            side_effect=AppException("Unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503))):
        await enrich_source_units(text, artifact, "tenant", {"enabled": True})
    assert artifact["unit_annotation"]["status"] == "unavailable"
    assert artifact["unit_manifest_hash"] == previous
    assert artifact["retrieval_units"]["units"][0]["temporal"]["data_years"] == []


def test_annotation_policy_cannot_carry_provider_credentials():
    from pydantic import ValidationError

    from app.modules.knowledge.services.unit_annotation import UnitAnnotationPolicy
    with pytest.raises(ValidationError):
        UnitAnnotationPolicy.model_validate({"enabled": True, "api_key": "invalid-fixture"})


def test_query_document_date_and_data_year_are_independent():
    from app.modules.rag.evidence_validation import validate_plan_years
    validate_plan_years(QueryPlan(query="Report 2026 data from 2023", years=[2023], document_years=[2026]),
        "In the report issued in 2026, what is the data for 2023?", [], 2026)
    with pytest.raises(ValueError):
        validate_plan_years(QueryPlan(query="Report 2026 data from 2022", years=[2022], document_years=[2026]),
            "In the report issued in 2026, what is the data for 2023?", [], 2026)


def test_compact_year_range_preserves_intermediate_years_without_guessing():
    from app.modules.rag.evidence_validation import validate_plan_years
    validate_plan_years(QueryPlan(query="Compare 2022–2024", years=[2022, 2023, 2024]), "Compare 2022–2024", [], 2026)
    with pytest.raises(ValueError):
        validate_plan_years(QueryPlan(query="Compare 2022 and 2024", years=[2022, 2023, 2024]),
            "Compare 2022 and 2024", [], 2026)


@pytest.mark.parametrize("title", ["Research", "Finance", "Library", "Academic policy"])
def test_generic_multi_year_table_keeps_column_years(title):
    artifact = build_source_artifact(f"# {title} 2026\n\n| Entity | 2022 | 2023 | 2024 |\n| --- | --- | --- | --- |\n| Department A | 17 | 18 | 19 |", 1, {})
    assert [f["raw_data"]["temporal_context"]["year"] for f in artifact["facts"]] == [2022, 2023, 2024]
    assert artifact["issues"] == []


def test_repeated_year_columns_without_subheadings_require_disambiguation():
    artifact = build_source_artifact("| Entity | 2024 | 2024 |\n| --- | --- | --- |\n| Department A | 17 | 18 |", 1, {})
    assert any(issue["code"] == "AMBIGUOUS_COLUMN_CONTEXT" for issue in artifact["issues"])
    assert all(f["raw_data"]["context_ambiguous"] for f in artifact["facts"])


def test_unit_context_is_reviewed_not_silently_promoted():
    from app.modules.knowledge.schemas import SourceContextEditRequest
    from app.modules.knowledge.services.source_context import (
        apply_context_edits,
        review_context_artifact,
    )

    text = "# Annual report 2026\n\nDepartment A recorded 17 items in 2023."
    artifact = build_source_artifact(text, 1, {})
    unit = artifact["retrieval_units"]["units"][-1]
    request = SourceContextEditRequest(expected_fact_set_hash=artifact["fact_set_hash"],
        expected_unit_manifest_hash=artifact["unit_manifest_hash"], reason="Verified with original source",
        units=[{"unit_id": unit["id"], "data_years": [2023], "role": "data", "evidence_quote": unit["text"]}])
    revised = apply_context_edits(artifact, request, "reviewer")
    assert revised["retrieval_units"]["units"][-1]["temporal"]["status"] == "proposed"
    assert artifact["retrieval_units"]["units"][-1]["temporal"]["data_years"] == []
    approved = review_context_artifact(revised, "approved", "reviewer", None)
    manifest = resolve_unit_manifest(text, approved)
    assert manifest.units[-1].temporal.data_years == [2023]
    assert manifest.units[-1].temporal.status == "verified"
    assert manifest_digest(manifest) != artifact["unit_manifest_hash"]
    request.units[0].data_years = [2026]
    with pytest.raises(Exception) as failure:
        apply_context_edits(artifact, request, "reviewer")
    assert failure.value.code == "UNIT_CONTEXT_INVALID"


def test_dense_and_lexical_use_the_same_verified_scope_and_keep_unknown():
    from app.modules.knowledge.normalization.retrieval_models import TemporalScope
    from app.modules.rag.retriever import filter_unit_years

    manifest = build_unit_manifest("History from 2023.")
    unit = manifest.units[0]
    unit.temporal = TemporalScope(data_years=[2023], role="data", status="verified", evidence_quote=unit.text)
    hit = {"chunk_id": "a", "metadata": {"source_unit": unit.model_dump()}}
    unknown = {"chunk_id": "b", "metadata": {}}
    assert filter_unit_years([hit, unknown], [2023]) == [hit, unknown]
    assert filter_unit_years([hit, unknown], [2026]) == [unknown]


@pytest.mark.asyncio
async def test_historical_fact_in_new_document_is_not_filtered_by_document_year():
    from types import SimpleNamespace

    source = split_source_blocks("# REPORT 2026\n\nOverview.", binding_id="b", index_id="i", source_id="s", title="Report")
    for block in source:
        block.scope_years = [2026]
    fact = SimpleNamespace(id="f", binding_id="b", index_revision_id="i", applicability_year=2023,
        entity_name="Department A", attribute_name="Count / 2023", attribute_value="17",
        raw_data={"table_id": "t", "row_index": 1, "column_index": 1, "page_number": 2,
                  "temporal_context": {"type": "year", "year": 2023, "status": "verified"}})
    db = AsyncMock()
    db.execute.return_value = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [fact]
    rows = await reviewed_fact_blocks(db, AskRequest(question="Department A in 2023", collection_id="c"),
        RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"}),
        QueryPlan(query="Department A", years=[2023]), source)
    assert len(rows) == 1 and rows[0].scope_years == [2023]
    assert rank_blocks(rows, ["Department A"], 5, [2023])
    assert not rank_blocks(rows, ["Department A"], 5, [2026])


@pytest.mark.asyncio
async def test_document_heading_does_not_force_prose_data_year():
    import hashlib
    from types import SimpleNamespace

    text = "# REPORT 2026\n\nDepartment A recorded 17 items in 2023."
    digest = hashlib.sha256(text.encode()).hexdigest()
    source = SimpleNamespace(id="s", canonical_markdown=text, canonical_hash=digest,
        page_manifest=[], citation_metadata={}, snapshot_metadata={"title": "Report"},
        parse_provenance={"structured_artifact": {"content_hash": digest, "facts": [], "issues": [], "review": {"status": "approved"}}})
    index = SimpleNamespace(id="i", chunk_count=1, parity_report={"parity_passed": True})
    binding = SimpleNamespace(id="b")
    db = AsyncMock()
    db.execute.return_value = MagicMock()
    db.execute.return_value.all.return_value = [(source, index, binding)]
    units = await load_published_blocks(db, RetrievalSnapshot(snapshot_id="snap", collection_id="c",
        tenant_id="tenant", workspace_id="workspace", binding_revisions={"b": "i"}))
    historical = next(block for block in units if "17 items" in block.text)
    assert not historical.scope_years or 2023 in historical.scope_years
    assert rank_blocks([historical], ["Department A"], 1, [2023])
