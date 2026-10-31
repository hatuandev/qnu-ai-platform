"""One deadline and one retry owner; only definite 401/429 may rotate a key.

Provider/model never changes here. Existing domain reservations therefore cover
the actual target, and ambiguous failures are returned without spending twice.
"""

import asyncio
import time
import uuid
from dataclasses import replace

from qnu.domains.modelops.resilience.admission import chat_slot
from qnu.domains.modelops.resilience.key_pool import acquire, finish
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException
from qnu.ports.provider_execution import ProviderFailure


class CredentialExecutor:
    def __init__(self, sessions=AsyncSessionFactory):
        self.sessions = sessions

    async def call(self, capability, request, invoke):
        if capability == "chat":
            async with chat_slot(request):
                try:
                    async with asyncio.timeout(request.timeout_seconds):
                        return await self._call(capability, request, invoke)
                except TimeoutError as exc:
                    raise AppException(
                        "Hết thời gian gọi model; không tự gửi lại.",
                        code="chat_provider_uncertain", status_code=504,
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
            async with asyncio.timeout(request.timeout_seconds) as deadline:
                for attempt in range(3):
                    remaining = request.timeout_seconds - (time.monotonic() - started)
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
                    attempt_started, tokens = time.monotonic(), None
                    try:
                        result = await invoke(
                            replace(request, api_key=lease.secret, timeout_seconds=remaining)
                        )
                        success, code = True, "ok"
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

    async def complete(self, messages, request):
        return await self.executor.call(
            "chat", request, lambda req: self.adapter.complete(messages, req)
        )


class ManagedOcrEngine:
    name = "nemotron"

    def __init__(self, adapter, executor=None):
        self.adapter, self.executor = adapter, executor or CredentialExecutor()

    async def extract_page(self, image_png, request):
        return await self.executor.call(
            "ocr", request, lambda req: self.adapter.extract_page(image_png, req)
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
