"""Versioned source units shared by indexing, search and source verification."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UNIT_VERSION = "source-units-v1"


class TemporalScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issued_date: str | None = None
    mentioned_years: list[int] = Field(default_factory=list)
    heading_years: list[int] = Field(default_factory=list)
    data_years: list[int] = Field(default_factory=list)
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


class UnitManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["source-units-v1"] = UNIT_VERSION
    canonical_hash: str
    units: list[SourceUnit] = Field(default_factory=list)


def temporal_is_compatible(scope: TemporalScope, years: list[int]) -> bool:
    """Only evidenced data applicability is a hard constraint, never issue date."""
    return not (years and scope.role == "data" and scope.status == "verified"
                and scope.data_years and not set(years).intersection(scope.data_years))
