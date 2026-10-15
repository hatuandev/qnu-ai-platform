"""Single-installation API contracts, with a bridge for persisted legacy jobs.

Tenant/workspace are no longer API fields or authorization dimensions. The
read-only properties only let older internal service signatures keep writing
their existing NOT NULL storage columns until those columns can be retired.
They must never be used to partition queries or cache entries.
"""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, model_validator

LEGACY_TENANT = "tenant_qnu"
LEGACY_WORKSPACE = "workspace_qnu"


class SingleApplicationModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def discard_legacy_scope(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {key: item for key, item in value.items()
                    if key not in {"tenant_id", "workspace_id"}}
        return value

    @property
    def tenant_id(self) -> str:
        return LEGACY_TENANT

    @property
    def workspace_id(self) -> str:
        return LEGACY_WORKSPACE
