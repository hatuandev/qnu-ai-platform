"""Regression contracts for reviewed, structure-preserving derived chunks."""

import hashlib
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.services.chunk_set_service import chunk_set_service
from app.modules.knowledge.services.source_artifact import build_source_artifact


def source_fixture(markdown, *, review=False):
    artifact = build_source_artifact(markdown, 0, {})
    if review:
        artifact["review"] = {"status": "required"}
    return KnowledgeSourceRevision(
        id="source", binding_id="binding", revision_no=1, status="ready",
        canonical_markdown=markdown, canonical_hash=hashlib.sha256(markdown.encode()).hexdigest(),
        origin_file_hash="original", parse_provenance={"structured_artifact": artifact},
    )


def db_fixture(source):
    db = AsyncMock()
    db.add = MagicMock()
    found, empty = MagicMock(), MagicMock()
    found.scalar_one_or_none.return_value = source
    empty.scalar_one_or_none.return_value = None
    empty.scalars.return_value.first.return_value = None
    db.execute.side_effect = [found, empty, empty]
    return db


@pytest.mark.asyncio
async def test_formula_and_legend_stay_together():
    markdown = "# Scope 2026\n\nOnly inside the interval:\n\n$$\ny = a*x\n\n+ b\n$$\n\nVariables:\n\n- x: input\n- y: result\n\n# Other 2025\n\nUnrelated."
    source = source_fixture(markdown)
    chunk_set = await chunk_set_service.get_or_create_chunk_set(db_fixture(source), source.id)
    formula = [c for c in chunk_set.chunk_config["_manifest"] if "y = a*x" in c["content"]]
    assert len(formula) == 1
    assert "$$\ny = a*x\n\n+ b\n$$" in formula[0]["content"]
    assert "x: input" in formula[0]["content"] and "y: result" in formula[0]["content"]
    assert "Only inside the interval" in formula[0]["content"]
    assert "Other 2025" not in formula[0]["content"]


@pytest.mark.asyncio
async def test_stale_ready_status_cannot_bypass_review():
    source = source_fixture("# Review\n\nText.", review=True)
    db = db_fixture(source)
    with pytest.raises(AppException) as error:
        await chunk_set_service.get_or_create_chunk_set(db, source.id)
    assert error.value.code == "FACT_SET_REVIEW_REQUIRED"
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_bundle_covers_metadata_not_only_chunk_text():
    from app.modules.knowledge.services.derived_bundle import validate_chunk_set

    source = source_fixture("# Heading\n\nText.")
    chunk_set = await chunk_set_service.get_or_create_chunk_set(db_fixture(source), source.id)
    artifact = source.parse_provenance["structured_artifact"]
    validate_chunk_set(source, artifact, chunk_set)
    chunk_set.chunk_config = deepcopy(chunk_set.chunk_config)
    chunk_set.chunk_config["_manifest"][0]["metadata"]["source_unit_id"] = "wrong"
    with pytest.raises(AppException) as error:
        validate_chunk_set(source, artifact, chunk_set)
    assert error.value.code == "DERIVED_BUNDLE_INVALID"


@pytest.mark.asyncio
async def test_publish_revalidates_after_remote_io_before_pointer_swap():
    from types import SimpleNamespace
    from unittest.mock import patch

    from app.modules.knowledge.services.selected_vector_publish import publish_selected_vectors
    from tests.test_selected_vector_publish import publication_fixture, publication_patches

    db, col, gen, bindings, _, _, item = publication_fixture()
    error = AppException("Changed during remote I/O", code="DERIVED_BUNDLE_INVALID", status_code=409)
    validate = AsyncMock(side_effect=[None, error])
    with publication_patches(col), patch(
        "app.modules.knowledge.services.generation_candidate.validate_candidate_artifacts", validate,
    ), pytest.raises(AppException) as failure:
        await publish_selected_vectors(db, col.id, gen.id, [item], SimpleNamespace(actor_id="reviewer"))
    assert failure.value.code == "DERIVED_BUNDLE_INVALID"
    assert bindings[0].active_index_revision_id is None
    assert db.commit.await_count == 1  # Read transaction only, not publication.


