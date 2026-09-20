"""Base Parser Interface (Strategy Pattern) for Document Intelligence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedTable:
    """Structured table representation extracted from document."""

    page_number: int
    headers: list[str]
    rows: list[list[str]]
    markdown_repr: str


@dataclass
class ParsedContent:
    """Standardized output of document parsing strategy."""

    raw_text: str
    page_count: int = 1
    tables: list[ExtractedTable] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Real geometry blocks: {page_number, type, coordinates(%), label, content_snippet}
    blocks: list[dict[str, Any]] = field(default_factory=list)
    # Canonical representation is retained in memory for quality validation and
    # record-aware chunking. It is intentionally not serialized into document metadata.
    canonical_document: Any | None = None


class BaseDocumentParser(ABC):
    """Abstract Strategy interface for parsing various file formats into clean text/markdown."""

    @abstractmethod
    async def parse(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        """Parse raw file bytes and extract structured text, layout, and tables."""
