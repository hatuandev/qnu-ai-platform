"""FastAPI Router for RAG Operations — Search, QA, Citations and Fact Lookup."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.schemas import FactItem
from app.modules.rag.facts import fact_layer
from app.modules.rag.schemas import AskRequest, AskResponse, SearchRequest, SearchResponse
from app.modules.rag.service import rag_service

router = APIRouter(prefix="/rag", tags=["RAG & Retrieval Engine"])


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Tìm kiếm Lai Đa Tầng (Dense Qdrant + Sparse Postgres FTS + Rerank)",
)
async def hybrid_search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_current_actor),
) -> SearchResponse:
    return await rag_service.search(db, body.model_copy(update={"tenant_id": actor.tenant_id, "workspace_id": actor.workspace_id}))


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Hỏi đáp RAG có Trích dẫn Nguồn & Format Thông minh",
)
async def ask_question(
    body: AskRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_current_actor),
) -> AskResponse:
    return await rag_service.ask(db, body.model_copy(update={"tenant_id": actor.tenant_id, "workspace_id": actor.workspace_id}))


@router.post(
    "/facts/lookup",
    response_model=list[FactItem],
    summary="Tra cứu Trực tiếp Bản ghi Sự thật Dạng Bảng (Structured Fact Layer)",
)
async def lookup_facts(
    collection_id: str,
    keywords: list[str],
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_current_actor),
) -> list[FactItem]:
    from app.modules.rag.retriever import hybrid_retriever

    snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, collection_id,
                       tenant_id=actor.tenant_id, workspace_id=actor.workspace_id)
    facts = await fact_layer.lookup_facts(db, collection_id=collection_id, keywords=keywords,
                    tenant_id=actor.tenant_id, workspace_id=actor.workspace_id,
                    active_index_revision_ids=set(snapshot.binding_revisions.values()))
    return [FactItem.model_validate(f) for f in facts]
