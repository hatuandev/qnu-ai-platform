"""Central Document Repository Module — MinIO storage, pre-parsing, and cross-collection reuse."""

from app.modules.documents.models import RepositoryDocument
from app.modules.documents.router import router as documents_router
from app.modules.documents.service import document_repository_service

__all__ = [
    "RepositoryDocument",
    "document_repository_service",
    "documents_router",
]
