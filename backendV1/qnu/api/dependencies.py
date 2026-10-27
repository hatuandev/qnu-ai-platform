"""Shared FastAPI dependencies: database session and authenticated actor."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.service import resolve_actor
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException, DependencyUnavailable
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

__all__ = ["get_actor", "get_blob_store", "get_db", "get_job_queue", "get_optional_actor"]


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield one async session per request, always closed."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_actor(request: Request) -> AuthActor:
    """Resolve the caller; fails closed when no authentication path is allowed."""
    return await resolve_actor(request)


async def get_optional_actor(request: Request) -> AuthActor | None:
    """Best-effort actor for public endpoints."""
    try:
        return await resolve_actor(request)
    except AppException as exc:
        if exc.status_code == 401 and not request.headers.get("authorization"):
            return None
        raise


def get_blob_store(request: Request) -> BlobStore:
    """Resolve the configured storage adapter; fail closed when startup did not run."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise DependencyUnavailable(
            "Kho lưu trữ chưa được khởi tạo.", code="storage_unavailable"
        )
    return container.blob_store


def get_job_queue(request: Request) -> JobQueue | None:
    """Return the queue when the process has one; a run stays queued instead of lost."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        return None
    return getattr(container, "job_queue", None)
