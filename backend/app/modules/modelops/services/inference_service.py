"""ModelOps Inference Service — Chat Completion, SSE Streaming, Dynamic Fallback, and Circuit Breaker."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.cost_tracker import cost_tracker
from app.core.crypto import decrypt_secret
from app.core.exceptions import AppException
from app.modules.modelops.circuit_breaker import circuit_breaker_registry
from app.modules.modelops.models import LLMUsageLog, ModelProviderConfig, TenantQuota
from app.modules.modelops.providers import get_llm_adapter
from app.modules.modelops.schemas import LLMGenerateRequest, LLMGenerateResponse
from app.modules.modelops.services.key_rotation import (
    classify_key_failure,
    describe_provider_failure,
)
from app.modules.modelops.services.key_status import normalize_provider_key_status
from app.modules.modelops.services.provider_key_rotation_service import (
    LeasedProviderKey,
    provider_key_rotation_service,
)
from app.modules.modelops.services.provider_service import (
    _DEFAULT_PROVIDER_KEYS,
    _auto_recover_cooldown,
    provider_service,
)
from app.modules.modelops.services.usage_accounting_service import usage_accounting_service

logger = logging.getLogger(__name__)

VALID_CHAT_PROVIDER_TYPES: set[str] = {
    "gemini",
    "openai",
    "cloudflare",
    "deepseek",
    "groq",
    "claude",
    "mistral",
    "openrouter",
    "nvidia",
    "custom",
}
NON_CHAT_MODEL_KEYWORDS: tuple[str, ...] = ("bge-", "embed", "rerank", "tableformer")


def _is_model_compatible_with_provider(p: dict[str, Any], model_name: str | None) -> bool:
    """Check if model name belongs to or is accepted by provider dynamically."""
    if not model_name or not str(model_name).strip():
        return False
    m_clean = str(model_name).strip()
    m_lower = m_clean.lower()
    p_models = [str(x).strip().lower() for x in (p.get("models") or [])]
    p_def_model = str(p.get("model_name", "")).strip().lower()

    # 1. Exact match in provider models list or default model
    if m_lower in p_models or m_lower == p_def_model:
        return True

    p_type = str(p.get("provider_type", "")).strip().lower()
    p_id = str(p.get("id", "")).strip().lower()

    # 2. Family & provider type matching
    if any(k in m_lower for k in ("gemini", "gemma")):
        return p_type in ("gemini", "google") or "gemini" in p_id or "google" in p_id
    if any(k in m_lower for k in ("gpt-", "chatgpt", "o1-", "o3-", "o1", "o3")):
        return p_type in ("openai", "azure") or "openai" in p_id
    if "claude" in m_lower:
        return p_type in ("anthropic", "claude") or "claude" in p_id
    if any(k in m_lower for k in ("mistral", "codestral", "ministral", "pixtral")):
        return p_type in ("mistral",) or "mistral" in p_id
    if any(k in m_lower for k in ("qwen", "deepseek", "llama", "phi-", "mixtral")):
        return p_type in (
            "groq",
            "cloudflare",
            "custom",
            "openrouter",
            "nvidia",
        )

    # 3. Custom / OpenRouter / OpenAI compatible proxies allow arbitrary model names
    return p_type in ("openai_compatible", "custom", "openrouter", "groq")


def _provider_has_credentials(p: dict[str, Any]) -> bool:
    """Check if a provider has at least one active API credential."""
    if p.get("api_key") or p.get("api_key_masked"):
        return True
    keys = p.get("api_keys") or []
    return any(
        k.get("is_active", True)
        and k.get("status") == "active"
        and (k.get("api_key") or k.get("key_ciphertext"))
        for k in keys
    )


class InferenceService:
    """Executes LLM inference (generate & stream) with Key Pool rotation, Dynamic Fallback, and Quota accounting."""

    def __init__(self, facade: Any = None) -> None:
        self.facade = facade

    def _get_facade(self) -> Any:
        if self.facade is not None:
            return self.facade
        import sys
        mod = sys.modules.get("app.modules.modelops.service")
        if mod and hasattr(mod, "modelops_service"):
            return mod.modelops_service
        return None

    async def _call_check_quota_available(
        self, db: AsyncSession, tenant_id: str, estimated_tokens: int = 500
    ) -> TenantQuota:
        facade = self._get_facade()
        if facade and hasattr(facade, "check_quota_available"):
            return await facade.check_quota_available(db, tenant_id, estimated_tokens)
        return await usage_accounting_service.check_quota_available(db, tenant_id, estimated_tokens)

    async def _call_get_active_providers(
        self, db: AsyncSession, only_active: bool = True
    ) -> list[dict[str, Any]]:
        facade = self._get_facade()
        if facade and hasattr(facade, "get_active_providers"):
            return await facade.get_active_providers(db, only_active=only_active)
        return await provider_service.get_active_providers(db, only_active=only_active)

    async def _call_record_usage_log(self, db: AsyncSession, **kwargs: Any) -> LLMUsageLog:
        facade = self._get_facade()
        if facade and hasattr(facade, "record_usage_log"):
            return await facade.record_usage_log(db, **kwargs)
        return await usage_accounting_service.record_usage_log(db, **kwargs)

    def _get_adapter_factory(self) -> Any:
        import sys
        mod = sys.modules.get("app.modules.modelops.service")
        if mod and hasattr(mod, "get_llm_adapter"):
            return mod.get_llm_adapter
        return get_llm_adapter

    @staticmethod
    def _estimate_request_tokens(req: LLMGenerateRequest) -> int:
        prompt_chars = sum(len(message.content) for message in req.messages)
        return max(1, prompt_chars // 4) + max(1, req.max_tokens)

    @staticmethod
    def _lease_to_key_entry(lease: LeasedProviderKey) -> dict[str, Any]:
        return {
            "id": lease.id,
            "name": lease.name,
            "api_key": lease.api_key,
            "account_id": lease.account_id,
            "_lease": lease,
        }

    @staticmethod
    def _prepare_available_keys(
        keys_pool: list[dict[str, Any]], estimated_tokens: int
    ) -> tuple[list[dict[str, Any]], bool]:
        """Recover cooldowns, enforce configured quotas and order usable keys."""
        before = [
            (key.get("id"), key.get("status"), key.get("cooldown_until"))
            for key in keys_pool
        ]
        _auto_recover_cooldown(keys_pool)

        for key in keys_pool:
            quota_limit = key.get("quota_limit")
            try:
                parsed_quota_limit = int(quota_limit) if quota_limit is not None else None
                usage_tokens = max(0, int(key.get("usage_tokens") or 0))
            except (TypeError, ValueError):
                parsed_quota_limit = None
                usage_tokens = 0
            if (
                key.get("is_active", True)
                and parsed_quota_limit is not None
                and usage_tokens >= parsed_quota_limit
            ):
                key["status"] = "exhausted"
                key["cooldown_until"] = None

        available_keys = [
            key
            for key in keys_pool
            if key.get("is_active", True)
            and normalize_provider_key_status(key.get("status")) == "active"
            and (key.get("quota_limit") is None or int(key.get("usage_tokens") or 0) + max(0, estimated_tokens) <= int(key["quota_limit"]))
        ]
        available_keys.sort(
            key=lambda key: (
                key.get("priority", 1),
                key.get("usage_tokens", 0),
                key.get("last_used_at") or "",
            )
        )
        after = [
            (key.get("id"), key.get("status"), key.get("cooldown_until"))
            for key in keys_pool
        ]
        return available_keys, before != after

    @staticmethod
    async def _persist_key_pool(
        db: AsyncSession,
        config: ModelProviderConfig | None,
        keys_pool: list[dict[str, Any]],
    ) -> None:
        if config is None:
            return
        extra = dict(config.extra_config or {})
        extra["api_keys"] = keys_pool
        config.extra_config = extra
        flag_modified(config, "extra_config")
        await db.commit()

    async def _record_key_success(
        self,
        db: AsyncSession,
        config: ModelProviderConfig | None,
        keys_pool: list[dict[str, Any]],
        key: dict[str, Any],
        total_tokens: int,
    ) -> None:
        key["usage_tokens"] = max(0, int(key.get("usage_tokens") or 0)) + total_tokens
        key["last_used_at"] = datetime.now(UTC).isoformat()
        quota_limit = key.get("quota_limit")
        if quota_limit is not None and key["usage_tokens"] >= int(quota_limit):
            key["status"] = "exhausted"
            key["cooldown_until"] = None
        await self._persist_key_pool(db, config, keys_pool)

    async def _record_key_failure(
        self,
        db: AsyncSession,
        config: ModelProviderConfig | None,
        keys_pool: list[dict[str, Any]],
        key: dict[str, Any],
        exc: Exception,
    ) -> str | None:
        failure = classify_key_failure(exc)
        if failure.state is None:
            return None

        key["status"] = failure.state
        if failure.state == "rate_limited":
            cooldown_seconds = failure.retry_after_seconds or 60
            key["cooldown_until"] = (
                datetime.now(UTC) + timedelta(seconds=cooldown_seconds)
            ).isoformat()
        else:
            key["cooldown_until"] = None
        key["last_error_code"] = failure.reason
        key["last_error_at"] = datetime.now(UTC).isoformat()
        await self._persist_key_pool(db, config, keys_pool)
        return failure.state

    async def generate(self, db: AsyncSession, req: LLMGenerateRequest) -> LLMGenerateResponse:
        """Execute chat completion with Key Pool rotation, Circuit Breaker, Dynamic Fallback and Quota logging."""
        # 1. Quota Pre-check
        estimated_tokens = self._estimate_request_tokens(req)
        quota = await self._call_check_quota_available(
            db, req.tenant_id, estimated_tokens=estimated_tokens
        )

        # 2. Retrieve Provider Cascade and filter for genuine Chat LLMs only
        all_providers = await self._call_get_active_providers(db, only_active=True)
        providers = [
            p
            for p in all_providers
            if p.get("provider_type") in VALID_CHAT_PROVIDER_TYPES
            and "routing" not in str(p.get("id", "")).lower()
        ]

        # Filter out cloud providers that have no active keys configured when configured providers exist
        configured_providers = [p for p in providers if _provider_has_credentials(p)]
        if configured_providers:
            providers = configured_providers

        if req.preferred_provider_id or req.preferred_model_name or req.fallback_model_name:
            def _match_score(p: dict[str, Any]) -> int:
                score = 0
                if _provider_has_credentials(p):
                    score += 200
                else:
                    score -= 500
                if req.preferred_provider_id and p.get("id") == req.preferred_provider_id:
                    score += 100
                p_models = p.get("models") or []
                if req.preferred_model_name:
                    if req.preferred_model_name in p_models or p.get("model_name") == req.preferred_model_name:
                        score += 50
                    elif _is_model_compatible_with_provider(p, req.preferred_model_name):
                        score += 40
                if req.fallback_model_name:
                    if req.fallback_model_name in p_models or p.get("model_name") == req.fallback_model_name:
                        score += 25
                    elif _is_model_compatible_with_provider(p, req.fallback_model_name):
                        score += 20
                return score

            providers = sorted(providers, key=_match_score, reverse=True)

        # 3. Traverse Providers with Circuit Breaker and Key Pool Rotation
        for idx, p in enumerate(providers):
            p_name = p["name"]
            cb = circuit_breaker_registry.get(p_name)
            provider_error: Exception | None = None

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

            relational_managed = False
            tried_relational_keys: set[str] = set()
            available_keys: list[dict[str, Any]] = []
            acquired = await provider_key_rotation_service.acquire(
                db, p["id"], estimated_tokens=estimated_tokens,
                lease_seconds=max(120, p["timeout_seconds"] + 30)
            )
            relational_managed = acquired.managed
            if acquired.lease is not None:
                available_keys.append(self._lease_to_key_entry(acquired.lease))

            if not relational_managed:
                available_keys, key_state_changed = self._prepare_available_keys(
                    keys_pool, estimated_tokens
                )
                if key_state_changed:
                    await self._persist_key_pool(db, cfg_obj, keys_pool)

                # Compatibility path until every deployment has run the migration.
                if not keys_pool and p.get("api_key"):
                    available_keys = [
                        {"id": "default", "name": "Default", "api_key": p["api_key"]}
                    ]
            if not available_keys:
                logger.info("Provider [%s] has no credentials configured, skipping to next fallback", p_name)
                continue

            # Try available keys in rotation
            for active_key_entry in available_keys:
                raw_key = active_key_entry.get("api_key")
                used_api_key = decrypt_secret(raw_key) if raw_key else None
                if not used_api_key:
                    lease = active_key_entry.get("_lease")
                    if isinstance(lease, LeasedProviderKey):
                        await provider_key_rotation_service.release(db, lease)
                    logger.debug("Provider [%s] key [%s] is empty, skipping key", p_name, active_key_entry.get("id"))
                    continue
                p_models = p.get("models") or []
                chat_candidates = [
                    m
                    for m in p_models
                    if not any(x in m.lower() for x in NON_CHAT_MODEL_KEYWORDS)
                ]

                # Resolve chosen_model dynamically respecting user's configuration
                if (
                    (req.preferred_provider_id and p.get("id") == req.preferred_provider_id and req.preferred_model_name)
                    or (req.preferred_model_name and _is_model_compatible_with_provider(p, req.preferred_model_name))
                ):
                    chosen_model = req.preferred_model_name
                elif req.fallback_model_name and _is_model_compatible_with_provider(p, req.fallback_model_name):
                    chosen_model = req.fallback_model_name
                else:
                    if chat_candidates and any(
                        x in str(p.get("model_name", "")).lower()
                        for x in NON_CHAT_MODEL_KEYWORDS
                    ):
                        chosen_model = chat_candidates[0]
                    else:
                        chosen_model = p["model_name"]

                # Hard safety check: never pass an embedding / reranker model to LLM chat generator
                if any(x in str(chosen_model).lower() for x in NON_CHAT_MODEL_KEYWORDS):
                    if chat_candidates:
                        chosen_model = chat_candidates[0]
                    else:
                        lease = active_key_entry.get("_lease")
                        if isinstance(lease, LeasedProviderKey):
                            await provider_key_rotation_service.release(db, lease)
                        logger.warning(
                            "Provider '%s' has only non-chat model '%s', skipping provider",
                            p["name"],
                            chosen_model,
                        )
                        continue

                is_fallback_run = bool(
                    idx > 0 or (req.preferred_model_name and chosen_model != req.preferred_model_name)
                )

                try:
                    adapter = self._get_adapter_factory()(
                        provider_type=p["provider_type"],
                        model_name=chosen_model,
                        api_key=used_api_key,
                        base_url=p["api_base_url"],
                        timeout_seconds=p["timeout_seconds"],
                        account_id=active_key_entry.get("account_id") or p.get("account_id"),
                    )

                    try:
                        resp = await adapter.generate(
                            messages=req.messages,
                            temperature=req.temperature,
                            max_tokens=req.max_tokens,
                            thinking_budget=getattr(req, "thinking_budget", 0),
                        )
                    except TypeError as te:
                        if "thinking_budget" in str(te):
                            resp = await adapter.generate(
                                messages=req.messages,
                                temperature=req.temperature,
                                max_tokens=req.max_tokens,
                            )
                        else:
                            raise

                    lease = active_key_entry.get("_lease")
                    if isinstance(lease, LeasedProviderKey):
                        await provider_key_rotation_service.complete_success(
                            db, lease, total_tokens=resp.total_tokens
                        )
                    else:
                        await self._record_key_success(
                            db,
                            cfg_obj,
                            keys_pool,
                            active_key_entry,
                            resp.total_tokens,
                        )

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

                        await self._call_record_usage_log(
                            db,
                            tenant_id=req.tenant_id,
                            assistant_id=req.assistant_code,
                            conversation_id=req.conversation_id,
                            provider=resp.provider,
                            model_name=resp.model,
                            prompt_tokens=resp.prompt_tokens,
                            completion_tokens=resp.completion_tokens,
                            latency_ms=resp.latency_ms,
                            is_fallback=is_fallback_run,
                            status="success",
                        )
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
                        is_fallback=is_fallback_run,
                        active_key_id=active_key_entry.get("id"),
                    )

                except asyncio.CancelledError:
                    lease = active_key_entry.get("_lease")
                    if isinstance(lease, LeasedProviderKey):
                        await provider_key_rotation_service.release(db, lease)
                    raise
                except Exception as exc:
                    provider_error = exc
                    lease = active_key_entry.get("_lease")
                    if isinstance(lease, LeasedProviderKey):
                        failure = await provider_key_rotation_service.complete_failure(
                            db, lease, exc
                        )
                        key_state = failure.state
                        tried_relational_keys.add(lease.id)
                        acquired = await provider_key_rotation_service.acquire(
                            db,
                            p["id"],
                            estimated_tokens=estimated_tokens,
                            excluded_key_ids=tried_relational_keys,
                            lease_seconds=max(120, p["timeout_seconds"] + 30),
                        )
                        if acquired.lease is not None:
                            available_keys.append(
                                self._lease_to_key_entry(acquired.lease)
                            )
                    else:
                        key_state = await self._record_key_failure(
                            db, cfg_obj, keys_pool, active_key_entry, exc
                        )
                    if key_state is not None:
                        logger.warning(
                            "Key [%s] for provider [%s] changed to [%s]. Rotating to next key...",
                            active_key_entry.get("name"),
                            p_name,
                            key_state,
                        )
                        continue
                    logger.warning(
                        "Key [%s] for provider [%s] failed with %s. Rotating to next key in pool...",
                        active_key_entry.get("name"),
                        p_name,
                        describe_provider_failure(exc),
                    )
                    continue

            if provider_error:
                cb.record_failure(RuntimeError(describe_provider_failure(provider_error)))
                logger.warning(
                    "All available keys for provider [%s] failed. Initiating fallback...",
                    p_name,
                )

        # 4. If all providers exhausted
        raise AppException(
            status_code=503,
            title="Dịch vụ AI đang gián đoạn",
            detail=(
                "Tất cả nhà cung cấp và khóa API khả dụng đều không phản hồi. "
                "Vui lòng kiểm tra trạng thái ModelOps hoặc thử lại sau."
            ),
            code="ALL_PROVIDERS_UNAVAILABLE",
        )

    async def generate_stream(
        self, db: AsyncSession, req: LLMGenerateRequest
    ) -> AsyncIterator[str]:
        """Stream chat tokens with Key Pool rotation, Preferred Model priority, Quota tracking and Dynamic Fallback."""
        # 1. Quota Pre-check
        estimated_tokens = self._estimate_request_tokens(req)
        quota = await self._call_check_quota_available(
            db, req.tenant_id, estimated_tokens=estimated_tokens
        )

        # 2. Retrieve Provider Cascade and filter for genuine Chat LLMs only
        all_providers = await self._call_get_active_providers(db, only_active=True)
        providers = [
            p
            for p in all_providers
            if p.get("provider_type") in VALID_CHAT_PROVIDER_TYPES
            and "routing" not in str(p.get("id", "")).lower()
        ]

        # Filter out cloud providers that have no active keys configured when configured providers exist
        configured_providers = [p for p in providers if _provider_has_credentials(p)]
        if configured_providers:
            providers = configured_providers

        if req.preferred_provider_id or req.preferred_model_name or req.fallback_model_name:
            def _match_score(p: dict[str, Any]) -> int:
                score = 0
                if _provider_has_credentials(p):
                    score += 200
                else:
                    score -= 500
                if req.preferred_provider_id and p.get("id") == req.preferred_provider_id:
                    score += 100
                p_models = p.get("models") or []
                if req.preferred_model_name:
                    if req.preferred_model_name in p_models or p.get("model_name") == req.preferred_model_name:
                        score += 50
                    elif _is_model_compatible_with_provider(p, req.preferred_model_name):
                        score += 40
                if req.fallback_model_name:
                    if req.fallback_model_name in p_models or p.get("model_name") == req.fallback_model_name:
                        score += 25
                    elif _is_model_compatible_with_provider(p, req.fallback_model_name):
                        score += 20
                return score

            providers = sorted(providers, key=_match_score, reverse=True)

        for idx, p in enumerate(providers):
            p_name = p["name"]
            cb = circuit_breaker_registry.get(p_name)
            provider_error: Exception | None = None
            if not cb.can_execute():
                continue

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

            relational_managed = False
            tried_relational_keys: set[str] = set()
            available_keys: list[dict[str, Any]] = []
            acquired = await provider_key_rotation_service.acquire(
                db, p["id"], estimated_tokens=estimated_tokens,
                lease_seconds=max(120, p["timeout_seconds"] + 30)
            )
            relational_managed = acquired.managed
            if acquired.lease is not None:
                available_keys.append(self._lease_to_key_entry(acquired.lease))

            if not relational_managed:
                available_keys, key_state_changed = self._prepare_available_keys(
                    keys_pool, estimated_tokens
                )
                if key_state_changed:
                    await self._persist_key_pool(db, cfg_obj, keys_pool)
                if not keys_pool and p.get("api_key"):
                    available_keys = [
                        {"id": "default", "name": "Default", "api_key": p["api_key"]}
                    ]
            if not available_keys:
                logger.info("Provider [%s] has no credentials configured, skipping to next fallback", p_name)
                continue

            for active_key_entry in available_keys:
                raw_key = active_key_entry.get("api_key")
                used_api_key = decrypt_secret(raw_key) if raw_key else None
                if not used_api_key:
                    lease = active_key_entry.get("_lease")
                    if isinstance(lease, LeasedProviderKey):
                        await provider_key_rotation_service.release(db, lease)
                    logger.debug("Provider [%s] key [%s] is empty, skipping key", p_name, active_key_entry.get("id"))
                    continue
                p_models = p.get("models") or []
                chat_candidates = [
                    m
                    for m in p_models
                    if not any(x in m.lower() for x in NON_CHAT_MODEL_KEYWORDS)
                ]

                # Resolve chosen_model dynamically respecting user's configuration
                if (
                    (req.preferred_provider_id and p.get("id") == req.preferred_provider_id and req.preferred_model_name)
                    or (req.preferred_model_name and _is_model_compatible_with_provider(p, req.preferred_model_name))
                ):
                    chosen_model = req.preferred_model_name
                elif req.fallback_model_name and _is_model_compatible_with_provider(p, req.fallback_model_name):
                    chosen_model = req.fallback_model_name
                else:
                    if chat_candidates and any(
                        x in str(p.get("model_name", "")).lower()
                        for x in NON_CHAT_MODEL_KEYWORDS
                    ):
                        chosen_model = chat_candidates[0]
                    else:
                        chosen_model = p["model_name"]

                # Hard safety check: never pass an embedding / reranker model to LLM chat generator
                if any(x in str(chosen_model).lower() for x in NON_CHAT_MODEL_KEYWORDS):
                    if chat_candidates:
                        chosen_model = chat_candidates[0]
                    else:
                        lease = active_key_entry.get("_lease")
                        if isinstance(lease, LeasedProviderKey):
                            await provider_key_rotation_service.release(db, lease)
                        logger.warning(
                            "Provider '%s' has only non-chat model '%s', skipping provider",
                            p["name"],
                            chosen_model,
                        )
                        continue

                is_fallback_run = bool(
                    idx > 0 or (req.preferred_model_name and chosen_model != req.preferred_model_name)
                )

                yielded_any = False
                streamed_chunks: list[str] = []
                start_time = time.perf_counter()
                last_renewed = start_time

                try:
                    adapter = self._get_adapter_factory()(
                        provider_type=p["provider_type"],
                        model_name=chosen_model,
                        api_key=used_api_key,
                        base_url=p["api_base_url"],
                        timeout_seconds=p["timeout_seconds"],
                        account_id=active_key_entry.get("account_id") or p.get("account_id"),
                    )
                    try:
                        token_stream = adapter.stream(
                            messages=req.messages,
                            temperature=req.temperature,
                            max_tokens=req.max_tokens,
                            thinking_budget=getattr(req, "thinking_budget", 0),
                        )
                    except TypeError as te:
                        if "thinking_budget" in str(te):
                            token_stream = adapter.stream(
                                messages=req.messages,
                                temperature=req.temperature,
                                max_tokens=req.max_tokens,
                            )
                        else:
                            raise

                    async for token_chunk in token_stream:
                        lease = active_key_entry.get("_lease")
                        if isinstance(lease, LeasedProviderKey) and time.perf_counter() - last_renewed >= 30:
                            renewed = await provider_key_rotation_service.renew(db, lease, max(120, p["timeout_seconds"] + 30))
                            if not renewed:
                                raise AppException("Quyền sử dụng khóa đã hết hiệu lực.", code="PROVIDER_KEY_LEASE_LOST", status_code=503)
                            last_renewed = time.perf_counter()
                        yielded_any = True
                        streamed_chunks.append(token_chunk)
                        yield token_chunk

                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
                    full_content = "".join(streamed_chunks)
                    prompt_chars = sum(len(m.content) for m in req.messages)
                    prompt_tokens = max(1, prompt_chars // 4)
                    completion_tokens = max(1, len(full_content) // 4)
                    total_tokens = prompt_tokens + completion_tokens

                    cost_usd = cost_tracker.calculate_cost(
                        provider=p["provider_type"],
                        model_name=chosen_model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                    )

                    lease = active_key_entry.get("_lease")
                    if isinstance(lease, LeasedProviderKey):
                        await provider_key_rotation_service.complete_success(
                            db, lease, total_tokens=total_tokens
                        )
                    else:
                        await self._record_key_success(
                            db,
                            cfg_obj,
                            keys_pool,
                            active_key_entry,
                            total_tokens,
                        )

                    cb.record_success()

                    try:
                        quota.tokens_used += total_tokens
                        quota.cost_used_usd += cost_usd

                        await self._call_record_usage_log(
                            db,
                            tenant_id=req.tenant_id,
                            assistant_id=req.assistant_code,
                            conversation_id=req.conversation_id,
                            provider=p["provider_type"],
                            model_name=chosen_model,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            latency_ms=elapsed_ms,
                            is_fallback=is_fallback_run,
                            status="success",
                        )
                    except Exception as db_err:
                        logger.warning("Failed to record streaming usage in database: %s", db_err)

                    return
                except (asyncio.CancelledError, GeneratorExit):
                    lease = active_key_entry.get("_lease")
                    if isinstance(lease, LeasedProviderKey):
                        await provider_key_rotation_service.release(db, lease)
                    raise
                except Exception as ex:
                    provider_error = ex
                    lease = active_key_entry.get("_lease")
                    if isinstance(lease, LeasedProviderKey):
                        failure = await provider_key_rotation_service.complete_failure(
                            db, lease, ex
                        )
                        key_state = failure.state
                        tried_relational_keys.add(lease.id)
                        if not yielded_any:
                            acquired = await provider_key_rotation_service.acquire(
                                db,
                                p["id"],
                                estimated_tokens=estimated_tokens,
                                excluded_key_ids=tried_relational_keys,
                            lease_seconds=max(120, p["timeout_seconds"] + 30),
                            )
                            if acquired.lease is not None:
                                available_keys.append(
                                    self._lease_to_key_entry(acquired.lease)
                                )
                    else:
                        key_state = await self._record_key_failure(
                            db, cfg_obj, keys_pool, active_key_entry, ex
                        )
                    logger.warning(
                        "Stream failed for key [%s] of provider [%s]: %s",
                        active_key_entry.get("name"),
                        p_name,
                        describe_provider_failure(ex),
                    )
                    if yielded_any:
                        raise
                    if key_state is not None:
                        logger.warning(
                            "Key [%s] for provider [%s] changed to [%s]. Rotating before first token...",
                            active_key_entry.get("name"),
                            p_name,
                            key_state,
                        )
                    continue

            if provider_error:
                cb.record_failure(RuntimeError(describe_provider_failure(provider_error)))

        raise AppException(
            status_code=503,
            title="Dịch vụ AI đang gián đoạn",
            detail="Toàn bộ các nhà cung cấp mô hình đều không phản hồi luồng trực tuyến.",
            code="ALL_PROVIDERS_UNAVAILABLE",
        )


inference_service = InferenceService()
