"""Assistant Service — Orchestrating Catalog Management & Conversational Chat Executions."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.modules.assistants.models import AssistantModel
from app.modules.assistants.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantResponse,
)
from app.modules.assistants.seeder import STANDARD_ASSISTANTS
from app.modules.workflows.schemas import WorkflowExecuteRequest
from app.modules.workflows.service import workflow_service

logger = logging.getLogger(__name__)


class AssistantService:
    """Service managing QNU's 5 Standard AI Assistants and their workflow invocations."""

    async def list_assistants(self, db: AsyncSession) -> list[AssistantResponse]:
        """List all assistants, automatically seeding default catalog if DB is empty."""
        try:
            stmt = select(AssistantModel).where(AssistantModel.is_active.is_(True))
            res = await db.execute(stmt)
            assistants = res.scalars().all()
            if assistants:
                return [
                    AssistantResponse(
                        id=a.id,
                        code=a.code,
                        name=a.name,
                        description=a.description,
                        avatar_url=a.avatar_url,
                        category=a.category,
                        workflow_id=a.workflow_id,
                        collection_id=a.collection_id,
                        is_active=a.is_active,
                        sample_questions=a.config.get("sample_questions", []),
                    )
                    for a in assistants
                ]
        except Exception as e:
            logger.debug("Database assistant query failed or empty, using standard catalog: %s", e)

        # Fallback to seeded in-memory catalog
        return [
            AssistantResponse(
                id=f"ast_{idx}",
                code=item["code"],
                name=item["name"],
                description=item["description"],
                avatar_url=item.get("avatar_url"),
                category=item["category"],
                workflow_id=item["workflow_id"],
                collection_id=item["collection_id"],
                is_active=True,
                sample_questions=item.get("sample_questions", []),
            )
            for idx, item in enumerate(STANDARD_ASSISTANTS, start=1)
        ]

    async def get_assistant(self, db: AsyncSession, code: str) -> AssistantResponse:
        """Get assistant details by unique code."""
        all_ast = await self.list_assistants(db)
        for a in all_ast:
            if a.code.lower() == code.lower():
                return a

        raise EntityNotFoundError(
            message=f"Trợ lý AI với mã '{code}' không tồn tại trên hệ thống QNU.",
            details={"code": code},
        )

    async def chat(
        self, db: AsyncSession, code: str, req: AssistantChatRequest
    ) -> AssistantChatResponse:
        """Execute chat interaction by running the assistant's underlying Workflow DAG."""
        assistant = await self.get_assistant(db, code)

        # Execute through Workflow DAG Engine
        wf_req = WorkflowExecuteRequest(
            workflow_id=assistant.workflow_id,
            inputs={"message": req.message},
            tenant_id=req.tenant_id,
            conversation_id=req.conversation_id,
        )

        wf_res = await workflow_service.execute(db, wf_req)

        answer_text = (
            wf_res.outputs.get("answer")
            or "Trợ lý QNU đã xử lý xong yêu cầu của bạn."
        )
        citations = wf_res.outputs.get("citations", [])
        status = wf_res.outputs.get("status") or wf_res.status

        # Pick suggested follow-up questions
        suggested = assistant.sample_questions[:3]

        return AssistantChatResponse(
            assistant_code=assistant.code,
            assistant_name=assistant.name,
            answer=answer_text,
            status=status,
            citations=citations,
            suggested_questions=suggested,
            latency_ms=wf_res.latency_ms,
            execution_id=wf_res.execution_id,
        )


assistant_service = AssistantService()
