"""Partial publication preserves unselected pointers and enforces snapshot gates."""

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import PublishVectorItem
from app.modules.knowledge.services.selected_vector_publish import (
    publish_selected_vectors,
    resolve_selected_publication,
)


def publication_fixture(active_generation: str | None = "gen"):
    col = KnowledgeCollection(
        id="col", tenant_id="tenant", workspace_id="workspace", index_epoch=3,
        collection_metadata={"active_vector_generation_id": active_generation},
    )
    gen = KnowledgeVectorGeneration(
        id="gen", collection_id="col", status="ready", embedding_model="dynamic_model",
        provider_id="dynamic_provider", embedding_dimension=8, qdrant_collection_name="vectors",
    )
    bindings = [KnowledgeBinding(
        id=f"b{number}", collection_id="col", tenant_id="tenant", workspace_id="workspace",
        status="active", active_source_revision_id=f"s{number}",
        active_index_revision_id="old2" if number == 2 and active_generation else None, active_epoch=1,
    ) for number in (1, 2, 3)]
    source = KnowledgeSourceRevision(
        id="s1", binding_id="b1", revision_no=1, status="ready", canonical_hash="hash",
        parse_provenance={"structured_artifact": {
            "content_hash": "hash", "issues": [], "review": {"status": "approved"},
        }},
    )
    index = KnowledgeIndexRevision(
        id="new1", binding_id="b1", source_revision_v2_id="s1", vector_generation_id="gen",
        status="ready", chunk_count=4, parity_report={"parity_passed": True},
    )
    item = PublishVectorItem(binding_id="b1", source_revision_id="s1", index_revision_id="new1")
    db = AsyncMock()
    db.add = MagicMock()
    db.get.side_effect = lambda model, key: {"gen": gen, "s1": source}.get(key)
    binding_result, index_result = MagicMock(), MagicMock()
    binding_result.all.return_value = bindings
    index_result.all.return_value = [index]
    db.scalars.side_effect = [binding_result, index_result, binding_result]
    return db, col, gen, bindings, source, index, item


def publication_patches(col, activate=None):
    stack = ExitStack()
    stack.enter_context(patch(
        "app.modules.knowledge.services.selected_vector_publish.get_scoped_collection",
        AsyncMock(return_value=col),
    ))
    stack.enter_context(patch(
        "app.modules.knowledge.services.generation_candidate.validate_candidate_artifacts", AsyncMock(),
    ))
    stack.enter_context(patch(
        "app.modules.knowledge.services.selected_vector_publish.vector_indexer.activate_index_revision",
        activate or AsyncMock(return_value=4),
    ))
    return stack


@pytest.mark.asyncio
@pytest.mark.parametrize("active_generation", [None, "gen"])
async def test_publish_one_source_without_requiring_or_changing_other_sources(active_generation):
    db, col, gen, bindings, _, index, item = publication_fixture(active_generation)
    with publication_patches(col):
        result = await publish_selected_vectors(db, col.id, gen.id, [item], SimpleNamespace(actor_id="officer"))
    assert result.new_epoch == 4
    assert bindings[0].active_index_revision_id == index.id
    assert bindings[1].active_index_revision_id == ("old2" if active_generation else None)
    assert bindings[1].active_epoch == 1
    assert bindings[2].active_index_revision_id is None
    assert gen.status == "active"
    assert db.add.call_count == 1


