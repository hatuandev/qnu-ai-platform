"""Knowledge module exports without importing runtime services eagerly."""

from typing import TYPE_CHECKING, Any

from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeDocument,
    KnowledgeFact,
    KnowledgeGroupSource,
)

if TYPE_CHECKING:
    from fastapi import APIRouter

    from app.modules.knowledge.service import KnowledgeService

    knowledge_router: APIRouter
    knowledge_service: KnowledgeService


def __getattr__(name: str) -> Any:
    """Load API/runtime exports only when the application requests them."""
    if name == "knowledge_router":
        from app.modules.knowledge.router import router

        return router
    if name == "knowledge_service":
        from app.modules.knowledge.service import knowledge_service

        return knowledge_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "KnowledgeBinding",
    "KnowledgeChunk",
    "KnowledgeCollection",
    "KnowledgeDocument",
    "KnowledgeFact",
    "KnowledgeGroupSource",
    "knowledge_router",
    "knowledge_service",
]
