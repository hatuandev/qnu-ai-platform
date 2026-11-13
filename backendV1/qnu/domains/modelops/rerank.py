"""Resolve rerank through encrypted keys and configured model capacity."""

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


def capacity(runtime: OcrRuntime) -> int | None:
    limits = runtime.token_limits
    available = (
        [
            value
            for value in (limits.max_input_tokens, limits.context_window_tokens)
            if value is not None
        ]
        if limits
        else []
    )
    return min(available) if available else None


def parts(query: str, documents: list[str]) -> tuple[int, list[int], list[int]]:
    """Byte sizes and per-document guard bounds; the guard compares bytes, not tokens."""
    query_bytes = len(query.encode())
    sizes = [len(document.encode()) for document in documents]
    return query_bytes, sizes, [query_bytes + size + 64 for size in sizes]


def measure(runtime: OcrRuntime, query: str, documents: list[str]) -> dict:
    """Sizing facts for trace: what is sent, the byte guard and the token capacity."""
    query_bytes, sizes, bounds = parts(query, documents)
    limit = capacity(runtime)
    return {
        "documents": len(documents),
        "query_bytes": query_bytes,
        "doc_bytes_total": sum(sizes),
        "doc_bytes_max": max(sizes, default=0),
        "guard_bytes_total": sum(bounds),
        "guard_bytes_max": max(bounds, default=0),
        "capacity_tokens": limit,
        "capacity_status": runtime.capacity_status,
        "over_capacity_documents": sum(
            1 for bound in bounds if limit is not None and bound > limit
        ),
    }


def budget(runtime: OcrRuntime, query: str, documents: list[str]) -> int:
    limit = capacity(runtime)
    if runtime.capacity_status not in ("configured", "provisional") or limit is None:
        raise Conflict("Cần cấu hình capacity rerank.", code="rerank_capacity_required")
    _, _, bounds = parts(query, documents)
    if any(bound > limit for bound in bounds):
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
