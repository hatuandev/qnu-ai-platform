"""Knowledge Sub-services Package — Modularized by domain responsibility."""

from __future__ import annotations

from app.modules.knowledge.services.collection_service import collection_service
from app.modules.knowledge.services.facts_service import facts_service
from app.modules.knowledge.services.ingestion_service import ingestion_service
from app.modules.knowledge.services.reconciliation_service import reconciliation_service

__all__ = [
    "collection_service",
    "facts_service",
    "ingestion_service",
    "reconciliation_service",
]
