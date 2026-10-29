"""Execute one durable compilation: reauthorize, call once, retain raw, validate draft."""

from __future__ import annotations

import asyncio
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation.artifacts import artifact, json_bytes, read, store
from qnu.domains.knowledge.compilation.drafting import (
    SYSTEM_PROMPT,
    build_draft,
    markdown_for,
    messages_for,
    output_schema,
)
from qnu.domains.knowledge.compilation.evidence import load_bound_documents
from qnu.domains.knowledge.compilation.lease import (
    ClaimLost,
    assert_claim,
    claim,
    commit_owned,
    heartbeat,
)
from qnu.domains.knowledge.compilation.models import CompilationInput, CompilationRun, utcnow
from qnu.domains.knowledge.compilation.service import authorize_collection
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.usage.service import usage_service
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel, ChatResponseError
from qnu.ports.provider_execution import bind_usage

logger = get_logger(__name__)


async def finish(
    db: AsyncSession, run: CompilationRun, status: str, code: str | None = None
) -> str:
    await assert_claim(db, run)
    if status == "completed":
        from qnu.domains.knowledge.compilation.workflow.automatic import schedule

        await schedule(db, run)
    run.status, run.error_code, run.finished_at = status, code, utcnow()
    run.lease_expires_at = None
    await commit_owned(db, run)
    logger.info(
        "compilation_finished",
        run_id=run.id,
        workspace_id=run.workspace_id,
        provider_id=run.provider_id,
        status=status,
        error_code=code,
        usage_tokens=run.usage_tokens,
    )
    return status


async def _inputs(db: AsyncSession, blob: BlobStore, run: CompilationRun) -> list[dict]:
    bindings = list(
        (
            await db.scalars(
                select(CompilationInput).where(
                    CompilationInput.run_id == run.id,
                )
            )
        ).all()
    )
    documents = await load_bound_documents(
        db,
        blob,
        run.workspace_id,
        run.collection_id,
        bindings,
    )
    _, original = await read(db, blob, run, "input_snapshot")
    snapshot = {
        "schema_version": "qnu.compiler.input/v1",
        "topic": run.topic,
        "documents": documents,
    }
    if (
        hashlib.sha256(original).hexdigest() != run.input_sha256
        or json_bytes(snapshot) != original
        or any(
            (b.canonical_sha256, b.manifest_sha256)
            != (
                next(d for d in documents if d["ocr_run_id"] == b.ocr_run_id)["canonical_sha256"],
                next(d for d in documents if d["ocr_run_id"] == b.ocr_run_id)["manifest_sha256"],
            )
            for b in bindings
        )
    ):
        raise Conflict("Nguồn đã khác snapshot Compiler.", code="compilation_source_mismatch")
    return documents


async def _settle(
    db: AsyncSession, run: CompilationRun, tokens: int | None, *, failed: bool = False
) -> None:
    if run.usage_id is not None:
        await usage_service.settle(db, run.usage_id, total_tokens=tokens, failed=failed)


