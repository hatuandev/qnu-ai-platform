"""Authenticated, read-only access to derived knowledge pages."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.services.wiki_snapshot import read_collection_map
from app.modules.knowledge.services.wiki_views import read_revision_pages, read_revision_review

router = APIRouter()


@router.get("/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/knowledge-pages")
async def get_knowledge_pages(collection_id: str, source_id: str, revision_id: str,
                             db: AsyncSession = Depends(get_db),
                             actor: AuthActor = Depends(require_permission("ai.knowledge.view"))) -> dict:
    return await read_revision_pages(db, collection_id, source_id, revision_id, actor)


@router.get("/collections/{collection_id}/knowledge-map")
async def get_knowledge_map(collection_id: str, db: AsyncSession = Depends(get_db),
                            actor: AuthActor = Depends(require_permission("ai.knowledge.view"))) -> dict:
    return await read_collection_map(db, collection_id, actor)


@router.get("/collections/{collection_id}/knowledge-map/review")
async def get_knowledge_map_review(collection_id: str, db: AsyncSession = Depends(get_db),
                                   actor: AuthActor = Depends(require_permission("ai.knowledge.review"))) -> dict:
    return await read_collection_map(db, collection_id, actor, review=True)


@router.get("/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/knowledge-pages/review")
async def get_knowledge_pages_review(collection_id: str, source_id: str, revision_id: str,
                                      db: AsyncSession = Depends(get_db),
                                      actor: AuthActor = Depends(require_permission("ai.knowledge.review"))) -> dict:
    return await read_revision_review(db, collection_id, source_id, revision_id, actor)
