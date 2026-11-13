"""Resolve the authorized embedding target and a conservative text-input budget."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from qnu.domains.modelops.capacity.automatic import operational_budget
from qnu.domains.modelops.capacity.service import read_capacity
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.embedding.configuration import read_dimension
from qnu.domains.modelops.public_api import OcrRuntime, _active_key
from qnu.domains.modelops.registry import transport_for
from qnu.platform.crypto import decrypt
from qnu.platform.errors import AppException, Conflict, DependencyUnavailable
from qnu.ports.embedding_model import EmbeddingRequest


@dataclass(frozen=True, slots=True)
class EmbeddingRuntime(OcrRuntime):
    dimension: int | None = None

    @property
    def configuration_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(
                {
                    "target": super(EmbeddingRuntime, self).configuration_hash,
                    "dimension": self.dimension,
                    "protocol": "openai-dense/v1",
                    "distance": "Cosine",
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()

    def public_dict(self) -> dict:
        return {
            **super(EmbeddingRuntime, self).public_dict(),
            "dimension": self.dimension,
            "protocol": "openai-dense/v1",
            "distance": "Cosine",
        }

    def request(self) -> EmbeddingRequest:
        return EmbeddingRequest(
            self.base_url,
            self.model_name,
            self.timeout_seconds,
            self.api_key,
            self.dimension,
            self.execution_scope,
        )

    def budget(self, texts: list[str]) -> int:
        if self.capacity_status not in ("configured", "provisional") or self.token_limits is None:
            raise Conflict(
                "Cần cấu hình capacity embedding đúng endpoint/model.",
                code="embedding_capacity_required",
            )
        limits = [
            n
            for n in (self.token_limits.max_input_tokens, self.token_limits.context_window_tokens)
            if n is not None
        ]
        if not limits:
            raise Conflict("Thiếu giới hạn đầu vào embedding.", code="embedding_capacity_required")
        # Text-only operational upper bound, not observed tokenizer usage.
        bounds = [len(t.encode("utf-8")) + 32 for t in texts]
        if any(n > min(limits) for n in bounds):
            raise AppException(
                "Đầu vào vượt giới hạn embedding.",
                code="embedding_input_limit_exceeded",
                status_code=422,
            )
        return max(1, sum(bounds))


async def resolve_embedding_runtime(
    db: AsyncSession,
    workspace_id: str,
    provider_id: str | None = None,
    *,
    require_dimension: bool = True,
) -> EmbeddingRuntime:
    """Trusted callers authorize the workspace before this resolution."""
    provider = await catalog_service.resolve_workspace_target(
        db, workspace_id, "embedding", provider_id
    )
    if "embedding" not in transport_for(provider.provider_type).protocols:
        raise AppException(
            "Loại provider embedding chưa hỗ trợ.",
            code="embedding_provider_unsupported",
            status_code=422,
        )
    dimension, state = read_dimension(provider)
    if require_dimension and dimension is None:
        raise Conflict(
            "Cần cấu hình số chiều embedding đúng endpoint/model.",
            code="embedding_dimension_stale"
            if state == "stale"
            else "embedding_dimension_required",
        )
    key = await _active_key(db, provider.id)
    if key is None:
        raise DependencyUnavailable(
            "Thiếu credential embedding.", code="embedding_credentials_missing"
        )
    try:
        secret = decrypt(key.secret_encrypted)
    except AppException as exc:
        raise DependencyUnavailable(
            "Không giải mã được credential embedding.", code="embedding_credentials_unreadable"
        ) from exc
    capacity = read_capacity(provider)
    effective = operational_budget(capacity, "embedding")
    return EmbeddingRuntime(
        workspace_id=workspace_id,
        session_factory=async_sessionmaker(db.bind, expire_on_commit=False),
        provider_id=provider.id,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        model_name=provider.model_name,
        base_url=provider.base_url,
        timeout_seconds=provider.timeout_seconds,
        api_key=secret,
        dimension=dimension,
        capacity_status="provisional" if effective.status == "provisional" else capacity.status,
        token_limits=effective.token_limits,
        operational_budget=effective,
    )
