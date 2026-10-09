"""ModelOps Model Catalog Service — System Model Defaults, Roles, and Discovery."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.schemas import (
    ModelOption,
    OCRComboItem,
    SystemModelDefaults,
    SystemModelDefaultsResponse,
    SystemModelDefaultsUpdate,
)

logger = logging.getLogger(__name__)

REMOVED_LOCAL_PROVIDER_TYPES = {
    "local",
    "sentence_transformers",
    "docling",
    "easyocr",
}
REMOVED_LOCAL_PROVIDER_IDS = {
    "prov_local",
    "prov_ollama",
    "prov_sentence_transformers",
    "prov_docling",
    "prov_easyocr",
}


def _without_local_models(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Remove retired in-process and self-hosted model entries from a routing chain."""
    return [
        item
        for item in (items or [])
        if str(item.get("provider_type", "")).lower() not in REMOVED_LOCAL_PROVIDER_TYPES
        and str(item.get("provider_id", "")) not in REMOVED_LOCAL_PROVIDER_IDS
    ]


DEFAULT_QNU_OCR_COMBO_CHAIN: list[dict[str, Any]] = [
    {
        "provider_id": "prov_gemini",
        "provider_name": "Google Gemini",
        "model_name": "gemini-3.1-flash-lite",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 1 (Cloud Primary): Google Gemini 2.5 Flash — Bóc tách bảng biểu Markdown GFM (~1.5s)",
    },
    {
        "provider_id": "prov_mistral",
        "provider_name": "Mistral AI",
        "model_name": "mistral-ocr-latest",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 2 (Cloud Fallback): Mistral OCR Cloud Vision — Chuyên trị tài liệu scan tiếng Việt và con dấu",
    },
    {
        "provider_id": "prov_openrouter",
        "provider_name": "OpenRouter / Qwen Vision",
        "model_name": "qwen/qwen-2.5-vl-72b-instruct",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 3: Qwen 2.5 VL 72B Instruct — Bóc tách Markdown & Bounding Boxes dự phòng",
    },
]

DEFAULT_QNU_EMBEDDING_COMBO_CHAIN: list[dict[str, Any]] = [
    {
        "provider_id": "prov_rtx5090_vllm",
        "provider_name": "On-Premise GPU RTX 5090 (vLLM)",
        "model_name": "bge-m3",
        "provider_type": "on_premise",
        "is_active": True,
        "description": "Ưu tiên 1 (On-Premise vLLM): BGE-M3 (1,024 dims) pooling/embeddings chạy trực tiếp trên GPU RTX 5090",
    },
    {
        "provider_id": "prov_cloudflare",
        "provider_name": "Cloudflare Workers AI",
        "model_name": "@cf/baai/bge-m3",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 2: Cloudflare BGE-M3 (1024D) — Máy chủ Edge toàn cầu dự phòng",
    },
    {
        "provider_id": "prov_gemini",
        "provider_name": "Google Gemini Cloud",
        "model_name": "text-embedding-004",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 3: Google text-embedding-004 — Truy xuất ngữ nghĩa tiếng Việt chuẩn xác",
    },
]

DEFAULT_QNU_RERANKER_COMBO_CHAIN: list[dict[str, Any]] = [
    {
        "provider_id": "prov_rtx5090_vllm",
        "provider_name": "On-Premise GPU RTX 5090 (vLLM)",
        "model_name": "bge-reranker-v2-m3",
        "provider_type": "on_premise",
        "is_active": True,
        "description": "Ưu tiên 1 (On-Premise vLLM): BGE-Reranker-v2-M3 Cross-Encoder rerank/score trên GPU RTX 5090",
    },
    {
        "provider_id": "prov_cloudflare",
        "provider_name": "Cloudflare Workers AI",
        "model_name": "@cf/baai/bge-reranker-base",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 2: Cloudflare BGE-Reranker-Base — Cross-Encoder Edge GPU tái chấm điểm Top-K",
    },
]

DEFAULT_QNU_CHAT_COMBO_CHAIN: list[dict[str, Any]] = [
    {
        "provider_id": "prov_gemini",
        "provider_name": "Google Gemini",
        "model_name": "gemini-3.1-flash-lite",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 1: Gemini 2.5 Flash — Tốc độ phản hồi cực nhanh, suy luận thông minh",
    },
    {
        "provider_id": "prov_openai",
        "provider_name": "OpenAI",
        "model_name": "gpt-4o-mini",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 2: OpenAI GPT-4o-mini — Ổn định và chi phí tối ưu",
    },
]

