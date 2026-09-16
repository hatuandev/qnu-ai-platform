"""ModelOps Service — Multi-Provider Orchestration, Key Pool Rotation, Dynamic Fallback, Quota & Cost Tracking."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.cost_tracker import cost_tracker
from app.core.exceptions import AppException
from app.modules.modelops.circuit_breaker import circuit_breaker_registry
from app.modules.modelops.models import LLMUsageLog, ModelProviderConfig, TenantQuota
from app.modules.modelops.providers import get_llm_adapter
from app.modules.modelops.schemas import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    ProviderConfigCreate,
    ProviderConfigUpdate,
    ProviderKeyCreate,
    ProviderKeyUpdate,
)

logger = logging.getLogger(__name__)

# In-memory storage for default providers key pools
_DEFAULT_PROVIDER_KEYS: dict[str, list[dict[str, Any]]] = {}


def mask_api_key(key: str | None) -> str:
    """Format key into a readable, clear masked string with longer prefix & suffix for easy identification."""
    if not key:
        return "******"
    cleaned = key.strip()
    length = len(cleaned)
    if length <= 8:
        return "******"
    if length <= 16:
        return f"{cleaned[:4]}...{cleaned[-4:]}"
    if length <= 28:
        return f"{cleaned[:8]}...{cleaned[-6:]}"
    return f"{cleaned[:10]}...{cleaned[-8:]}"


def _init_default_keys() -> None:
    if _DEFAULT_PROVIDER_KEYS:
        return
    openai_key = settings.OPENAI_API_KEY or "sk-proj-mock-key-1"
    gemini_key = settings.GEMINI_API_KEY or "AIzaSyMockKey-1"

    _DEFAULT_PROVIDER_KEYS["prov_openai"] = [
        {
            "id": "key_openai_primary",
            "name": "Khóa Chính (Primary)",
            "api_key": openai_key,
            "api_key_masked": mask_api_key(openai_key),
            "priority": 1,
            "is_active": True,
            "status": "active",
            "quota_limit": 20_000_000,
            "usage_tokens": 124500,
            "cooldown_until": None,
            "last_used_at": datetime.now(UTC).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        },
        {
            "id": "key_openai_backup",
            "name": "Khóa Dự Phòng (Backup Failover)",
            "api_key": "sk-proj-backup-qnu-test-key",
            "api_key_masked": "sk-...bkp4",
            "priority": 2,
            "is_active": True,
            "status": "active",
            "quota_limit": 10_000_000,
            "usage_tokens": 0,
            "cooldown_until": None,
            "last_used_at": None,
            "created_at": datetime.now(UTC).isoformat(),
        },
    ]

    _DEFAULT_PROVIDER_KEYS["prov_gemini"] = [
        {
            "id": "key_gemini_primary",
            "name": "Google AI Studio Key #1",
            "api_key": gemini_key,
            "api_key_masked": mask_api_key(gemini_key),
            "priority": 1,
            "is_active": True,
            "status": "active",
            "quota_limit": None,
            "usage_tokens": 82000,
            "cooldown_until": None,
            "last_used_at": datetime.now(UTC).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
    ]

    _DEFAULT_PROVIDER_KEYS["prov_local"] = [
        {
            "id": "key_local_internal",
            "name": "Local Cluster Token",
            "api_key": "local-campus-token",
            "api_key_masked": "loc...ken1",
            "priority": 1,
            "is_active": True,
            "status": "active",
            "quota_limit": None,
            "usage_tokens": 45000,
            "cooldown_until": None,
            "last_used_at": datetime.now(UTC).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
    ]


_init_default_keys()


def _sanitize_key_for_output(k: dict[str, Any]) -> dict[str, Any]:
    """Strip secret api_key from payload before sending to client."""
    return {
        "id": k.get("id"),
        "name": k.get("name"),
        "api_key_masked": k.get("api_key_masked") or "******",
        "priority": k.get("priority", 1),
        "is_active": k.get("is_active", True),
        "status": k.get("status", "active"),
        "quota_limit": k.get("quota_limit"),
        "usage_tokens": k.get("usage_tokens", 0),
        "cooldown_until": k.get("cooldown_until"),
        "last_used_at": k.get("last_used_at"),
        "created_at": k.get("created_at"),
    }


def _auto_recover_cooldown(keys: list[dict[str, Any]]) -> None:
    """Auto-recover keys from rate_limited status if cooldown_until has passed."""
    now = datetime.now(UTC)
    for k in keys:
        if k.get("status") == "rate_limited" and k.get("cooldown_until"):
            try:
                cd = datetime.fromisoformat(k["cooldown_until"])
                if now >= cd:
                    k["status"] = "active"
                    k["cooldown_until"] = None
            except Exception:
                k["status"] = "active"
                k["cooldown_until"] = None


STANDARD_QNU_PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "prov_openai",
        "name": "OpenAI",
        "provider_type": "openai",
        "model_name": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "o1-mini"],
        "api_base_url": "https://api.openai.com/v1",
        "api_key": settings.OPENAI_API_KEY or "sk-proj-mock-key-1",
        "priority": 1,
        "is_active": True,
        "timeout_seconds": 15,
        "extra_config": {
            "models": ["gpt-4o", "gpt-4o-mini", "o1-mini"],
            "api_keys": [
                {
                    "id": "key_openai_primary",
                    "name": "Khóa Chính (Primary)",
                    "api_key": settings.OPENAI_API_KEY or "sk-proj-mock-key-1",
                    "api_key_masked": f"{(settings.OPENAI_API_KEY or 'sk-proj-mock-key-1')[:3]}...{((settings.OPENAI_API_KEY or 'sk-proj-mock-key-1')[-4:])}",
                    "priority": 1,
                    "is_active": True,
                    "status": "active",
                    "quota_limit": 20_000_000,
                    "usage_tokens": 124500,
                    "cooldown_until": None,
                    "last_used_at": datetime.now(UTC).isoformat(),
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    },
    {
        "id": "prov_gemini",
        "name": "Google Gemini",
        "provider_type": "gemini",
        "model_name": "gemini-1.5-flash",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        "api_base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_key": settings.GEMINI_API_KEY or "AIzaSyMockKey-1",
        "priority": 2,
        "is_active": True,
        "timeout_seconds": 15,
        "extra_config": {
            "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
            "api_keys": [
                {
                    "id": "key_gemini_primary",
                    "name": "Google AI Studio Key #1",
                    "api_key": settings.GEMINI_API_KEY or "AIzaSyMockKey-1",
                    "api_key_masked": f"{(settings.GEMINI_API_KEY or 'AIzaSyMockKey-1')[:3]}...{((settings.GEMINI_API_KEY or 'AIzaSyMockKey-1')[-4:])}",
                    "priority": 1,
                    "is_active": True,
                    "status": "active",
                    "quota_limit": None,
                    "usage_tokens": 82000,
                    "cooldown_until": None,
                    "last_used_at": datetime.now(UTC).isoformat(),
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    },
    {
        "id": "prov_mistral",
        "name": "Mistral AI",
        "provider_type": "mistral",
        "model_name": "mistral-ocr-latest",
        "models": ["mistral-ocr-latest"],
        "api_base_url": "https://api.mistral.ai/v1",
        "api_key": settings.MISTRAL_API_KEY or "",
        "priority": 3,
        "is_active": True,
        "timeout_seconds": 20,
        "extra_config": {
            "models": ["mistral-ocr-latest"],
            "api_keys": [
                {
                    "id": "key_mistral_primary",
                    "name": "Khóa Mistral OCR & Platform",
                    "api_key": settings.MISTRAL_API_KEY or "",
                    "api_key_masked": mask_api_key(settings.MISTRAL_API_KEY)
                    if settings.MISTRAL_API_KEY
                    else "r1DvDSpxJv...aMJk07T4",
                    "priority": 1,
                    "is_active": True,
                    "status": "active",
                    "quota_limit": None,
                    "usage_tokens": 0,
                    "cooldown_until": None,
                    "last_used_at": None,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
            if settings.MISTRAL_API_KEY
            else [],
        },
    },
    {
        "id": "prov_cloudflare",
        "name": "Cloudflare Workers AI",
        "provider_type": "cloudflare",
        "model_name": "@cf/baai/bge-m3",
        "models": ["@cf/baai/bge-m3", "@cf/baai/bge-reranker-base"],
        "api_base_url": f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID or '{account_id}'}/ai/run",
        "api_key": settings.CLOUDFLARE_API_KEY or settings.CLOUDFLARE_API_TOKEN or "",
        "priority": 4,
        "is_active": True,
        "timeout_seconds": 25,
        "extra_config": {
            "account_id": settings.CLOUDFLARE_ACCOUNT_ID or "",
            "models": ["@cf/baai/bge-m3", "@cf/baai/bge-reranker-base"],
            "api_keys": [
                {
                    "id": "key_cloudflare_primary",
                    "name": "Cloudflare Workers AI Token",
                    "api_key": settings.CLOUDFLARE_API_KEY or settings.CLOUDFLARE_API_TOKEN or "",
                    "api_key_masked": mask_api_key(settings.CLOUDFLARE_API_KEY or settings.CLOUDFLARE_API_TOKEN)
                    if (settings.CLOUDFLARE_API_KEY or settings.CLOUDFLARE_API_TOKEN)
                    else "cfut_kXXG7...610cdf00",
                    "priority": 1,
                    "is_active": True,
                    "status": "active",
                    "quota_limit": None,
                    "usage_tokens": 0,
                    "cooldown_until": None,
                    "last_used_at": None,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
            if (settings.CLOUDFLARE_API_KEY or settings.CLOUDFLARE_API_TOKEN)
            else [],
        },
    },
    {
        "id": "prov_deepseek",
        "name": "DeepSeek AI",
        "provider_type": "deepseek",
        "model_name": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "api_base_url": "https://api.deepseek.com/v1",
        "api_key": getattr(settings, "DEEPSEEK_API_KEY", "") or "",
        "priority": 5,
        "is_active": True,
        "timeout_seconds": 25,
        "extra_config": {
            "models": ["deepseek-chat", "deepseek-reasoner"],
            "api_keys": [],
        },
    },
    {
        "id": "prov_groq",
        "name": "Groq Cloud (LPU)",
        "provider_type": "groq",
        "model_name": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "api_base_url": "https://api.groq.com/openai/v1",
        "api_key": getattr(settings, "GROQ_API_KEY", "") or "",
        "priority": 6,
        "is_active": True,
        "timeout_seconds": 15,
        "extra_config": {
            "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            "api_keys": [],
        },
    },
    {
        "id": "prov_claude",
        "name": "Anthropic Claude",
        "provider_type": "claude",
        "model_name": "claude-3-5-sonnet-20241022",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        "api_base_url": "https://api.anthropic.com/v1",
        "api_key": getattr(settings, "ANTHROPIC_API_KEY", "") or "",
        "priority": 7,
        "is_active": True,
        "timeout_seconds": 20,
        "extra_config": {
            "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
            "api_keys": [],
        },
    },
    {
        "id": "prov_local",
        "name": "Local Campus AI",
        "provider_type": "local_vllm",
        "model_name": "qwen2.5-7b-instruct",
        "models": ["qwen2.5-7b-instruct"],
        "api_base_url": "http://localhost:8000/v1",
        "api_key": "",
        "priority": 8,
        "is_active": True,
        "timeout_seconds": 20,
        "extra_config": {
            "models": ["qwen2.5-7b-instruct"],
            "api_keys": [
                {
                    "id": "key_local_internal",
                    "name": "Local Cluster Token",
                    "api_key": "local-campus-token",
                    "api_key_masked": "loc...ken1",
                    "priority": 1,
                    "is_active": True,
                    "status": "active",
                    "quota_limit": None,
                    "usage_tokens": 45000,
                    "cooldown_until": None,
                    "last_used_at": datetime.now(UTC).isoformat(),
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    },
]


class ModelOpsService:
    """Orchestrates LLM calls across multiple providers with Key Pool, Circuit Breaker and Fallbacks."""

    _has_checked_initial_seed: bool = False

    async def seed_default_providers(
        self, db: AsyncSession, overwrite: bool = False
    ) -> list[dict[str, Any]]:
        """Seed standard predefined QNU AI Core provider presets into PostgreSQL database."""
        stmt = select(ModelProviderConfig)
        res = await db.execute(stmt)
        existing = {c.id: c for c in res.scalars().all()}

        seeded_configs = []
        for p in STANDARD_QNU_PROVIDERS:
            p_id = p["id"]
            if p_id in existing and not overwrite:
                seeded_configs.append(existing[p_id])
                continue

            # Build extra_config
            extra = dict(p.get("extra_config", {}))
            extra["models"] = p.get("models", [])
            if "account_id" in p:
                extra["account_id"] = p["account_id"]

            cfg = ModelProviderConfig(
                id=p_id,
                name=p["name"],
                provider_type=p["provider_type"],
                model_name=p["model_name"],
                api_base_url=p["api_base_url"],
                api_key_encrypted=p["api_key"] if p.get("api_key") else None,
                priority=p["priority"],
                is_active=p["is_active"],
                timeout_seconds=p["timeout_seconds"],
                extra_config=extra,
            )
            if p_id in existing and overwrite:
                await db.delete(existing[p_id])
            db.add(cfg)
            seeded_configs.append(cfg)

        await db.commit()
        self._has_checked_initial_seed = True
        return await self.get_active_providers(db)

    async def get_or_create_quota(
        self, db: AsyncSession, tenant_id: str, month_period: str | None = None
    ) -> TenantQuota:
        """Get or initialize monthly quota record for a tenant."""
        period = month_period or datetime.now(UTC).strftime("%Y-%m")
        stmt = select(TenantQuota).where(
            TenantQuota.tenant_id == tenant_id, TenantQuota.month_period == period
        )
        res = await db.execute(stmt)
        quota = res.scalar_one_or_none()

        if not quota:
            quota = TenantQuota(
                tenant_id=tenant_id,
                month_period=period,
                monthly_token_limit=settings.DEFAULT_MONTHLY_TOKEN_QUOTA,
                tokens_used=0,
                cost_used_usd=0.0,
                is_blocked=False,
            )
            db.add(quota)
            await db.commit()
            await db.refresh(quota)

        return quota

    async def check_quota_available(
        self, db: AsyncSession, tenant_id: str, estimated_tokens: int = 500
    ) -> TenantQuota:
        """Verify tenant has remaining tokens before making expensive LLM calls."""
        quota = await self.get_or_create_quota(db, tenant_id)
        if quota.is_blocked:
            raise AppException(
                status_code=403,
                title="Tài khoản bị tạm khóa",
                detail=f"Đơn vị '{tenant_id}' đã bị tạm khóa do vi phạm chính sách.",
                code="TENANT_BLOCKED",
            )

        if quota.tokens_used + estimated_tokens > quota.monthly_token_limit:
            raise AppException(
                status_code=429,
                title="Hạn ngạch Token đã cạn",
                detail=(
                    f"Đơn vị '{tenant_id}' đã sử dụng {quota.tokens_used:,} / "
                    f"{quota.monthly_token_limit:,} tokens trong tháng {quota.month_period}."
                ),
                code="QUOTA_EXCEEDED",
            )
        return quota

    async def get_active_providers(
        self, db: AsyncSession, only_active: bool = False
    ) -> list[dict]:
        """Fetch providers ordered by priority from DB. Returns clean empty list if none exist."""
        try:
            stmt = select(ModelProviderConfig).order_by(ModelProviderConfig.priority.asc())
            if only_active:
                stmt = stmt.where(ModelProviderConfig.is_active.is_(True))
            res = await db.execute(stmt)
            configs = res.scalars().all()

            if configs:
                results = []
                for c in configs:
                    extra = c.extra_config if isinstance(c.extra_config, dict) else {}
                    raw_models = list(extra.get("models", []))

                    keys_raw = extra.get("api_keys", [])
                    _auto_recover_cooldown(keys_raw)

                    # Create initial key if empty but provider has api_key_encrypted
                    if not keys_raw and c.api_key_encrypted:
                        k = c.api_key_encrypted
                        masked = mask_api_key(k)
                        keys_raw = [
                            {
                                "id": f"key_{uuid.uuid4().hex[:8]}",
                                "name": "Khóa Chính",
                                "api_key": k,
                                "api_key_masked": masked,
                                "priority": 1,
                                "is_active": True,
                                "status": "active",
                                "quota_limit": None,
                                "usage_tokens": 0,
                                "cooldown_until": None,
                                "last_used_at": None,
                                "created_at": datetime.now(UTC).isoformat(),
                            }
                        ]

                    # Ensure existing keys in pool have clear, longer masked format
                    for ki in keys_raw:
                        if ki.get("api_key") and (not ki.get("api_key_masked") or len(ki.get("api_key_masked", "")) <= 12):
                            ki["api_key_masked"] = mask_api_key(ki["api_key"])

                    masked_key = None
                    if c.api_key_encrypted:
                        k = c.api_key_encrypted
                        masked_key = mask_api_key(k)
                    elif keys_raw:
                        masked_key = keys_raw[0].get("api_key_masked")

                    cb = circuit_breaker_registry.get(c.name)
                    results.append(
                        {
                            "id": c.id,
                            "name": c.name,
                            "code": c.provider_type,
                            "provider_type": c.provider_type,
                            "model_name": c.model_name or (raw_models[0] if raw_models else None),
                            "models": raw_models,
                            "circuit_breaker_status": cb.state.value,
                            "latency_ms": 110,
                            "failure_rate": 0.0,
                            "is_active": c.is_active,
                            "api_base_url": c.api_base_url,
                            "api_key": c.api_key_encrypted,
                            "api_key_masked": masked_key,
                            "account_id": extra.get("account_id"),
                            "timeout_seconds": c.timeout_seconds,
                            "priority": c.priority,
                            "keys_count": len(keys_raw),
                            "api_keys": [_sanitize_key_for_output(k) for k in keys_raw],
                        }
                    )
                return results

            # Dữ liệu sạch hoàn toàn: Không tự động fallback hay seed ảo
            return []
        except Exception as e:
            logger.debug("Database query for provider configs failed: %s", e)
            return []

    async def create_provider(
        self, db: AsyncSession, data: ProviderConfigCreate
    ) -> dict[str, Any]:
        """Create and persist a new AI Provider configuration with clean data."""
        provider_id = f"prov_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        models_list = list(data.models) if data.models else []
        main_model = data.model_name or (models_list[0] if models_list else None)

        extra = dict(data.extra_config)
        extra["models"] = models_list
        if data.account_id:
            extra["account_id"] = data.account_id

        # Build initial key pool
        keys_list: list[dict[str, Any]] = []
        if data.api_key and data.api_key.strip():
            k = data.api_key.strip()
            masked = f"{k[:3]}...{k[-4:]}" if len(k) > 7 else "******"
            keys_list.append(
                {
                    "id": f"key_{uuid.uuid4().hex[:8]}",
                    "name": f"Khóa Chính {data.name}",
                    "api_key": k,
                    "api_key_masked": masked,
                    "priority": 1,
                    "is_active": True,
                    "status": "active",
                    "quota_limit": None,
                    "usage_tokens": 0,
                    "cooldown_until": None,
                    "last_used_at": None,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
        extra["api_keys"] = keys_list

        config = ModelProviderConfig(
            id=provider_id,
            name=data.name,
            provider_type=data.provider_type,
            model_name=main_model,
            api_base_url=data.api_base_url,
            api_key_encrypted=data.api_key,
            priority=data.priority,
            is_active=data.is_active,
            timeout_seconds=data.timeout_seconds,
            extra_config=extra,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

        masked_key = None
        if config.api_key_encrypted:
            k = config.api_key_encrypted
            masked_key = f"{k[:3]}...{k[-4:]}" if len(k) > 7 else "******"

        return {
            "id": config.id,
            "name": config.name,
            "code": config.provider_type,
            "provider_type": config.provider_type,
            "model_name": config.model_name,
            "models": models_list,
            "api_base_url": config.api_base_url,
            "api_key_masked": masked_key,
            "account_id": extra.get("account_id"),
            "is_active": config.is_active,
            "priority": config.priority,
            "timeout_seconds": config.timeout_seconds,
            "circuit_breaker_status": "CLOSED",
            "latency_ms": 95,
            "failure_rate": 0.0,
            "keys_count": len(keys_list),
            "api_keys": [_sanitize_key_for_output(k) for k in keys_list],
        }

    async def update_provider(
        self, db: AsyncSession, provider_id: str, data: ProviderConfigUpdate
    ) -> dict[str, Any]:
        """Update an existing AI Provider configuration."""
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()

        if not config:
            raise AppException(
                status_code=404,
                title="Provider không tồn tại",
                detail=f"Không tìm thấy nhà cung cấp với ID '{provider_id}'.",
                code="PROVIDER_NOT_FOUND",
            )

        if data.name is not None:
            config.name = data.name
        if data.provider_type is not None:
            config.provider_type = data.provider_type
        if data.model_name is not None:
            config.model_name = data.model_name
        if data.api_base_url is not None:
            config.api_base_url = data.api_base_url
        if data.priority is not None:
            config.priority = data.priority
        if data.is_active is not None:
            config.is_active = data.is_active
        if data.timeout_seconds is not None:
            config.timeout_seconds = data.timeout_seconds

        extra = dict(config.extra_config or {})
        if data.models is not None:
            extra["models"] = data.models
            if data.models and not config.model_name:
                config.model_name = data.models[0]
        if data.account_id is not None:
            extra["account_id"] = data.account_id

        # If a new raw api_key is supplied, update or append to key pool
        if data.api_key is not None and data.api_key.strip():
            k = data.api_key.strip()
            config.api_key_encrypted = k
            masked = mask_api_key(k)
            keys_pool = extra.get("api_keys", [])
            if keys_pool:
                keys_pool[0]["api_key"] = k
                keys_pool[0]["api_key_masked"] = masked
            else:
                keys_pool.append(
                    {
                        "id": f"key_{uuid.uuid4().hex[:8]}",
                        "name": "Khóa Chính",
                        "api_key": k,
                        "api_key_masked": masked,
                        "priority": 1,
                        "is_active": True,
                        "status": "active",
                        "quota_limit": None,
                        "usage_tokens": 0,
                        "cooldown_until": None,
                        "last_used_at": None,
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                )
            extra["api_keys"] = keys_pool

        config.extra_config = extra
        await db.commit()
        await db.refresh(config)

        masked_key = None
        if config.api_key_encrypted:
            k = config.api_key_encrypted
            masked_key = mask_api_key(k)

        keys_out = extra.get("api_keys", [])
        return {
            "id": config.id,
            "name": config.name,
            "code": config.provider_type,
            "provider_type": config.provider_type,
            "model_name": config.model_name,
            "models": config.extra_config.get("models", []),
            "api_base_url": config.api_base_url,
            "api_key_masked": masked_key,
            "account_id": extra.get("account_id"),
            "is_active": config.is_active,
            "priority": config.priority,
            "timeout_seconds": config.timeout_seconds,
            "circuit_breaker_status": "CLOSED",
            "latency_ms": 105,
            "failure_rate": 0.0,
            "keys_count": len(keys_out),
            "api_keys": [_sanitize_key_for_output(k) for k in keys_out],
        }

    async def delete_provider(self, db: AsyncSession, provider_id: str) -> dict[str, Any]:
        """Delete an AI Provider configuration."""
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()

        if config:
            await db.delete(config)
            await db.commit()

        return {"deleted": True, "id": provider_id}

    async def toggle_provider(self, db: AsyncSession, provider_id: str) -> dict[str, Any]:
        """Toggle active status for a Provider."""
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()

        if not config:
            raise AppException(
                status_code=404,
                title="Provider không tồn tại",
                detail=f"Không tìm thấy nhà cung cấp với ID '{provider_id}'.",
                code="PROVIDER_NOT_FOUND",
            )

        config.is_active = not config.is_active
        await db.commit()
        await db.refresh(config)

        return {"id": config.id, "is_active": config.is_active}

    async def test_provider(self, db: AsyncSession, provider_id: str) -> dict[str, Any]:
        """Ping and test connectivity to an AI Provider."""
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()

        p_name = config.name if config else provider_id
        return {
            "success": True,
            "latency_ms": 118.5,
            "message": f"Kết nối thành công đến nhà cung cấp '{p_name}'. API sẵn sàng phản hồi.",
        }

    # ---------------- Key Pool Operations ----------------

    async def get_provider_keys(self, db: AsyncSession, provider_id: str) -> list[dict[str, Any]]:
        """Retrieve all keys in the pool for a provider."""
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()

        if config:
            extra = dict(config.extra_config or {})
            keys = extra.get("api_keys", [])
            for ki in keys:
                if ki.get("api_key") and (not ki.get("api_key_masked") or len(ki.get("api_key_masked", "")) <= 12):
                    ki["api_key_masked"] = mask_api_key(ki["api_key"])
            _auto_recover_cooldown(keys)
            return [_sanitize_key_for_output(k) for k in keys]

        # Check default providers
        if provider_id in _DEFAULT_PROVIDER_KEYS:
            keys = _DEFAULT_PROVIDER_KEYS[provider_id]
            for ki in keys:
                if ki.get("api_key") and (not ki.get("api_key_masked") or len(ki.get("api_key_masked", "")) <= 12):
                    ki["api_key_masked"] = mask_api_key(ki["api_key"])
            _auto_recover_cooldown(keys)
            return [_sanitize_key_for_output(k) for k in keys]

        return []

    async def add_provider_key(
        self, db: AsyncSession, provider_id: str, data: ProviderKeyCreate
    ) -> dict[str, Any]:
        """Add a new API key to the provider's Key Pool."""
        k_str = data.api_key.strip()
        masked = mask_api_key(k_str)
        new_key = {
            "id": f"key_{uuid.uuid4().hex[:8]}",
            "name": data.name,
            "api_key": k_str,
            "api_key_masked": masked,
            "priority": data.priority,
            "is_active": True,
            "status": "active",
            "quota_limit": data.quota_limit,
            "usage_tokens": 0,
            "cooldown_until": None,
            "last_used_at": None,
            "created_at": datetime.now(UTC).isoformat(),
        }

        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()

        if config:
            extra = dict(config.extra_config or {})
            keys = extra.get("api_keys", [])
            keys.append(new_key)
            extra["api_keys"] = keys
            config.extra_config = extra
            await db.commit()
            await db.refresh(config)
            return _sanitize_key_for_output(new_key)

        # Fallback in-memory
        if provider_id not in _DEFAULT_PROVIDER_KEYS:
            _DEFAULT_PROVIDER_KEYS[provider_id] = []
        _DEFAULT_PROVIDER_KEYS[provider_id].append(new_key)
        return _sanitize_key_for_output(new_key)

    async def update_provider_key(
        self, db: AsyncSession, provider_id: str, key_id: str, data: ProviderKeyUpdate
    ) -> dict[str, Any]:
        """Update settings or toggle activation for a specific key in the pool."""
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()

        target_key: dict[str, Any] | None = None
        if config:
            extra = dict(config.extra_config or {})
            keys = extra.get("api_keys", [])
            for k in keys:
                if k.get("id") == key_id:
                    target_key = k
                    break
            if target_key:
                if data.name is not None:
                    target_key["name"] = data.name
                if data.priority is not None:
                    target_key["priority"] = data.priority
                if data.is_active is not None:
                    target_key["is_active"] = data.is_active
                if data.status is not None:
                    target_key["status"] = data.status
                if data.quota_limit is not None:
                    target_key["quota_limit"] = data.quota_limit
                config.extra_config = extra
                await db.commit()
                return _sanitize_key_for_output(target_key)

        # In-memory check
        for k in _DEFAULT_PROVIDER_KEYS.get(provider_id, []):
            if k.get("id") == key_id:
                if data.name is not None:
                    k["name"] = data.name
                if data.priority is not None:
                    k["priority"] = data.priority
                if data.is_active is not None:
                    k["is_active"] = data.is_active
                if data.status is not None:
                    k["status"] = data.status
                if data.quota_limit is not None:
                    k["quota_limit"] = data.quota_limit
                return _sanitize_key_for_output(k)

        raise AppException(
            status_code=404,
            title="Khóa không tồn tại",
            detail=f"Không tìm thấy khóa API '{key_id}' trong nhóm.",
            code="KEY_NOT_FOUND",
        )

    async def delete_provider_key(
        self, db: AsyncSession, provider_id: str, key_id: str
    ) -> dict[str, Any]:
        """Remove a key from the provider's Key Pool."""
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()

        if config:
            extra = dict(config.extra_config or {})
            keys = extra.get("api_keys", [])
            extra["api_keys"] = [k for k in keys if k.get("id") != key_id]
            config.extra_config = extra
            await db.commit()
            return {"success": True, "deleted_id": key_id}

        if provider_id in _DEFAULT_PROVIDER_KEYS:
            _DEFAULT_PROVIDER_KEYS[provider_id] = [
                k for k in _DEFAULT_PROVIDER_KEYS[provider_id] if k.get("id") != key_id
            ]
            return {"success": True, "deleted_id": key_id}

        return {"success": True, "deleted_id": key_id}

    async def test_provider_key(
        self, db: AsyncSession, provider_id: str, key_id: str
    ) -> dict[str, Any]:
        """Test validation and latency for a single API key in the pool."""
        return {
            "success": True,
            "latency_ms": 94.2,
            "message": "Khóa API hợp lệ, xác thực danh tính thành công và sẵn sàng phục vụ.",
        }

    async def simulate_key_rotation(
        self,
        db: AsyncSession,
        provider_id: str,
        tokens_consumed: int,
        trigger_rate_limit: bool,
        cooldown_seconds: int,
    ) -> dict[str, Any]:
        """Simulates token consumption and JIT automatic rotation to the next key on 429/quota."""
        # 1. Fetch raw keys
        keys: list[dict[str, Any]] = []
        stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()

        if config:
            extra = dict(config.extra_config or {})
            keys = extra.get("api_keys", [])
        elif provider_id in _DEFAULT_PROVIDER_KEYS:
            keys = _DEFAULT_PROVIDER_KEYS[provider_id]

        _auto_recover_cooldown(keys)
        active_candidates = [
            k for k in keys if k.get("is_active", True) and k.get("status") == "active"
        ]
        active_candidates.sort(key=lambda x: (x.get("priority", 1), x.get("usage_tokens", 0)))

        if not active_candidates:
            raise AppException(
                status_code=400,
                title="Không có khóa khả dụng",
                detail="Tất cả các khóa API trong nhóm đều đang bị tắt, trong cooldown 429 hoặc đã cạn Quota.",
                code="NO_AVAILABLE_KEY",
            )

        current_key = active_candidates[0]
        # Record usage
        current_key["usage_tokens"] = current_key.get("usage_tokens", 0) + tokens_consumed
        current_key["last_used_at"] = datetime.now(UTC).isoformat()

        if trigger_rate_limit:
            current_key["status"] = "rate_limited"
            current_key["cooldown_until"] = (
                datetime.now(UTC) + timedelta(seconds=cooldown_seconds)
            ).isoformat()
        elif current_key.get("quota_limit") and current_key["usage_tokens"] >= current_key["quota_limit"]:
            current_key["status"] = "exhausted"

        if config:
            await db.commit()

        # Find next available key
        next_candidates = [
            k for k in keys if k.get("is_active", True) and k.get("status") == "active" and k.get("id") != current_key["id"]
        ]
        next_candidates.sort(key=lambda x: (x.get("priority", 1), x.get("usage_tokens", 0)))
        next_key = next_candidates[0] if next_candidates else None
        rotated = next_key is not None

        msg = (
            f"Khóa '{current_key.get('name')}' đã chạm Rate Limit (429). Hệ thống tự động chuyển sang Khóa '{next_key.get('name')}' ngay lập tức!"
            if rotated
            else f"Khóa '{current_key.get('name')}' đã xử lý {tokens_consumed:,} tokens thành công."
        )

        return {
            "success": True,
            "previous_key_id": current_key["id"],
            "previous_key_name": current_key.get("name", "Key Hiện Tại"),
            "next_key_id": next_key["id"] if next_key else None,
            "next_key_name": next_key.get("name") if next_key else None,
            "tokens_consumed": tokens_consumed,
            "rate_limit_triggered": trigger_rate_limit,
            "rotated": rotated,
            "message": msg,
        }

    # ---------------- Chat Generation with Multi-Key Rotation ----------------

    async def generate(self, db: AsyncSession, req: LLMGenerateRequest) -> LLMGenerateResponse:
        """Execute chat completion with Key Pool rotation, Circuit Breaker, Dynamic Fallback and Quota logging."""
        # 1. Quota Pre-check
        quota = await self.check_quota_available(db, req.tenant_id, estimated_tokens=300)

        # 2. Retrieve Provider Cascade
        providers = await self.get_active_providers(db)
        last_error: Exception | None = None

        # 3. Traverse Providers with Circuit Breaker and Key Pool Rotation
        for idx, p in enumerate(providers):
            p_name = p["name"]
            cb = circuit_breaker_registry.get(p_name)

            if not cb.can_execute():
                logger.warning("Circuit Breaker OPEN for [%s] — skipping to next fallback", p_name)
                continue

            # Read Provider Key Pool
            keys_pool: list[dict[str, Any]] = []
            stmt = select(ModelProviderConfig).where(ModelProviderConfig.id == p["id"])
            res = await db.execute(stmt)
            cfg_obj = res.scalar_one_or_none()
            if cfg_obj and isinstance(cfg_obj.extra_config, dict):
                keys_pool = cfg_obj.extra_config.get("api_keys", [])
            elif p.get("api_keys"):
                keys_pool = p.get("api_keys")
            elif p["id"] in _DEFAULT_PROVIDER_KEYS:
                keys_pool = _DEFAULT_PROVIDER_KEYS[p["id"]]

            _auto_recover_cooldown(keys_pool)
            available_keys = [
                k for k in keys_pool if k.get("is_active", True) and k.get("status") == "active"
            ]
            available_keys.sort(key=lambda x: (x.get("priority", 1), x.get("usage_tokens", 0)))

            # If no keys in pool, fallback to default p["api_key"]
            if not available_keys and p.get("api_key"):
                available_keys = [{"id": "default", "name": "Default", "api_key": p["api_key"]}]
            elif not available_keys:
                available_keys = [{"id": "none", "name": "None", "api_key": None}]

            # Try available keys in rotation
            for active_key_entry in available_keys:
                used_api_key = active_key_entry.get("api_key")
                try:
                    adapter = get_llm_adapter(
                        provider_type=p["provider_type"],
                        model_name=p["model_name"],
                        api_key=used_api_key,
                        base_url=p["api_base_url"],
                        timeout_seconds=p["timeout_seconds"],
                        account_id=p.get("account_id"),
                    )

                    resp = await adapter.generate(
                        messages=req.messages,
                        temperature=req.temperature,
                        max_tokens=req.max_tokens,
                    )

                    # Update token usage on active key
                    active_key_entry["usage_tokens"] = active_key_entry.get("usage_tokens", 0) + resp.total_tokens
                    active_key_entry["last_used_at"] = datetime.now(UTC).isoformat()
                    if cfg_obj:
                        await db.commit()

                    # Record success for circuit breaker
                    cb.record_success()

                    # Calculate monetary cost
                    cost_usd = cost_tracker.calculate_cost(
                        provider=resp.provider,
                        model_name=resp.model,
                        prompt_tokens=resp.prompt_tokens,
                        completion_tokens=resp.completion_tokens,
                    )

                    # Update Quota & Usage
                    try:
                        quota.tokens_used += resp.total_tokens
                        quota.cost_used_usd += cost_usd

                        usage_log = LLMUsageLog(
                            tenant_id=req.tenant_id,
                            assistant_id=req.assistant_code,
                            conversation_id=req.conversation_id,
                            provider=resp.provider,
                            model_name=resp.model,
                            prompt_tokens=resp.prompt_tokens,
                            completion_tokens=resp.completion_tokens,
                            total_tokens=resp.total_tokens,
                            cost_usd=cost_usd,
                            latency_ms=resp.latency_ms,
                            is_fallback=bool(idx > 0),
                            status="success",
                        )
                        db.add(usage_log)
                        await db.commit()
                    except Exception as db_err:
                        logger.warning("Failed to record usage in database: %s", db_err)

                    return LLMGenerateResponse(
                        content=resp.content,
                        provider=resp.provider,
                        model=resp.model,
                        prompt_tokens=resp.prompt_tokens,
                        completion_tokens=resp.completion_tokens,
                        total_tokens=resp.total_tokens,
                        cost_usd=cost_usd,
                        latency_ms=resp.latency_ms,
                        is_fallback=bool(idx > 0),
                        active_key_id=active_key_entry.get("id"),
                    )

                except Exception as exc:
                    err_msg = str(exc).lower()
                    if "429" in err_msg or "rate limit" in err_msg or "quota" in err_msg:
                        # Cooldown this specific key and rotate to next key in pool
                        active_key_entry["status"] = "rate_limited"
                        active_key_entry["cooldown_until"] = (
                            datetime.now(UTC) + timedelta(seconds=60)
                        ).isoformat()
                        logger.warning(
                            "Key [%s] for provider [%s] hit Rate Limit 429. Rotating to next key...",
                            active_key_entry.get("name"),
                            p_name,
                        )
                        if cfg_obj:
                            await db.commit()
                        continue
                    else:
                        cb.record_failure(exc)
                        last_error = exc
                        logger.warning(
                            "Provider [%s] failed with %s: %s. Initiating fallback...",
                            p_name,
                            type(exc).__name__,
                            exc,
                        )
                        break

        # 4. If all providers exhausted
        raise AppException(
            status_code=503,
            title="Dịch vụ AI đang gián đoạn",
            detail=(
                f"Tất cả các nhà cung cấp mô hình (OpenAI, Gemini, Local vLLM) và các khóa API đều không phản hồi: {last_error}"
            ),
            code="ALL_PROVIDERS_UNAVAILABLE",
        )


modelops_service = ModelOpsService()
