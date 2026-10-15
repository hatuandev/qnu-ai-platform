"""Server-reviewed conversion rules and public calculator inputs, never arbitrary formulas."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.modules.rag.evidence_schemas import QuoteReference, StrictContract
from app.modules.rag.schemas import Citation


def parse_score(value: str) -> Decimal:
    if not re.fullmatch(r"\d{1,6}(?:[.,]\d{1,2})?", value.strip()):
        raise ValueError("Điểm phải là số không âm, tối đa hai chữ số thập phân; không dùng dấu phân cách hàng nghìn.")
    return Decimal(value.strip().replace(",", "."))


class ScoreConversionRequest(StrictContract):
    collection_id: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2200)
    source_method: str = Field(min_length=1, max_length=200)
    combination: str = Field(min_length=1, max_length=80)
    score: str = Field(min_length=1, max_length=12)

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: str) -> str:
        parse_score(value)
        return value.strip()


class SourceCell(StrictContract):
    """An exact reviewed-fact cell, not a model-provided numeric quote."""

    block_id: str
    fact_id: str
    attribute: str
    value: str


class ConversionPoint(StrictContract):
    source: SourceCell
    target: SourceCell


class CombinationMapping(StrictContract):
    combination: str
    base_combination: str
    proof: SourceCell


class ConversionRule(StrictContract):
    id: str = Field(min_length=1)
    status: Literal["verified"]
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    binding_id: str
    index_revision_id: str
    source_revision_id: str
    canonical_hash: str = Field(min_length=64, max_length=64)
    year: int = Field(ge=1900, le=2200)
    source_method: str
    source_attribute: str
    source_aliases: list[str] = Field(default_factory=list, max_length=20)
    target_method: str
    target_attribute: str
    base_combination: str
    # A mapping row may identify itself by subject list, so the code column header is reviewed too.
    combination_context_attribute: str = Field(min_length=1, max_length=200)
    mappings: list[CombinationMapping] = Field(min_length=1, max_length=500)
    points: list[ConversionPoint] = Field(min_length=2, max_length=1000)
    operation: Literal["piecewise_linear"]
    decimal_places: int = Field(ge=0, le=6)
    rounding: Literal["ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_DOWN"]
    rule_proofs: list[QuoteReference] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def check_review(self) -> "ConversionRule":
        if self.reviewed_at.tzinfo is None:
            raise ValueError("Review timestamp must include timezone")
        if self.source_method == self.target_method:
            raise ValueError("Conversion source and target methods must differ")
        return self


class ScoreConversionResult(StrictContract):
    status: Literal["calculated", "missing", "clarify"]
    reason: str
    message: str
    rule_id: str | None = None
    year: int | None = None
    source_method: str | None = None
    target_method: str | None = None
    combination: str | None = None
    base_combination: str | None = None
    input_score: str | None = None
    x1: str | None = None
    x2: str | None = None
    y1: str | None = None
    y2: str | None = None
    result: str | None = None
    formula: str | None = None
    rounding: str | None = None
    source_revision_id: str | None = None
    index_revision_id: str | None = None
    snapshot_id: str | None = None
    evidence_block_ids: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
