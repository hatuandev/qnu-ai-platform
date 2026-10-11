"""Normal platform startup must not populate sample knowledge content."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cli import verify_core_seed_data
from app.modules.knowledge import seeder
from app.modules.modelops.services.provider_service import STANDARD_QNU_PROVIDERS
from scripts.clear_seed_knowledge import is_unchanged_sample


@pytest.mark.asyncio
async def test_default_seed_creates_empty_collections_not_sample_content():
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    with patch.object(seeder, "seed_drafting_knowledge", AsyncMock()) as drafting, \
            patch.object(seeder, "seed_regulations_knowledge", AsyncMock()) as regulations, \
            patch.object(seeder, "seed_admissions_knowledge", AsyncMock()) as admissions, \
            patch.object(seeder, "seed_library_knowledge", AsyncMock()) as library, \
            patch.object(seeder, "seed_question_bank_knowledge", AsyncMock()) as questions:
        await seeder.seed_default_knowledge(db)
    for sample_seed in (drafting, regulations, admissions, library, questions):
        sample_seed.assert_not_awaited()
    assert db.add.call_count == 5
    assert all(isinstance(call.args[0], seeder.KnowledgeCollection) for call in db.add.call_args_list)
    assert all(call.args[0].collection_metadata["document_count"] == 0 for call in db.add.call_args_list)


@pytest.mark.asyncio
async def test_readiness_accepts_empty_knowledge_and_does_not_require_chunks():
    db = AsyncMock()
    providers = MagicMock()
    providers.scalars.return_value.all.return_value = [p["id"] for p in STANDARD_QNU_PROVIDERS]
    collections = MagicMock()
    collections.scalars.return_value.all.return_value = [
        "col_admissions", "col_library", "col_drafting", "col_question_bank", "col_regulations",
    ]
    empty = MagicMock()
    empty.scalars.return_value.all.return_value = []
    db.execute.side_effect = [providers, collections, empty]
    factory = MagicMock()
    factory.return_value.__aenter__.return_value = db
    with patch("app.cli.AsyncSessionFactory", factory):
        assert await verify_core_seed_data()
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_existing_collections_are_not_modified_or_populated():
    db = AsyncMock()
    db.add = MagicMock()
    existing = SimpleNamespace(name="User name", collection_metadata={"custom": "keep"})
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    db.execute.return_value = result
    seeded = await seeder.seed_default_knowledge(db)
    assert seeded["collections_seeded"] == 0
    assert seeded["facts_seeded"] == 0
    assert existing.name == "User name" and existing.collection_metadata == {"custom": "keep"}
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_database_failure_never_returns_success_or_sample_fallback():
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("DB unavailable")
    with pytest.raises(RuntimeError, match="DB unavailable"):
        await seeder.seed_default_knowledge(db)
    db.commit.assert_not_awaited()


@pytest.mark.parametrize("modified", ["original", "file", "chunk", "fact", "repository", "index"])
def test_cleanup_never_removes_modified_or_user_owned_data(modified):
    chunks = [{"id": "sample", "content": "seed text"}]
    facts = [{"entity_name": "entity", "attribute_name": "property", "value": "original"}]
    doc = SimpleNamespace(file_hash=hashlib.sha256(b"seed text").hexdigest(), repository_document_id=None)
    chunk = SimpleNamespace(id="sample", content="seed text", index_revision_id=None)
    fact = SimpleNamespace(entity_name="entity", attribute_name="property", attribute_value="original", index_revision_id=None)
    if modified == "file":
        doc.file_hash = "user hash"
    elif modified == "chunk":
        chunk.content = "user text"
    elif modified == "fact":
        fact.attribute_value = "user number"
    elif modified == "repository":
        doc.repository_document_id = "uploaded"
    elif modified == "index":
        chunk.index_revision_id = "user index"
    assert is_unchanged_sample(doc, [chunk], [fact], chunks, facts) == (modified == "original")
