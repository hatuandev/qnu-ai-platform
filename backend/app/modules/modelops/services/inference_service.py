"""ModelOps Inference Service — Chat Completion, SSE Streaming, Dynamic Fallback, and Circuit Breaker."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import AsyncIterator
from contextlib import aclosing
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
from app.modules.modelops.services.chat_capabilities import (
    load_chat_capabilities,
    save_chat_capabilities,
)
from app.modules.modelops.services.chat_routes import VALID_CHAT_PROVIDER_TYPES, plan_chat_routes
from app.modules.modelops.services.inference_policy import filter_chat_routes, transient_retry_scope
from app.modules.modelops.services.key_rotation import (
    classify_key_failure,
    describe_provider_failure,
    is_context_overflow_error,
    provider_failure_diagnostics,
)
from app.modules.modelops.services.key_status import normalize_provider_key_status
from app.modules.modelops.services.output_contract import resolve_contract
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
        if req.output_contract is not None and req.stream:
            raise AppException("Hợp đồng selector chỉ hỗ trợ non-streaming.", code="MODEL_OUTPUT_STREAM_UNSUPPORTED", status_code=422)
        with transient_retry_scope():
            return await self._generate(db, req)

    async def _generate(self, db: AsyncSession, req: LLMGenerateRequest) -> LLMGenerateResponse:
        """Execute chat completion with Key Pool rotation, Circuit Breaker, Dynamic Fallback and Quota logging."""
        # 1. Quota Pre-check
        estimated_tokens = self._estimate_request_tokens(req)
        await self._call_check_quota_available(
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

        routes = filter_chat_routes(plan_chat_routes(providers, req))

        # 3. Traverse Providers with Circuit Breaker and Key Pool Rotation
        fallback_reasons: list[str] = []
        attempted_overflow = False
        attempted_other_error = False
        contract_failure = None
        attempt_trace = []
        for idx, (p, chosen_model) in enumerate(routes):
            p_name = p["name"]
            cb = circuit_breaker_registry.get(p_name)
            provider_error: Exception | None = None
            provider_overflow = False

            if not cb.can_execute():
                fallback_reasons.append(f"{p['id']}: circuit_breaker_open")
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
                if relational_managed:
                    skip_reason = "key_lease_unavailable"
                elif not keys_pool:
                    skip_reason = "no_credentials_configured"
                else:
                    skip_reason = "no_available_credentials"
                fallback_reasons.append(f"{p['id']}: {skip_reason}")
                logger.warning("Provider [%s] skipped: %s (keys_in_pool=%d)",
                               p_name, skip_reason, len(keys_pool))
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
                        request_capabilities=load_chat_capabilities(
                            cfg_obj.extra_config if cfg_obj else {}, chosen_model, p['api_base_url']),
                    )

                    effective_contract = resolve_contract(req.output_contract,
                        getattr(adapter, "request_capabilities", {}),
                        supports_chat_schema=getattr(adapter, "supports_output_contract", False)) if req.output_contract else None
                    parameters = inspect.signature(adapter.generate).parameters
                    extra_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values())
                    arguments = {"messages": req.messages, "temperature": req.temperature, "max_tokens": req.max_tokens}
                    if "thinking_budget" in parameters or extra_kwargs:
                        arguments["thinking_budget"] = req.thinking_budget
                    if effective_contract and getattr(adapter, "supports_output_contract", False):
                        if "output_contract" not in parameters and not extra_kwargs:
                            raise AppException("Adapter không nhận hợp đồng đầu ra.", code="MODEL_OUTPUT_CONTRACT_UNSUPPORTED", status_code=422)
                        arguments["output_contract"] = effective_contract
                    resp = await adapter.generate(**arguments)
                    attempt_trace.append({"provider_id": p["id"], "model": chosen_model, "status": "response",
                        "output_contract": effective_contract, "transport_attempts": getattr(resp, "attempt_trace", [])})

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
                    await save_chat_capabilities(db, p['id'], chosen_model, p['api_base_url'],
                                                 getattr(adapter, 'request_capabilities', {}))

                    # Calculate monetary cost
                    cost_usd = cost_tracker.calculate_cost(
                        provider=resp.provider,
                        model_name=resp.model,
                        prompt_tokens=resp.prompt_tokens,
                        completion_tokens=resp.completion_tokens,
                    )

                    # Update Quota & Usage
                    try:
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
                            error_message=('Fallback: ' + '; '.join(fallback_reasons))[:500] if fallback_reasons else None,
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
                        requested_model=req.preferred_model_name,
                        provider_id=p['id'],
                        fallback_reason='; '.join(fallback_reasons) or None,
                        finish_reason=getattr(resp, "finish_reason", None),
                        refusal=getattr(resp, "refusal", None),
                        response_metadata=getattr(resp, "response_metadata", {}),
                        output_contract=effective_contract,
                        attempt_trace=attempt_trace,
                    )

                except asyncio.CancelledError:
                    lease = active_key_entry.get("_lease")
                    if isinstance(lease, LeasedProviderKey):
                        await provider_key_rotation_service.release(db, lease)
                    raise
                except Exception as exc:
                    if req.output_contract and (getattr(exc, "code", "").startswith("MODEL_OUTPUT_") or
                                               getattr(exc, "code", "") == "SEMANTIC_CONTEXT_INCOMPLETE" or
                                               getattr(exc, "code", "") == "MODEL_REQUEST_CONFIG_INVALID" or
                                               getattr(exc, "code", "") == "MODEL_RESPONSE_PROTOCOL_ERROR"):
                        lease = active_key_entry.get("_lease")
                        if isinstance(lease, LeasedProviderKey):
                            await provider_key_rotation_service.release(db, lease)
                        attempt_trace.append({"provider_id": p["id"], "model": chosen_model, "status": "rejected", "code": exc.code,
                            "transport_attempts": getattr(exc, "output_attempt_trace", [])})
                        exc.details = {**(exc.details or {}), "attempt_trace": attempt_trace}
                        if exc.code != "MODEL_OUTPUT_CONTRACT_UNSUPPORTED":
                            raise
                        contract_failure = exc
                        fallback_reasons.append(f"{p['id']}: {exc.code}")
                        break
                    provider_error = exc
                    if req.output_contract:
                        attempt_trace.append({"provider_id": p["id"], "model": chosen_model, "status": "failed",
                            "error_type": type(exc).__name__, "transport_attempts": getattr(exc, "output_attempt_trace", [])})
                    if is_context_overflow_error(exc):
                        # Our request exceeds the serving window: retrying the
                        # same prompt on sibling keys cannot succeed. Fall
                        # through to the next route, but never charge the
                        # circuit breaker for a healthy provider.
                        provider_overflow = True
                        detail = describe_provider_failure(exc)
                        logger.warning('model_context_exceeded provider_id=%s requested_model=%s detail=%s',
                                       p['id'], chosen_model, detail)
                        fallback_reasons.append(f"{p['id']}: model_context_exceeded")
                        lease = active_key_entry.get("_lease")
                        if isinstance(lease, LeasedProviderKey):
                            await provider_key_rotation_service.release(db, lease)
                        break
                    detail = describe_provider_failure(exc)
                    fallback_reasons.append(f"{p['id']}: {detail}")
                    logger.warning('model_inference_failed provider_id=%s requested_model=%s stage=generate diagnostics=%s',
                                   p['id'], chosen_model, provider_failure_diagnostics(exc))
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
                if provider_overflow:
                    attempted_overflow = True
                    logger.warning(
                        "Provider [%s] rejected the request context window; "
                        "circuit breaker not charged. Initiating fallback...",
                        p_name,
                    )
                else:
                    attempted_other_error = True
                    cb.record_failure(RuntimeError(describe_provider_failure(provider_error)))
                    logger.warning(
                        "All available keys for provider [%s] failed. Initiating fallback...",
                        p_name,
                    )

        # 4. If all providers exhausted
        if contract_failure and not attempted_other_error and not attempted_overflow:
            raise contract_failure
        if attempted_overflow and not attempted_other_error:
            raise AppException(
                status_code=502,
                title="Yêu cầu vượt giới hạn ngữ cảnh của model",
                detail=(
                    "Nội dung truy vấn kèm bằng chứng vượt quá cửa sổ ngữ cảnh "
                    "của model phục vụ. Mọi route đã thử đều báo tràn ngữ cảnh; "
                    "không có lỗi hạ tầng provider nào khác."
                ),
                code="MODEL_CONTEXT_EXCEEDED",
            )
        raise AppException(
            status_code=503,
            title="Dịch vụ AI đang gián đoạn",
            detail=(
                "Tất cả nhà cung cấp và khóa API khả dụng đều không phản hồi. "
                "Vui lòng kiểm tra trạng thái ModelOps hoặc thử lại sau."
            ),
            code="ALL_PROVIDERS_UNAVAILABLE",
            details={"stage": "provider", "attempt_trace": attempt_trace} if req.output_contract else None,
        )

    async def generate_stream(
        self, db: AsyncSession, req: LLMGenerateRequest
    ) -> AsyncIterator[str]:
        if req.output_contract is not None:
            raise AppException("Hợp đồng selector chỉ hỗ trợ non-streaming.", code="MODEL_OUTPUT_STREAM_UNSUPPORTED", status_code=422)
        with transient_retry_scope():
            async with aclosing(self._generate_stream(db, req)) as stream:
                async for chunk in stream:
                    yield chunk

    async def _generate_stream(
        self, db: AsyncSession, req: LLMGenerateRequest
    ) -> AsyncIterator[str]:
        """Stream chat tokens with Key Pool rotation, Preferred Model priority, Quota tracking and Dynamic Fallback."""
        # 1. Quota Pre-check
        estimated_tokens = self._estimate_request_tokens(req)
        await self._call_check_quota_available(
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

        routes = filter_chat_routes(plan_chat_routes(providers, req))

        attempted_overflow = False
        attempted_other_error = False
        for idx, (p, chosen_model) in enumerate(routes):
            p_name = p["name"]
            cb = circuit_breaker_registry.get(p_name)
            provider_error: Exception | None = None
            provider_overflow = False
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
                if relational_managed:
                    skip_reason = "key_lease_unavailable"
                elif not keys_pool:
                    skip_reason = "no_credentials_configured"
                else:
                    skip_reason = "no_available_credentials"
                logger.warning("Provider [%s] skipped: %s (keys_in_pool=%d)",
                               p_name, skip_reason, len(keys_pool))
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
                        request_capabilities=load_chat_capabilities(
                            cfg_obj.extra_config if cfg_obj else {}, chosen_model, p['api_base_url']),
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
                    reported_usage = getattr(adapter, 'stream_usage', {})
                    prompt_chars = sum(len(m.content) for m in req.messages)
                    prompt_tokens = reported_usage.get('prompt_tokens', max(1, prompt_chars // 4)) if isinstance(reported_usage, dict) else max(1, prompt_chars // 4)
                    completion_tokens = reported_usage.get('completion_tokens', max(1, len(full_content) // 4)) if isinstance(reported_usage, dict) else max(1, len(full_content) // 4)
                    total_tokens = prompt_tokens + completion_tokens
                    served_model = getattr(adapter, 'served_model', None)
                    if not isinstance(served_model, str):
                        served_model = chosen_model

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

                    await save_chat_capabilities(db, p['id'], chosen_model, p['api_base_url'],
                                                 getattr(adapter, 'request_capabilities', {}))

                    try:
                        await self._call_record_usage_log(
                            db,
                            tenant_id=req.tenant_id,
                            assistant_id=req.assistant_code,
                            conversation_id=req.conversation_id,
                            provider=p["provider_type"],
                            model_name=served_model,
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
                    if is_context_overflow_error(ex):
                        provider_overflow = True
                        logger.warning('model_context_exceeded provider_id=%s requested_model=%s detail=%s',
                                       p['id'], chosen_model, describe_provider_failure(ex))
                        lease = active_key_entry.get("_lease")
                        if isinstance(lease, LeasedProviderKey):
                            await provider_key_rotation_service.release(db, lease)
                        if yielded_any:
                            # A started stream is never continued from another
                            # key/provider/model: surfacing the failure keeps
                            # the emitted prefix intact instead of appending
                            # fallback text to it, like other mid-stream errors.
                            raise
                        break
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
                    logger.warning("model_inference_failed provider_id=%s requested_model=%s stage=stream diagnostics=%s",
                                   p['id'], chosen_model, provider_failure_diagnostics(ex))
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
                if provider_overflow:
                    attempted_overflow = True
                    logger.warning(
                        "Provider [%s] rejected the stream context window; "
                        "circuit breaker not charged.",
                        p_name,
                    )
                else:
                    attempted_other_error = True
                    cb.record_failure(RuntimeError(describe_provider_failure(provider_error)))

        if attempted_overflow and not attempted_other_error:
            raise AppException(
                status_code=502,
                title="Yêu cầu vượt giới hạn ngữ cảnh của model",
                detail=(
                    "Nội dung truy vấn kèm bằng chứng vượt quá cửa sổ ngữ cảnh "
                    "của model phục vụ cho luồng trực tuyến."
                ),
                code="MODEL_CONTEXT_EXCEEDED",
            )
        raise AppException(
            status_code=503,
            title="Dịch vụ AI đang gián đoạn",
            detail="Toàn bộ các nhà cung cấp mô hình đều không phản hồi luồng trực tuyến.",
            code="ALL_PROVIDERS_UNAVAILABLE",
        )


inference_service = InferenceService()