def chunks_for(markdown, **kwargs):
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    from app.modules.knowledge.normalization.structure_chunks import structure_chunks

    artifact = build_source_artifact(markdown, 0, {})
    manifest = resolve_unit_manifest(markdown, artifact)
    return structure_chunks(markdown, manifest, context_graph=artifact["context_graph"], **kwargs)


def test_list_children_keep_parent_and_intro_without_sibling_leak():
    markdown = "# Requirements\n\nChoose:\n\n- Parent A\n  - Child A1\n  - Child A2\n- Parent B\n  - Child B1\n\n# Separate\n\nOther."
    chunks = chunks_for(markdown)
    first = next(chunk for chunk in chunks if "Child A1" in chunk["content"])
    assert "Choose:" in first["content"] and "Parent A" in first["content"]
    assert "  - Child A2" in first["content"]
    assert "Parent B" not in first["content"] and "Other." not in first["content"]
    assert first["page_number"] is None
    assert len(first["metadata"]["source_unit_ids"]) == 3


@pytest.mark.parametrize("fence", ["```", "~~~~"])
def test_fenced_code_is_atomic_even_with_blank_lines_headings_and_lists(fence):
    body = f"{fence}text\n# Literal heading\n\n- literal item\n{fence}"
    chunks = chunks_for("# Actual heading\n\n" + body + "\n\nAfter.")
    block = next(chunk for chunk in chunks if "Literal heading" in chunk["content"])
    assert body in block["content"] and block["metadata"]["structure_kind"] == "code"
    assert len([chunk for chunk in chunks if "literal item" in chunk["content"]]) == 1
    after = next(chunk for chunk in chunks if "After." in chunk["content"])
    assert "Literal heading" not in after["content"]


def test_table_rows_keep_header_unit_and_notes_without_merging_years():
    markdown = "# Rates 2026\n\nUnit: USD per month.\n\n| Entity | Amount |\n| --- | --- |\n| Alpha | 0 |\n| Beta | — |\n\nNotes:\n\n1. Applies only to full-time students.\n\n# Historical 2025\n\nOther conditions."
    row = next(chunk for chunk in chunks_for(markdown) if "| Alpha | 0 |" in chunk["content"])
    assert "Unit: USD" in row["content"] and "| Entity | Amount |" in row["content"]
    assert "full-time" in row["content"] and "Historical" not in row["content"]
    assert row["metadata"]["source_unit"]["temporal"]["data_years"] == []


def test_oversize_formula_rejected_not_truncated():
    with pytest.raises(AppException) as error:
        chunks_for("# Formula\n\n$$\nx = 123456789\n$$\n\nLegend:\n\n- x: number", max_chars=30)
    assert error.value.code == "SOURCE_UNIT_TOO_LARGE"


def test_bad_chunker_cannot_invent_or_drop_source_text():
    from types import SimpleNamespace

    fake = MagicMock()
    fake.chunk.return_value = [SimpleNamespace(content="Invented replacement")]
    with pytest.raises(AppException) as error:
        chunks_for("Source paragraph.", chunker=fake)
    assert error.value.code == "CHUNK_SOURCE_MISMATCH"


@pytest.mark.asyncio
async def test_same_text_different_fact_annotations_changes_chunk_config_key():
    from app.modules.knowledge.services.derived_bundle import digest

    first = source_fixture("| Entity | Value |\n| --- | --- |\n| Alpha | 21 |")
    second = source_fixture(first.canonical_markdown)
    artifact = second.parse_provenance["structured_artifact"]
    artifact["facts"][0]["raw_data"]["operator_note"] = "reviewed context"
    artifact["fact_set_hash"] = digest(artifact["facts"])
    one = await chunk_set_service.get_or_create_chunk_set(db_fixture(first), first.id)
    two = await chunk_set_service.get_or_create_chunk_set(db_fixture(second), second.id)
    assert one.chunk_set_key != two.chunk_set_key


