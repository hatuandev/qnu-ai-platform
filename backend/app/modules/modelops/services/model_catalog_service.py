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


DEFAULT_QNU_OCR_COMBO_CHAIN: list[dict[str, Any]] = [
    {
        "provider_id": "prov_ace0d9fe",
        "provider_name": "Google Gemini",
        "model_name": "gemini-2.5-flash",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 1: Google Gemini 2.5 Flash — Bóc tách bảng biểu Markdown GFM siêu tốc (~2s)",
    },
    {
        "provider_id": "prov_ace0d9fe",
        "provider_name": "Google Gemini",
        "model_name": "gemini-2.5-flash-lite",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 2: Google Gemini 2.5 Flash-Lite — Phản hồi nhanh, tối ưu quota dự phòng",
    },
    {
        "provider_id": "prov_mistral",
        "provider_name": "Mistral AI",
        "model_name": "mistral-ocr-latest",
        "provider_type": "cloud",
        "is_active": True,
        "description": "Ưu tiên 3: Mistral OCR Cloud Vision — Chuyên trị tài liệu scan tiếng Việt và con dấu",
    },
    {
        "provider_id": "prov_docling",
        "provider_name": "Docling Local",
        "model_name": "docling",
        "provider_type": "local",
        "is_active": True,
        "description": "Ưu tiên 4: IBM Docling TableFormer — Bóc tách cấu trúc bảng biểu offline nội bộ",
    },
    {
        "provider_id": "prov_easyocr",
        "provider_name": "EasyOCR Local",
        "model_name": "easyocr",
        "provider_type": "local",
        "is_active": True,
        "description": "Ưu tiên 5: EasyOCR Local Engine — Nhận diện hình ảnh và con dấu offline",
    },
]

DEFAULT_QNU_COMBO: dict[str, Any] = {
    "id": "combo_qnu_ocr_master",
    "name": "qnu-ocr-master",
    "strategy": "fallback",
    "models": DEFAULT_QNU_OCR_COMBO_CHAIN,
    "is_default": True,
    "description": "Combo OCR đa tầng mặc định ĐH Quy Nhơn (Tự động failover khi hết Quota 429)",
}

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

        default_data = {
            "default_embedding_provider_id": "prov_cloudflare",
            "default_embedding_model": "@cf/baai/bge-m3",
            "default_reranker_provider_id": "prov_cloudflare",
            "default_reranker_model": "@cf/baai/bge-reranker-base",
            "default_ocr_provider_id": "prov_ace0d9fe",
            "default_ocr_model": "gemini-2.5-flash",
            "default_ocr_mode": "combo",
            "ocr_combo_chain": DEFAULT_QNU_OCR_COMBO_CHAIN,
            "model_combos": [DEFAULT_QNU_COMBO],
            "vision_adapter": DEFAULT_VISION_ADAPTER,
        }

        if cfg_record and cfg_record.extra_config and "defaults" in cfg_record.extra_config:
            default_data.update(cfg_record.extra_config["defaults"])
            if not default_data.get("ocr_combo_chain"):
                default_data["ocr_combo_chain"] = DEFAULT_QNU_OCR_COMBO_CHAIN
            if not default_data.get("default_ocr_mode"):
                default_data["default_ocr_mode"] = "combo"
            if not default_data.get("model_combos"):
                default_data["model_combos"] = [DEFAULT_QNU_COMBO]
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
            category = "cloud"
            if p_type in ("sentence_transformers", "docling", "ollama", "local_vllm", "local") or "local" in p.id:
                category = "local"
            elif p_type == "custom":
                category = "custom"

            for m in models_list:
                m_lower = m.lower()
                if (
                    "bge" in m_lower or "embed" in m_lower or p_type in ("sentence_transformers",)
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
                        or p_type in ("docling", "mistral")
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

        # Add local fallback RRF option if not present
        if not any(r.model_name == "rrf_fallback" for r in available_rerankers):
            available_rerankers.append(
                ModelOption(
                    provider_id="prov_sentence_transformers",
                    provider_name="Local Rank Fusion (RRF)",
                    provider_type="local",
                    model_name="rrf_fallback",
                    category="local",
                    description="Xếp hạng hợp nhất RRF k=60 cục bộ (không phụ thuộc mạng ngoài)",
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
            if "cloudflare" in update_data.default_embedding_provider_id.lower():
                settings.EMBEDDING_PROVIDER = "cloudflare"
            else:
                settings.EMBEDDING_PROVIDER = "sentence_transformers"

        if update_data.default_embedding_model is not None:
            defaults["default_embedding_model"] = update_data.default_embedding_model
            settings.EMBEDDING_MODEL = update_data.default_embedding_model

        if update_data.default_reranker_provider_id is not None:
            defaults["default_reranker_provider_id"] = update_data.default_reranker_provider_id
            if "cloudflare" in update_data.default_reranker_provider_id.lower():
                settings.RERANKER_PROVIDER = "cloudflare"
            else:
                settings.RERANKER_PROVIDER = "local"

        if update_data.default_reranker_model is not None:
            defaults["default_reranker_model"] = update_data.default_reranker_model
            settings.RERANKER_MODEL = update_data.default_reranker_model

        if update_data.default_ocr_provider_id is not None:
            defaults["default_ocr_provider_id"] = update_data.default_ocr_provider_id

        if update_data.default_ocr_model is not None:
            defaults["default_ocr_model"] = update_data.default_ocr_model

        if update_data.default_ocr_mode is not None:
            defaults["default_ocr_mode"] = update_data.default_ocr_mode

        if update_data.ocr_combo_chain is not None:
            defaults["ocr_combo_chain"] = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in update_data.ocr_combo_chain
            ]

        if update_data.model_combos is not None:
            defaults["model_combos"] = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in update_data.model_combos
            ]
            default_combo = next((c for c in defaults["model_combos"] if c.get("is_default")), None)
            if default_combo and default_combo.get("models"):
                defaults["ocr_combo_chain"] = default_combo["models"]
                first_model = default_combo["models"][0]
                defaults["default_ocr_provider_id"] = first_model.get("provider_id", defaults.get("default_ocr_provider_id"))
                defaults["default_ocr_model"] = first_model.get("model_name", defaults.get("default_ocr_model"))
                defaults["default_ocr_mode"] = "combo"

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