@pytest.mark.asyncio
async def test_new_generation_cannot_drop_other_published_sources():
    db, col, gen, bindings, _, _, item = publication_fixture("different_gen")
    with publication_patches(col), pytest.raises(AppException) as exc:
        await resolve_selected_publication(db, col.id, gen.id, [item], None)
    assert exc.value.code == "GENERATION_SWITCH_REQUIRES_SERVING_SOURCES"
    assert bindings[1].active_index_revision_id == "old2"
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_generation_switch_covers_serving_sources_without_requiring_unpublished_source():
    db, col, gen, bindings, source, index, item = publication_fixture("different_gen")
    old_gen = KnowledgeVectorGeneration(id="different_gen", collection_id=col.id, status="active")
    second_source = KnowledgeSourceRevision(
        id="s2", binding_id="b2", revision_no=1, status="ready", canonical_hash="hash",
        parse_provenance=source.parse_provenance,
    )
    second_index = KnowledgeIndexRevision(
        id="new2", binding_id="b2", source_revision_v2_id="s2", vector_generation_id=gen.id,
        status="ready", chunk_count=3, parity_report={"parity_passed": True},
    )
    db.get.side_effect = lambda model, key: {
        "gen": gen, "different_gen": old_gen, "s1": source, "s2": second_source,
    }.get(key)
    bindings_result, indexes_result = MagicMock(), MagicMock()
    bindings_result.all.return_value = bindings
    indexes_result.all.return_value = [index, second_index]
    db.scalars.side_effect = [bindings_result, indexes_result, bindings_result]
    second_item = PublishVectorItem(binding_id="b2", source_revision_id="s2", index_revision_id="new2")
    with publication_patches(col):
        await publish_selected_vectors(db, col.id, gen.id, [item, second_item], None)
    assert bindings[1].active_index_revision_id == "new2"
    assert bindings[2].active_index_revision_id is None
    assert old_gen.status == "retired"


@pytest.mark.asyncio
@pytest.mark.parametrize("case, code", [
    ("foreign", "SOURCE_NOT_FOUND"), ("duplicate", "INVALID_PUBLISH_SELECTION"),
    ("stale", "SOURCE_REVISION_CHANGED"), ("review", "FACT_SET_REVIEW_REQUIRED"),
    ("parity", "PARITY_GATE_FAILED"),
])
async def test_invalid_targets_fail_before_remote_activation(case, code):
    db, col, gen, _, source, index, item = publication_fixture()
    items = [item]
    if case == "foreign":
        items = [item.model_copy(update={"binding_id": "foreign"})]
    elif case == "duplicate":
        items = [item, item]
    elif case == "stale":
        items = [item.model_copy(update={"source_revision_id": "other"})]
    elif case == "review":
        source.parse_provenance["structured_artifact"]["review"]["status"] = "required"
    else:
        index.parity_report = {"parity_passed": False}
    activate = AsyncMock()
    with publication_patches(col, activate), pytest.raises(AppException) as exc:
        await publish_selected_vectors(db, col.id, gen.id, items, None)
    assert exc.value.code == code
    activate.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_remote_failure_leaves_all_serving_pointers_unchanged():
    db, col, gen, bindings, _, _, item = publication_fixture()
    activate = AsyncMock(side_effect=RuntimeError("Qdrant unavailable"))
    with publication_patches(col, activate), pytest.raises(RuntimeError, match="Qdrant unavailable"):
        await publish_selected_vectors(db, col.id, gen.id, [item], None)
    assert [binding.active_index_revision_id for binding in bindings] == [None, "old2", None]
    assert col.index_epoch == 3
    assert gen.status == "ready"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_source_change_during_activation_fails_compare_and_swap():
    db, col, gen, bindings, _, _, item = publication_fixture()
    async def change_source(*args, **kwargs):
        bindings[0].active_source_revision_id = "changed"
    with publication_patches(col, AsyncMock(side_effect=change_source)), pytest.raises(AppException) as exc:
        await publish_selected_vectors(db, col.id, gen.id, [item], None)
    assert exc.value.code == "GENERATION_CAS_CONFLICT"
    assert bindings[0].active_index_revision_id is None
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_partial_candidate_includes_preserved_serving_sources():
    from app.modules.knowledge.services.generation_candidate import resolve_candidate_snapshot

    db, col, gen, _, _, _, item = publication_fixture()
    with publication_patches(col):
        snapshot = await resolve_candidate_snapshot(db, col.id, gen.id, None, [item])
    assert snapshot.binding_revisions == {"b1": "new1", "b2": "old2"}
    assert snapshot.vector_generations == {"b1": "gen", "b2": "gen"}
