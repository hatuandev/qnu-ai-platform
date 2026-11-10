"""Admin provider onboarding, independent from executable model/grant IDs."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.audit import record_event
from qnu.domains.modelops.connections.schemas import (
    ConnectionCreate,
    ConnectionModelCreate,
    ConnectionResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    ConnectionUpdate,
)
from qnu.domains.modelops.diagnostics.schemas import DiagnosticCheck
from qnu.domains.modelops.diagnostics.service import HISTORY_KEY, history_current
from qnu.domains.modelops.models import Provider, ProviderKey
from qnu.domains.modelops.providers.service import provider_service
from qnu.domains.modelops.schemas import ProviderCreateRequest
from qnu.domains.workspaces.access import actor_ref
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.platform.network_policy import assert_allowed_endpoint
from qnu.ports.provider_diagnostics import ProviderDiagnosticClient


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
                if not history_current(row, latest, active)
                else ("success" if check.outcome == "ok" else check.outcome)
            )
            tested_at = check.tested_at
        extra = row.extra_config or {}
        family = extra.get("connection_family", "custom")
        prefix = extra.get("prefix")
        api_type = extra.get("api_type") or (
            "anthropic" if family == "anthropic" else "openai_compatible"
        )
        result.append(
            ConnectionResponse(
                id=row.id,
                name=row.name,
                family=family,
                base_url=row.base_url,
                timeout_seconds=row.timeout_seconds,
                is_active=row.is_active,
                prefix=prefix,
                api_type=api_type,
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
    db: AsyncSession,
    actor: AuthActor,
    req: ConnectionCreate | ConnectionUpdate,
    connection_id: str | None = None,
) -> ConnectionResponse:
    require_model_admin(actor)
    if req.base_url:
        assert_allowed_endpoint(req.base_url, allow_private=True)
    row = await get_connection(db, connection_id, lock=True) if connection_id else None
    if req.name is not None:
        duplicate = await db.scalar(select(Provider.id).where(Provider.name == req.name))
        if duplicate and (row is None or duplicate != row.id):
            raise Conflict("Tên nhà cung cấp đã tồn tại.", code="provider_name_exists")
    if (
        row is not None
        and req.base_url is not None
        and row.base_url.rstrip("/") != req.base_url.rstrip("/")
    ):
        child = await db.scalar(select(Provider.id).where(Provider.parent_id == row.id).limit(1))
        if child:
            raise Conflict(
                "Nhà cung cấp đã có model đang được tham chiếu; tạo kết nối mới khi đổi endpoint.",
                code="connection_endpoint_bound",
            )
    if row is None:
        if req.name is None or req.base_url is None:
            raise Conflict("Tên và địa chỉ API không được để trống.", code="invalid_input")
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

    if req.name is not None:
        row.name = req.name
    if req.base_url is not None:
        row.base_url = req.base_url.rstrip("/")
    if req.timeout_seconds is not None:
        row.timeout_seconds = req.timeout_seconds

    current_extra = dict(row.extra_config or {})
    if req.api_type is not None:
        api_type = req.api_type.strip()
        target_type = "mineru" if api_type == "mineru" else "openai_compatible"
        if target_type != row.provider_type and connection_id:
            child = await db.scalar(
                select(Provider.id).where(Provider.parent_id == row.id).limit(1)
            )
            if child:
                raise Conflict(
                    "Kết nối đã có model; tạo kết nối mới khi đổi giao thức.",
                    code="connection_endpoint_bound",
                )
        row.provider_type = target_type
    if req.family is not None:
        current_extra["connection_family"] = req.family
    if req.prefix is not None:
        current_extra["prefix"] = req.prefix
    if req.api_type is not None:
        current_extra["api_type"] = req.api_type
    row.extra_config = current_extra

    if isinstance(req, ConnectionUpdate) and req.is_active is not None:
        row.is_active = req.is_active
    elif connection_id is None:
        row.is_active = True

    record_event(
        db,
        actor,
        "connection.updated" if connection_id else "connection.created",
        row.id,
        ["name", "family", "base_url", "is_active", "prefix", "api_type"],
    )
    await db.commit()
    return (await output(db, [row]))[0]


async def _provider_references(db: AsyncSession, ids: set[str]) -> list[str]:
    from qnu.domains.assistants.models import Assistant
    from qnu.domains.knowledge.compilation.models import CompilationRun
    from qnu.domains.knowledge.compilation.review.models import CompilationReview
    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.domains.modelops.models import (
        ModelDefaults,
        ModelUsageRecord,
        WorkspaceAllowedProvider,
        WorkspaceModelDefault,
    )

    default_columns = (
        ModelDefaults.chat_provider_id,
        ModelDefaults.embedding_provider_id,
        ModelDefaults.rerank_provider_id,
        ModelDefaults.ocr_provider_id,
    )
    checks = (
        (
            "cấu hình mặc định hệ thống",
            select(ModelDefaults.id).where(
                or_(*(column.in_(ids) for column in default_columns))
            ),
        ),
        (
            "cấu hình mặc định của đơn vị",
            select(WorkspaceModelDefault.workspace_id).where(
                WorkspaceModelDefault.provider_id.in_(ids)
            ),
        ),
        (
            "quyền sử dụng model của đơn vị",
            select(WorkspaceAllowedProvider.workspace_id).where(
                WorkspaceAllowedProvider.provider_id.in_(ids)
            ),
        ),
        ("trợ lý", select(Assistant.id).where(Assistant.chat_provider_id.in_(ids))),
        ("lịch sử lập chỉ mục", select(IndexRun.id).where(IndexRun.provider_id.in_(ids))),
        (
            "lịch sử biên soạn",
            select(CompilationRun.id).where(CompilationRun.provider_id.in_(ids)),
        ),
        (
            "lịch sử phản biện",
            select(CompilationReview.id).where(CompilationReview.provider_id.in_(ids)),
        ),
        (
            "lịch sử sử dụng model",
            select(ModelUsageRecord.id).where(ModelUsageRecord.provider_id.in_(ids)),
        ),
    )
    return [
        label
        for label, statement in checks
        if await db.scalar(statement.limit(1)) is not None
    ]


async def _require_unreferenced(db: AsyncSession, ids: set[str]) -> None:
    references = await _provider_references(db, ids)
    if references:
        raise Conflict(
            "Không thể xóa model/nhà cung cấp đang được tham chiếu: "
            + ", ".join(references)
            + ". Hãy chuyển cấu hình, trợ lý và quyền sử dụng sang model khác trước.",
            code="model_provider_in_use",
        )


async def delete_connection(db: AsyncSession, actor: AuthActor, connection_id: str) -> None:
    require_model_admin(actor)
    row = await get_connection(db, connection_id, lock=True)
    # Delete child models
    child_ids = list((await db.scalars(select(Provider.id).where(Provider.parent_id == connection_id))).all())
    await _require_unreferenced(db, {connection_id, *child_ids})
    for cid in child_ids:
        child = await db.get(Provider, cid)
        if child:
            await db.delete(child)
    # Delete keys
    keys = list((await db.scalars(select(ProviderKey).where(ProviderKey.provider_id == connection_id))).all())
    for k in keys:
        await db.delete(k)
    # Delete connection itself
    await db.delete(row)
    record_event(db, actor, "connection.deleted", connection_id, ["deleted"])
    await db.commit()


async def _shared_key_id(db: AsyncSession, connection_id: str) -> str | None:
    return await db.scalar(
        select(ProviderKey.id)
        .where(
            ProviderKey.provider_id == connection_id,
            ProviderKey.status == "active",
            ProviderKey.model_ids.is_(None),
        )
        .order_by(ProviderKey.priority, ProviderKey.created_at, ProviderKey.id)
        .limit(1)
    )


async def add_model(
    db: AsyncSession,
    actor: AuthActor,
    connection_id: str,
    req: ConnectionModelCreate,
    *,
    client: ProviderDiagnosticClient | None = None,
) -> Provider:
    require_model_admin(actor)
    if (
        client is not None
        and req.discovery_check_id is None
        and req.token_limits is None
        and req.embedding_dimension is None
    ):
        from qnu.domains.modelops.connections.capacity import cached_metadata

        parent = await get_connection(db, connection_id)
        if (
            parent.is_active
            and parent.provider_type != "mineru"
            and (key_id := await _shared_key_id(db, connection_id)) is not None
            and not await cached_metadata(db, actor, parent, req.model_name)
        ):
            await test_connection(
                db, actor, connection_id, ConnectionTestRequest(key_id=key_id), client
            )
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
    if await _shared_key_id(db, parent.id) is None:
        raise Conflict(
            "Thêm API key dùng chung tại nhà cung cấp trước khi thêm model; khóa cũ giữ phạm vi model ban đầu.",
            code="connection_key_required",
        )
    limits, dimension, basis, source = (
        req.token_limits,
        req.embedding_dimension,
        "operator_configured",
        None,
    )
    if parent.provider_type != "mineru" and (
        req.discovery_check_id or (limits is None and dimension is None)
    ):
        from qnu.domains.modelops.connections.capacity import (
            cached_metadata,
            current_discovery,
            merge_limits,
            metadata_for,
            source_for,
        )

        cached = None
        if req.discovery_check_id:
            check = await current_discovery(db, actor, parent, req.discovery_check_id)
            cached = check, metadata_for(check, req.model_name)
        else:
            cached = await cached_metadata(db, actor, parent, req.model_name)
        if cached:
            check, metadata = cached
            limits = merge_limits(None, metadata)
            dimension = metadata.embedding_dimension if "embedding" in req.capabilities else None
            basis, source = "server_reported", source_for(check, metadata)
    # ProviderCreateRequest applies existing capability/capacity validations.
    model = await provider_service.create(
        db,
        ProviderCreateRequest(
            name=f"{parent.name} · {req.model_name}",
            base_url=parent.base_url,
            provider_type=parent.provider_type
            if parent.provider_type == "mineru"
            else "openai_compatible",
            model_name=req.model_name,
            capabilities=req.capabilities,
            timeout_seconds=parent.timeout_seconds,
            token_limits=limits,
            embedding_dimension=dimension,
        ),
        actor,
        parent_id=parent.id,
        capacity_basis=basis,
        capacity_source=source,
    )
    return model


async def delete_model(
    db: AsyncSession, actor: AuthActor, connection_id: str, model_id: str
) -> None:
    require_model_admin(actor)
    await get_connection(db, connection_id, lock=True)
    model = (await db.scalars(
        select(Provider).where(Provider.id == model_id, Provider.parent_id == connection_id)
    )).first()
    if model is None:
        raise EntityNotFound("Không tìm thấy model trong nhà cung cấp này.", code="model_not_found")
    await _require_unreferenced(db, {model.id})
    await db.delete(model)
    record_event(db, actor, "model.deleted", model_id, ["deleted"])
    await db.commit()


async def delete_key(
    db: AsyncSession, actor: AuthActor, connection_id: str, key_id: str
) -> None:
    require_model_admin(actor)
    await get_connection(db, connection_id, lock=True)
    key = (await db.scalars(
        select(ProviderKey).where(ProviderKey.id == key_id, ProviderKey.provider_id == connection_id)
    )).first()
    if key is None:
        raise EntityNotFound("Không tìm thấy API key.", code="key_not_found")
    await db.delete(key)
    record_event(db, actor, "key.deleted", key_id, ["deleted"])
    await db.commit()


async def list_models(db: AsyncSession, connection_id: str):
    await get_connection(db, connection_id)
    return list(
        (
            await db.scalars(
                select(Provider).where(Provider.parent_id == connection_id).order_by(Provider.name)
            )
        ).all()
    )


async def test_connection(
    db: AsyncSession,
    actor: AuthActor,
    connection_id: str,
    req: ConnectionTestRequest,
    client: ProviderDiagnosticClient | None = None,
) -> ConnectionTestResponse:
    from qnu.adapters.providers.diagnostics import HttpProviderDiagnosticClient
    from qnu.domains.modelops.connections.testing import run_test

    require_model_admin(actor)
    parent = await get_connection(db, connection_id)
    return await run_test(db, actor, parent, req, client or HttpProviderDiagnosticClient())
