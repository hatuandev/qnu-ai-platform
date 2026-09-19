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
    SystemModelDefaults,
    SystemModelDefaultsResponse,
    SystemModelDefaultsUpdate,
)

logger = logging.getLogger(__name__)


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
            "default_ocr_provider_id": "prov_mistral",
            "default_ocr_model": "mistral-ocr-latest",
        }

        if cfg_record and cfg_record.extra_config and "defaults" in cfg_record.extra_config:
            default_data.update(cfg_record.extra_config["defaults"])
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
                if "ocr" in m_lower or p_type in ("docling", "mistral"):
                    available_ocrs.append(
                        ModelOption(
                            provider_id=p.id,
                            provider_name=p.name,
                            provider_type=p.provider_type,
                            model_name=m,
                            category=category,
                            description=f"Bóc tách văn bản và bảng biểu qua {p.name}",
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

        extra["defaults"] = defaults
        cfg_record.extra_config = extra
        await db.commit()

        logger.info(
            "Updated system model defaults: embedding=%s (%s), reranker=%s (%s), ocr=%s (%s)",
            defaults.get("default_embedding_model"),
            defaults.get("default_embedding_provider_id"),
            defaults.get("default_reranker_model"),
            defaults.get("default_reranker_provider_id"),
            defaults.get("default_ocr_model"),
            defaults.get("default_ocr_provider_id"),
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
        else:
            raise AppException(
                status_code=400,
                title="Vai trò không hợp lệ",
                detail=f"Vai trò [{role}] không được hỗ trợ. Chỉ chấp nhận embedding, reranker, ocr.",
                code="INVALID_ROLE",
            )

        return await self.update_system_model_defaults(db, update_data)


model_catalog_service = ModelCatalogService()
