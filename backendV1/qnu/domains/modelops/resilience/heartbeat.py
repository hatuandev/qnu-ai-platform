"""Renew finite fenced leases while a model response has no execution deadline."""

import asyncio
from contextlib import asynccontextmanager, suppress

from qnu.platform.errors import AppException


@asynccontextmanager
async def maintain_lease(renew, interval: float):
    owner = asyncio.current_task()
    failed = False

    async def pulse():
        nonlocal failed
        while True:
            await asyncio.sleep(interval)
            try:
                async with asyncio.timeout(5):
                    if not await renew():
                        raise RuntimeError("Lease ownership lost")
            except Exception:
                failed = True
                owner.cancel()
                return

    task = asyncio.create_task(pulse())
    try:
        yield
    except asyncio.CancelledError:
        if failed:
            raise AppException(
                "Không giữ được quyền thực thi; chưa xác định kết quả model.",
                code="chat_provider_uncertain", status_code=504,
            ) from None
        raise
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
