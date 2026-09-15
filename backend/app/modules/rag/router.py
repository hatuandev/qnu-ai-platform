"""FastAPI Router for RAG Operations — Search, QA, Citations and Fact Lookup."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
) -> SearchResponse:
    return await rag_service.search(db, body)


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Hỏi đáp RAG có Trích dẫn Nguồn & Format Thông minh",
)
async def ask_question(
    body: AskRequest,
    db: AsyncSession = Depends(get_db),
) -> AskResponse:
    return await rag_service.ask(db, body)


@router.post(
    "/facts/lookup",
    response_model=list[FactItem],
    summary="Tra cứu Trực tiếp Bản ghi Sự thật Dạng Bảng (Structured Fact Layer)",
)
async def lookup_facts(
    collection_id: str,
    keywords: list[str],
    db: AsyncSession = Depends(get_db),
) -> list[FactItem]:
    facts = await fact_layer.lookup_facts(db, collection_id=collection_id, keywords=keywords)
    return [FactItem.model_validate(f) for f in facts]
