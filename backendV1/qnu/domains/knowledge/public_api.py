"""Read-only surface of the knowledge domain for other domains.

Only what another domain legitimately needs: a revision pinned to its workspace,
collection and source, and the verified bytes of that revision. Nothing here can
write, list or widen scope.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.policies.access import (
    WRITE_ROLES,
    load_collection,
    load_revision,
    load_source,
)
from qnu.platform.errors import AppException, DependencyUnavailable
from qnu.ports.blob_store import BlobStore


@dataclass(frozen=True, slots=True)
class RevisionScope:
    """A revision proven to belong to one workspace → collection → source chain."""

    workspace_id: str
    collection_id: str
    source_id: str
    revision_id: str
    revision_no: int
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    storage_key: str

    @property
    def extension(self) -> str:
        return PurePosixPath(self.file_name).suffix.lower()


async def resolve_revision_scope(
    db: AsyncSession,
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
) -> RevisionScope:
    """Walk the whole chain; a mismatch anywhere is a 404, never a partial match."""
    await load_collection(db, workspace_id, collection_id)
    await load_source(db, workspace_id, collection_id, source_id)
    revision = await load_revision(db, workspace_id, source_id, revision_id)
    if revision.collection_id != collection_id:
        raise AppException(
            "Phiên bản không thuộc kho tri thức đã chọn.",
            code="revision_not_found",
            status_code=404,
            title="Không tìm thấy",
        )
    return RevisionScope(
        workspace_id=revision.workspace_id,
        collection_id=revision.collection_id,
        source_id=revision.source_id,
        revision_id=revision.id,
        revision_no=revision.revision_no,
        file_name=revision.file_name,
        content_type=revision.content_type,
        size_bytes=revision.size_bytes,
        sha256=revision.sha256,
        storage_key=revision.storage_key,
    )


async def read_revision_bytes(blob_store: BlobStore, scope: RevisionScope) -> bytes:
    """Return the stored bytes only after the checksum matches the recorded revision."""
    try:
        payload = await blob_store.get_bytes(scope.storage_key)
    except FileNotFoundError as exc:
        raise AppException(
            "Tệp gốc không còn trong kho lưu trữ.",
            code="blob_missing",
            status_code=502,
            title="Thiếu tệp gốc",
        ) from exc
    except Exception as exc:
        raise DependencyUnavailable(
            "Không đọc được kho lưu trữ.", code="storage_unavailable"
        ) from exc
    if len(payload) != scope.size_bytes or hashlib.sha256(payload).hexdigest() != scope.sha256:
        raise AppException(
            "Tệp gốc không khớp checksum đã lưu; không xử lý tiếp.",
            code="revision_content_mismatch",
            status_code=502,
            title="Tệp gốc không toàn vẹn",
        )
    return payload


__all__ = ["WRITE_ROLES", "RevisionScope", "read_revision_bytes", "resolve_revision_scope"]
