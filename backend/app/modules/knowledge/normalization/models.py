"""Canonical Document Data Models for Structured Document Intelligence.

Enforces typed, unambiguous representations of blocks, cells, rows, and multi-page tables,
ensuring raw values remain immutable while normalized values serve structured downstream tasks.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class BlockType(StrEnum):
    """Semantic block type classification."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    HEADER = "header"
    FOOTER = "footer"
    SIGNATURE = "signature"


class SourceSpan(BaseModel):
    """Exact source provenance location within the document."""

    page_number: int = Field(ge=1, description="1-indexed physical page number")
    bbox: tuple[float, float, float, float] | None = Field(
        default=None,
        description="Coordinates (x0, y0, x1, y1) in absolute points or 0-100 percent",
    )


class CanonicalCell(BaseModel):
    """Atomic cell record preserving raw source value and normalized clean value."""

    raw_value: str = Field(description="Exact immutable string extracted from PDF/DOCX")
    normalized_value: str | None = Field(
        default=None,
        description="Cleaned, reflowed and normalized value (None if empty cell)",
    )
    row_span: int = Field(default=1, ge=1, description="Number of rows spanned by merged cell")
    column_span: int = Field(default=1, ge=1, description="Number of columns spanned by merged cell")
    source_span: SourceSpan = Field(description="Page and coordinates provenance")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="OCR/extraction confidence")


class CanonicalRow(BaseModel):
    """A row of cells in a canonical table."""

    row_id: str = Field(description="Unique row identifier within the table")
    cells: list[CanonicalCell] = Field(default_factory=list, description="Ordered cells in row")
    source_pages: list[int] = Field(default_factory=list, description="Source pages contributing to this row")
    is_continuation: bool = Field(
        default=False,
        description="True if row was stitched from an orphan continuation chunk on next page",
    )


class CanonicalTable(BaseModel):
    """Reconstructed logical table spanning one or multiple pages."""

    table_id: str = Field(description="Unique table identifier")
    schema_key: str = Field(description="Hash signature of table headers for cross-page matching")
    headers: list[str] = Field(default_factory=list, description="Normalized column header titles")
    rows: list[CanonicalRow] = Field(default_factory=list, description="Data rows")
    source_pages: list[int] = Field(default_factory=list, description="All pages this table spans")
    bbox: tuple[float, float, float, float] | None = Field(
        default=None,
        description="Bounding box on primary page (x0, y0, x1, y1)",
    )


class CanonicalBlock(BaseModel):
    """A semantic text/paragraph block outside any table."""

    block_id: str = Field(description="Unique block identifier")
    type: BlockType = Field(default=BlockType.PARAGRAPH, description="Block semantic classification")
    text: str = Field(description="Clean text content of this block")
    source_span: SourceSpan = Field(description="Page and bounding box provenance")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)


class QualityIssue(BaseModel):
    """Quality issue detected by DataQualityGate."""

    code: str = Field(description="Standardized error code, e.g. CONFLICTING_FACT_VALUES")
    severity: str = Field(description="'info' | 'warning' | 'blocking'")
    message: str = Field(description="Human-readable explanation of the issue")
    page_number: int | None = None
    table_id: str | None = None
    row_id: str | None = None
    raw_values: list[str] = Field(default_factory=list)


class CanonicalDocument(BaseModel):
    """Full canonical document containing non-duplicated blocks, tables, and quality issues."""

    document_id: str = Field(description="Document ID or hash")
    page_count: int = Field(default=1, ge=1)
    blocks: list[CanonicalBlock] = Field(default_factory=list, description="Non-table blocks in reading order")
    tables: list[CanonicalTable] = Field(default_factory=list, description="Reconstructed logical tables")
    issues: list[QualityIssue] = Field(default_factory=list, description="Quality findings")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")
