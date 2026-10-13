"""Never release the capture barrier or delete scratch while blocking I/O still runs."""

import asyncio


async def finish_thread(function, *args):
    task = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # Cancellation of to_thread alone does not stop its OS thread. Drain it
        # before unwinding maintenance/scratch contexts; errors still propagate.
        await task
        raise
