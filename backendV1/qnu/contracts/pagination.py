"""Offset pagination contract shared by list endpoints."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageMeta(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=200)
    total: int = Field(0, ge=0)

    @property
    def total_pages(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)


class Page(BaseModel, Generic[T]):  # noqa: UP046 - Pydantic v2 requires the Generic base
    items: list[T] = Field(default_factory=list)
    meta: PageMeta = Field(default_factory=PageMeta)
