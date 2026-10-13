"""Keep a credential reservation alive during batched remote inference."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from app.core.database import AsyncSessionFactory
from app.core.exceptions import AppException
from app.modules.modelops.services.model_runtime_resolver import ModelRuntimeConfig
from app.modules.modelops.services.provider_key_rotation_service import (
    provider_key_rotation_service,
)


@asynccontextmanager
async def renew_runtime_key(runtime: ModelRuntimeConfig) -> AsyncIterator[None]:
    lease = runtime.key_lease()
    if lease is None:
        yield
        return
    owner = asyncio.current_task()

    async def renew() -> None:
        try:
            while True:
                await asyncio.sleep(30)
                async with AsyncSessionFactory() as db:
                    if not await provider_key_rotation_service.renew(
                        db, lease, max(120, runtime.timeout_seconds + 30),
                    ):
                        raise AppException("Quyền sử dụng khóa đã hết hiệu lực.", code="MODEL_KEY_LEASE_LOST", status_code=503)
        except Exception:
            if owner is not None:
                owner.cancel()
            raise

    pulse = asyncio.create_task(renew())
    try:
        yield
    finally:
        pulse.cancel()
        with suppress(asyncio.CancelledError):
            await pulse
