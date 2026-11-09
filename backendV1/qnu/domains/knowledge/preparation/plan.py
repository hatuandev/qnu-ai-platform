"""Preparation contract: idempotency hashes, compiler flags and pinned AI policy."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import CompilationRun
from qnu.domains.knowledge.preparation.models import PreparationIntent
from qnu.domains.knowledge.preparation.schemas import PreparationRequest
from qnu.domains.modelops.public_api import (
    OPTIONAL_CHAT_UNAVAILABLE_CODES,
    assert_provider_allowed,
    resolve_chat_runtime,
)
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.platform.errors import AppException, Conflict, DependencyUnavailable

POLICY_VERSION = "qnu.preparation.auto/v1"
REUSE_VERSION = "qnu.preparation.reuse/v1"
AI_UNAVAILABLE_CODES = frozenset(
    {"chat_credentials_missing", "chat_credentials_unreadable", "provider_keys_unavailable"}
)


def request_hash(
    collection_id: str,
    source_id: str,
    revision_id: str,
    req: PreparationRequest,
    topic: str,
    mode: str | None = None,
) -> str:
    material = {
        "version": 1,
        "collection_id": collection_id,
        "source_id": source_id,
        "revision_id": revision_id,
        "mode": mode or req.mode,
        "ocr_run_id": req.ocr_run_id,
        "text_version": req.text_version,
        "topic": topic,
        "provider_id": req.provider_id,
        "max_output_tokens": req.max_output_tokens,
    }
    return hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def plan_flags(mode: str, policy: dict | None) -> dict:
    """The single mapping from preparation mode + pinned policy to compiler flags."""
    if mode == "ai":
        return {
            "source_first": False,
            "ai_supplement": True,
            "selective_supplement": False,
            "auto_review": False,
        }
    if mode == "auto" and (policy or {}).get("supplement") == "selective":
        return {
            "source_first": False,
            "ai_supplement": False,
            "selective_supplement": True,
            "auto_review": False,
        }
    return {
        "source_first": True,
        "ai_supplement": False,
        "selective_supplement": False,
        "auto_review": False,
    }


async def _resolve_auto_policy(
    db: AsyncSession, workspace_id: str, provider_id: str
) -> dict:
    """Pin one safe policy: selective source supplement when chat is usable, else source."""
    policy = {
        "version": POLICY_VERSION,
        "supplement": "disabled",
        "reason": None,
        "provider_id": provider_id,
    }
    try:
        runtime = await resolve_chat_runtime(db, workspace_id, provider_id)
    except AppException as exc:
        if exc.code not in OPTIONAL_CHAT_UNAVAILABLE_CODES:
            raise
        policy["reason"] = exc.code
        return policy
    policy.update(
        {
            "supplement": "selective",
            "configuration_hash": runtime.inference_configuration_hash("compiler"),
            "provider_name": runtime.provider_name,
            "model_name": runtime.model_name,
        }
    )
    return policy


async def auto_policy(
    db: AsyncSession, actor: AuthActor, workspace_id: str
) -> tuple[dict, str | None]:
    """Pin the automatic policy without blocking on optional AI configuration."""
    try:
        provider = await assert_provider_allowed(db, actor, workspace_id, "chat", None)
    except AppException as exc:
        if exc.code not in OPTIONAL_CHAT_UNAVAILABLE_CODES:
            raise
        return {
            "version": POLICY_VERSION,
            "supplement": "disabled",
            "reason": exc.code,
            "provider_id": None,
        }, None
    return await _resolve_auto_policy(db, workspace_id, provider.id), provider.id


async def verify_auto_policy(
    db: AsyncSession, intent: PreparationIntent, workspace_id: str
) -> None:
    """Honor the pinned policy; never swap model silently or reuse an old cache."""
    policy = dict(intent.config.get("policy") or {})
    if policy.get("supplement") != "selective":
        return
    try:
        runtime = await resolve_chat_runtime(db, workspace_id, intent.provider_id)
    except DependencyUnavailable as exc:
        if exc.code not in AI_UNAVAILABLE_CODES:
            raise
        policy.update({"supplement": "disabled", "reason": exc.code})
        intent.config = {
            **intent.config,
            **plan_flags("auto", policy),
            "policy": policy,
        }
        await db.commit()
        return
    if runtime.inference_configuration_hash("compiler") != policy.get("configuration_hash"):
        raise Conflict(
            "Model hoặc chính sách đã thay đổi từ lúc tạo yêu cầu; hãy chuẩn bị lại.",
            code="preparation_policy_changed",
        )


def reuse_key(intent: PreparationIntent, run: OcrProcessingRun) -> str:
    policy = intent.config.get("policy") or {}
    material = {
        "version": REUSE_VERSION,
        "workspace_id": intent.workspace_id,
        "collection_id": intent.collection_id,
        "source_id": intent.source_id,
        "revision_id": intent.revision_id,
        "revision_sha256": intent.revision_sha256,
        "ocr_run_id": run.id,
        "ocr_config_fingerprint": run.config_fingerprint,
        "text_version": intent.text_version,
        "text_version_id": intent.text_version_id,
        "text_canonical_sha256": intent.text_canonical_sha256,
        "topic": intent.topic,
        "policy_version": policy.get("version"),
        "provider_id": intent.provider_id,
        "configuration_hash": policy.get("configuration_hash"),
        "supplement": policy.get("supplement"),
    }
    return hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


async def reusable_compilation(
    db: AsyncSession, intent: PreparationIntent, key: str
) -> CompilationRun | None:
    return await db.scalar(
        select(CompilationRun)
        .where(
            CompilationRun.workspace_id == intent.workspace_id,
            CompilationRun.collection_id == intent.collection_id,
            CompilationRun.config["reuse_key"].as_string() == key,
            CompilationRun.status.in_(("queued", "running", "completed")),
        )
        .order_by(CompilationRun.requested_at.desc())
        .limit(1)
    )