DEFAULT_QNU_OCR_COMBO: dict[str, Any] = {
    "id": "combo_qnu_ocr_master",
    "name": "qnu-ocr-master",
    "task_type": "ocr",
    "strategy": "fallback",
    "models": DEFAULT_QNU_OCR_COMBO_CHAIN,
    "is_default": True,
    "description": "Combo OCR đa tầng mặc định ĐH Quy Nhơn (Tự động failover khi hết Quota 429)",
}

DEFAULT_QNU_EMBEDDING_COMBO: dict[str, Any] = {
    "id": "combo_qnu_embedding_shield",
    "name": "qnu-embedding-resilience",
    "task_type": "embedding",
    "strategy": "fallback",
    "models": DEFAULT_QNU_EMBEDDING_COMBO_CHAIN,
    "is_default": True,
    "description": "Chuỗi nhúng vector qua API (Cloudflare Edge ➔ Gemini)",
}

DEFAULT_QNU_RERANKER_COMBO: dict[str, Any] = {
    "id": "combo_qnu_reranker_shield",
    "name": "qnu-reranker-resilience",
    "task_type": "reranker",
    "strategy": "fallback",
    "models": DEFAULT_QNU_RERANKER_COMBO_CHAIN,
    "is_default": True,
    "description": "Tái xếp hạng RAG qua Cloudflare Workers AI",
}

DEFAULT_QNU_CHAT_COMBO: dict[str, Any] = {
    "id": "combo_qnu_chat_shield",
    "name": "qnu-chat-resilience",
    "task_type": "chat",
    "strategy": "fallback",
    "models": DEFAULT_QNU_CHAT_COMBO_CHAIN,
    "is_default": False,
    "description": "Chuỗi LLM hội thoại qua API (Gemini ➔ GPT-4o-mini)",
}

DEFAULT_INITIAL_COMBOS: list[dict[str, Any]] = [
    DEFAULT_QNU_OCR_COMBO,
    DEFAULT_QNU_EMBEDDING_COMBO,
    DEFAULT_QNU_RERANKER_COMBO,
    DEFAULT_QNU_CHAT_COMBO,
]

DEFAULT_VISION_ADAPTER: dict[str, Any] = {
    "enabled": True,
    "strategy": "fallback",
    "models": DEFAULT_QNU_OCR_COMBO_CHAIN,
}


