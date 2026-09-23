"""ModelOps Inference Service — Chat Completion, SSE Streaming, Dynamic Fallback, and Circuit Breaker."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cost_tracker import cost_tracker
from app.core.crypto import decrypt_secret
from app.core.exceptions import AppException
from app.modules.modelops.circuit_breaker import circuit_breaker_registry
from app.modules.modelops.models import LLMUsageLog, ModelProviderConfig, TenantQuota
from app.modules.modelops.providers import get_llm_adapter
from app.modules.modelops.schemas import LLMGenerateRequest, LLMGenerateResponse
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
    "local_vllm",
    "local",
    "ollama",
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
            "local",
            "vllm",
            "local_vllm",
            "ollama",
            "groq",
            "cloudflare",
            "custom",
            "openrouter",
            "nvidia",
        )

    # 3. Custom / OpenRouter / OpenAI compatible proxies allow arbitrary model names
    return p_type in ("openai_compatible", "custom", "local", "vllm", "local_vllm", "openrouter", "groq")


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
        self, db: AsyncSession, only_active: bool = False
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

    async def generate(self, db: AsyncSession, req: LLMGenerateRequest) -> LLMGenerateResponse:
        """Execute chat completion with Key Pool rotation, Circuit Breaker, Dynamic Fallback and Quota logging."""
        # 1. Quota Pre-check
        quota = await self._call_check_quota_available(db, req.tenant_id, estimated_tokens=300)

        # 2. Retrieve Provider Cascade and filter for genuine Chat LLMs only
        all_providers = await self._call_get_active_providers(db)
        providers = [
            p
            for p in all_providers
            if p.get("provider_type") in VALID_CHAT_PROVIDER_TYPES
            and not any(x in str(p.get("id", "")).lower() for x in ("routing", "sentence_transformers", "docling"))
        ]
        if req.preferred_provider_id or req.preferred_model_name or req.fallback_model_name:
            def _match_score(p: dict[str, Any]) -> int:
                score = 0
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
                raw_key = active_key_entry.get("api_key")
                used_api_key = decrypt_secret(raw_key) if raw_key else None
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

    async def generate_stream(
        self, db: AsyncSession, req: LLMGenerateRequest
    ) -> AsyncIterator[str]:
        """Stream chat tokens with Key Pool rotation, Preferred Model priority, Quota tracking and Dynamic Fallback."""
        # 1. Quota Pre-check
        quota = await self._call_check_quota_available(db, req.tenant_id, estimated_tokens=300)

        # 2. Retrieve Provider Cascade and filter for genuine Chat LLMs only
        all_providers = await self._call_get_active_providers(db)
        providers = [
            p
            for p in all_providers
            if p.get("provider_type") in VALID_CHAT_PROVIDER_TYPES
            and not any(x in str(p.get("id", "")).lower() for x in ("routing", "sentence_transformers", "docling"))
        ]
        if req.preferred_provider_id or req.preferred_model_name or req.fallback_model_name:
            def _match_score(p: dict[str, Any]) -> int:
                score = 0
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

            _auto_recover_cooldown(keys_pool)
            available_keys = [
                k for k in keys_pool if k.get("is_active", True) and k.get("status") == "active"
            ]
            available_keys.sort(key=lambda x: (x.get("priority", 1), x.get("usage_tokens", 0)))
            if not available_keys and p.get("api_key"):
                available_keys = [{"id": "default", "name": "Default", "api_key": p["api_key"]}]
            elif not available_keys:
                available_keys = [{"id": "none", "name": "None", "api_key": None}]

            for active_key_entry in available_keys:
                raw_key = active_key_entry.get("api_key")
                used_api_key = decrypt_secret(raw_key) if raw_key else None
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

                    active_key_entry["usage_tokens"] = (
                        active_key_entry.get("usage_tokens", 0) + total_tokens
                    )
                    active_key_entry["last_used_at"] = datetime.now(UTC).isoformat()
                    if cfg_obj:
                        await db.commit()

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
                except Exception as ex:
                    cb.record_failure(ex)
                    logger.warning("Stream failed for provider [%s]: %s", p_name, ex)
                    if yielded_any:
                        raise
                    continue

        raise AppException(
            status_code=503,
            title="Dịch vụ AI đang gián đoạn",
            detail="Toàn bộ các nhà cung cấp mô hình đều không phản hồi luồng trực tuyến.",
            code="ALL_PROVIDERS_UNAVAILABLE",
        )


inference_service = InferenceService()
