"""Server-owned RAG provider restrictions and shared bounded transport retries."""

import asyncio
import json
import logging
import math
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

import httpx

from app.core.exceptions import AppException
from app.core.paths import get_configs_dir

logger = logging.getLogger(__name__)
_allowed_providers: ContextVar[frozenset[str] | None] = ContextVar("rag_chat_providers", default=None)
_rag_scope_active: ContextVar[bool] = ContextVar("rag_scope_active", default=False)
_required_output: ContextVar[bool] = ContextVar("required_structured_output", default=False)


@dataclass
class RetryBudget:
    remaining: int = 1


_retry_budget: ContextVar[RetryBudget | None] = ContextVar("chat_transient_retry_budget", default=None)


async def load_rag_provider_ids() -> frozenset[str] | None:
    path = get_configs_dir() / "rag_inference_policy.json"
    try:
        data = json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("Policy must be an object")
        mode = data.get("chat_provider_mode", "allowlist")
        if mode == "modelops":
            if "allowed_chat_provider_ids" in data:
                raise ValueError("Conflicting provider policies")
            return None  # Only the routes configured and enabled in ModelOps.
        if mode != "allowlist":
            raise ValueError("Unknown provider policy")
        values = data["allowed_chat_provider_ids"]
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError("Invalid provider list")
        return frozenset(values)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise AppException("Chưa có chính sách provider RAG hợp lệ trên máy chủ.",
                           code="RAG_INFERENCE_POLICY_UNAVAILABLE", status_code=503) from exc


@contextmanager
def transient_retry_scope() -> Iterator[None]:
    """Nested calls share one retry, rather than multiplying retries per layer."""
    token = _retry_budget.set(RetryBudget()) if _retry_budget.get() is None else None
    try:
        yield
    finally:
        if token is not None:
            _retry_budget.reset(token)


@asynccontextmanager
async def rag_chat_scope() -> AsyncIterator[None]:
    if _rag_scope_active.get():
        yield
        return
    token = _allowed_providers.set(await load_rag_provider_ids())
    active_token = _rag_scope_active.set(True)
    try:
        with transient_retry_scope():
            yield
    finally:
        _rag_scope_active.reset(active_token)
        _allowed_providers.reset(token)


@contextmanager
def preserve_structured_output() -> Iterator[None]:
    token = _required_output.set(True)
    try:
        yield
    finally:
        _required_output.reset(token)


def minimum_chat_output(requested: int, observed_minimum: int) -> int:
    return max(requested, observed_minimum) if _required_output.get() else observed_minimum


def filter_chat_routes(routes: list[tuple[dict, str]]) -> list[tuple[dict, str]]:
    allowed = _allowed_providers.get()
    if allowed is None:
        return routes
    permitted = [(provider, model) for provider, model in routes if provider["id"] in allowed]
    if len(permitted) != len(routes):
        logger.warning("rag_provider_routes_blocked count=%d", len(routes) - len(permitted))
    if not permitted:
        raise AppException("Provider được chọn không thuộc danh sách RAG được máy chủ cho phép.",
                           code="RAG_PROVIDER_NOT_ALLOWED", status_code=403)
    return permitted


async def retry_transient_response(response: httpx.Response, deadline: float) -> bool:
    budget = _retry_budget.get()
    if (response.status_code not in (502, 503) or budget is None or budget.remaining < 1
            or not math.isfinite(deadline)):
        return False
    from app.modules.modelops.services.key_rotation import classify_key_failure

    error = httpx.HTTPStatusError("Upstream rejected request", request=response.request, response=response)
    if classify_key_failure(error).state is not None:
        return False  # Quota/auth failures are not transient transport failures.
    delay = 0.1
    retry_after = response.headers.get("retry-after")
    if retry_after is not None:
        try:
            seconds = float(retry_after)
            if not math.isfinite(seconds) or seconds < 0:
                return False
            delay = max(delay, seconds)
        except ValueError:
            return False  # Never ignore an unknown server retry delay.
    if not delay < deadline - time.monotonic():
        return False
    budget.remaining -= 1
    logger.warning("chat_transient_retry http_status=%d remaining=%d", response.status_code, budget.remaining)
    await response.aclose()
    await asyncio.sleep(delay)
    return True
