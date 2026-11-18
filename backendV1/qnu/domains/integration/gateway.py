"""Single-turn OpenAI transport over the existing assistant-configured RAG pipeline."""

import time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.assistants.schemas import AssistantResponse
from qnu.domains.assistants.service import get_assistant
from qnu.domains.identity.actor import AuthActor
from qnu.domains.integration.access import (
    authenticate_api_key,
    check_access,
    get_redis_client,
    openai_error,
)
from qnu.domains.integration.models import AppApiKey, AppClient, AppRequestLog, utcnow
from qnu.domains.integration.schemas import (
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIChoice,
    OpenAIChoiceMessage,
    OpenAIModelItem,
    OpenAIModelsResponse,
    OpenAIUsage,
)
from qnu.domains.lifecycle.guards import visible
from qnu.domains.ocr.ids import new_id
from qnu.domains.rag.answer.schemas import AnswerRequest, AnswerResponse
from qnu.domains.rag.answer.service import answer as execute_rag_answer
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.reranker import Reranker
from qnu.ports.vector_store import VectorStore

__all__ = ["authenticate_api_key", "get_redis_client", "openai_error", "openai_gateway_service"]
logger = get_logger(__name__)


def validate_options(req: OpenAIChatCompletionRequest) -> str:
    if req.stream:
        raise openai_error(
            "Streaming chưa được hỗ trợ; đặt stream=false.", 400, "streaming_not_supported"
        )
    if req.tools is not None or req.functions is not None:
        raise openai_error("Tool/function calling chưa được hỗ trợ.", 400, "tools_not_supported")
    if any(value is not None for value in (req.temperature, req.top_p, req.max_tokens)):
        raise openai_error(
            "Sampling và max_tokens do cấu hình trợ lý quản lý.", 400, "unsupported_parameter"
        )
    if len(req.messages) != 1 or req.messages[0].role != "user":
        raise openai_error(
            "API hiện chỉ hỗ trợ một user message; chưa hỗ trợ history/system messages.",
            400,
            "unsupported_messages",
        )
    question = req.messages[0].content.strip()
    if not question:
        raise openai_error("Câu hỏi không được rỗng.", 400, "empty_user_message")
    return question


