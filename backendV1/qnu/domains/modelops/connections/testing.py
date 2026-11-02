"""Exact-key discovery with the shared diagnostic adapter and safe history."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.audit import record_event
from qnu.domains.modelops.connections.schemas import ConnectionTestRequest, ConnectionTestResponse
from qnu.domains.modelops.diagnostics.schemas import DiagnosticCheck
from qnu.domains.modelops.diagnostics.service import HISTORY_KEY, configuration_identity
from qnu.domains.modelops.models import Provider, ProviderKey
from qnu.platform.crypto import decrypt
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.ports.provider_diagnostics import (
    DiagnosticResult,
    DiagnosticTarget,
    ProviderDiagnosticClient,
)


async def selected_key(
    db: AsyncSession, connection_id: str, key_id: str | None
) -> ProviderKey | None:
    stmt = select(ProviderKey).where(ProviderKey.provider_id == connection_id)
    stmt = (
        stmt.where(ProviderKey.id == key_id)
        if key_id
        else stmt.where(ProviderKey.status == "active")
    )
    key = (
        await db.scalars(
            stmt.order_by(ProviderKey.priority, ProviderKey.created_at, ProviderKey.id)
            .limit(1)
            .execution_options(populate_existing=True)
        )
    ).first()
    if key_id and key is None:
        raise EntityNotFound(
            "Không tìm thấy khóa trong nhà cung cấp này.", code="provider_key_not_found"
        )
    if key and key.status != "active":
        raise Conflict("Khóa không hoạt động; không gửi yêu cầu thử.", code="provider_key_inactive")
    return key


async def run_test(
    db: AsyncSession,
    actor: AuthActor,
    parent: Provider,
    req: ConnectionTestRequest,
    client: ProviderDiagnosticClient,
) -> ConnectionTestResponse:
    if not parent.is_active:
        raise Conflict(
            "Nhà cung cấp đang tắt; bật lại trước khi kiểm tra.", code="provider_inactive"
        )
    key = None if req.api_key else await selected_key(db, parent.id, req.key_id)
    fingerprint = configuration_identity(parent, key)
    key_id = key.id if key else None
    secret = req.api_key
    credential_error = False
    if key:
        try:
            secret = decrypt(key.secret_encrypted)
        except AppException:
            credential_error = True
    extra = parent.extra_config or {}
    auth_scheme = (
        "anthropic"
        if (extra.get("api_type") or extra.get("connection_family")) == "anthropic"
        else "bearer"
    )
    target = DiagnosticTarget(
        parent.base_url,
        "",
        parent.provider_type,
        parent.timeout_seconds,
        api_key=secret,
        auth_scheme=auth_scheme,
    )
    await db.commit()  # Release read transaction before upstream I/O.
    result = (
        DiagnosticResult("failed", "credentials_unreadable", "Không đọc được khóa đã lưu.")
        if credential_error
        else await client.check("ocr" if parent.provider_type == "mineru" else "discovery", target)
    )
    check = DiagnosticCheck(
        id="diag_" + uuid.uuid4().hex[:16],
        key_id=key_id,
        kind="ocr" if parent.provider_type == "mineru" else "discovery",
        outcome=result.outcome,
        tested_at=datetime.now(UTC),
        latency_ms=result.latency_ms,
        code=result.code,
        detail=result.detail,
        http_status=result.http_status,
        retry_after=result.retry_after,
        requested_model="",
        models=result.models,
        model_metadata=result.model_metadata,
    )
    current = (
        await db.execute(
            select(Provider)
            .where(Provider.id == parent.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    current_key = await selected_key(db, parent.id, key_id) if key_id else None
    if (
        current is None
        or not current.is_active
        or configuration_identity(current, current_key) != fingerprint
    ):
        await db.rollback()
        raise Conflict(
            "Cấu hình/khóa đã đổi trong lúc thử; hãy chạy lại.",
            code="diagnostic_configuration_changed",
        )
    if not req.api_key:
        current.extra_config = {
            **(current.extra_config or {}),
            HISTORY_KEY: [
                {**check.model_dump(mode="json"), "identity": fingerprint},
                *(current.extra_config or {}).get(HISTORY_KEY, []),
            ][:20],
        }
        record_event(
            db, actor, "provider.diagnostic.discovery", parent.id, [check.code, key_id or "no_key"]
        )
        await db.commit()
    return ConnectionTestResponse(
        ok=result.outcome == "ok",
        key_id=key_id,
        check_id=check.id if not req.api_key else None,
        tested_at=check.tested_at,
        code=result.code,
        detail=result.detail,
        http_status=result.http_status,
        retry_after=result.retry_after,
        latency_ms=result.latency_ms,
        models=result.models,
        model_metadata=result.model_metadata,
    )
