"""Register domain routers under one API prefix."""

from __future__ import annotations

from fastapi import FastAPI

from qnu.api.health import router as health_router
from qnu.domains.answer_review.router import router as answer_review_router
from qnu.domains.assistants.router import router as assistants_router
from qnu.domains.conversations.router import router as conversations_router
from qnu.domains.evaluation.router import router as evaluation_router
from qnu.domains.identity.router import router as identity_router
from qnu.domains.integration.router import admin_router as integration_admin_router
from qnu.domains.integration.router import gateway_router as integration_gateway_router
from qnu.domains.knowledge.collections.router import router as knowledge_collections_router
from qnu.domains.knowledge.compilation.review.router import router as compilation_review_router
from qnu.domains.knowledge.compilation.router import router as compilation_router
from qnu.domains.knowledge.compilation.workflow.router import router as compilation_workflow_router
from qnu.domains.knowledge.folders.router import router as knowledge_folders_router
from qnu.domains.knowledge.inbox.router import router as knowledge_inbox_router
from qnu.domains.knowledge.index.router import router as indexing_router
from qnu.domains.knowledge.preparation.router import router as preparation_router
from qnu.domains.knowledge.publication.router import router as publication_router
from qnu.domains.knowledge.review.router import router as knowledge_review_router
from qnu.domains.knowledge.sources.router import router as knowledge_sources_router
from qnu.domains.lifecycle.router import router as lifecycle_router
from qnu.domains.modelops.connections.router import router as connections_router
from qnu.domains.modelops.diagnostics.router import router as diagnostics_router
from qnu.domains.modelops.resilience.router import router as resilience_router
from qnu.domains.modelops.router import router as modelops_router
from qnu.domains.modelops.router import workspace_router as modelops_workspace_router
from qnu.domains.modelops.usage.router import router as usage_router
from qnu.domains.ocr.review.router import router as ocr_review_router
from qnu.domains.ocr.router import router as ocr_processing_router
from qnu.domains.operations.router import router as operations_router
from qnu.domains.rag.answer.router import router as answers_router
from qnu.domains.workspaces.router import router as workspaces_router
from qnu.platform.config import Settings


def register_routes(app: FastAPI, settings: Settings) -> None:
    app.include_router(connections_router, prefix=settings.API_PREFIX)
    app.include_router(health_router)
    app.include_router(identity_router, prefix=settings.API_PREFIX)
    app.include_router(workspaces_router, prefix=settings.API_PREFIX)
    app.include_router(assistants_router, prefix=settings.API_PREFIX)
    app.include_router(answer_review_router, prefix=settings.API_PREFIX)
    app.include_router(conversations_router, prefix=settings.API_PREFIX)
    app.include_router(knowledge_collections_router, prefix=settings.API_PREFIX)
    app.include_router(knowledge_folders_router, prefix=settings.API_PREFIX)
    app.include_router(knowledge_sources_router, prefix=settings.API_PREFIX)
    app.include_router(preparation_router, prefix=settings.API_PREFIX)
    app.include_router(ocr_processing_router, prefix=settings.API_PREFIX)
    app.include_router(ocr_review_router, prefix=settings.API_PREFIX)
    app.include_router(compilation_router, prefix=settings.API_PREFIX)
    app.include_router(compilation_review_router, prefix=settings.API_PREFIX)
    app.include_router(compilation_workflow_router, prefix=settings.API_PREFIX)
    app.include_router(publication_router, prefix=settings.API_PREFIX)
    app.include_router(knowledge_review_router, prefix=settings.API_PREFIX)
    app.include_router(knowledge_inbox_router, prefix=settings.API_PREFIX)
    app.include_router(indexing_router, prefix=settings.API_PREFIX)
    app.include_router(answers_router, prefix=settings.API_PREFIX)
    app.include_router(modelops_router, prefix=settings.API_PREFIX)
    app.include_router(diagnostics_router, prefix=settings.API_PREFIX)
    app.include_router(resilience_router, prefix=settings.API_PREFIX)
    app.include_router(modelops_workspace_router, prefix=settings.API_PREFIX)
    app.include_router(usage_router, prefix=settings.API_PREFIX)
    app.include_router(operations_router, prefix=settings.API_PREFIX)
    app.include_router(lifecycle_router, prefix=settings.API_PREFIX)
    app.include_router(evaluation_router, prefix=settings.API_PREFIX)
    app.include_router(integration_admin_router, prefix=settings.API_PREFIX)
    app.include_router(integration_gateway_router, prefix=settings.API_PREFIX)
