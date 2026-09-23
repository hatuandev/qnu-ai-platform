"""Pydantic Schemas for OCR Document Recognition & Studio Intelligence."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OCREngineResponse(BaseModel):
    id: str
    name: str
    display_name: str
    engine_type: str
    provider_category: str
    capabilities: list[str] = Field(default_factory=list)
    avg_confidence: float
    is_active: bool
    is_default: bool

    model_config = {"from_attributes": True}


class OCRPageResult(BaseModel):
    page_number: int
    extracted_text: str
    confidence: float
    word_count: int
    line_count: int
    has_tables: bool = False
    blocks: list[dict[str, Any]] = Field(default_factory=list)


class OCRExtractResponse(BaseModel):
    filename: str
    success: bool
    engine_used: str
    fallback_triggered: bool = False
    fallback_engine: str | None = None
    cascade_trace: list[str] = Field(default_factory=list)
    total_pages: int
    overall_confidence: float
    latency_ms: float
    raw_text: str
    pages: list[OCRPageResult] = Field(default_factory=list)


class StudioOCRRegion(BaseModel):
    type: str
    label: str
    text: str
    top: float
    left: float
    width: float
    height: float


class StudioOCRPageResponse(BaseModel):
    page_number: int = Field(alias="pageNumber")
    title: str
    is_signed: bool = Field(default=False, alias="isSigned")
    has_table: bool = Field(default=False, alias="hasTable")
    image_url: str = Field(alias="imageUrl")
    markdown: str
    raw_text: str = Field(alias="rawText")
    regions: list[StudioOCRRegion] = Field(default_factory=list)
    dimensions: dict[str, int] = Field(default_factory=lambda: {"width": 1240, "height": 1754})
    word_count: int = Field(default=0, alias="wordCount")
    line_count: int = Field(default=0, alias="lineCount")
    sheet_data: dict[str, Any] | None = Field(default=None, alias="sheetData")

    model_config = {"populate_by_name": True}


class StudioOCRParseResponse(BaseModel):
    filename: str
    total_pages: int = Field(alias="totalPages")
    size: str
    provider: str
    model: str
    latency_ms: float = Field(alias="latencyMs")
    pages: list[StudioOCRPageResponse] = Field(default_factory=list)
    sheets_data: list[dict[str, Any]] | None = Field(default=None, alias="sheetsData")

    model_config = {"populate_by_name": True}
