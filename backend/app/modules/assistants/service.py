"""Facade service for QNU AI Assistant administration and runtime chat."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistants.models import AssistantModel, AssistantVersionModel
from app.modules.assistants.schemas import (
    AssistantBundle,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantCloneRequest,
    AssistantCreateRequest,
    AssistantForkWorkflowResponse,
    AssistantGenerateRequest,
    AssistantGenerateResponse,
    AssistantPublishResponse,
    AssistantReadinessResponse,
    AssistantResponse,
    AssistantRollbackResponse,
    AssistantSeedResponse,
    AssistantTemplateResponse,
    AssistantUpdateRequest,
    AssistantVersionResponse,
)
from app.modules.assistants.services.assistant_chat_service import (
    AssistantChatService,
    assistant_chat_service,
)
from app.modules.assistants.services.assistant_lifecycle_service import (
    AssistantLifecycleService,
    _clean_text,
    _to_response,
    assistant_lifecycle_service,
)
from app.modules.workflows.service import workflow_service


class AssistantService:
    """Facade for QNU AI Assistant operations, delegating to specialized sub-services.

    - AssistantLifecycleService: CRUD, versioning, templates, cloning, bundle import/export, workflow forking.
    - AssistantChatService: Conversational chat execution and token streaming.
    """

    def __init__(
        self,
        lifecycle_service: AssistantLifecycleService | None = None,
        chat_service: AssistantChatService | None = None,
    ) -> None:
        self._lifecycle = lifecycle_service or assistant_lifecycle_service
        self._chat = chat_service or assistant_chat_service
        self._lifecycle.facade = self

    # --- Lifecycle Operations ---
    async def list_assistants(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        category: str | None = None,
        include_inactive: bool = False,
    ) -> list[AssistantResponse]:
        return await self._lifecycle.list_assistants(
            db, search=search, category=category, include_inactive=include_inactive
        )

    async def get_assistant(self, db: AsyncSession, reference: str) -> AssistantResponse:
        return await self._lifecycle.get_assistant(db, reference)

    async def _get_record(self, db: AsyncSession, reference: str) -> AssistantModel:
        return await self._lifecycle._get_record(db, reference)

    async def create_assistant(
        self, db: AsyncSession, request: AssistantCreateRequest
    ) -> AssistantResponse:
        return await self._lifecycle.create_assistant(db, request)

    async def update_assistant(
        self, db: AsyncSession, reference: str, request: AssistantUpdateRequest
    ) -> AssistantResponse:
        return await self._lifecycle.update_assistant(db, reference, request)

    async def delete_assistant(self, db: AsyncSession, reference: str) -> None:
        return await self._lifecycle.delete_assistant(db, reference)

    async def publish_assistant(
        self,
        db: AsyncSession,
        reference: str,
        *,
        version_name: str | None = None,
        change_log: str | None = None,
    ) -> AssistantPublishResponse:
        return await self._lifecycle.publish_assistant(
            db, reference, version_name=version_name, change_log=change_log
        )

    async def rollback_assistant(
        self, db: AsyncSession, reference: str, version_id: str
    ) -> AssistantRollbackResponse:
        return await self._lifecycle.rollback_version(db, reference, version_id)

    async def rollback_version(
        self, db: AsyncSession, reference: str, version_id: str
    ) -> AssistantRollbackResponse:
        return await self._lifecycle.rollback_version(db, reference, version_id)

    async def list_versions(
        self, db: AsyncSession, reference: str
    ) -> list[AssistantVersionResponse]:
        return await self._lifecycle.get_versions(db, reference)

    async def get_versions(
        self, db: AsyncSession, reference: str
    ) -> list[AssistantVersionResponse]:
        return await self._lifecycle.get_versions(db, reference)

    async def _create_version_snapshot(
        self,
        db: AsyncSession,
        record: AssistantModel,
        change_summary: str,
        created_by: str = "cán bộ quản trị",
    ) -> AssistantVersionModel:
        return await self._lifecycle._create_version_snapshot(
            db, record, change_summary, created_by=created_by
        )

    async def get_version(
        self, db: AsyncSession, reference: str, version_id: str
    ) -> AssistantVersionResponse:
        # get single version from list
        versions = await self._lifecycle.get_versions(db, reference)
        for v in versions:
            if v.id == version_id:
                return v
        from app.core.exceptions import EntityNotFoundError
        raise EntityNotFoundError(
            f"Phiên bản '{version_id}' không tồn tại cho trợ lý '{reference}'.",
            details={"version_id": version_id, "assistant_reference": reference},
        )

    def list_templates(self) -> list[AssistantTemplateResponse]:
        return self._lifecycle.list_templates()

    async def seed_defaults(self, db: AsyncSession) -> AssistantSeedResponse:
        return await self._lifecycle.seed_defaults(db)

    async def clone_assistant(
        self, db: AsyncSession, reference: str, request: AssistantCloneRequest
    ) -> AssistantResponse:
        return await self._lifecycle.clone_assistant(db, reference, request)

    async def fork_workflow(
        self, db: AsyncSession, reference: str
    ) -> AssistantForkWorkflowResponse:
        return await self._lifecycle.fork_workflow(db, reference)

    async def generate_assistant_spec(
        self, request: AssistantGenerateRequest, db: AsyncSession | None = None
    ) -> AssistantGenerateResponse:
        if db is not None:
            return await self._lifecycle.generate_spec(db, request)
        # Handle case where db is not passed: fallback spec
        from app.modules.assistants.services.assistant_lifecycle_service import _build_fallback_spec
        return _build_fallback_spec(request.idea, request.category_hint)

    async def generate_spec(
        self, db: AsyncSession, request: AssistantGenerateRequest
    ) -> AssistantGenerateResponse:
        return await self._lifecycle.generate_spec(db, request)

    async def get_readiness(
        self, db: AsyncSession, reference: str
    ) -> AssistantReadinessResponse:
        return await self._lifecycle.get_readiness(db, reference)

    async def export_bundle(self, db: AsyncSession, reference: str) -> AssistantBundle:
        return await self._lifecycle.export_bundle(db, reference)

    async def import_bundle(
        self,
        db: AsyncSession,
        bundle: AssistantBundle,
        *,
        conflict_strategy: str = "rename",
        override_code: str | None = None,
    ) -> AssistantResponse:
        return await self._lifecycle.import_bundle(
            db,
            bundle,
            conflict_strategy=conflict_strategy,
            override_code=override_code,
        )

    # --- Chat & Streaming Operations ---
    async def chat(
        self,
        db: AsyncSession,
        reference: str,
        request: AssistantChatRequest,
        *,
        correlation_id: str | None = None,
    ) -> AssistantChatResponse:
        return await self._chat.chat(db, reference, request, correlation_id=correlation_id)

    async def chat_stream(
        self,
        db: AsyncSession,
        reference: str,
        request: AssistantChatRequest,
        *,
        correlation_id: str | None = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._chat.chat_stream(
            db, reference, request, correlation_id=correlation_id
        ):
            yield chunk

    async def _get_recent_conversation_history(
        self, db: AsyncSession, conversation_id: str, limit: int = 6
    ) -> list[dict[str, str]]:
        return await self._chat._get_recent_conversation_history(db, conversation_id, limit=limit)


assistant_service = AssistantService()

__all__ = [
    "AssistantService",
    "_clean_text",
    "_to_response",
    "assistant_service",
    "workflow_service",
]
