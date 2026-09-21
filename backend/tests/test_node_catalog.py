"""Tests for the Core-compatible Platform Node Catalog."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.node_catalog.service import NodeCatalogService


@pytest.mark.asyncio
async def test_node_catalog_api_returns_core_manifests() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/platform/v1alpha1/nodes")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) >= 14
    assert payload["items"][0]["api_version"] == "qnu.ai/v1alpha1"
    assert any(item["type"] == "core.knowledge.answer" for item in payload["items"])
    assert any(item["type"] == "query.rewrite" for item in payload["items"])


@pytest.mark.asyncio
async def test_node_catalog_supports_search_and_category_filters() -> None:
    service = NodeCatalogService(Path(__file__).resolve().parents[2] / "configs" / "nodes")

    knowledge_nodes = await service.list_nodes(category="knowledge")
    search_results = await service.list_nodes(search="citation")

    assert [node.type for node in knowledge_nodes] == ["core.knowledge.answer"]
    assert {node.type for node in search_results} == {"guard.citation_policy"}


@pytest.mark.asyncio
async def test_node_catalog_returns_empty_when_catalog_directory_is_missing(tmp_path: Path) -> None:
    service = NodeCatalogService(tmp_path / "missing-nodes")

    assert await service.list_nodes() == []
