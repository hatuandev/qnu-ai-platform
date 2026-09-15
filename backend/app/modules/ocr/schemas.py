"""Pydantic Schemas for OCR Document Recognition."""

from __future__ import annotations

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


class OCRExtractResponse(BaseModel):
    filename: str
    success: bool
    engine_used: str
    fallback_triggered: bool = False
    total_pages: int
    overall_confidence: float
    latency_ms: float
    raw_text: str
    pages: list[OCRPageResult] = Field(default_factory=list)
