"""Recover a rejected window using same-server tokenization, never character guesses."""

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def fit_rejected_context(client: httpx.AsyncClient, endpoint: str, headers: dict[str, str],
                               payload: dict[str, Any], response: httpx.Response,
                               minimum_output: int = 1) -> bool:
    """One caller-bounded retry; no prompt cropping or persisted per-request budgets.

    Only the vLLM-compatible window error + tokenize contract is recognized.
    Unsupported endpoints/errors remain normal failures for ModelOps failover.
    """
    if response.status_code != 400 or not endpoint.endswith("/v1/chat/completions"):
        return False
    try:
        message = response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return False
    if not isinstance(message, str):
        return False
    window = re.search(r"maximum context length is (\d+) tokens", message)
    prompt = re.search(r"prompt contains (?:at least )?(\d+) input tokens", message)
    parameter = next((key for key in ("max_tokens", "max_completion_tokens", "max_output_tokens") if key in payload), None)
    if not window or not prompt or parameter is None:
        return False
    tokenize = {"model": payload["model"], "messages": payload["messages"], "add_generation_prompt": True}
    if "chat_template_kwargs" in payload:
        tokenize["chat_template_kwargs"] = payload["chat_template_kwargs"]
    try:
        result = await client.post(endpoint.removesuffix("/v1/chat/completions") + "/tokenize",
                                   headers=headers, json=tokenize)
        result.raise_for_status()
        data = result.json()
    except (httpx.HTTPError, ValueError):
        logger.info("model_context_fit_unavailable reason=tokenize_failed")
        return False
    count = data.get("count") if isinstance(data, dict) else None
    maximum = data.get("max_model_len") if isinstance(data, dict) else None
    if (type(count) is not int or type(maximum) is not int or maximum != int(window[1])
            or count < max(1, int(prompt[1]))):
        logger.info("model_context_fit_unavailable reason=invalid_token_count")
        return False
    available = maximum - count
    if not max(1, minimum_output) <= available < payload[parameter]:
        logger.info("model_context_fit_unavailable reason=no_usable_output_space")
        return False
    logger.info("model_context_fitted input_tokens=%d context_window=%d requested_output=%d effective_output=%d",
                count, maximum, payload[parameter], available)
    payload[parameter] = available
    return True
