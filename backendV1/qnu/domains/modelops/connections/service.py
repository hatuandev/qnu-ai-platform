"""Admin provider onboarding, independent from executable model/grant IDs."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.audit import record_event
from qnu.domains.modelops.connections.schemas import (
    ConnectionCreate,
    ConnectionModelCreate,
    ConnectionResponse,
    ConnectionUpdate,
)
from qnu.domains.modelops.diagnostics.schemas import DiagnosticCheck
from qnu.domains.modelops.diagnostics.service import HISTORY_KEY, configuration_identity
from qnu.domains.modelops.models import Provider, ProviderKey
from qnu.domains.modelops.providers.service import provider_service
from qnu.domains.modelops.schemas import ProviderCreateRequest
from qnu.domains.workspaces.access import actor_ref
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.platform.network_policy import assert_allowed_endpoint


async def get_connection(db: AsyncSession, connection_id: str, *, lock: bool = False) -> Provider:
    stmt = select(Provider).where(Provider.id == connection_id, Provider.is_connection.is_(True))
    if lock:
        stmt = stmt.with_for_update()
    row = await db.scalar(stmt.execution_options(populate_existing=True))
    if row is None:
        raise EntityNotFound("Không tìm thấy nhà cung cấp.", code="connection_not_found")
    return row


async def output(db: AsyncSession, rows: list[Provider]) -> list[ConnectionResponse]:
    ids = [p.id for p in rows]
    models = (
        (await db.scalars(select(Provider).where(Provider.parent_id.in_(ids)))).all() if ids else []
    )
    keys = (
        (
            await db.scalars(
                select(ProviderKey)
                .where(ProviderKey.provider_id.in_(ids))
                .order_by(ProviderKey.priority, ProviderKey.created_at)
            )
        ).all()
        if ids
        else []
    )
    result = []
    for row in rows:
        children = [m for m in models if m.parent_id == row.id]
        owned = [k for k in keys if k.provider_id == row.id]
        active = [k for k in owned if k.status == "active"]
        history = (row.extra_config or {}).get(HISTORY_KEY, [])
        status, tested_at = "untested", None
        if history:
            latest = history[0]
            check = DiagnosticCheck.model_validate(latest)
            status = (
                "stale"
                if latest.get("identity")
                != configuration_identity(row, active[0] if active else None)
                else ("success" if check.outcome == "ok" else check.outcome)
            )
            tested_at = check.tested_at
        family = (row.extra_config or {}).get("connection_family", "custom")
        result.append(
            ConnectionResponse(
                id=row.id,
                name=row.name,
                family=family,
                base_url=row.base_url,
                timeout_seconds=row.timeout_seconds,
                is_active=row.is_active,
                model_count=len(children),
                active_model_count=sum(m.is_active for m in children),
                active_keys_count=len(active),
                total_keys_count=len(owned),
                last_probe_status=status,
                last_probe_at=tested_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return result


async def list_connections(db: AsyncSession) -> list[ConnectionResponse]:
    rows = (
        await db.scalars(
            select(Provider)
            .where(Provider.is_connection.is_(True))
            .order_by(Provider.created_at, Provider.id)
        )
    ).all()
    return await output(db, list(rows))


async def save_connection(
    db: AsyncSession, actor: AuthActor, req: ConnectionCreate, connection_id: str | None = None
) -> ConnectionResponse:
    require_model_admin(actor)
    assert_allowed_endpoint(req.base_url, allow_private=True)
    row = await get_connection(db, connection_id, lock=True) if connection_id else None
    duplicate = await db.scalar(select(Provider.id).where(Provider.name == req.name))
    if duplicate and (row is None or duplicate != row.id):
        raise Conflict("Tên nhà cung cấp đã tồn tại.", code="provider_name_exists")
    if row is not None and row.base_url.rstrip("/") != req.base_url.rstrip("/"):
        child = await db.scalar(select(Provider.id).where(Provider.parent_id == row.id).limit(1))
        if child:
            raise Conflict(
                "Nhà cung cấp đã có model đang được tham chiếu; tạo kết nối mới khi đổi endpoint.",
                code="connection_endpoint_bound",
            )
    if row is None:
        row = Provider(
            id="conn_" + uuid.uuid4().hex[:16],
            is_connection=True,
            model_name="",
            capabilities=[],
            provider_type="openai_compatible",
            created_by=actor_ref(actor),
            extra_config={},
        )
        db.add(row)
    row.name, row.base_url, row.timeout_seconds = (
        req.name,
        req.base_url.rstrip("/"),
        req.timeout_seconds,
    )
    row.extra_config = {**(row.extra_config or {}), "connection_family": req.family}
    if isinstance(req, ConnectionUpdate):
        if req.is_active is not None:
            row.is_active = req.is_active
    else:
        row.is_active = True
    record_event(
        db,
        actor,
        "connection.updated" if connection_id else "connection.created",
        row.id,
        ["name", "family", "base_url", "is_active"],
    )
    await db.commit()
    return (await output(db, [row]))[0]


async def add_model(
    db: AsyncSession, actor: AuthActor, connection_id: str, req: ConnectionModelCreate
) -> Provider:
    require_model_admin(actor)
    parent = await get_connection(db, connection_id, lock=True)
    if not parent.is_active:
        raise Conflict("Nhà cung cấp đang tắt.", code="provider_inactive")
    existing = await db.scalar(
        select(Provider.id).where(
            Provider.parent_id == connection_id, Provider.model_name == req.model_name
        )
    )
    if existing:
        raise Conflict("Model đã được thêm vào nhà cung cấp.", code="model_already_registered")
    if not await db.scalar(
        select(ProviderKey.id)
        .where(
            ProviderKey.provider_id == parent.id,
            ProviderKey.status == "active",
            ProviderKey.model_ids.is_(None),
        )
        .limit(1)
    ):
        raise Conflict(
            "Thêm API key dùng chung tại nhà cung cấp trước khi thêm model; khóa cũ giữ phạm vi model ban đầu.",
            code="connection_key_required",
        )
    # ProviderCreateRequest applies existing capability/capacity validations.
    model = await provider_service.create(
        db,
        ProviderCreateRequest(
            name=f"{parent.name} · {req.model_name}",
            base_url=parent.base_url,
            provider_type="openai_compatible",
            model_name=req.model_name,
            capabilities=req.capabilities,
            timeout_seconds=parent.timeout_seconds,
            token_limits=req.token_limits,
            embedding_dimension=req.embedding_dimension,
        ),
        actor,
        parent_id=parent.id,
    )
    return model


async def list_models(db: AsyncSession, connection_id: str):
    await get_connection(db, connection_id)
    return list(
        (
            await db.scalars(
                select(Provider).where(Provider.parent_id == connection_id).order_by(Provider.name)
            )
        ).all()
    )
