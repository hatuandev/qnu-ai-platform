"""One deadline and one retry owner; only definite 401/429 may rotate a key.

Provider/model never changes here. Existing domain reservations therefore cover
the actual target, and ambiguous failures are returned without spending twice.
"""

import asyncio
import json
import re
import time
import uuid
from dataclasses import replace

from qnu.domains.modelops.resilience.admission import chat_slot
from qnu.domains.modelops.resilience.heartbeat import maintain_lease
from qnu.domains.modelops.resilience.key_pool import acquire, finish
from qnu.domains.modelops.resilience.key_pool import renew as renew_key
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException
from qnu.platform.logging import get_logger
from qnu.ports.chat_model import ChatResponseError
from qnu.ports.provider_execution import ProviderFailure

logger = get_logger(__name__)


def _reported_output_limit(error: ChatResponseError, requested: int) -> int | None:
    failure = error.provider_failure
    if (
        error.code != "chat_provider_rejected"
        or failure is None
        or failure.upstream_status not in (400, 422)
        or error.usage_tokens not in (None, 0)
    ):
        return None
    try:
        payload = json.loads(error.raw_body)
        detail = payload["error"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(detail, dict):
        return None
    usage = payload.get("usage")
    if isinstance(usage, dict) and any(
        usage.get(field) not in (None, 0) for field in ("completion_tokens", "total_tokens")
    ):
        return None
    limit = (
        detail.get("max_output_tokens")
        if detail.get("code") == "max_output_tokens_exceeded"
        else None
    )
    message = detail.get("message")
    if limit is None and isinstance(message, str):
        match = re.search(
            r"\bmax_tokens:\s*(\d{1,9})\s*>\s*(\d{1,9}),\s*which is the maximum allowed number of output tokens",
            message,
            re.IGNORECASE,
        )
        if match and int(match[1]) == requested:
            limit = int(match[2])
    return limit if type(limit) is int and 0 < limit < requested else None


class CredentialExecutor:
    def __init__(self, sessions=AsyncSessionFactory):
        self.sessions = sessions

    async def call(self, capability, request, invoke):
        if capability == "chat":
            async with chat_slot(request):
                try:
                    async with asyncio.timeout(
                        None
                        if getattr(request, "wait_for_completion", False)
                        else request.timeout_seconds
                    ):
                        return await self._call(capability, request, invoke)
                except TimeoutError as exc:
                    raise AppException(
                        "Hết thời gian gọi model; không tự gửi lại.",
                        code="chat_provider_uncertain",
                        status_code=504,
                    ) from exc
        return await self._call(capability, request, invoke)

    async def _call(self, capability, request, invoke):
        if request.execution is None:
            return await invoke(request)
        excluded, started, call_id = set(), time.monotonic(), uuid.uuid4().hex
        sessions = request.execution.sessions or self.sessions
        last_error = None
        uncertain_code = {
            "chat": "chat_provider_uncertain",
            "embedding": "embedding_uncertain",
            "ocr": "ocr_provider_timeout",
            "rerank": "rerank_uncertain",
        }[capability]
        try:
            wait = capability in {"chat", "ocr"} and getattr(request, "wait_for_completion", False)
            async with asyncio.timeout(None if wait else request.timeout_seconds) as deadline:
                for attempt in range(3):
                    remaining = (
                        request.timeout_seconds
                        if wait
                        else (request.timeout_seconds - (time.monotonic() - started))
                    )
                    async with sessions() as db:
                        try:
                            lease = await acquire(
                                db,
                                request.execution,
                                capability,
                                request.endpoint,
                                request.model,
                                remaining,
                                excluded,
                            )
                        except AppException as exc:
                            if last_error is not None and exc.code == "provider_keys_unavailable":
                                raise last_error
                            raise
                    if lease.key_id:
                        excluded.add(lease.key_id)
                    failure, success, code = None, False, "cancelled"
                    budget_trace = {}
                    attempt_started, tokens = time.monotonic(), None
                    try:
                        live_request = replace(
                            request, api_key=lease.secret, timeout_seconds=remaining
                        )
                        if (
                            capability == "chat"
                            and lease.policy.retry_owner != "qnu"
                            and getattr(live_request, "automatic_output_budget", False)
                        ):
                            live_request = replace(live_request, automatic_output_budget=False)
                        if wait and lease.token:

                            async def renew(lease=lease, remaining=remaining):
                                async with sessions() as db:
                                    return await renew_key(db, lease, remaining)

                            async with maintain_lease(renew, max(0.01, (remaining + 10) / 3)):
                                result = await invoke(live_request)
                        else:
                            result = await invoke(live_request)
                        success, code = True, "ok"
                        budget_trace = getattr(result, "budget_trace", {})
                        tokens = getattr(
                            result, "total_tokens", getattr(result, "usage_tokens", None)
                        )
                        return result
                    except AppException as exc:
                        code = exc.code
                        tokens = getattr(exc, "usage_tokens", None)
                        failure = getattr(exc, "provider_failure", None)
                        if not (
                            isinstance(failure, ProviderFailure)
                            and failure.retryable_key
                            and lease.key_id is not None
                            and lease.policy.key_pool_enabled
                            and lease.policy.retry_owner == "qnu"
                            and attempt + 1 < lease.policy.max_key_attempts
                            and getattr(exc, "usage_tokens", None) in (None, 0)
                        ):
                            raise
                        last_error = exc
                    except asyncio.CancelledError:
                        code = uncertain_code if deadline.expired() else "cancelled"
                        raise
                    except Exception:
                        code = "execution_failed"
                        raise
                    finally:

                        async def release(
                            lease=lease,
                            code=code,
                            failure=failure,
                            success=success,
                            tokens=tokens,
                            attempt=attempt,
                            attempt_started=attempt_started,
                            budget_trace=budget_trace,
                        ):
                            async with sessions() as db:
                                await finish(
                                    db,
                                    lease,
                                    call_id=call_id,
                                    capability=capability,
                                    code=code,
                                    failure=failure,
                                    success=success,
                                    latency_ms=int((time.monotonic() - attempt_started) * 1000),
                                    attempt=attempt + 1,
                                    total_tokens=tokens,
                                    usage_id=request.execution.usage_id,
                                    budget_trace=budget_trace,
                                )

                        await asyncio.shield(release())
        except TimeoutError as exc:
            raise AppException(
                "Hết thời gian gọi model; không tự gửi lại.",
                code=uncertain_code,
                status_code=504,
            ) from exc


class ManagedChatModel:
    def __init__(self, adapter, executor=None):
        self.adapter, self.executor = adapter, executor or CredentialExecutor()
        self._output_limits: dict[tuple[str, str, str, str | None], tuple[float, int]] = {}

    async def complete(self, messages, request):
        recovered = False

        async def invoke(req):
            nonlocal recovered
            if not getattr(req, "automatic_output_budget", False) or req.execution is None:
                return await self.adapter.complete(messages, req)
            key = (req.execution.provider_id, req.endpoint, req.model, req.budget_identity)
            cached = self._output_limits.get(key)
            if cached and cached[0] > time.monotonic():
                req = replace(req, max_output_tokens=min(req.max_output_tokens, cached[1]))
            try:
                result = await self.adapter.complete(messages, req)
            except ChatResponseError as exc:
                limit = _reported_output_limit(exc, req.max_output_tokens)
                if limit is None or recovered:
                    raise
                recovered = True
                if len(self._output_limits) >= 256:
                    self._output_limits.pop(next(iter(self._output_limits)))
                self._output_limits[key] = (time.monotonic() + 600, limit)
                logger.info("chat_output_limit_observed", provider_id=key[0], limit=limit)
                req = replace(req, max_output_tokens=limit)
                result = await self.adapter.complete(messages, req)
            return replace(
                result,
                budget_trace={
                    "mode": "automatic",
                    "reserved_output_tokens": request.max_output_tokens,
                    "sent_output_tokens": req.max_output_tokens,
                    "observed_output_limit": req.max_output_tokens
                    if req.max_output_tokens < request.max_output_tokens
                    else None,
                },
            )

        return await self.executor.call("chat", request, invoke)


class ManagedOcrEngine:
    name = "ocr"

    def __init__(self, adapter, executor=None, *, document_adapter=None):
        self.adapter, self.executor = adapter, executor or CredentialExecutor()
        self.document_adapter = document_adapter

    async def extract_page(self, image_png, request):
        return await self.executor.call(
            "ocr", request, lambda req: self.adapter.extract_page(image_png, req)
        )

    async def extract_document(self, pdf, request, *, checkpoint, save, guard):
        if self.document_adapter is None:
            raise AppException(
                "Chưa cấu hình adapter OCR tài liệu ở composition root.",
                code="ocr_document_adapter_missing",
                status_code=503,
            )
        return await self.executor.call(
            "ocr",
            request,
            lambda req: self.document_adapter.extract_document(
                pdf, req, checkpoint=checkpoint, save=save, guard=guard
            ),
        )


class ManagedEmbeddingModel:
    def __init__(self, adapter, executor=None):
        self.adapter, self.executor = adapter, executor or CredentialExecutor()

    async def embed(self, texts, request):
        return await self.executor.call(
            "embedding", request, lambda req: self.adapter.embed(texts, req)
        )


class ManagedReranker:
    def __init__(self, adapter, executor=None):
        self.adapter, self.executor = adapter, executor or CredentialExecutor()

    async def rerank(self, query, documents, top_k, request):
        return await self.executor.call(
            "rerank", request, lambda req: self.adapter.rerank(query, documents, top_k, req)
        )
