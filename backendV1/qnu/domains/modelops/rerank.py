"""Resolve rerank through grants, encrypted keys and configured model capacity."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from qnu.domains.modelops.capacity.automatic import operational_budget
from qnu.domains.modelops.capacity.service import read_capacity
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.public_api import OcrRuntime, _active_key
from qnu.domains.modelops.registry import transport_for
from qnu.platform.crypto import decrypt
from qnu.platform.errors import Conflict, DependencyUnavailable
from qnu.ports.reranker import RerankRequest


async def resolve(
    db: AsyncSession, workspace_id: str, provider_id: str | None = None
) -> OcrRuntime:
    from qnu.domains.modelops.resilience.routing import choose_target

    provider_id, routing = await choose_target(db, workspace_id, "rerank", provider_id)
    provider = await catalog_service.resolve_workspace_provider(
        db, workspace_id, "rerank", provider_id
    )
    if "rerank" not in transport_for(provider.provider_type).protocols:
        raise Conflict("Loại provider rerank chưa hỗ trợ.", code="rerank_provider_unsupported")
    key = await _active_key(db, provider.id)
    if key is None:
        raise DependencyUnavailable("Thiếu credential rerank.", code="rerank_credentials_missing")
    capacity = read_capacity(provider)
    effective = operational_budget(capacity, "rerank")
    return OcrRuntime(
        workspace_id=workspace_id,
        session_factory=async_sessionmaker(db.bind, expire_on_commit=False),
        routing_trace=routing,
        provider_id=provider.id,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        model_name=provider.model_name,
        base_url=provider.base_url,
        timeout_seconds=provider.timeout_seconds,
        api_key=decrypt(key.secret_encrypted),
        token_limits=effective.token_limits,
        capacity_status="provisional" if effective.status == "provisional" else capacity.status,
        operational_budget=effective,
    )


def budget(runtime: OcrRuntime, query: str, documents: list[str]) -> int:
    limits = runtime.token_limits
    bounds = [len(query.encode()) + len(d.encode()) + 64 for d in documents]
    available = (
        [v for v in (limits.max_input_tokens, limits.context_window_tokens) if v is not None]
        if limits
        else []
    )
    if runtime.capacity_status not in ("configured", "provisional") or not available:
        raise Conflict("Cần cấu hình capacity rerank.", code="rerank_capacity_required")
    if any(n > min(available) for n in bounds):
        raise Conflict("Ứng viên vượt capacity rerank.", code="rerank_input_limit_exceeded")
    return max(1, sum(bounds))


def request(runtime: OcrRuntime) -> RerankRequest:
    return RerankRequest(
        runtime.base_url,
        runtime.model_name,
        runtime.timeout_seconds,
        runtime.api_key,
        runtime.execution_scope,
    )
