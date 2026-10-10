"""Chunking Strategies (Strategy Pattern) — Semantic, Clause-based & Table Chunkers."""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import AppException


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


@dataclass
class TableHeaderSchema:
    """Captured Markdown table header structure for contextual injection across chunks."""

    header_row: str
    separator_row: str
    col_count: int
    column_names: list[str] = field(default_factory=list)


def is_table_row(line: str) -> bool:
    """Check if a line matches markdown table row formatting."""
    s = line.strip()
    return s.startswith("|") and (s.endswith("|") or "|" in s[1:])


def is_table_sep(line: str) -> bool:
    """Check if a line is a markdown table separator row (| :--- | :---: |)."""
    s = line.strip()
    if not s.startswith("|"):
        return False
    inner = s[1:-1] if s.endswith("|") else s.lstrip("|")
    cells = [c.strip() for c in inner.split("|")]
    return len(cells) > 0 and all(re.match(r"^:?-+:?$", c.replace(" ", "")) for c in cells if c)


def count_cols(line: str) -> int:
    """Count number of pipe-separated columns in a markdown line."""
    clean_s = line.strip().replace(r"\|", "___ESCAPED_PIPE___")
    inner = clean_s[1:-1] if clean_s.endswith("|") else clean_s.lstrip("|")
    return len(inner.split("|"))


def split_table_cells(line: str) -> list[str]:
    """Split a markdown table row into trimmed cell values."""
    clean_s = line.strip().replace(r"\|", "___ESCAPED_PIPE___")
    inner = clean_s[1:-1] if clean_s.endswith("|") else clean_s.lstrip("|")
    return [c.replace("___ESCAPED_PIPE___", "|").strip() for c in inner.split("|")]


def is_likely_header_row(line: str) -> bool:
    """Morphological check: determine whether a table row is column headers vs data."""
    if not is_table_row(line) or is_table_sep(line):
        return False
    cells = split_table_cells(line)
    non_empty = [c for c in cells if c.strip()]
    if not non_empty:
        return False
    first = non_empty[0].strip()
    if re.match(r"^\d+(?:\.\d+)+$", first):
        return False
    if len(non_empty) >= 2 and re.match(r"^\d+$", non_empty[0]) and re.match(r"^\d+$", non_empty[1]):
        return False
    numeric_count = sum(1 for c in non_empty if re.match(r"^[-+]?\d+(?:[\.,]\d+)?%?$", c.strip()))
    if numeric_count / len(non_empty) > 0.40:
        return False
    alpha_count = sum(1 for c in non_empty if re.search(r"[a-zA-Z\u00C0-\u024F\u1EA0-\u1EF9]", c))
    return (alpha_count / len(non_empty)) >= 0.50


def extract_table_header(lines: list[str]) -> TableHeaderSchema | None:
    """Detect and extract TableHeaderSchema if lines contain a valid table header."""
    for idx in range(len(lines) - 1):
        line0 = lines[idx].strip()
        line1 = lines[idx + 1].strip()
        if is_table_row(line0) and is_table_sep(line1) and is_likely_header_row(line0):
            cols = count_cols(line0)
            col_names = split_table_cells(line0)
            return TableHeaderSchema(
                header_row=line0,
                separator_row=line1,
                col_count=cols,
                column_names=col_names,
            )
    return None


_RE_AGGREGATE_ROW = re.compile(
    r"\b(tổng|tổng số|tổng cộng|toàn trường|total|sum|kết quả)\b",
    re.IGNORECASE,
)


