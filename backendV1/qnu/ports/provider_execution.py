"""Internal execution identity; never accepted from a public request body."""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class ProviderExecution:
    workspace_id: str
    provider_id: str
    usage_id: str | None = None
    sessions: Callable[[], Any] | None = field(default=None, repr=False, compare=False)


def bind_usage(request, usage_id: str):
    """Attach the domain's committed reservation without changing inference input."""
    return (
        replace(request, execution=replace(request.execution, usage_id=usage_id))
        if request.execution
        else request
    )


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    """Only a definite rejection may try another credential on the same target."""

    upstream_status: int
    retry_after_seconds: float | None = None

    @property
    def retryable_key(self) -> bool:
        return self.upstream_status in (401, 429)
