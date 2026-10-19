"""Pure review DTOs shared by API schemas and services; no service initialization."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_identity: dict[str, str | None]
    input_hash: str
    source_unit_id: str
    coordinate_space: Literal["unit_codepoints", "cell_raw_codepoints"]
    column_id: str | None = None
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text_sha256: str
    evidence_id: str



class ContextDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issue_id: str
    target: dict[str, str | list[str]]
    action: Literal["scope_confirmed", "not_applicable_to_target", "related_context_reviewed"]
    evidence_binding: EvidenceBinding
    evidence_quote: str = Field(min_length=3, max_length=10000)
    reason: str = Field(min_length=3, max_length=2000)
    supporting_evidence: list[EvidenceBinding] = Field(default_factory=list, max_length=32)

