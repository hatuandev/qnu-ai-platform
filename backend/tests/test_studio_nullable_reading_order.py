from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service


@pytest.mark.asyncio
@pytest.mark.parametrize("order,legacy_order,expected", [(None, None, 1), (None, 4, 4), (0, 4, 0)])
async def test_studio_accepts_nullable_reading_order(order, legacy_order, expected):
    revision = SimpleNamespace(
        id="revision",
        status="ready",
        canonical_markdown="Nội dung trang",
        snapshot_metadata={},
        parse_provenance={},
        citation_metadata={}, canonical_hash=None,
        page_manifest=[
            {
                "page": 1,
                "blocks": [
                    {
                        "id": "block",
                        "type": "text",
                        "text": "Nội dung trang",
                        "order": order,
                        "reading_order": legacy_order,
                    }
                ],
            }
        ],
    )
    binding = SimpleNamespace(id="source", status="active", active_source_revision=revision)
    with patch.object(source_ingestion_service, "get_source", AsyncMock(return_value=binding)):
        result = await source_ingestion_service.get_source_studio_data(AsyncMock(), "col", "source")
    assert result.pages[0].regions[0].reading_order == expected
    assert result.pages[0].regions[0].details == "Nội dung trang"