class ModelCatalogService:
    """Manages system-wide default models (Embedding, Reranker, OCR) and dynamic model discovery."""

    def __init__(self, facade: Any = None) -> None:
        self.facade = facade

    async def resolve_embedding_dimension(
        self,
        db: AsyncSession,
        provider_id: str,
        model_name: str,
        *,
        metadata_dimension: int | None = None,
    ) -> int:
        """Resolve and validate one embedding vector space from the ModelOps database."""
        provider_result = await db.execute(
            select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        )
        provider = provider_result.scalar_one_or_none()
        if provider is None or provider.is_active is False:
            raise AppException(
                f"Embedding provider '{provider_id}' không tồn tại hoặc chưa hoạt động.",
                code="EMBEDDING_PROVIDER_UNAVAILABLE",
                status_code=409,
                details={"provider_id": provider_id, "model_name": model_name},
            )

        extra_config = provider.extra_config or {}
        model_specs = extra_config.get("model_specs") or {}
        legacy_dimensions = extra_config.get("model_dimensions") or {}
        configured_models = set(extra_config.get("models") or [])
        if provider.model_name:
            configured_models.add(provider.model_name)
        configured_models.update(model_specs)
        configured_models.update(legacy_dimensions)
        if configured_models and model_name not in configured_models:
            raise AppException(
                f"Mô hình embedding '{model_name}' không thuộc provider '{provider_id}'.",
                code="EMBEDDING_MODEL_NOT_AVAILABLE",
                status_code=409,
                details={"provider_id": provider_id, "model_name": model_name},
            )

        model_spec = model_specs.get(model_name) or {}
        raw_dimension = model_spec.get("dimension") or model_spec.get("dims")
        if raw_dimension is None:
            raw_dimension = legacy_dimensions.get(model_name)
        if raw_dimension is None:
            raw_dimension = extra_config.get("embedding_dimension")

        try:
            dimension = int(raw_dimension)
        except (TypeError, ValueError):
            dimension = 0
        if dimension <= 0:
            raise AppException(
                f"Mô hình embedding '{model_name}' thiếu cấu hình số chiều trong ModelOps.",
                code="EMBEDDING_DIMENSION_NOT_CONFIGURED",
                status_code=400,
                details={"provider_id": provider_id, "model_name": model_name},
            )

        if metadata_dimension is not None and metadata_dimension != dimension:
            raise AppException(
                "Kích thước vector đã lưu không còn khớp cấu hình ModelOps; cần tạo thế hệ chỉ mục mới.",
                code="EMBEDDING_DIMENSION_MISMATCH",
                status_code=409,
                details={
                    "provider_id": provider_id,
                    "model_name": model_name,
                    "metadata_dimension": metadata_dimension,
                    "modelops_dimension": dimension,
                },
            )

        return dimension

    async def get_system_model_defaults(self, db: AsyncSession) -> SystemModelDefaultsResponse:
        """Retrieve current system-wide default models for Embedding, Reranker, and OCR.

        Fails fast with MODEL_DEFAULT_NOT_CONFIGURED if defaults are not yet stored in PostgreSQL.
        Dynamically enumerates available options across all registered active providers.
        """
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == "system_model_defaults")
        res = await db.execute(stmt)
        cfg_record = res.scalar_one_or_none()

        if not cfg_record or not cfg_record.extra_config or "defaults" not in cfg_record.extra_config:
            raise AppException(
                "Cấu hình mặc định mô hình hệ thống chưa được khởi tạo trong CSDL.",
                code="MODEL_DEFAULT_NOT_CONFIGURED",
                status_code=400,
            )

        default_data = dict(cfg_record.extra_config["defaults"])
        if not default_data.get("default_embedding_model") or not default_data.get("default_embedding_provider_id"):
            raise AppException(
                "Thiếu cấu hình default embedding model hoặc provider trong CSDL.",
                code="MODEL_DEFAULT_NOT_CONFIGURED",
                status_code=400,
            )

        for chain_key in (
            "embedding_combo_chain",
            "reranker_combo_chain",
            "ocr_combo_chain",
            "chat_combo_chain",
        ):
            default_data[chain_key] = _without_local_models(default_data.get(chain_key))
        for combo in default_data.get("model_combos") or []:
            combo["models"] = _without_local_models(combo.get("models"))
        vision_adapter = default_data.get("vision_adapter") or {}
        vision_adapter["models"] = _without_local_models(vision_adapter.get("models"))
        default_data["vision_adapter"] = vision_adapter

        # Enumerate available options from active providers
        providers_stmt = select(ModelProviderConfig).where(
            ModelProviderConfig.is_active.is_(True),
            ModelProviderConfig.id != "system_model_defaults",
        )
        p_res = await db.execute(providers_stmt)
        active_providers = p_res.scalars().all()

        available_embeddings: list[ModelOption] = []
        available_rerankers: list[ModelOption] = []
        available_ocrs: list[ModelOption] = []

        for p in active_providers:
            p_extra = p.extra_config or {}
            models_list: list[str] = list(p_extra.get("models") or [])
            if p.model_name and p.model_name not in models_list:
                models_list.append(p.model_name)

            p_type = (p.provider_type or "").lower()
            category = "custom" if p_type == "custom" else "cloud"

            p_specs = p_extra.get("model_specs") or {}

            for m in models_list:
                m_lower = m.lower()
                m_spec = p_specs.get(m) or {}
                m_dim_raw = m_spec.get("dimension") or m_spec.get("dims")
                m_dim = int(m_dim_raw) if m_dim_raw is not None else None

                if (
                    "bge" in m_lower or "embed" in m_lower
                ) and "rerank" not in m_lower:
                    desc = (
                        f"Nhúng vector {m_dim} chiều qua {p.name}"
                        if m_dim
                        else f"Nhúng vector qua {p.name}"
                    )
                    available_embeddings.append(
                        ModelOption(
                            provider_id=p.id,
                            provider_name=p.name,
                            provider_type=p.provider_type,
                            model_name=m,
                            category=category,
                            description=desc,
                            dimension=m_dim,
                        )
                    )
                if "rerank" in m_lower:
                    available_rerankers.append(
                        ModelOption(
                            provider_id=p.id,
                            provider_name=p.name,
                            provider_type=p.provider_type,
                            model_name=m,
                            category=category,
                            description=f"Xếp hạng lại tương quan ngữ nghĩa qua {p.name}",
                        )
                    )

                is_ocr_candidate = False
                if "can_ocr" in m_spec:
                    is_ocr_candidate = bool(m_spec.get("can_ocr"))
                else:
                    is_ocr_candidate = (
                        "ocr" in m_lower
                        or p_type == "mistral"
                        or (
                            p_type in ("gemini", "google")
                            and any(kw in m_lower for kw in ("flash", "vision", "pro", "image"))
                            and not m_lower.startswith("gemma")
                        )
                    )

                if is_ocr_candidate:
                    desc = (
                        m_spec.get("description")
                        or f"Bóc tách văn bản, bảng biểu và nhận diện OCR qua {p.name}"
                    )
                    available_ocrs.append(
                        ModelOption(
                            provider_id=p.id,
                            provider_name=p.name,
                            provider_type=p.provider_type,
                            model_name=m,
                            category=category,
                            description=desc,
                        )
                    )

        return SystemModelDefaultsResponse(
            defaults=SystemModelDefaults(**default_data),
            available_embeddings=available_embeddings,
            available_rerankers=available_rerankers,
            available_ocrs=available_ocrs,
        )

    async def update_system_model_defaults(
        self, db: AsyncSession, update_data: SystemModelDefaultsUpdate
    ) -> SystemModelDefaultsResponse:
        """Update system-wide default models, commit to DB, and synchronize runtime settings."""
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == "system_model_defaults")
        res = await db.execute(stmt)
        cfg_record = res.scalar_one_or_none()

        if not cfg_record:
            cfg_record = ModelProviderConfig(
                id="system_model_defaults",
                name="Cấu Hình Mặc Định Hệ Thống",
                provider_type="system_routing",
                is_active=True,
                priority=0,
                extra_config={"defaults": {}},
            )
            db.add(cfg_record)

        extra = dict(cfg_record.extra_config or {})
        defaults = dict(extra.get("defaults") or {})

        if update_data.default_embedding_provider_id is not None:
            defaults["default_embedding_provider_id"] = update_data.default_embedding_provider_id

        if update_data.default_embedding_model is not None:
            defaults["default_embedding_model"] = update_data.default_embedding_model

        if update_data.default_reranker_provider_id is not None:
            defaults["default_reranker_provider_id"] = update_data.default_reranker_provider_id

        if update_data.default_reranker_model is not None:
            defaults["default_reranker_model"] = update_data.default_reranker_model

        # Embedding Mode & Chain
        if update_data.default_embedding_mode is not None:
            defaults["default_embedding_mode"] = update_data.default_embedding_mode
        if update_data.default_embedding_combo_id is not None:
            defaults["default_embedding_combo_id"] = update_data.default_embedding_combo_id
        if update_data.embedding_combo_chain is not None:
            defaults["embedding_combo_chain"] = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in update_data.embedding_combo_chain
            ]

        # Reranker Mode & Chain
        if update_data.default_reranker_mode is not None:
            defaults["default_reranker_mode"] = update_data.default_reranker_mode
        if update_data.default_reranker_combo_id is not None:
            defaults["default_reranker_combo_id"] = update_data.default_reranker_combo_id
        if update_data.reranker_combo_chain is not None:
            defaults["reranker_combo_chain"] = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in update_data.reranker_combo_chain
            ]

        # OCR Mode & Chain
        if update_data.default_ocr_provider_id is not None:
            defaults["default_ocr_provider_id"] = update_data.default_ocr_provider_id
        if update_data.default_ocr_model is not None:
            defaults["default_ocr_model"] = update_data.default_ocr_model
        if update_data.default_ocr_mode is not None:
            defaults["default_ocr_mode"] = update_data.default_ocr_mode
        if update_data.default_ocr_combo_id is not None:
            defaults["default_ocr_combo_id"] = update_data.default_ocr_combo_id
        if update_data.ocr_combo_chain is not None:
            defaults["ocr_combo_chain"] = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in update_data.ocr_combo_chain
            ]

        # Chat Mode & Chain
        if update_data.default_chat_provider_id is not None:
            defaults["default_chat_provider_id"] = update_data.default_chat_provider_id
        if update_data.default_chat_model is not None:
            defaults["default_chat_model"] = update_data.default_chat_model
        if update_data.default_chat_mode is not None:
            defaults["default_chat_mode"] = update_data.default_chat_mode
        if update_data.default_chat_combo_id is not None:
            defaults["default_chat_combo_id"] = update_data.default_chat_combo_id
        if update_data.chat_combo_chain is not None:
            defaults["chat_combo_chain"] = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in update_data.chat_combo_chain
            ]

        # Model Combos Hub update
        if update_data.model_combos is not None:
            defaults["model_combos"] = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in update_data.model_combos
            ]
            # Synchronize default chains per task_type when combo is marked is_default
            for combo in defaults["model_combos"]:
                if combo.get("is_default") and combo.get("models"):
                    task_t = combo.get("task_type") or "ocr"
                    first_model = combo["models"][0]
                    p_id = first_model.get("provider_id")
                    m_name = first_model.get("model_name")
                    if task_t == "embedding":
                        defaults["embedding_combo_chain"] = combo["models"]
                        defaults["default_embedding_combo_id"] = combo.get("id")
                        if p_id:
                            defaults["default_embedding_provider_id"] = p_id
                        if m_name:
                            defaults["default_embedding_model"] = m_name
                    elif task_t == "reranker":
                        defaults["reranker_combo_chain"] = combo["models"]
                        defaults["default_reranker_combo_id"] = combo.get("id")
                        if p_id:
                            defaults["default_reranker_provider_id"] = p_id
                        if m_name:
                            defaults["default_reranker_model"] = m_name
                    elif task_t == "ocr":
                        defaults["ocr_combo_chain"] = combo["models"]
                        defaults["default_ocr_combo_id"] = combo.get("id")
                        if p_id:
                            defaults["default_ocr_provider_id"] = p_id
                        if m_name:
                            defaults["default_ocr_model"] = m_name
                    elif task_t == "chat":
                        defaults["chat_combo_chain"] = combo["models"]
                        defaults["default_chat_combo_id"] = combo.get("id")
                        if p_id:
                            defaults["default_chat_provider_id"] = p_id
                        if m_name:
                            defaults["default_chat_model"] = m_name

        if update_data.vision_adapter is not None:
            defaults["vision_adapter"] = (
                update_data.vision_adapter.model_dump()
                if hasattr(update_data.vision_adapter, "model_dump")
                else dict(update_data.vision_adapter)
            )

        extra["defaults"] = defaults
        cfg_record.extra_config = extra
        await db.commit()

        logger.info(
            "Updated system model defaults: embedding=%s (%s), reranker=%s (%s), ocr=%s (%s), ocr_mode=%s, combo_steps=%d",
            defaults.get("default_embedding_model"),
            defaults.get("default_embedding_provider_id"),
            defaults.get("default_reranker_model"),
            defaults.get("default_reranker_provider_id"),
            defaults.get("default_ocr_model"),
            defaults.get("default_ocr_provider_id"),
            defaults.get("default_ocr_mode"),
            len(defaults.get("ocr_combo_chain") or []),
        )

        return await self.get_system_model_defaults(db)

    async def set_provider_model_as_default(
        self, db: AsyncSession, provider_id: str, role: str, model_name: str
    ) -> SystemModelDefaultsResponse:
        """Set a specific provider's model as system default for embedding, reranker, or ocr."""
        update_data = SystemModelDefaultsUpdate()
        role_lower = role.lower().strip()
        if role_lower == "embedding":
            update_data.default_embedding_provider_id = provider_id
            update_data.default_embedding_model = model_name
        elif role_lower == "reranker":
            update_data.default_reranker_provider_id = provider_id
            update_data.default_reranker_model = model_name
        elif role_lower == "ocr":
            update_data.default_ocr_provider_id = provider_id
            update_data.default_ocr_model = model_name
        elif role_lower in ("fallback_ocr", "ocr_fallback"):
            # Add or update to top of fallback chain
            cur = await self.get_system_model_defaults(db)
            chain = list(cur.defaults.ocr_combo_chain)
            # Prepend or update
            chain.insert(
                1,
                OCRComboItem(
                    provider_id=provider_id,
                    provider_name=provider_id,
                    model_name=model_name,
                    provider_type="cloud",
                    is_active=True,
                    description=f"Dự phòng: {model_name}",
                ),
            )
            update_data.ocr_combo_chain = chain
        elif role_lower in ("ocr_combo", "combo"):
            update_data.default_ocr_mode = "combo"
        else:
            raise AppException(
                status_code=400,
                title="Vai trò không hợp lệ",
                detail=f"Vai trò [{role}] không được hỗ trợ. Chấp nhận embedding, reranker, ocr, fallback_ocr, ocr_combo.",
                code="INVALID_ROLE",
            )

        return await self.update_system_model_defaults(db, update_data)


model_catalog_service = ModelCatalogService()
