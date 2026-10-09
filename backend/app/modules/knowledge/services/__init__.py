"""Knowledge Sub-services Package — Modularized by domain responsibility."""

from __future__ import annotations

from app.modules.knowledge.services.binding_service import binding_service
from app.modules.knowledge.services.canary_service import canary_service
from app.modules.knowledge.services.collection_service import collection_service
from app.modules.knowledge.services.facts_service import facts_service
from app.modules.knowledge.services.gc_service import gc_service
from app.modules.knowledge.services.index_build_service import index_build_service
from app.modules.knowledge.services.ingestion_service import ingestion_service
from app.modules.knowledge.services.reconciliation_service import reconciliation_service

__all__ = [
    "binding_service",
    "canary_service",
    "collection_service",
    "facts_service",
    "gc_service",
    "index_build_service",
    "ingestion_service",
    "reconciliation_service",
]
