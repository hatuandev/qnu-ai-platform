"""Plan explicit model/provider pairs without guessing model families."""

from typing import Any

from app.modules.modelops.schemas import LLMGenerateRequest

VALID_CHAT_PROVIDER_TYPES = {
    "gemini", "openai", "cloudflare", "deepseek", "groq", "claude", "mistral",
    "openrouter", "nvidia", "custom", "vllm", "openai_compatible",
    "ollama", "ollama_cloud",
}


def is_chat_model(provider: dict[str, Any], model: str) -> bool:
    capability = (provider.get("model_capabilities") or {}).get(model)
    if capability is not None:
        return capability.get("probe_role") == "chat"
    specs = provider.get("model_specs") or {}
    role = (specs.get(model) or {}).get("type", "text")
    spec = specs.get(model) or {}
    return spec.get("supports_chat", role in {"text", "chat", "llm", "vision", "multimodal", "reasoning", "vision_ocr"})


def plan_chat_routes(
    providers: list[dict[str, Any]], request: LLMGenerateRequest,
) -> list[tuple[dict[str, Any], str]]:
    """Pinned providers accept aliases; unpinned aliases require exact catalog ownership.

    Primary and fallback can belong to the same provider. Do not silently replace
    a requested model with some other provider's default.
    """
    routes: list[tuple[dict[str, Any], str]] = []
    seen: set[tuple[str, str]] = set()
    targets = [(request.preferred_provider_id, request.preferred_model_name),
               (request.fallback_provider_id, request.fallback_model_name)]
    explicit = any(pid or model for pid, model in targets)
    if not explicit:
        targets = [(str(p["id"]), p.get("model_name")) for p in providers]
    for provider_id, model_name in targets:
        if not model_name and not provider_id:
            continue
        for provider in providers:
            if provider_id and provider["id"] != provider_id:
                continue
            model = model_name or provider.get("model_name")
            if not model:
                continue
            catalog = provider.get("models") or []
            if not provider_id and model not in catalog and model != provider.get("model_name"):
                continue
            key = (str(provider["id"]), model)
            if key not in seen and is_chat_model(provider, model):
                seen.add(key)
                routes.append((provider, model))
    return routes
