"""Central Document Repository Module — MinIO storage, pre-parsing, and cross-collection reuse."""

from typing import TYPE_CHECKING, Any

from app.modules.documents.models import DocumentGroup, DocumentRevision, RepositoryDocument

if TYPE_CHECKING:
    from fastapi import APIRouter

    from app.modules.documents.service import DocumentRepositoryService

    documents_router: APIRouter
    document_repository_service: DocumentRepositoryService


def __getattr__(name: str) -> Any:
    """Load API/runtime exports only when the application requests them."""
    if name == "documents_router":
        from app.modules.documents.router import router

        return router
    if name == "document_repository_service":
        from app.modules.documents.service import document_repository_service

        return document_repository_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DocumentGroup",
    "DocumentRevision",
    "RepositoryDocument",
    "document_repository_service",
    "documents_router",
]
