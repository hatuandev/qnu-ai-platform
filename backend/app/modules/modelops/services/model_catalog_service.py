"""ModelOps Model Catalog Service — System Model Defaults, Roles, and Discovery."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
    "local_vllm",
    "ollama",
    "sentence_transformers",
    "docling",
    "easyocr",
    "vllm",
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
        "provider_id": "prov_rtx5090_ollama",
        "provider_name": "On-Premise GPU RTX 5090 (Tailscale)",
        "model_name": "qwen3-vl:8b",
        "provider_type": "on_premise",
        "is_active": True,
        "description": "Ưu tiên 1 (On-Premise): Qwen 3 Vision 8B trên GPU RTX 5090 — Bóc tách tài liệu scan, bảng biểu & bảo mật nội bộ 100%",
    },
    {
        "provider_id": "prov_gemini",
        "provider_name": "Google Gemini",
        "model_name": "gemini-3.1-flash-lite",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 2 (Cloud Fallback): Google Gemini 2.5 Flash — Bóc tách bảng biểu Markdown GFM dự phòng (~2s)",
    },
    {
        "provider_id": "prov_mistral",
        "provider_name": "Mistral AI",
        "model_name": "mistral-ocr-latest",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 3 (Cloud Fallback): Mistral OCR Cloud Vision — Chuyên trị tài liệu scan tiếng Việt và con dấu",
    },
    {
        "provider_id": "prov_openrouter",
        "provider_name": "OpenRouter / Qwen Vision",
        "model_name": "qwen/qwen-2.5-vl-72b-instruct",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 4: Qwen 2.5 VL 72B Instruct — Bóc tách Markdown & Bounding Boxes dự phòng",
    },
]

DEFAULT_QNU_EMBEDDING_COMBO_CHAIN: list[dict[str, Any]] = [
    {
        "provider_id": "prov_cloudflare",
        "provider_name": "Cloudflare Workers AI",
        "model_name": "@cf/baai/bge-m3",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 1: Cloudflare BGE-M3 (1024D) — Máy chủ Edge toàn cầu, tốc độ cao không tốn quota API",
    },
    {
        "provider_id": "prov_gemini",
        "provider_name": "Google Gemini Cloud",
        "model_name": "text-embedding-004",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 2: Google text-embedding-004 — Chất lượng truy xuất ngữ nghĩa tiếng Việt chuẩn xác",
    },
]

DEFAULT_QNU_RERANKER_COMBO_CHAIN: list[dict[str, Any]] = [
    {
        "provider_id": "prov_cloudflare",
        "provider_name": "Cloudflare Workers AI",
        "model_name": "@cf/baai/bge-reranker-base",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 1: Cloudflare BGE-Reranker-Base — Cross-Encoder Edge GPU tái chấm điểm Top-K",
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

    async def get_system_model_defaults(self, db: AsyncSession) -> SystemModelDefaultsResponse:
        """Retrieve current system-wide default models for Embedding, Reranker, and OCR.

        If not yet stored in PostgreSQL, seeds default values matching Cloudflare Edge GPU & Mistral.
        Dynamically enumerates available options across all registered active providers.
        """
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == "system_model_defaults")
        res = await db.execute(stmt)
        cfg_record = res.scalar_one_or_none()

        default_data: dict[str, Any] = {
            "default_embedding_provider_id": "prov_rtx5090_ollama",
            "default_embedding_model": "bge-m3:latest",
            "default_embedding_mode": "combo",
            "default_embedding_combo_id": "combo_qnu_embedding_shield",
            "embedding_combo_chain": DEFAULT_QNU_EMBEDDING_COMBO_CHAIN,

            "default_reranker_provider_id": "prov_cloudflare",
            "default_reranker_model": "@cf/baai/bge-reranker-base",
            "default_reranker_mode": "combo",
            "default_reranker_combo_id": "combo_qnu_reranker_shield",
            "reranker_combo_chain": DEFAULT_QNU_RERANKER_COMBO_CHAIN,

            "default_ocr_provider_id": "prov_gemini",
            "default_ocr_model": "gemini-3.1-flash-lite",
            "default_ocr_mode": "combo",
            "default_ocr_combo_id": "combo_qnu_ocr_master",
            "ocr_combo_chain": DEFAULT_QNU_OCR_COMBO_CHAIN,

            "default_chat_provider_id": "prov_gemini",
            "default_chat_model": "gemini-3.1-flash-lite",
            "default_chat_mode": "single",
            "default_chat_combo_id": "combo_qnu_chat_shield",
            "chat_combo_chain": DEFAULT_QNU_CHAT_COMBO_CHAIN,

            "model_combos": DEFAULT_INITIAL_COMBOS,
            "vision_adapter": DEFAULT_VISION_ADAPTER,
        }

        if cfg_record and cfg_record.extra_config and "defaults" in cfg_record.extra_config:
            default_data.update(cfg_record.extra_config["defaults"])
            # Upgrade existing stored combos if task_type is missing
            combos_list = default_data.get("model_combos") or []
            existing_ids = {c.get("id") for c in combos_list}
            for c in combos_list:
                if not c.get("task_type"):
                    c["task_type"] = "ocr"
            # Add missing default combos for embedding/reranker/chat
            for initial_c in DEFAULT_INITIAL_COMBOS:
                if initial_c["id"] not in existing_ids:
                    combos_list.append(initial_c)
            default_data["model_combos"] = combos_list

            if not default_data.get("embedding_combo_chain"):
                default_data["embedding_combo_chain"] = DEFAULT_QNU_EMBEDDING_COMBO_CHAIN
            if not default_data.get("reranker_combo_chain"):
                default_data["reranker_combo_chain"] = DEFAULT_QNU_RERANKER_COMBO_CHAIN
            if not default_data.get("ocr_combo_chain"):
                default_data["ocr_combo_chain"] = DEFAULT_QNU_OCR_COMBO_CHAIN
            if not default_data.get("chat_combo_chain"):
                default_data["chat_combo_chain"] = DEFAULT_QNU_CHAT_COMBO_CHAIN
            if not default_data.get("default_ocr_mode"):
                default_data["default_ocr_mode"] = "combo"
            if not default_data.get("default_embedding_mode"):
                default_data["default_embedding_mode"] = "combo"
            if not default_data.get("default_reranker_mode"):
                default_data["default_reranker_mode"] = "combo"
            if not default_data.get("vision_adapter"):
                default_data["vision_adapter"] = DEFAULT_VISION_ADAPTER
        else:
            if not cfg_record:
                cfg_record = ModelProviderConfig(
                    id="system_model_defaults",
                    name="Cấu Hình Mặc Định Hệ Thống",
                    provider_type="system_routing",
                    model_name=default_data["default_embedding_model"],
                    is_active=True,
                    priority=0,
                    extra_config={"defaults": default_data},
                )
                db.add(cfg_record)
                await db.commit()

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

            for m in models_list:
                m_lower = m.lower()
                if (
                    "bge" in m_lower or "embed" in m_lower
                ) and "rerank" not in m_lower:
                    available_embeddings.append(
                        ModelOption(
                            provider_id=p.id,
                            provider_name=p.name,
                            provider_type=p.provider_type,
                            model_name=m,
                            category=category,
                            description=f"Nhúng vector 1024 chiều qua {p.name}",
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
                p_specs = p_extra.get("model_specs") or {}
                m_spec = p_specs.get(m) or {}

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
            provider_hint = update_data.default_embedding_provider_id.lower()
            settings.EMBEDDING_PROVIDER = (
                "cloudflare" if "cloudflare" in provider_hint else "gemini"
            )

        if update_data.default_embedding_model is not None:
            defaults["default_embedding_model"] = update_data.default_embedding_model
            settings.EMBEDDING_MODEL = update_data.default_embedding_model

        if update_data.default_reranker_provider_id is not None:
            defaults["default_reranker_provider_id"] = update_data.default_reranker_provider_id
            settings.RERANKER_PROVIDER = "cloudflare"

        if update_data.default_reranker_model is not None:
            defaults["default_reranker_model"] = update_data.default_reranker_model
            settings.RERANKER_MODEL = update_data.default_reranker_model

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
