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
    _RE_PAGE_MARKER = re.compile(
        r"<!--\s*(?:Trang|Page)\s+(\d+)\s*-->", re.IGNORECASE
    )

    def chunk(self, text: str, **kwargs: Any) -> list[ChunkDraft]:
        if not text:
            return []

        # Split text on articles (Điều X...)
        raw_sections = self._RE_ARTICLE.split(text)
        chunks: list[ChunkDraft] = []
        chunk_idx = 0
        current_page: int | None = None

        for raw_sec in raw_sections:
            clean_sec = raw_sec.strip()
            if not clean_sec or len(clean_sec) < 20:
                page_matches = list(self._RE_PAGE_MARKER.finditer(raw_sec))
                if page_matches:
                    try:
                        current_page = int(page_matches[-1].group(1))
                    except (TypeError, ValueError):
                        pass
                continue

            sec_matches = list(self._RE_PAGE_MARKER.finditer(raw_sec))
            sec_start_page = current_page
            if sec_matches and (sec_matches[0].start() < 60 or sec_start_page is None):
                try:
                    sec_start_page = int(sec_matches[0].group(1))
                except (TypeError, ValueError):
                    pass

            # Update current_page for subsequent sections
            if sec_matches:
                try:
                    current_page = int(sec_matches[-1].group(1))
                except (TypeError, ValueError):
                    pass

            # Extract title of the article from first line
            first_line = clean_sec.split("\n", 1)[0].strip()
            section_title = first_line[:120] if len(first_line) > 5 else None

            # If article is too long (> 2000 chars), subdivide it into paragraphs
            if len(clean_sec) > 2000:
                sub_parts = clean_sec.split("\n\n")
                buffer = ""
                sub_page = sec_start_page
                for part in sub_parts:
                    p_match = self._RE_PAGE_MARKER.search(part)
                    if p_match:
                        try:
                            sub_page = int(p_match.group(1))
                        except (TypeError, ValueError):
                            pass
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
                                    page_number=sub_page,
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
                            page_number=sub_page,
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
                        page_number=sec_start_page,
                    )
                )
                chunk_idx += 1

        # Fallback to SemanticChunker if no legal clauses detected
        if not chunks:
            return SemanticChunker().chunk(text, **kwargs)

        return chunks


