"""Observed dependency/configuration readiness, explicitly separate from live inference."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.embedding.runtime import resolve_embedding_runtime
from qnu.domains.modelops.public_api import resolve_chat_runtime, resolve_ocr_runtime
from qnu.domains.modelops.usage.service import month_start, usage_service
from qnu.domains.operations import service
from qnu.domains.operations.recovery.service import HEAD
from qnu.platform.errors import AppException

if TYPE_CHECKING:
    from qnu.api.wiring import Container


async def inspect(
    db: AsyncSession, actor: AuthActor, workspace_id: str, container: Container
) -> dict:
    await service.authorize(db, actor, workspace_id, admin=True)
    head = await db.scalar(text("SELECT version_num FROM alembic_version_backendv1"))
    checks = {"database": {"ok": head == HEAD, "schema_head": head}}
    quota = await usage_service.read_quota(db, actor, workspace_id, month_start())
    remaining = (
        max(0, quota.monthly_token_limit - quota.tokens_used - quota.tokens_reserved)
        if quota is not None and quota.monthly_token_limit is not None
        else None
    )
    checks["quota"] = {
        "ok": quota is not None and not quota.is_blocked and (remaining is None or remaining > 0),
        "configured": quota is not None,
        "remaining_tokens": remaining,
        "blocked": quota.is_blocked if quota is not None else None,
    }
    for name, adapter in [("queue", container.job_queue), ("vector", container.vector_store)]:
        try:
            health = getattr(adapter, "health", None)
            value = await health() if health else {"ok": False, "code": "probe_not_supported"}
            checks[name] = value
        except AppException as exc:
            checks[name] = {"ok": False, "code": exc.code}
    checks["worker"] = {"ok": checks["queue"].get("worker_schema_head") == HEAD}
    for name, resolver in [
        ("ocr", resolve_ocr_runtime),
        ("chat", resolve_chat_runtime),
        ("embedding", resolve_embedding_runtime),
    ]:
        try:
            runtime = await resolver(db, workspace_id)
            checks[name] = {
                "ok": runtime.capacity_status == "configured",
                "provider_id": runtime.provider_id,
                "model": runtime.model_name,
                "inference_verified": False,
            }
        except AppException as exc:
            checks[name] = {"ok": False, "code": exc.code, "inference_verified": False}
    # Read a pinned object if one exists. A configured driver is not an observed IO probe.
    import hashlib

    from qnu.domains.knowledge.models import KBSourceRevision

    source = await db.scalar(
        select(KBSourceRevision).where(KBSourceRevision.workspace_id == workspace_id).limit(1)
    )
    checks["storage"] = {"ok": False, "code": "no_source_to_probe"}
    if source:
        try:
            value = await container.blob_store.get_bytes(source.storage_key)
            checks["storage"] = {
                "ok": hashlib.sha256(value).hexdigest() == source.sha256,
                "probe": "pinned_source_read",
            }
        except Exception:
            checks["storage"] = {"ok": False, "code": "storage_unavailable"}
    return {
        "scope": "dependency_and_modelops_configuration",
        "ready": all(item["ok"] for item in checks.values()),
        "checks": checks,
        "live_inference_verified": False,
        "production_auth_configured": not container.settings.DEV_AUTH_ENABLED
        and container.settings.SSO_ENABLED,
        "reconcile_enabled": container.settings.OWN_RECONCILE,
    }