def generate_linearized_projections(header: TableHeaderSchema, lines: list[str]) -> list[str]:
    """Generate key-value projections for summary/aggregate rows in wide tables (>= 4 cols)."""
    if header.col_count < 4:
        return []
    projections: list[str] = []
    for line in lines:
        if (
            not is_table_row(line)
            or is_table_sep(line)
            or line.strip() == header.header_row.strip()
            or is_likely_header_row(line)
        ):
            continue
        if not _RE_AGGREGATE_ROW.search(line):
            continue
        cells = split_table_cells(line)
        if len(cells) < 3:
            continue
        label_cell = next(
            (c for c in cells if c and not re.match(r"^[-+]?\d+(?:[\.,]\d+)?%?$", c)),
            "Tổng số",
        )
        label_clean = re.sub(r"<[^>]+>", " ", label_cell).strip()
        pairs = []
        for col_name, cell_val in zip(header.column_names, cells):
            clean_c = col_name.strip()
            clean_v = cell_val.strip()
            if not clean_c or not clean_v:
                continue
            if clean_v == label_cell or clean_v == label_clean:
                continue
            primary_col = clean_c.split("/")[0].strip()
            pairs.append(f"{primary_col}: {clean_v}")
        if pairs:
            projections.append(f"> - [{label_clean}]: " + " | ".join(pairs))
    return projections


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
        active_table_header: TableHeaderSchema | None = None

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

                    # Detect or inject table header in sub_parts
                    p_lines = [ln.strip() for ln in part.split("\n") if ln.strip()]
                    tbl_lines = [ln for ln in p_lines if is_table_row(ln)]
                    if tbl_lines:
                        det_hdr = extract_table_header(p_lines)
                        if det_hdr:
                            active_table_header = det_hdr
                        elif active_table_header and count_cols(tbl_lines[0]) == active_table_header.col_count:
                            injected = []
                            done = False
                            for ln in p_lines:
                                if is_table_row(ln) and not done:
                                    injected.append(active_table_header.header_row)
                                    injected.append(active_table_header.separator_row)
                                    done = True
                                injected.append(ln)
                            part = "\n".join(injected)

                    if len(buffer) + len(part) < 1800:
                        buffer += "\n\n" + part if buffer else part
                    else:
                        if buffer:
                            buf_content = buffer.strip()
                            buf_hdr = extract_table_header(buf_content.splitlines()) or active_table_header
                            if buf_hdr:
                                proj = generate_linearized_projections(buf_hdr, buf_content.splitlines())
                                if proj:
                                    buf_content += "\n\n" + "\n".join(proj)
                            chunks.append(
                                ChunkDraft(
                                    index=chunk_idx,
                                    content=buf_content,
                                    token_count=self.estimate_tokens(buf_content),
                                    chunk_hash=self.compute_hash(buf_content),
                                    section=section_title,
                                    page_number=sub_page,
                                )
                            )
                            chunk_idx += 1
                        buffer = part
                if buffer:
                    buf_content = buffer.strip()
                    buf_hdr = extract_table_header(buf_content.splitlines()) or active_table_header
                    if buf_hdr:
                        proj = generate_linearized_projections(buf_hdr, buf_content.splitlines())
                        if proj:
                            buf_content += "\n\n" + "\n".join(proj)
                    chunks.append(
                        ChunkDraft(
                            index=chunk_idx,
                            content=buf_content,
                            token_count=self.estimate_tokens(buf_content),
                            chunk_hash=self.compute_hash(buf_content),
                            section=section_title,
                            page_number=sub_page,
                        )
                    )
                    chunk_idx += 1
            else:
                final_content = clean_sec
                sec_hdr = extract_table_header(final_content.splitlines())
                if sec_hdr:
                    proj = generate_linearized_projections(sec_hdr, final_content.splitlines())
                    if proj:
                        final_content += "\n\n" + "\n".join(proj)
                chunks.append(
                    ChunkDraft(
                        index=chunk_idx,
                        content=final_content,
                        token_count=self.estimate_tokens(final_content),
                        chunk_hash=self.compute_hash(final_content),
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
    """General-purpose paragraph chunker with token limit, table header preservation, and overlap."""

    _RE_PAGE_MARKER = re.compile(
        r"<!--\s*(?:Trang|Page)\s+(\d+)\s*-->", re.IGNORECASE
    )
    _RE_HEADING = re.compile(r"^#{1,3}\s+", re.MULTILINE)

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 64,
        enable_table_header_injection: bool = True,
    ):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.enable_table_header_injection = enable_table_header_injection
        self._active_table_header: TableHeaderSchema | None = None

    def reset(self) -> None:
        """Reset internal table state across document boundaries."""
        self._active_table_header = None

    def _split_oversized_table(
        self,
        table_text: str,
        header: TableHeaderSchema | None,
    ) -> list[str]:
        """Split an oversized table into smaller row batches, preserving header in every batch."""
        lines = [ln.strip() for ln in table_text.split("\n") if ln.strip()]
        if not lines or not header:
            return [table_text]

        data_rows: list[str] = []
        prefix_lines: list[str] = []
        for ln in lines:
            if is_table_sep(ln) or ln == header.header_row:
                continue
            if is_table_row(ln):
                data_rows.append(ln)
            else:
                prefix_lines.append(ln)

        if not data_rows:
            return [table_text]

        header_block = f"{header.header_row}\n{header.separator_row}"
        header_tokens = self.estimate_tokens(header_block)
        max_batch_tokens = max(100, self.max_tokens - header_tokens - 40)

        batches: list[str] = []
        current_batch: list[str] = []
        current_tokens = 0

        for row in data_rows:
            row_tokens = self.estimate_tokens(row)
            if current_tokens + row_tokens > max_batch_tokens and current_batch:
                batch_content = header_block + "\n" + "\n".join(current_batch)
                if prefix_lines and not batches:
                    batch_content = "\n".join(prefix_lines) + "\n\n" + batch_content
                batches.append(batch_content)
                current_batch = [row]
                current_tokens = row_tokens
            else:
                current_batch.append(row)
                current_tokens += row_tokens

        if current_batch:
            batch_content = header_block + "\n" + "\n".join(current_batch)
            if prefix_lines and not batches:
                batch_content = "\n".join(prefix_lines) + "\n\n" + batch_content
            batches.append(batch_content)

        return batches

    def chunk(self, text: str, **kwargs: Any) -> list[ChunkDraft]:
        if not text:
            return []

        if kwargs.get("reset_state", False):
            self.reset()

        paragraphs = text.split("\n\n")
        chunks: list[ChunkDraft] = []
        current_chunk_parts: list[str] = []
        current_tokens = 0
        chunk_idx = 0
        current_page: int | None = None

        def _build_and_append_chunk(parts: list[str], page: int | None) -> None:
            nonlocal chunk_idx
            full_content = "\n\n".join(parts).strip()
            if not full_content:
                return

            chunk_lines = full_content.splitlines()
            detected_hdr = extract_table_header(chunk_lines) or self._active_table_header

            if detected_hdr:
                projections = generate_linearized_projections(detected_hdr, chunk_lines)
                if projections:
                    full_content += "\n\n" + "\n".join(projections)

            chunk_page = page
            content_match = self._RE_PAGE_MARKER.search(full_content)
            if content_match:
                try:
                    chunk_page = int(content_match.group(1))
                except (TypeError, ValueError):
                    pass

            chunk_meta: dict[str, Any] = {}
            if detected_hdr and any(is_table_row(ln) for ln in chunk_lines):
                chunk_meta["has_table"] = True
                chunk_meta["table_cols"] = detected_hdr.col_count
                if detected_hdr.column_names:
                    chunk_meta["table_columns"] = [c for c in detected_hdr.column_names if c]

            chunks.append(
                ChunkDraft(
                    index=chunk_idx,
                    content=full_content,
                    token_count=self.estimate_tokens(full_content),
                    chunk_hash=self.compute_hash(full_content),
                    page_number=chunk_page,
                    metadata=chunk_meta,
                )
            )
            chunk_idx += 1

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

            # Major section heading resets active table schema
            if self._RE_HEADING.match(para_clean):
                self._active_table_header = None

            lines = [ln.strip() for ln in para_clean.split("\n") if ln.strip()]
            table_lines = [ln for ln in lines if is_table_row(ln)]
            is_table_para = len(table_lines) >= 1 and (len(table_lines) / len(lines) >= 0.5)

            para_units = [para_clean]

            if is_table_para:
                detected_hdr = extract_table_header(lines)
                if detected_hdr:
                    self._active_table_header = detected_hdr
                elif self._active_table_header and self.enable_table_header_injection:
                    first_tbl = table_lines[0]
                    if count_cols(first_tbl) == self._active_table_header.col_count:
                        injected = []
                        done = False
                        for ln in lines:
                            if is_table_row(ln) and not done:
                                injected.append(self._active_table_header.header_row)
                                injected.append(self._active_table_header.separator_row)
                                done = True
                            injected.append(ln)
                        para_clean = "\n".join(injected)

                if self.estimate_tokens(para_clean) > self.max_tokens:
                    para_units = self._split_oversized_table(para_clean, self._active_table_header)
                else:
                    para_units = [para_clean]

            for unit in para_units:
                unit_tokens = self.estimate_tokens(unit)
                if current_tokens + unit_tokens > self.max_tokens and current_chunk_parts:
                    _build_and_append_chunk(current_chunk_parts, current_page)
                    # Overlap: keep last part only if fitting and not an entire table
                    last_part = current_chunk_parts[-1]
                    if self.estimate_tokens(last_part) <= self.overlap_tokens and not is_table_para:
                        current_chunk_parts = [last_part, unit]
                        current_tokens = self.estimate_tokens(last_part) + unit_tokens
                    else:
                        current_chunk_parts = [unit]
                        current_tokens = unit_tokens
                else:
                    current_chunk_parts.append(unit)
                    current_tokens += unit_tokens

        if current_chunk_parts:
            _build_and_append_chunk(current_chunk_parts, current_page)

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


CHUNK_STRATEGY_REGISTRY: dict[str, type[BaseChunker]] = {
    # Canonical class names
    "clausebasedchunker": ClauseBasedChunker,
    "semanticchunker": SemanticChunker,
    "admissionsrecordchunker": AdmissionsRecordChunker,
    "implementationtaskchunker": ImplementationTaskChunker,
    # Supported aliases
    "clause": ClauseBasedChunker,
    "clause_based": ClauseBasedChunker,
    "regulations": ClauseBasedChunker,
    "semantic": SemanticChunker,
    "admissions": AdmissionsRecordChunker,
    "admission_program": AdmissionsRecordChunker,
    "admissions_record": AdmissionsRecordChunker,
    "task": ImplementationTaskChunker,
    "implementation_task": ImplementationTaskChunker,
    "action_plan": ImplementationTaskChunker,
}


def get_chunker(strategy: str = "SemanticChunker") -> BaseChunker:
    """Factory creating appropriate chunking strategy without silent fallback.

    Raises:
        AppException: with code INVALID_CHUNK_STRATEGY (status 400) if strategy is unknown.
    """
    if not strategy or not isinstance(strategy, str):
        raise AppException(
            message=f"Chiến lược cắt đoạn '{strategy}' không hợp lệ.",
            code="INVALID_CHUNK_STRATEGY",
            status_code=400,
        )
    clean_strat = strategy.lower().strip()
    chunker_cls = CHUNK_STRATEGY_REGISTRY.get(clean_strat)
    if not chunker_cls:
        raise AppException(
            message=f"Chiến lược cắt đoạn '{strategy}' không được hỗ trợ. Các chiến lược hợp lệ: ClauseBasedChunker, SemanticChunker, AdmissionsRecordChunker, ImplementationTaskChunker.",
            code="INVALID_CHUNK_STRATEGY",
            status_code=400,
        )
    return chunker_cls()