async def _compile(db: AsyncSession, blob: BlobStore, run: CompilationRun, model: ChatModel) -> str:
    actor = background_actor(run.requested_by)
    await authorize_collection(db, actor, run.workspace_id, run.collection_id, write=True)
    documents = await _inputs(db, blob, run)
    existing_raw = await artifact(db, run.id, "raw_response")
    if run.request_started_at is not None and existing_raw is None:
        await _settle(db, run, None, failed=True)
        return await finish(db, run, "uncertain", "compilation_request_interrupted")
    if run.attempt_count > 3:
        return await finish(db, run, "failed", "compilation_attempts_exhausted")
    if existing_raw is not None:
        _, payload = await read(db, blob, run, "raw_response")
        try:
            content = json.loads(payload)["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AppException("Raw chat không đọc được.", code="compilation_raw_invalid") from exc
        await _settle(db, run, run.usage_tokens)
    else:
        content = await _call(db, blob, run, actor, documents, model)
    draft = build_draft(content, run.topic, documents, run.id)
    await assert_claim(db, run)
    await store(db, blob, run, "draft_json", json_bytes(draft))
    await store(db, blob, run, "markdown", markdown_for(draft).encode("utf-8"))
    await commit_owned(db, run)
    return await finish(db, run, "completed")


async def _call(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    actor: AuthActor,
    documents: list[dict],
    model: ChatModel,
) -> str:
    messages = messages_for(run.topic, documents)
    schema = output_schema(documents) if run.config.get("structured_output") else None
    runtime, request, budget = await prepare_chat_request(
        db,
        actor,
        run.workspace_id,
        messages,
        provider_id=run.provider_id,
        max_output_tokens=run.config["max_output_tokens"],
        output_schema=schema,
    )
    if (
        runtime.configuration_hash != run.config["provider"]["configuration_hash"]
        or hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest() != run.config["prompt_sha256"]
        or (
            schema is not None
            and hashlib.sha256(json_bytes(schema)).hexdigest()
            != run.config.get("output_schema_sha256")
        )
    ):
        raise Conflict(
            "Model hoặc prompt đã đổi so với yêu cầu.", code="compilation_provider_changed"
        )
    await assert_claim(db, run)
    usage = await usage_service.reserve(
        db,
        actor,
        run.workspace_id,
        "chat",
        f"compile:{run.id}",
        run.request_hash,
        budget.total_reserved_tokens,
        run.provider_id,
    )
    await assert_claim(db, run)
    run.usage_id, run.request_started_at = usage.id, utcnow()
    await commit_owned(db, run)
    try:
        result = await model.complete(messages, bind_usage(request, usage.id))
    except ChatResponseError as exc:
        try:
            await assert_claim(db, run)
        except ClaimLost:
            await _settle(db, run, exc.usage_tokens, failed=True)
            raise
        await store(db, blob, run, "raw_response", exc.raw_body)
        run.usage_tokens = exc.usage_tokens
        # The raw reply may be diagnostic but must never later become a draft.
        run.config = {**run.config, "response_error_code": exc.code}
        await commit_owned(db, run)
        await _settle(db, run, exc.usage_tokens, failed=True)
        raise
    except AppException:
        await _settle(db, run, None, failed=True)
        raise
    try:
        await assert_claim(db, run)
    except ClaimLost:
        await _settle(db, run, result.total_tokens, failed=True)
        raise
    await store(db, blob, run, "raw_response", result.raw_body)
    run.usage_tokens = result.total_tokens
    await commit_owned(db, run)
    await _settle(db, run, result.total_tokens)
    return result.content


async def execute_run(
    db: AsyncSession,
    blob: BlobStore,
    run_id: str,
    *,
    worker_id: str,
    model: ChatModel,
) -> str:
    seconds = get_settings().COMPILER_LEASE_SECONDS
    run = await claim(db, run_id, worker_id, seconds)
    if run is None:
        return "not_claimed"
    token = run.worker_id
    async with heartbeat(run, seconds):
        try:
            if run.config.get("response_error_code"):
                return await finish(db, run, "failed", run.config["response_error_code"])
            return await _compile(db, blob, run, model)
        except ClaimLost:
            await db.rollback()
            return "not_claimed"
        except asyncio.CancelledError:
            # Persisted in-flight marker is reconciled to uncertain; never resend.
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            run = await db.get(CompilationRun, run_id, populate_existing=True)
            if run is None or run.worker_id != token:
                return "not_claimed"
            code = exc.code if isinstance(exc, AppException) else "compilation_failed"
            try:
                raw = await artifact(db, run.id, "raw_response")
                uncertain = code == "chat_provider_uncertain" or (
                    run.request_started_at is not None
                    and raw is None
                    and code not in {"chat_provider_unreachable"}
                )
                return await finish(db, run, "uncertain" if uncertain else "failed", code)
            except ClaimLost:
                await db.rollback()
                return "not_claimed"
