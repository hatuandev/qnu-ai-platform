"""Chunking Strategies (Strategy Pattern) — Semantic, Clause-based & Table Chunkers."""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChunkDraft:
    """Draft chunk unit ready for indexing."""

    index: int
    content: str
    token_count: int
    chunk_hash: str
    section: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseChunker(ABC):
    """Abstract Strategy interface for text chunking algorithms."""

    @abstractmethod
    def chunk(self, text: str, **kwargs: Any) -> list[ChunkDraft]:
        pass

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token count estimation for Vietnamese / Latin text (~4 chars / token)."""
        return max(1, len(text) // 4)

    @staticmethod
    def compute_hash(text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


class ClauseBasedChunker(BaseChunker):
    """Specialized chunker for regulations and legal documents splitting by 'Điều' and 'Khoản'."""

    _RE_ARTICLE = re.compile(
        r"(?=^(?:Điều|Chương|Phần)\s+\d+[\.:]?\s+)", re.MULTILINE | re.IGNORECASE
    )

    def chunk(self, text: str, **kwargs: Any) -> list[ChunkDraft]:
        if not text:
            return []

        # Split text on articles (Điều X...)
        raw_sections = self._RE_ARTICLE.split(text)
        chunks: list[ChunkDraft] = []
        chunk_idx = 0

        for raw_sec in raw_sections:
            clean_sec = raw_sec.strip()
            if not clean_sec or len(clean_sec) < 20:
                continue

            # Extract title of the article from first line
            first_line = clean_sec.split("\n", 1)[0].strip()
            section_title = first_line[:120] if len(first_line) > 5 else None

            # If article is too long (> 2000 chars), subdivide it into paragraphs
            if len(clean_sec) > 2000:
                sub_parts = clean_sec.split("\n\n")
                buffer = ""
                for part in sub_parts:
                    if len(buffer) + len(part) < 1800:
                        buffer += "\n\n" + part if buffer else part
                    else:
                        if buffer:
                            chunks.append(
                                ChunkDraft(
                                    index=chunk_idx,
                                    content=buffer.strip(),
                                    token_count=self.estimate_tokens(buffer),
                                    chunk_hash=self.compute_hash(buffer),
                                    section=section_title,
                                )
                            )
                            chunk_idx += 1
                        buffer = part
                if buffer:
                    chunks.append(
                        ChunkDraft(
                            index=chunk_idx,
                            content=buffer.strip(),
                            token_count=self.estimate_tokens(buffer),
                            chunk_hash=self.compute_hash(buffer),
                            section=section_title,
                        )
                    )
                    chunk_idx += 1
            else:
                chunks.append(
                    ChunkDraft(
                        index=chunk_idx,
                        content=clean_sec,
                        token_count=self.estimate_tokens(clean_sec),
                        chunk_hash=self.compute_hash(clean_sec),
                        section=section_title,
                    )
                )
                chunk_idx += 1

        # Fallback to SemanticChunker if no legal clauses detected
        if not chunks:
            return SemanticChunker().chunk(text, **kwargs)

        return chunks


class SemanticChunker(BaseChunker):
    """General-purpose paragraph chunker with token limit and overlap."""

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 64):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, text: str, **kwargs: Any) -> list[ChunkDraft]:
        if not text:
            return []

        paragraphs = text.split("\n\n")
        chunks: list[ChunkDraft] = []
        current_chunk_parts: list[str] = []
        current_tokens = 0
        chunk_idx = 0

        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue

            para_tokens = self.estimate_tokens(para_clean)

            if current_tokens + para_tokens > self.max_tokens and current_chunk_parts:
                full_content = "\n\n".join(current_chunk_parts).strip()
                chunks.append(
                    ChunkDraft(
                        index=chunk_idx,
                        content=full_content,
                        token_count=self.estimate_tokens(full_content),
                        chunk_hash=self.compute_hash(full_content),
                    )
                )
                chunk_idx += 1
                # Overlap: keep last paragraph if it fits
                if self.estimate_tokens(current_chunk_parts[-1]) <= self.overlap_tokens:
                    current_chunk_parts = [current_chunk_parts[-1], para_clean]
                    current_tokens = self.estimate_tokens(current_chunk_parts[0]) + para_tokens
                else:
                    current_chunk_parts = [para_clean]
                    current_tokens = para_tokens
            else:
                current_chunk_parts.append(para_clean)
                current_tokens += para_tokens

        if current_chunk_parts:
            full_content = "\n\n".join(current_chunk_parts).strip()
            chunks.append(
                ChunkDraft(
                    index=chunk_idx,
                    content=full_content,
                    token_count=self.estimate_tokens(full_content),
                    chunk_hash=self.compute_hash(full_content),
                )
            )

        return chunks


def get_chunker(strategy: str = "semantic") -> BaseChunker:
    """Factory creating appropriate chunking strategy."""
    clean_strat = strategy.lower().strip()
    if clean_strat in ("clause", "regulations", "clause_based"):
        return ClauseBasedChunker()
    return SemanticChunker()
