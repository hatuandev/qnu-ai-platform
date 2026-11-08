"""Action capabilities for one already-authorized workspace role.

Read models expose these booleans so a caller sees the same actions the API will
enforce. They never replace server-side authorization and never grant access.
"""

from __future__ import annotations

from pydantic import BaseModel


class SummaryCapabilities(BaseModel):
    can_prepare: bool
    can_register: bool
    can_approve: bool
    can_publish: bool


def summary_capabilities(role: str) -> SummaryCapabilities:
    return SummaryCapabilities(
        can_prepare=role in {"admin", "editor"},
        can_register=role in {"admin", "editor"},
        can_approve=role in {"admin", "reviewer"},
        can_publish=role == "admin",
    )
