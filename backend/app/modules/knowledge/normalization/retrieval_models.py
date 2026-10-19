"""Versioned source units shared by indexing, search and source verification."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

UNIT_VERSION = "source-units-v1"


class TemporalScope(BaseModel):
    """Typed, source-qualified time metadata; declarations are never approvals."""

    model_config = ConfigDict(extra="forbid")
    issued_date: str | None = None
    mentioned_years: list[int] = Field(default_factory=list)
    heading_years: list[int] = Field(default_factory=list)
    data_years: list[int] = Field(default_factory=list)
    academic_year: Any | None = None
    effective_from: dict[str, Any] | None = None
    effective_to: dict[str, Any] | None = None
    event_from: dict[str, Any] | None = None
    event_to: dict[str, Any] | None = None
    recurrence: Any | None = None
    basis_quote: str | None = None
    scope_level: Literal["unknown", "block", "row", "column", "field"] = "unknown"
    unsupported: dict[str, Any] = Field(default_factory=dict)
    status: Literal["unknown", "proposed", "verified", "ambiguous"] = "unknown"
    role: Literal["data", "effective", "event", "unknown"] = "unknown"
    evidence_quote: str | None = None


class SourceUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    parent_id: str | None = None
    kind: Literal["heading", "paragraph", "list", "table"]
    text: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    page_number: int | None = None
    heading_path: list[str] = Field(default_factory=list)
    header_context: str = ""
    is_container: bool = False
    temporal: TemporalScope = Field(default_factory=TemporalScope)
    # Explicit standard provenance stays server-side, outside embedding text.
    qnu_block_id: str | None = None
    source_locations: list[dict] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)
    field_context_refs: dict[str, list[str]] = Field(default_factory=dict)
    field_usage: dict[str, Literal["description_only"]] = Field(default_factory=dict)
    # Backend-derived assertion metadata; never a human approval or source rewrite.
    semantic_scope: dict[str, Any] = Field(default_factory=dict, exclude_if=lambda value: not value)


class UnitManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["source-units-v1"] = UNIT_VERSION
    canonical_hash: str
    units: list[SourceUnit] = Field(default_factory=list)
    semantic_annotation_hash: str | None = None


def temporal_is_compatible(scope: TemporalScope, years: list[int]) -> bool:
    """Only evidenced data applicability is a hard constraint, never issue date."""
    return not (years and scope.role == "data" and scope.status == "verified"
                and scope.data_years and not set(years).intersection(scope.data_years))
