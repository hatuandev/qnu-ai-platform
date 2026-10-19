"""One monotonic deadline across build, inference, binding and atomic staging."""
import asyncio
import math

from app.core.exceptions import AppException


class SemanticRunBudget:
    def __init__(self, seconds: float):
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("INVALID_SEMANTIC_DEADLINE")
        self.loop = asyncio.get_running_loop()
        self.expires_at = self.loop.time() + seconds

    def check(self) -> None:
        task = asyncio.current_task()
        if task and task.cancelling():
            raise asyncio.CancelledError
        if self.loop.time() >= self.expires_at:
            raise self.error("SEMANTIC_RUN_DEADLINE")

    @staticmethod
    def error(code: str) -> AppException:
        return AppException("Đã hết thời gian xử lý; chưa áp dụng dữ liệu.", code=code, status_code=504,
            details={"stage": "run_deadline" if code == "SEMANTIC_RUN_DEADLINE" else "call_deadline"})

    async def wait(self, factory, *, call_seconds: float | None = None):
        self.check()
        stop = min(self.expires_at, self.loop.time() + call_seconds) if call_seconds is not None else self.expires_at
        guard = asyncio.timeout_at(stop)
        try:
            async with guard:
                result = await factory()
                self.check()
                return result
        except TimeoutError as exc:
            if not guard.expired():
                raise  # Inner provider/transport timeout retains its own contract.
            code = "SEMANTIC_RUN_DEADLINE" if stop == self.expires_at else "SEMANTIC_CALL_DEADLINE"
            raise self.error(code) from exc