class OpenAIGatewayService:
    async def list_models(
        self, db: AsyncSession, key: AppApiKey, app: AppClient, actor: AuthActor
    ) -> OpenAIModelsResponse:
        key, _ = await check_access(db, key.id, app.id, actor, key.workspace_id)
        stmt = (
            select(Assistant)
            .where(
                Assistant.workspace_id == key.workspace_id,
                Assistant.is_active.is_(True),
                visible("assistant", Assistant.id),
                visible("collection", Assistant.collection_id),
            )
            .order_by(Assistant.name, Assistant.id)
        )
        if key.allowed_assistant_ids:
            stmt = stmt.where(Assistant.id.in_(key.allowed_assistant_ids))
        assistants = (await db.scalars(stmt)).all()
        return OpenAIModelsResponse(
            data=[
                OpenAIModelItem(
                    id=row.id,
                    created=int(row.created_at.timestamp()),
                    name=row.name,
                    description=row.description or "QNU AI Assistant",
                )
                for row in assistants
            ]
        )

    async def create_chat_completion(
        self,
        db: AsyncSession,
        blob: BlobStore,
        embedding: EmbeddingModel,
        vectors: VectorStore,
        chat: ChatModel,
        key: AppApiKey,
        app: AppClient,
        actor: AuthActor,
        req: OpenAIChatCompletionRequest,
        *,
        reranker: Reranker | None = None,
    ) -> OpenAIChatCompletionResponse:
        started = time.monotonic()
        question = validate_options(req)
        # /models exposes immutable assistant IDs. Names are not unique aliases.
        assistant = await get_assistant(db, actor, key.workspace_id, req.model)
        if not assistant.is_active:
            raise openai_error("Trợ lý đang tạm dừng.", 409, "assistant_inactive")
        snapshot = AssistantResponse.model_validate(assistant)
        collection_ids = list(
            dict.fromkeys(
                item
                for item in [snapshot.collection_id, *(snapshot.collection_ids or [])]
                if item
            )
        )
        if not collection_ids:
            raise openai_error(
                "Trợ lý chưa gắn kho tri thức nên chưa thể trả lời.",
                409,
                "assistant_no_collections",
            )
        key_id, app_id, workspace_id = key.id, app.id, key.workspace_id

        async def checkpoint() -> None:
            current_key, _ = await check_access(db, key_id, app_id, actor, workspace_id)
            if (
                current_key.allowed_assistant_ids
                and snapshot.id not in current_key.allowed_assistant_ids
            ):
                raise openai_error(
                    "Khóa không được phép gọi trợ lý này.", 403, "model_permission_denied"
                )
            current = await get_assistant(db, actor, workspace_id, snapshot.id)
            if not current.is_active or current.revision != snapshot.revision:
                raise Conflict(
                    "Trợ lý đã dừng hoặc đổi cấu hình; gửi yêu cầu mới.", code="assistant_changed"
                )

        async def log(
            status: int, error: str | None = None, result: AnswerResponse | None = None
        ) -> None:
            trace = result.trace if result else None
            db.add(
                AppRequestLog(
                    id=new_id("log"),
                    app_id=app_id,
                    key_id=key_id,
                    workspace_id=workspace_id,
                    assistant_id=snapshot.id,
                    endpoint="/integrations/openai/v1/chat/completions",
                    status_code=status,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    error_code=error,
                    prompt_tokens=trace.prompt_tokens if trace else None,
                    completion_tokens=trace.completion_tokens if trace else None,
                    total_tokens=trace.total_tokens if trace else None,
                )
            )
            await db.commit()

        try:
            await checkpoint()
            await db.commit()  # Release authorization row locks before network I/O.
            result = await execute_rag_answer(
                db=db,
                blob=blob,
                embedding=embedding,
                vectors=vectors,
                chat=chat,
                actor=actor,
                workspace_id=workspace_id,
                collection_id=collection_ids[0],
                req=AnswerRequest(
                    question=question,
                    top_k=snapshot.top_k,
                    provider_id=snapshot.chat_provider_id,
                    max_output_tokens=snapshot.max_output_tokens,
                    **snapshot.rag_policy.model_dump(mode="json"),
                ),
                persona=snapshot.persona,
                checkpoint=checkpoint,
                reranker=reranker,
                collection_ids=collection_ids,
            )
            await checkpoint()
            key.last_used_at = utcnow()
            await log(200, result=result)
        except AppException as exc:
            await db.rollback()
            await log(exc.status_code, exc.code)
            raise
        except HTTPException as exc:
            await db.rollback()
            await log(exc.status_code, "request_rejected")
            raise
        except Exception as exc:
            await db.rollback()
            await log(500, "inference_error")
            logger.error("integration_inference_failed", error_type=type(exc).__name__)
            raise openai_error(
                "Không thể hoàn tất yêu cầu; hãy thử lại sau.", 500, "inference_error"
            ) from exc

        return OpenAIChatCompletionResponse(
            id=f"chatcmpl-{new_id('cmp')}",
            created=int(time.time()),
            model=snapshot.id,
            choices=[OpenAIChoice(message=OpenAIChoiceMessage(content=result.answer or ""))],
            usage=OpenAIUsage(
                prompt_tokens=result.trace.prompt_tokens,
                completion_tokens=result.trace.completion_tokens,
                total_tokens=result.trace.total_tokens,
            ),
            qnu_extensions={
                "assistant_id": snapshot.id,
                "assistant_name": snapshot.name,
                "assistant_revision": snapshot.revision,
                "status": result.status,
                "reason": result.reason,
                "statements": [s.model_dump(mode="json") for s in result.statements],
                "sources": [s.model_dump(mode="json") for s in result.sources],
                "verification": result.trace.verification,
            },
        )


openai_gateway_service = OpenAIGatewayService()