class SemanticChunker(BaseChunker):
    """General-purpose paragraph chunker with token limit and overlap."""

    _RE_PAGE_MARKER = re.compile(
        r"<!--\s*(?:Trang|Page)\s+(\d+)\s*-->", re.IGNORECASE
    )

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
        current_page: int | None = None

        for para in paragraphs:
            p_match = self._RE_PAGE_MARKER.search(para)
            if p_match:
                try:
                    current_page = int(p_match.group(1))
                except (TypeError, ValueError):
                    pass

            para_clean = para.strip()
            if not para_clean:
                continue

            para_tokens = self.estimate_tokens(para_clean)

            if current_tokens + para_tokens > self.max_tokens and current_chunk_parts:
                full_content = "\n\n".join(current_chunk_parts).strip()
                chunk_page = current_page
                content_match = self._RE_PAGE_MARKER.search(full_content)
                if content_match:
                    try:
                        chunk_page = int(content_match.group(1))
                    except (TypeError, ValueError):
                        pass
                chunks.append(
                    ChunkDraft(
                        index=chunk_idx,
                        content=full_content,
                        token_count=self.estimate_tokens(full_content),
                        chunk_hash=self.compute_hash(full_content),
                        page_number=chunk_page,
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
            chunk_page = current_page
            content_match = self._RE_PAGE_MARKER.search(full_content)
            if content_match:
                try:
                    chunk_page = int(content_match.group(1))
                except (TypeError, ValueError):
                    pass
            chunks.append(
                ChunkDraft(
                    index=chunk_idx,
                    content=full_content,
                    token_count=self.estimate_tokens(full_content),
                    chunk_hash=self.compute_hash(full_content),
                    page_number=chunk_page,
                )
            )

        return chunks


class AdmissionsRecordChunker(BaseChunker):
    """Atomic chunker for University Admissions programs (1 program = 1 atomic chunk)."""

    def chunk(self, text: str, **kwargs: Any) -> list[ChunkDraft]:
        records = kwargs.get("records")
        if not records:
            # Fallback to SemanticChunker if no pre-extracted records are provided
            return SemanticChunker().chunk(text, **kwargs)

        chunks: list[ChunkDraft] = []
        for idx, rec in enumerate(records):
            quota_str = str(rec.expected_quota) if getattr(rec, "expected_quota", None) is not None else "Chưa công bố cụ thể"
            methods_str = ", ".join(getattr(rec, "admission_methods", [])) or "1, 2, 4"
            comb_lines = []
            for combo in getattr(rec, "subject_combinations", []):
                comb_lines.append(" - ".join(combo))
            comb_text = "; ".join(comb_lines) if comb_lines else "Theo quy định tuyển sinh chung"

            content = (
                f"Thông tin tuyển sinh ngành {rec.program_name} (Mã ngành: {rec.program_code}):\n"
                f"- Phương thức xét tuyển: {methods_str}\n"
                f"- Chỉ tiêu dự kiến: {quota_str}\n"
                f"- Các tổ hợp môn xét tuyển: {comb_text}"
            )
            p_num = rec.source_pages[0] if getattr(rec, "source_pages", None) else None

            chunks.append(
                ChunkDraft(
                    index=idx,
                    content=content,
                    token_count=self.estimate_tokens(content),
                    chunk_hash=self.compute_hash(content),
                    page_number=p_num,
                    section=f"Ngành {rec.program_name}",
                    metadata={
                        "chunk_type": "admission_program",
                        "entity_key": f"program:{rec.program_code}",
                        "program_code": rec.program_code,
                        "program_name": rec.program_name,
                    },
                )
            )
        return chunks


class ImplementationTaskChunker(BaseChunker):
    """Atomic chunker for institutional action plan tasks (1 task = 1 atomic chunk)."""

    def chunk(self, text: str, **kwargs: Any) -> list[ChunkDraft]:
        records = kwargs.get("records")
        if not records:
            return SemanticChunker().chunk(text, **kwargs)

        chunks: list[ChunkDraft] = []
        for idx, task in enumerate(records):
            coord_str = ", ".join(getattr(task, "coordinating_units", [])) if getattr(task, "coordinating_units", None) else "Không"
            time_parts = []
            if getattr(task, "start_date", None):
                time_parts.append(f"bắt đầu: {task.start_date}")
            if getattr(task, "end_date", None):
                time_parts.append(f"hoàn thành: {task.end_date}")
            time_str = ", ".join(time_parts) if time_parts else "Trong năm học 2025 - 2026"
            deliv_str = "; ".join(getattr(task, "deliverables", [])) if getattr(task, "deliverables", None) else "Theo kế hoạch phê duyệt"

            content = (
                f"Kế hoạch nhiệm vụ {task.task_code} ({task.category}):\n"
                f"- Nội dung nhiệm vụ: {task.content}\n"
                f"- Đơn vị chủ trì: {task.lead_unit or 'Chưa phân công'}\n"
                f"- Đơn vị phối hợp: {coord_str}\n"
                f"- Thời gian thực hiện: {time_str}\n"
                f"- Sản phẩm kết quả: {deliv_str}"
            )
            p_num = task.source_pages[0] if getattr(task, "source_pages", None) else None

            chunks.append(
                ChunkDraft(
                    index=idx,
                    content=content,
                    token_count=self.estimate_tokens(content),
                    chunk_hash=self.compute_hash(content),
                    page_number=p_num,
                    section=f"Nhiệm vụ {task.task_code}",
                    metadata={
                        "chunk_type": "implementation_task",
                        "entity_key": f"task:{task.task_code}",
                        "task_code": task.task_code,
                        "category": task.category,
                        "lead_unit": task.lead_unit,
                    },
                )
            )
        return chunks


def get_chunker(strategy: str = "semantic") -> BaseChunker:
    """Factory creating appropriate chunking strategy."""
    clean_strat = strategy.lower().strip()
    if clean_strat in ("clause", "regulations", "clause_based"):
        return ClauseBasedChunker()
    if clean_strat in ("admissions", "admission_program", "admissions_record"):
        return AdmissionsRecordChunker()
    if clean_strat in ("task", "implementation_task", "action_plan"):
        return ImplementationTaskChunker()
    return SemanticChunker()

