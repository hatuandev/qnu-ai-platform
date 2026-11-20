"""Safe, gated system reset and seed routine for staging/dev/UAT environments.

Wipes all application data (PostgreSQL runtime tables, Qdrant vectors, MinIO/S3 blobs,
and Redis cache) and seeds default demonstration records (Workspace 'shl', ModelOps
providers/keys/defaults, sample collection, and published assistant).
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant, AssistantCollection
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.dev_accounts import SHL_PILOT_PROFILES
from qnu.domains.knowledge.models import KBCollection
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.connections import service as conn_service
from qnu.domains.modelops.connections.schemas import ConnectionCreate, ConnectionModelCreate
from qnu.domains.modelops.keys.service import key_service
from qnu.domains.modelops.providers.service import provider_service
from qnu.domains.modelops.reasoning import ReasoningPolicy
from qnu.domains.modelops.resilience.service import effective_policy, save_policy
from qnu.domains.modelops.schemas import DefaultsUpdateRequest, KeyCreateRequest
from qnu.domains.operations.schemas import SystemResetRequest, SystemResetResponse
from qnu.domains.publications.models import AssistantPublication
from qnu.domains.workspaces.models import Workspace, WorkspaceMember
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict, Forbidden
from qnu.ports.blob_store import BlobStore
from qnu.ports.vector_store import VectorStore

logger = logging.getLogger(__name__)

TABLES_TO_TRUNCATE = [
    # Assistant publications & chat
    "assistant_publication_questions",
    "assistant_publication_stats",
    "assistant_publications",
    "chat_turns",
    "chat_conversations",
    "chat_assistant_collections",
    "chat_assistants",
    # Answer reviews
    "kb_answer_review_items",
    "kb_answer_reviews",
    # Indexing & table facts
    "kb_index_table_facts",
    "kb_index_chunks",
    "kb_index_inputs",
    "kb_index_sync",
    "kb_index_runs",
    # Publication & reviews
    "kb_publication_decisions",
    "kb_publication_previews",
    "kb_review_submission_actions",
    "kb_review_submission_previews",
    "kb_review_submissions",
    # Compilation
    "kb_compilation_edit_previews",
    "kb_compilation_review_segment_artifacts",
    "kb_compilation_review_segments",
    "kb_compilation_review_artifacts",
    "kb_compilation_review_jobs",
    "kb_compilation_reviews",
    "kb_compilation_segment_artifacts",
    "kb_compilation_segments",
    "kb_compilation_artifacts",
    "kb_compilation_inputs",
    "kb_compilation_outputs",
    "kb_compilation_runs",
    "kb_compiled_documents",
    "kb_compiled_versions",
    # Knowledge sources & preparation
    "kb_preparation_intents",
    "kb_upload_requests",
    "kb_source_revisions",
    "kb_sources",
    "kb_folders",
    "kb_collections",
    # OCR
    "ocr_run_artifacts",
    "ocr_run_pages",
    "ocr_spelling_dispositions",
    "ocr_spelling_reviews",
    "ocr_spelling_runs",
    "ocr_text_versions",
    "ocr_processing_runs",
    # Ops & Lifecycle
    "ops_actions",
    "ops_evidence_backups",
    "ops_storage_cleanup_actions",
    "resource_lifecycle_actions",
    "resource_lifecycle_states",
    # Workspaces
    "workspace_events",
    "workspace_quotas",
    "workspace_members",
    "workspaces",
]

MODELOPS_TABLES = [
    "provider_key_audits",
    "provider_keys",
    "model_defaults",
    "modelops_events",
    "model_usage_records",
    "providers",
]

QNU_GATEWAY = "http://100.105.13.53:8000"
ROUTER_URL = "https://qnu-9router.duckdns.org/v1"
QWEN_MODEL = "qwen3.8-27b-q4"


async def truncate_database_tables(db: AsyncSession, reset_modelops: bool) -> list[str]:
    """Truncate runtime tables with CASCADE, leaving migration tracking intact."""
    tables = list(TABLES_TO_TRUNCATE)
    if reset_modelops:
        tables.extend(MODELOPS_TABLES)

    # Wrap in quotes for safe SQL identifier execution
    quoted = ", ".join(f'"{name}"' for name in tables)
    await db.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE;"))
    await db.commit()
    return tables


async def delete_qdrant_collections(vectors: VectorStore | None) -> list[str]:
    """Delete all vector collections matching qnu_v1_idx_*."""
    deleted: list[str] = []
    if vectors is None or not hasattr(vectors, "_request"):
        return deleted
    try:
        res = await vectors._request("GET", "/collections")
        if res.status_code == 200:
            cols = res.json().get("result", {}).get("collections", [])
            for col in cols:
                name = str(col.get("name", ""))
                if name.startswith("qnu_v1_idx_"):
                    try:
                        await vectors.delete_collection(name)
                        deleted.append(name)
                    except Exception as exc:
                        logger.warning("delete_qdrant_collection_failed", extra={"col": name, "error": str(exc)})
    except Exception as exc:
        logger.warning("list_qdrant_collections_failed", extra={"error": str(exc)})
    return deleted


async def purge_storage_objects(blob: BlobStore | None) -> int:
    """Purge uploaded and derived objects from blob storage."""
    if blob is None:
        return 0
    purged = 0
    try:
        objects = await blob.list_objects(prefix="")
        for obj in objects:
            try:
                await blob.purge(obj.key)
                purged += 1
            except Exception as exc:
                logger.warning("purge_blob_object_failed", extra={"key": obj.key, "error": str(exc)})
    except Exception as exc:
        logger.warning("list_blob_objects_failed", extra={"error": str(exc)})
    return purged


async def clear_redis_cache_and_queues() -> int:
    """Clear Redis keys in application namespace and task queue."""
    cleared = 0
    try:
        from qnu.platform.cache import get_redis

        redis = get_redis()
        settings = get_settings()
        pattern = f"{settings.CACHE_NAMESPACE}*"
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis.unlink(*keys)
                cleared += len(keys)
            if cursor == 0:
                break
        await redis.delete(settings.QUEUE_NAME)
    except Exception as exc:
        logger.warning("clear_redis_cache_failed", extra={"error": str(exc)})
    return cleared


async def seed_shl_workspace(db: AsyncSession, actor: AuthActor) -> Workspace:
    """Create the SHL pilot workspace and default members."""
    workspace_id = uuid.uuid4().hex
    workspace = Workspace(
        id=workspace_id,
        code="shl",
        name="Trung tâm Số & Học liệu",
        description="Không gian thử nghiệm nghiệp vụ của Trung tâm Số & Học liệu.",
        status="active",
        created_by=actor.actor_id,
    )
    db.add(workspace)

    # Ensure calling actor is admin
    db.add(
        WorkspaceMember(
            id=uuid.uuid4().hex,
            workspace_id=workspace_id,
            actor_ref=actor.actor_id,
            display_name=actor.username or "Admin",
            role="admin",
            status="active",
        )
    )

    # Add standard pilot profiles
    for name, (actor_id, display_name, role) in SHL_PILOT_PROFILES.items():
        if actor_id != actor.actor_id:
            db.add(
                WorkspaceMember(
                    id=uuid.uuid4().hex,
                    workspace_id=workspace_id,
                    actor_ref=actor_id,
                    display_name=display_name,
                    role=role,
                    status="active",
                )
            )

    await db.flush()
    return workspace


async def seed_modelops_defaults(db: AsyncSession, actor: AuthActor) -> dict[str, str]:
    """Seed ModelOps connections, models, reasoning policy, and default assignments."""
    qnu_key = os.getenv("E2E_QNU_API_KEY", "").strip() or "qnu-local-api-key"
    router_key = os.getenv("E2E_9ROUTER_API_KEY", "").strip()
    defaults: dict[str, str] = {}

    # 1. QNU AI Server (chat, embedding, rerank)
    conn_qnu = await conn_service.save_connection(
        db,
        actor,
        ConnectionCreate(
            name="QNU AI Server",
            base_url=f"{QNU_GATEWAY}/v1",
            family="qnu",
            api_type="openai_compatible",
            timeout_seconds=300,
        ),
    )
    await key_service.add_key(
        db, conn_qnu, KeyCreateRequest(name="QNU API Key", secret=qnu_key), actor
    )

    m_chat = await conn_service.add_model(
        db,
        actor,
        conn_qnu.id,
        ConnectionModelCreate(model_name=QWEN_MODEL, capabilities=["chat"]),
    )
    m_embed = await conn_service.add_model(
        db,
        actor,
        conn_qnu.id,
        ConnectionModelCreate(
            model_name="bge-m3",
            capabilities=["embedding"],
            embedding_dimension=1024,
        ),
    )
    m_rerank = await conn_service.add_model(
        db,
        actor,
        conn_qnu.id,
        ConnectionModelCreate(
            model_name="bge-reranker-v2-m3",
            capabilities=["rerank"],
        ),
    )

    # Qwen reasoning configuration
    qwen_policy = ReasoningPolicy(
        mode="chat_template_kwarg",
        parameter="enable_thinking",
        off_value=False,
        low_value=True,
        level="off",
        verified=True,
    )
    await provider_service.set_reasoning(db, m_chat.id, qwen_policy, actor)
    policy = effective_policy(m_chat)
    if not policy.wait_for_completion:
        await save_policy(
            db, actor, m_chat.id, policy.model_copy(update={"wait_for_completion": True})
        )

    defaults["chat_provider_id"] = m_chat.id
    defaults["embedding_provider_id"] = m_embed.id
    defaults["rerank_provider_id"] = m_rerank.id

    # 2. QNU MinerU GPU (OCR)
    conn_mineru = await conn_service.save_connection(
        db,
        actor,
        ConnectionCreate(
            name="QNU MinerU GPU",
            base_url=f"{QNU_GATEWAY}/mineru",
            family="qnu",
            api_type="mineru",
            timeout_seconds=300,
        ),
    )
    await key_service.add_key(
        db, conn_mineru, KeyCreateRequest(name="MinerU Key", secret=qnu_key), actor
    )
    m_ocr = await conn_service.add_model(
        db,
        actor,
        conn_mineru.id,
        ConnectionModelCreate(model_name="mineru", capabilities=["ocr"]),
    )
    defaults["ocr_provider_id"] = m_ocr.id

    # 3. 9router Luna (fallback)
    if router_key and len(router_key) >= 8:
        try:
            conn_router = await conn_service.save_connection(
                db,
                actor,
                ConnectionCreate(
                    name="9router Luna",
                    base_url=ROUTER_URL,
                    family="qnu",
                    api_type="openai_compatible",
                    timeout_seconds=300,
                ),
            )
            await key_service.add_key(
                db, conn_router, KeyCreateRequest(name="9router Key", secret=router_key), actor
            )
            await conn_service.add_model(
                db,
                actor,
                conn_router.id,
                ConnectionModelCreate(model_name="cx/gpt-6-luna", capabilities=["chat"]),
            )
        except Exception as exc:
            logger.warning("seed_9router_optional_skipped", extra={"error": str(exc)})

    # Persist defaults
    await catalog_service.update_defaults(db, DefaultsUpdateRequest(**defaults), actor)
    return defaults


async def seed_pilot_assistant_and_collection(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    chat_provider_id: str | None,
) -> tuple[str, str]:
    """Seed sample Collection and published Assistant for Tuyển sinh 2026."""
    collection_id = uuid.uuid4().hex
    collection = KBCollection(
        id=collection_id,
        workspace_id=workspace_id,
        name="Kho tri thức Tuyển sinh 2026",
        description="Tập hợp tài liệu thông tin tuyển sinh Đại học Quy Nhơn năm 2026.",
        created_by=actor.actor_id,
    )
    db.add(collection)
    await db.flush()

    assistant_id = uuid.uuid4().hex
    assistant = Assistant(
        id=assistant_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        name="Trợ lý Tuyển sinh QNU 2026",
        description="Trợ lý AI tư vấn và giải đáp thông tin tuyển sinh Đại học Quy Nhơn năm 2026.",
        persona=(
            "Bạn là Trợ lý AI tư vấn tuyển sinh chính thức của Trường Đại học Quy Nhơn (QNU). "
            "Hãy trả lời thí sinh và phụ huynh một cách ân cần, chính xác, rõ ràng và dựa trên thông tin chính thống của trường."
        ),
        chat_provider_id=chat_provider_id,
        top_k=5,
        history_turns=3,
        max_output_tokens=2048,
        revision=1,
        is_active=True,
        created_by=actor.actor_id,
    )
    db.add(assistant)
    db.add(
        AssistantCollection(
            assistant_id=assistant_id,
            collection_id=collection_id,
            workspace_id=workspace_id,
            position=0,
        )
    )
    await db.flush()

    # Public chatbot release
    pub = AssistantPublication(
        id=uuid.uuid4().hex,
        assistant_id=assistant_id,
        workspace_id=workspace_id,
        slug="tuyen-sinh-qnu-2026",
        display_name="Trợ lý Tuyển sinh QNU 2026",
        welcome_message=(
            "Xin chào! Tôi là Trợ lý Tuyển sinh của Trường Đại học Quy Nhơn. "
            "Tôi có thể hỗ trợ giải đáp các thắc mắc về tuyển sinh, ngành đào tạo, phương thức xét tuyển và học phí năm 2026."
        ),
        starter_prompts=[
            "Trường Đại học Quy Nhơn có những ngành đào tạo nào năm 2026?",
            "Học phí và các chế độ học bổng cho tân sinh viên ra sao?",
            "Phương thức xét tuyển năm 2026 của trường có điểm gì mới?",
        ],
        max_turns_per_session=15,
        enabled=True,
        revision=1,
        updated_by=actor.actor_id,
    )
    db.add(pub)
    await db.flush()
    return collection_id, assistant_id


async def perform_system_reset_and_seed(
    db: AsyncSession,
    actor: AuthActor,
    blob: BlobStore | None,
    vectors: VectorStore | None,
    request: SystemResetRequest,
) -> SystemResetResponse:
    """Execute complete system wipe and re-seed with safety guards."""
    settings = get_settings()

    # 1. Environment Guard
    is_non_prod = settings.ENVIRONMENT.lower() in ("development", "test", "staging")
    if not is_non_prod and not settings.ALLOW_SYSTEM_RESET:
        raise Forbidden(
            "Hệ thống đang ở môi trường production và chưa bật cờ ALLOW_SYSTEM_RESET.",
            code="reset_forbidden_in_production",
        )

    # 2. Confirmation Phrase Guard
    if request.confirm_phrase != "RESET_AND_SEED":
        raise Conflict(
            "Cụm từ xác nhận không chính xác. Vui lòng nhập 'RESET_AND_SEED'.",
            code="invalid_confirm_phrase",
        )

    # 3. Truncate PostgreSQL Tables
    truncated_tables = await truncate_database_tables(db, reset_modelops=request.seed_modelops)

    # 4. Delete Qdrant Vector Collections
    deleted_vectors = await delete_qdrant_collections(vectors)

    # 5. Purge Storage Objects
    purged_objects = await purge_storage_objects(blob)

    # 6. Clear Redis Cache & Queues
    cleared_redis = await clear_redis_cache_and_queues()

    stats: dict[str, Any] = {
        "tables_truncated": len(truncated_tables),
        "qdrant_collections_deleted": len(deleted_vectors),
        "blob_objects_purged": purged_objects,
        "redis_keys_cleared": cleared_redis,
    }

    workspace_id: str | None = None
    assistant_id: str | None = None

    # 7. Seed Workspace
    if request.seed_workspace:
        ws = await seed_shl_workspace(db, actor)
        workspace_id = ws.id
        stats["workspace_code"] = ws.code
        stats["workspace_name"] = ws.name

    # 8. Seed ModelOps
    defaults: dict[str, str] = {}
    if request.seed_modelops:
        defaults = await seed_modelops_defaults(db, actor)
        stats["modelops_defaults"] = defaults

    # 9. Seed Assistant & Collection
    if request.seed_assistant and workspace_id:
        chat_provider = defaults.get("chat_provider_id")
        col_id, asst_id = await seed_pilot_assistant_and_collection(
            db, actor, workspace_id, chat_provider
        )
        assistant_id = asst_id
        stats["collection_id"] = col_id
        stats["assistant_id"] = asst_id
        stats["publication_slug"] = "tuyen-sinh-qnu-2026"

    await db.commit()

    return SystemResetResponse(
        success=True,
        message="Hệ thống đã được đặt lại và nạp dữ liệu mẫu thành công.",
        workspace_id=workspace_id,
        assistant_id=assistant_id,
        stats=stats,
    )
