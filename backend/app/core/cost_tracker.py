"""LLM Token Usage & Cost Management Tracking."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Price catalog per 1,000,000 tokens (USD) as of 2026: (input_price, output_price)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI Models
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    # Google Gemini Models
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-2.0-flash": (0.10, 0.40),
    # Local & On-Premises (Free computation cost)
    "qwen2.5:7b": (0.0, 0.0),
    "llama3.1:8b": (0.0, 0.0),
    "local": (0.0, 0.0),
}


@dataclass
class CostCalculation:
    """Estimated cost calculation for an LLM invocation."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost_usd: float
    completion_cost_usd: float
    total_cost_usd: float


def calculate_llm_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> CostCalculation:
    """Calculate the estimated USD cost for an LLM inference call."""
    clean_model = model.lower().strip()

    # Find matching pricing rate or fallback to default gpt-4o-mini
    rate = MODEL_PRICING.get(clean_model)
    if rate is None:
        for key, val in MODEL_PRICING.items():
            if key in clean_model:
                rate = val
                break
    if rate is None:
        rate = MODEL_PRICING["gpt-4o-mini"]

    input_rate_per_token = rate[0] / 1_000_000.0
    output_rate_per_token = rate[1] / 1_000_000.0

    prompt_cost = prompt_tokens * input_rate_per_token
    completion_cost = completion_tokens * output_rate_per_token
    total_cost = prompt_cost + completion_cost

    return CostCalculation(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        prompt_cost_usd=round(prompt_cost, 7),
        completion_cost_usd=round(completion_cost, 7),
        total_cost_usd=round(total_cost, 7),
    )


class CostTracker:
    """Helper class for tracking and calculating LLM costs."""

    def calculate_cost(
        self,
        provider: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        calc = calculate_llm_cost(
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        return calc.total_cost_usd


cost_tracker = CostTracker()
