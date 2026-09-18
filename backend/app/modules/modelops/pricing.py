"""Model pricing directory and cost estimation utilities for QNU AI Platform."""

from __future__ import annotations

# Pricing rates per 1 Million tokens (Prompt / Completion) in USD
MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "gpt-4o": {"prompt": 2.50, "completion": 10.00},
    "text-embedding-3-small": {"prompt": 0.02, "completion": 0.0},
    "text-embedding-3-large": {"prompt": 0.13, "completion": 0.0},
    # Google Gemini
    "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-1.5-pro": {"prompt": 1.25, "completion": 5.00},
    "gemini-2.0-flash": {"prompt": 0.10, "completion": 0.40},
    # Mistral
    "mistral-large-latest": {"prompt": 2.00, "completion": 6.00},
    "mistral-small-latest": {"prompt": 0.20, "completion": 0.60},
    "mistral-ocr-latest": {"prompt": 0.0, "completion": 0.0, "fixed_per_call": 0.001},
    # DeepSeek & Open Source / Cloudflare
    "deepseek-chat": {"prompt": 0.14, "completion": 0.28},
    "deepseek-reasoner": {"prompt": 0.55, "completion": 2.19},
    "qwen2.5-7b-instruct": {"prompt": 0.10, "completion": 0.20},
    "qwen2.5-72b-instruct": {"prompt": 0.35, "completion": 0.70},
    # Local & On-Premise Models (0 USD)
    "bge-m3": {"prompt": 0.0, "completion": 0.0},
    "bge-reranker-v2-m3": {"prompt": 0.0, "completion": 0.0},
    "local-vllm": {"prompt": 0.0, "completion": 0.0},
    "ollama": {"prompt": 0.0, "completion": 0.0},
}

DEFAULT_FALLBACK_PRICING = {"prompt": 0.15, "completion": 0.60}


def calculate_cost_usd(
    model_name: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> float:
    """Calculate the estimated USD cost for a model generation.

    Cost = (prompt_tokens / 1_000_000 * rate_prompt) + (completion_tokens / 1_000_000 * rate_completion)
    """
    normalized_name = model_name.strip().lower()
    rates = DEFAULT_FALLBACK_PRICING

    for key, val in MODEL_PRICING.items():
        if key in normalized_name:
            rates = val
            break

    fixed_cost = rates.get("fixed_per_call", 0.0)
    prompt_cost = (prompt_tokens / 1_000_000.0) * rates.get("prompt", 0.15)
    completion_cost = (completion_tokens / 1_000_000.0) * rates.get("completion", 0.60)

    return round(fixed_cost + prompt_cost + completion_cost, 6)
