"""Collection summaries must include snapshot sources, not only group links."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.knowledge.models import KnowledgeCollection
from app.modules.knowledge.services.group_source_service import GroupSourceService


@pytest.mark.asyncio
@pytest.mark.parametrize("published_count, expected_status", [(19, "ready"), (0, "pending")])
async def test_summary_counts_direct_sources_and_serving_embedding(
    published_count: int, expected_status: str,
) -> None:
    collection = KnowledgeCollection(
        id="col_summary",
        name="Snapshot collection",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        collection_metadata={
            "active_vector_generation_id": "generation_dynamic",
            "embedding_model": "embedding_from_active_generation",
            "data_processing": {"embedding_model": "previous_config"},
        },
    )
    groups = MagicMock()
    groups.scalars.return_value.all.return_value = []
    counts = MagicMock()
    counts.scalar.return_value = 19
    counts.one.return_value = (published_count, 227 if published_count else 0)
    db = AsyncMock()
    db.get.return_value = collection
    db.execute.side_effect = [groups, counts, counts]

    result = await GroupSourceService().get_collection_summary_metrics(db, collection.id)

    assert result.total_sources == 19
    assert result.published_documents_count == published_count
    assert result.collection_status == expected_status
    assert result.configured_embedding_model == "embedding_from_active_generation"


@pytest.mark.asyncio
async def test_summary_does_not_hide_database_failure_as_empty_collection() -> None:
    db = AsyncMock()
    db.get.side_effect = ConnectionError("Database unavailable")

    with pytest.raises(ConnectionError, match="Database unavailable"):
        await GroupSourceService().get_collection_summary_metrics(db, "col_summary")
