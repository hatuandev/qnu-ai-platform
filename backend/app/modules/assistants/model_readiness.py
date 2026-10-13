"""Check persisted ModelOps ownership and credentials without paid health probes."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistants.schemas import AssistantLifecycleConfig
from app.modules.modelops.models import ModelProviderConfig, ProviderApiKey
from app.modules.modelops.services.chat_routes import VALID_CHAT_PROVIDER_TYPES, is_chat_model


async def check_model_routes(db: AsyncSession, config: AssistantLifecycleConfig) -> list[str]:
    providers = (await db.execute(select(ModelProviderConfig).where(
        ModelProviderConfig.is_active.is_(True)))).scalars().all()
    keys = (await db.execute(select(ProviderApiKey))).scalars().all()
    defaults_record = next((p for p in providers if p.id == "system_model_defaults"), None)
    defaults = ((defaults_record.extra_config or {}).get("defaults") or {}) if defaults_record else {}
    model_policy = config.model_policy
    targets = [("Primary", model_policy.preferred_provider_id, model_policy.primary_model, "chat")]
    if model_policy.fallback_model:
        targets.append(("Fallback", model_policy.fallback_provider_id, model_policy.fallback_model, "chat"))
    reranker = config.knowledge_policy.reranker_policy
    if reranker.enabled:
        targets.append(("Reranker", reranker.provider_id or defaults.get("default_reranker_provider_id"),
                        reranker.model_name or defaults.get("default_reranker_model"), "reranker"))
    errors: list[str] = []
    for label, provider_id, model, role in targets:
        candidates = [p for p in providers if (p.id == provider_id if provider_id else
                      model in ((p.extra_config or {}).get("models") or []) or model == p.model_name)]
        if not model or len(candidates) != 1:
            errors.append(f"{label}: chưa chọn cặp provider–model hợp lệ, duy nhất.")
            continue
        provider = candidates[0]
        extra = provider.extra_config or {}
        spec = (extra.get("model_specs") or {}).get(model) or {}
        capability = (extra.get("model_capabilities") or {}).get(model)
        rerank_role = capability.get("probe_role") if capability is not None else spec.get("type")
        if (role == "chat" and (provider.provider_type not in VALID_CHAT_PROVIDER_TYPES
                                or not is_chat_model({"model_specs": extra.get("model_specs"), "model_capabilities": extra.get("model_capabilities")}, model))
                or role == "reranker" and rerank_role != "reranker"):
            errors.append(f"{label}: model không đúng vai trò {role}.")
        managed_keys = [k for k in keys if k.provider_id == provider.id]
        provider_keys = [k for k in managed_keys if k.is_active and k.status == "active" and k.api_key_encrypted
                         and (k.quota_limit is None or k.usage_tokens < k.quota_limit)]
        legacy_keys = extra.get("api_keys") or []
        legacy_valid = any(k.get("is_active", True) and k.get("status") == "active"
                           and k.get("api_key") for k in legacy_keys)
        has_credentials = bool(provider_keys) if managed_keys else bool(legacy_valid or (not legacy_keys and provider.api_key_encrypted))
        if not has_credentials:
            errors.append(f"{label}: provider chưa có khóa API khả dụng.")
    return errors
