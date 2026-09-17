"""HTTP routes for the Core-compatible Node Catalog."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.modules.node_catalog.schemas import NodeCatalogResponse
from app.modules.node_catalog.service import node_catalog_service

router = APIRouter(prefix="/nodes", tags=["Node Catalog"])


@router.get(
    "",
    response_model=NodeCatalogResponse,
    summary="Liệt kê các NodeManifest đã được chứng nhận từ QNU AI Core",
)
async def list_nodes(
    search: str | None = Query(None, max_length=255),
    category: str | None = Query(None, max_length=64),
    status: str | None = Query(None, max_length=32),
) -> NodeCatalogResponse:
    """Return the same ``{items: [...]}`` contract used by qnu-ai-core."""
    items = await node_catalog_service.list_nodes(search=search, category=category, status=status)
    return NodeCatalogResponse(items=items)
