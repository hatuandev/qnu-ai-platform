"""RAG Module Package Initialization."""

from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.composer import answer_format_planner
from app.modules.rag.facts import fact_layer
from app.modules.rag.fusion import reciprocal_rank_fusion
from app.modules.rag.reranker import reranker_client
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.router import router as rag_router
from app.modules.rag.service import rag_service
from app.modules.rag.vector_indexer import vector_indexer

__all__ = [
    "answer_format_planner",
    "citation_guard",
    "fact_layer",
    "hybrid_retriever",
    "rag_router",
    "rag_service",
    "reciprocal_rank_fusion",
    "reranker_client",
    "vector_indexer",
]
