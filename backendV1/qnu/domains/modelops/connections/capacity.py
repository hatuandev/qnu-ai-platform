"""Apply an admin-selected, current discovery snapshot without guessing absent limits."""

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.audit import record_event
from qnu.domains.modelops.capacity.schemas import ModelTokenLimits
from qnu.domains.modelops.capacity.service import read_capacity, set_capacity
from qnu.domains.modelops.connections.schemas import CapacitySyncRequest
from qnu.domains.modelops.diagnostics.schemas import DiagnosticCheck
from qnu.domains.modelops.diagnostics.service import read_diagnostics
from qnu.domains.modelops.embedding.configuration import read_dimension, set_dimension
from qnu.domains.modelops.models import Provider
from qnu.platform.errors import Conflict
from qnu.ports.provider_diagnostics import DiscoveredModel


async def current_discovery(
    db: AsyncSession, actor: AuthActor, parent: Provider, check_id: str
) -> DiagnosticCheck:
    checks = (await read_diagnostics(db, parent.id, actor)).checks
    latest = next((check for check in checks if check.kind == "discovery"), None)
    if (
        not parent.is_active
        or latest is None
        or latest.id != check_id
        or latest.outcome != "ok"
        or latest.configuration_status != "current"
    ):
        raise Conflict(
            "Danh sách model đã cũ; lấy lại trước khi áp dụng.", code="discovery_snapshot_stale"
        )
    return latest


async def cached_metadata(
    db: AsyncSession, actor: AuthActor, parent: Provider, model_name: str
) -> tuple[DiagnosticCheck, DiscoveredModel] | None:
    """Use only the latest successful, identity-matched snapshot; never send HTTP."""
    checks = (await read_diagnostics(db, parent.id, actor)).checks
    latest = next((check for check in checks if check.kind == "discovery"), None)
    if latest is None or latest.outcome != "ok" or latest.configuration_status != "current":
        return None
    row = next((item for item in latest.model_metadata if item.id == model_name), None)
    return (latest, row) if row else None


def metadata_for(check: DiagnosticCheck, model_name: str) -> DiscoveredModel:
    row = next((item for item in check.model_metadata if item.id == model_name), None)
    if row is None:
        raise Conflict(
            "Model không có trong kết quả lấy danh sách.", code="discovery_model_missing"
        )
    return row


def merge_limits(provider: Provider | None, row: DiscoveredModel) -> ModelTokenLimits | None:
    capacity = read_capacity(provider) if provider else None
    previous = capacity.token_limits if capacity and capacity.status == "configured" else None
    values = previous.model_dump() if previous else {}
    for field in ("context_window_tokens", "max_output_tokens"):
        if (value := getattr(row, field)) is not None:
            values[field] = value
    if not values:
        return None
    try:
        return ModelTokenLimits.model_validate(values)
    except ValidationError as exc:
        raise Conflict(
            "Giới hạn server mâu thuẫn cấu hình đã lưu; kiểm tra lại các giới hạn riêng.",
            code="discovery_capacity_conflict",
        ) from exc


def source_for(check: DiagnosticCheck, row: DiscoveredModel) -> dict:
    return {
        "check_id": check.id,
        "reported_at": check.tested_at.isoformat(),
        "metadata": row.model_dump(exclude_none=True),
    }


async def sync_capacity(
    db: AsyncSession, actor: AuthActor, connection_id: str, req: CapacitySyncRequest
) -> list[Provider]:
    from qnu.domains.modelops.connections.service import get_connection

    require_model_admin(actor)
    parent = await get_connection(db, connection_id, lock=True)
    check = await current_discovery(db, actor, parent, req.check_id)
    names = set(req.model_names)
    models = list(
        await db.scalars(
            select(Provider)
            .where(Provider.parent_id == parent.id, Provider.model_name.in_(names))
            .order_by(Provider.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    if len(models) != len(names):
        raise Conflict("Model không thuộc nhà cung cấp này.", code="discovery_model_missing")
    for model in models:
        apply_metadata(db, actor, model, parent, check)
    await db.commit()
    return models


def apply_metadata(
    db: AsyncSession, actor: AuthActor, model: Provider, parent: Provider, check: DiagnosticCheck
) -> None:
    if not model.is_active or model.base_url.rstrip("/") != parent.base_url.rstrip("/"):
        raise Conflict("Model đã đổi hoặc đang tắt.", code="discovery_model_changed")
    row = metadata_for(check, model.model_name)
    limits = merge_limits(model, row)
    dimension, _ = read_dimension(model)
    if row.embedding_dimension and "embedding" in model.capabilities:
        if dimension is not None and dimension != row.embedding_dimension:
            raise Conflict(
                "Số chiều embedding đã đổi; kiểm tra cấu hình/index trước khi áp dụng.",
                code="discovery_dimension_conflict",
            )
        set_dimension(model, row.embedding_dimension, basis="server_reported")
    source = source_for(check, row)
    state = read_capacity(model)
    if (
        (model.extra_config or {}).get("capacity_discovery_v1") == source
        and state.token_limits == limits
        and ("embedding" not in model.capabilities or row.embedding_dimension in (None, dimension))
    ):
        return
    if limits and (row.context_window_tokens or row.max_output_tokens):
        sources = {
            field: state.field_sources.get(field, state.basis or "operator_configured")
            for field in limits.model_dump(exclude_none=True)
        }
        for field in ("context_window_tokens", "max_output_tokens"):
            if getattr(row, field) is not None:
                sources[field] = "server_reported"
        set_capacity(model, limits, basis="server_reported", field_sources=sources)
    model.extra_config = {**(model.extra_config or {}), "capacity_discovery_v1": source}
    record_event(db, actor, "provider.capacity.synced", model.id, [check.id])
