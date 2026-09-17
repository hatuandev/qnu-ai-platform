"""Application service for persisted QNU AI Assistant administration."""

from __future__ import annotations

import logging
import unicodedata
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, EntityAlreadyExistsError, EntityNotFoundError
from app.modules.assistants.models import AssistantModel
from app.modules.assistants.runtime import build_runtime_profile, prepare_user_message
from app.modules.assistants.schemas import (
    AssistantBundle,
    AssistantBundleWorkflow,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantCreateRequest,
    AssistantLifecycleConfig,
    AssistantResponse,
    AssistantSeedResponse,
    AssistantTemplateResponse,
    AssistantUpdateRequest,
)
from app.modules.assistants.seeder import STANDARD_ASSISTANTS, seed_standard_assistants
from app.modules.workflows.models import WorkflowDefinition
from app.modules.workflows.schemas import WorkflowExecuteRequest
from app.modules.workflows.service import workflow_service

logger = logging.getLogger(__name__)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return unicodedata.normalize("NFC", value.strip())


def _to_response(record: AssistantModel) -> AssistantResponse:
    config = AssistantLifecycleConfig.model_validate(record.config or {})
    return AssistantResponse(
        id=record.id,
        code=record.code,
        name=record.name,
        description=record.description,
        avatar_url=record.avatar_url,
        category=record.category,
        system_prompt=record.system_prompt,
        workflow_id=record.workflow_id,
        collection_id=record.collection_id,
        is_active=record.is_active,
        tenant_id=record.tenant_id,
        sample_questions=config.sample_questions,
        config=config,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class AssistantService:
    """Manage assistants, their lifecycle policy, bundles and workflow invocations."""

    async def list_assistants(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        category: str | None = None,
        include_inactive: bool = False,
    ) -> list[AssistantResponse]:
        query = select(AssistantModel).order_by(AssistantModel.name)
        if not include_inactive:
            query = query.where(AssistantModel.is_active.is_(True))
        if category:
            query = query.where(AssistantModel.category == category)
        if search and search.strip():
            pattern = f"%{_clean_text(search).casefold()}%"
            query = query.where(
                func.lower(AssistantModel.code).like(pattern)
                | func.lower(AssistantModel.name).like(pattern)
                | func.lower(AssistantModel.description).like(pattern)
            )
        records = list((await db.execute(query)).scalars().all())
        return [_to_response(record) for record in records]

    async def get_assistant(self, db: AsyncSession, reference: str) -> AssistantResponse:
        return _to_response(await self._get_record(db, reference))

    async def create_assistant(
        self, db: AsyncSession, request: AssistantCreateRequest
    ) -> AssistantResponse:
        code = _clean_text(request.code)
        if not code:
            raise AppException("Mã trợ lý không được để trống.", code="assistant_invalid")
        existing = await db.execute(
            select(AssistantModel.id).where(func.lower(AssistantModel.code) == code.casefold())
        )
        if existing.scalar_one_or_none():
            raise EntityAlreadyExistsError(
                f"Mã trợ lý '{code}' đã tồn tại.",
                details={"assistant_code": code},
            )

        record = AssistantModel(
            code=code,
            name=_clean_text(request.name) or request.name,
            description=_clean_text(request.description) or request.description,
            avatar_url=_clean_text(request.avatar_url),
            category=_clean_text(request.category) or request.category,
            system_prompt=_clean_text(request.system_prompt) or request.system_prompt,
            workflow_id=_clean_text(request.workflow_id) or request.workflow_id,
            collection_id=_clean_text(request.collection_id) or request.collection_id,
            is_active=request.is_active,
            tenant_id=_clean_text(request.tenant_id) or request.tenant_id,
            config=request.config.model_dump(mode="json"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info("Created assistant code=%s workflow=%s", record.code, record.workflow_id)
        return _to_response(record)

    async def update_assistant(
        self,
        db: AsyncSession,
        reference: str,
        request: AssistantUpdateRequest,
    ) -> AssistantResponse:
        record = await self._get_record(db, reference)
        updates = request.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            if field_name == "config" and value is not None:
                value = request.config.model_dump(mode="json") if request.config else None
            elif isinstance(value, str):
                value = _clean_text(value)
            setattr(record, field_name, value)
        await db.commit()
        await db.refresh(record)
        logger.info("Updated assistant code=%s", record.code)
        return _to_response(record)

    async def deactivate_assistant(self, db: AsyncSession, reference: str) -> AssistantResponse:
        record = await self._get_record(db, reference)
        record.is_active = False
        await db.commit()
        await db.refresh(record)
        logger.info("Deactivated assistant code=%s", record.code)
        return _to_response(record)

    async def seed_defaults(self, db: AsyncSession) -> AssistantSeedResponse:
        return await seed_standard_assistants(db)

    def list_templates(self) -> list[AssistantTemplateResponse]:
        return [
            AssistantTemplateResponse(
                code=str(item["code"]),
                name=str(item["name"]),
                description=str(item["description"]),
                category=str(item["category"]),
                workflow_id=str(item["workflow_id"]),
                collection_id=str(item["collection_id"]),
                system_prompt=str(item["system_prompt"]),
                config=AssistantLifecycleConfig.model_validate(item["config"]),
            )
            for item in STANDARD_ASSISTANTS
        ]

    async def export_bundle(self, db: AsyncSession, reference: str) -> AssistantBundle:
        record = await self._get_record(db, reference)
        workflow_result = await db.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.id == record.workflow_id)
        )
        workflow_record = workflow_result.scalar_one_or_none()
        workflow = None
        if workflow_record:
            workflow = AssistantBundleWorkflow(
                id=workflow_record.id,
                name=workflow_record.name,
                display_name=workflow_record.display_name,
                description=workflow_record.description,
                module_code=workflow_record.module_code,
                version=workflow_record.version,
                dag_spec=workflow_record.dag_spec,
            )
        return AssistantBundle(
            exported_at=datetime.now(UTC),
            assistant=AssistantCreateRequest(
                code=record.code,
                name=record.name,
                description=record.description,
                avatar_url=record.avatar_url,
                category=record.category,
                system_prompt=record.system_prompt,
                workflow_id=record.workflow_id,
                collection_id=record.collection_id,
                is_active=record.is_active,
                tenant_id=record.tenant_id,
                config=AssistantLifecycleConfig.model_validate(record.config or {}),
            ),
            workflow=workflow,
        )

    async def import_bundle(self, db: AsyncSession, bundle: AssistantBundle) -> AssistantResponse:
        workflow = bundle.workflow
        if workflow:
            existing_workflow = await db.execute(
                select(WorkflowDefinition.id).where(WorkflowDefinition.id == workflow.id)
            )
            if not existing_workflow.scalar_one_or_none():
                db.add(
                    WorkflowDefinition(
                        id=workflow.id,
                        name=workflow.name,
                        display_name=workflow.display_name,
                        description=workflow.description,
                        module_code=workflow.module_code,
                        version=workflow.version,
                        is_active=True,
                        dag_spec=workflow.dag_spec,
                    )
                )
        return await self.create_assistant(db, bundle.assistant)

    async def chat(
        self,
        db: AsyncSession,
        reference: str,
        request: AssistantChatRequest,
        *,
        correlation_id: str | None = None,
    ) -> AssistantChatResponse:
        assistant = await self.get_assistant(db, reference)
        if not assistant.is_active:
            raise AppException(
                f"Trợ lý '{assistant.code}' đang bị vô hiệu hóa.",
                code="assistant_inactive",
                status_code=409,
                details={"assistant_code": assistant.code},
            )
        runtime_profile = build_runtime_profile(assistant)
        sanitized_message = prepare_user_message(request.message, runtime_profile)
        workflow_request = WorkflowExecuteRequest(
            workflow_id=assistant.workflow_id,
            inputs={"message": sanitized_message},
            tenant_id=request.tenant_id,
            conversation_id=request.conversation_id,
        )
        workflow_response = await workflow_service.execute(
            db,
            workflow_request,
            assistant_profile=runtime_profile,
            correlation_id=correlation_id,
        )
        answer = workflow_response.outputs.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            answer = assistant.config.guardrails.no_answer_message
        citations = workflow_response.outputs.get("citations", [])
        return AssistantChatResponse(
            assistant_code=assistant.code,
            assistant_name=assistant.name,
            answer=answer,
            status=str(workflow_response.outputs.get("status") or workflow_response.status),
            citations=citations if isinstance(citations, list) else [],
            suggested_questions=assistant.sample_questions[:3],
            latency_ms=workflow_response.latency_ms,
            execution_id=workflow_response.execution_id,
        )

    async def _get_record(self, db: AsyncSession, reference: str) -> AssistantModel:
        normalized_reference = _clean_text(reference) or reference
        result = await db.execute(
            select(AssistantModel).where(
                or_(
                    AssistantModel.id == normalized_reference,
                    func.lower(AssistantModel.code) == normalized_reference.casefold(),
                )
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise EntityNotFoundError(
                f"Trợ lý AI '{reference}' không tồn tại.",
                details={"assistant_reference": reference},
            )
        return record


assistant_service = AssistantService()
