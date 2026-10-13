"""Shared opt-in policy for evidence-bound assistant answers."""

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceSourcePreference(BaseModel):
    """Human-approved precedence, restricted to equivalent applicability tuples."""

    preferred_source_revision_id: str = Field(min_length=1)
    superseded_source_revision_ids: list[str] = Field(min_length=1, max_length=20)
    years: list[int] = Field(min_length=1, max_length=10)
    same_context_only: Literal[True] = True
    authorization_note: str = Field(min_length=1, max_length=1000)


class EvidencePolicy(BaseModel):
    enabled: bool = False
    reference_year_mode: Literal["clarify", "current_year", "fixed"] = "clarify"
    timezone: str = "Asia/Ho_Chi_Minh"
    default_reference_year: int | None = Field(None, ge=1900, le=2099)
    candidate_limit: int = Field(24, ge=8, le=40)
    context_limit: int = Field(10, ge=3, le=16)
    max_context_chars: int = Field(36000, ge=6000, le=64000)
    timeout_seconds: int = Field(90, ge=15, le=240)
    retrieval_timeout_seconds: float = Field(10, ge=1, le=30)
    rerank_timeout_seconds: float = Field(3, ge=0.2, le=15)
    source_preferences: list[EvidenceSourcePreference] = Field(default_factory=list, max_length=10)