@pytest.mark.asyncio
async def test_cross_revision_reuse_rebinds_seal_without_mutating_old_set():
    from app.modules.knowledge.services.derived_bundle import validate_chunk_set

    source = source_fixture("# Data\n\nUnchanged.")
    first = await chunk_set_service.get_or_create_chunk_set(db_fixture(source), source.id)
    old_config = deepcopy(first.chunk_config)
    source2 = source_fixture(source.canonical_markdown)
    source2.id = "source2"
    source2.revision_no = 2
    db = db_fixture(source2)
    found, empty, reusable = MagicMock(), MagicMock(), MagicMock()
    found.scalar_one_or_none.return_value = source2
    empty.scalar_one_or_none.return_value = None
    reusable.scalars.return_value.first.return_value = first
    db.execute.side_effect = [found, empty, reusable]
    second = await chunk_set_service.get_or_create_chunk_set(db, source2.id)
    assert second.chunk_set_key == first.chunk_set_key and second.id != first.id
    assert second.chunk_config["_bundle"]["source_revision_id"] == source2.id
    assert second.chunk_config["_bundle_hash"] != first.chunk_config["_bundle_hash"]
    assert first.chunk_config == old_config
    validate_chunk_set(source2, source2.parse_provenance["structured_artifact"], second)


def test_grouped_child_year_cannot_bypass_explicit_retrieval_scope():
    from app.modules.knowledge.normalization.retrieval_models import SourceUnit, TemporalScope
    from app.modules.rag.retriever import filter_unit_years

    parent = SourceUnit(id="p", kind="list", text="Parent", start=0, end=6)
    child = SourceUnit(id="c", kind="list", text="Data 2025", start=7, end=16,
                       temporal=TemporalScope(status="verified", role="data", data_years=[2025], evidence_quote="2025"))
    hit = {"metadata": {"source_unit": parent.model_dump(), "source_units": [parent.model_dump(), child.model_dump()]}}
    assert filter_unit_years([hit], [2026]) == []
    assert filter_unit_years([hit], [2025]) == [hit]
    assert filter_unit_years([hit], []) == [hit]


def test_table_header_footnote_is_included_with_every_row():
    markdown = "# Scope\n\n| Entity | Amount[^u] |\n| --- | --- |\n| Alpha | 0 |\n\n[^u]: USD per month, only during semester."
    row = next(chunk for chunk in chunks_for(markdown) if "| Alpha | 0 |" in chunk["content"])
    assert "USD per month, only during semester" in row["content"]


def test_missing_footnote_requires_review_not_silent_drop():
    with pytest.raises(AppException) as error:
        chunks_for("# Scope\n\nAmount[^missing].")
    assert error.value.code == "SOURCE_CONTEXT_UNRESOLVED"


def test_formula_does_not_absorb_and_break_adjacent_code_fence():
    markdown = "# Scope\n\n$$\ny = x\n$$\n\n```text\nDo not interpret\n\n- code line\n```"
    chunks = chunks_for(markdown)
    formula = next(chunk for chunk in chunks if chunk["metadata"]["structure_kind"] == "formula")
    assert "```" not in formula["content"]
    code = next(chunk for chunk in chunks if chunk["metadata"]["structure_kind"] == "code")
    assert "```text\nDo not interpret\n\n- code line\n```" in code["content"]


@pytest.mark.asyncio
async def test_selected_publication_rejects_generation_changed_during_remote_io():
    from unittest.mock import patch

    from app.modules.knowledge.services.selected_vector_publish import publish_selected_vectors
    from tests.test_selected_vector_publish import publication_fixture, publication_patches

    db, col, gen, bindings, _, index, item = publication_fixture()

    async def changed(*args, **kwargs):
        index.vector_generation_id = "foreign-generation"

    with publication_patches(col), patch(
        "app.modules.knowledge.services.selected_vector_publish.vector_indexer.activate_index_revision",
        AsyncMock(side_effect=changed),
    ), pytest.raises(AppException) as error:
        await publish_selected_vectors(db, col.id, gen.id, [item], None)
    assert error.value.code == "SOURCE_NOT_READY"
    assert bindings[0].active_index_revision_id is None
