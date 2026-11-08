"""Inbox rows are derived from current resource state, never from dismissal."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from qnu.contracts.pagination import PageMeta

InboxKind = Literal[
    "review_pending",
    "changes_requested",
    "awaiting_publish",
    "sync_incomplete",
    "preparation_failed",
]


class InboxItem(BaseModel):
    id: str
    kind: InboxKind
    title: str
    problem: str
    detail: str = ""
    occurred_at: datetime
    collection_id: str
    collection_name: str
    document_id: str | None = None
    version_id: str | None = None
    submission_id: str | None = None
    source_id: str | None = None
    # Who can act on this row; an empty owner is never invented.
    allowed_roles: list[str] = Field(default_factory=list)
    deep_path: str


class InboxPage(BaseModel):
    items: list[InboxItem] = Field(default_factory=list)
    meta: PageMeta = Field(default_factory=PageMeta)
    counts: dict[str, int] = Field(default_factory=dict)
