"""Ordered availability fallback before a target/ledger is pinned, never mid-call."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.models import Provider, ProviderKey, WorkspaceAllowedProvider
from qnu.domains.modelops.registry import transport_for
from qnu.domains.modelops.resilience.key_pool import eligible
from qnu.domains.modelops.resilience.schemas import TASK_CAPABILITIES, Task
from qnu.domains.modelops.resilience.service import effective_policy
from qnu.platform.errors import Conflict, DependencyUnavailable, EntityNotFound


async def choose_target(
    db: AsyncSession, workspace_id: str, task: Task, provider_id: str | None
) -> tuple[str | None, tuple[dict, ...]]:
    # Explicit selection is a hard pin, including replay of a durable run.
    if provider_id is not None:
        return provider_id, ()
    capability = TASK_CAPABILITIES[task]
    primary = (await catalog_service.workspace_defaults(db, workspace_id)).get(capability)
    if primary is None:
        return None, ()  # Preserve the existing model_not_configured contract.
    if await db.get(WorkspaceAllowedProvider, (workspace_id, primary)) is None:
        raise EntityNotFound("Model chưa được cấp cho workspace.", code="provider_not_found")
    provider = await db.get(Provider, primary)
    if provider is None:
        raise EntityNotFound("Không tìm thấy model.", code="provider_not_found")
    candidates = effective_policy(provider).fallbacks.get(task, [])
    if not candidates:
        return primary, ()
    trace = []
    for pid in [primary, *candidates]:
        # Policies never grant permission. Do not disclose an ungranted candidate's ID.
        if await db.get(WorkspaceAllowedProvider, (workspace_id, pid)) is None:
            trace.append({"provider_id": None, "code": "candidate_not_granted"})
            continue
        row = await db.get(Provider, pid)
        if row is None or not row.is_active:
            trace.append({"provider_id": pid, "code": "provider_inactive"})
            continue
        if (
            capability not in row.capabilities
            or capability not in transport_for(row.provider_type).protocols
        ):
            raise Conflict(
                "Cấu hình model dự phòng không còn phù hợp.", code="fallback_capability_mismatch"
            )
        stmt = select(ProviderKey.id).where(
            ProviderKey.provider_id == pid, ProviderKey.status == "active"
        )
        if effective_policy(row).key_pool_enabled:
            stmt = stmt.where(*eligible(datetime.now(UTC)))
        has_key = await db.scalar(stmt.limit(1)) is not None
        if not has_key and not (
            capability == "ocr" and (row.extra_config or {}).get("ocr_auth_optional")
        ):
            trace.append({"provider_id": pid, "code": "keys_unavailable"})
            continue
        trace.append({"provider_id": pid, "code": "selected"})
        return pid, tuple(trace)
    raise DependencyUnavailable(
        "Không có model sẵn sàng trong chuỗi được phép.", code="fallback_exhausted"
    )
