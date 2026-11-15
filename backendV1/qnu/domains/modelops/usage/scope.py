"""Optional request-scoped accounting for an inference consumer."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Protocol


class UsageAccount(Protocol):
    async def reserve(self, usage_id: str, tokens: int) -> None: ...

    async def settle(self, usage_id: str, tokens: int | None) -> None: ...


current_account: ContextVar[UsageAccount | None] = ContextVar("usage_account", default=None)


@contextmanager
def use_account(account: UsageAccount) -> Iterator[None]:
    token = current_account.set(account)
    try:
        yield
    finally:
        current_account.reset(token)
