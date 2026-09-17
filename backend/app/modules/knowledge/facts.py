"""Structured Fact Extraction — Vietnamese Admissions Tables to Fact Records.

Converts raw ``ExtractedTable`` structures (headers + rows) into meaningful
``knowledge_facts`` rows (entity/attribute/value) that the RAG Fact Layer can
match by keyword: major names, quotas, cutoff scores, combos, methods, fees.

Honesty rules: unrecognized columns are skipped (never guessed), empty cells
produce no facts, and every emitted fact keeps its source location
(document, page, table index, row) in ``raw_data`` for citation tracing.
"""

from __future__ import annotations

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"(19|20)\d{2}")
_CONFIDENCE_EXACT = 0.95
_CONFIDENCE_HEURISTIC = 0.80


def _normalize_header(header: str) -> str:
    """Lowercase, strip markdown/accents-noise and collapse spaces."""
    text = re.sub(r"[*_`~]", "", header or "")
    text = unicodedata.normalize("NFC", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def parse_vietnamese_int(raw: str | None) -> int | None:
    """Parse Vietnamese integers: '180' -> 180, '1.200' -> 1200, '180 sinh viên' -> 180.

    Returns None for anything ambiguous: decimals ('2.5'), lists ('1,4'),
    or tokens whose dots are not clean thousands separators.
    """
    if raw is None:
        return None
    text = re.sub(r"\s+", "", str(raw).strip())
    if not text or "," in text:
        return None
    match = re.match(r"-?(\d[\d.]*)", text)
    if not match:
        return None
    token, rest = match.group(1), text[match.end():]
    if re.search(r"\d", rest):
        return None
    groups = token.split(".")
    if len(groups) > 1 and any(len(g) != 3 for g in groups[1:]):
        return None  # e.g. '2.5' is a decimal, not two thousand five
    digits = "".join(groups)
    if not digits.isdigit():
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def parse_vietnamese_float(raw: str | None) -> float | None:
    """Parse Vietnamese decimals: '24,5' -> 24.5, '16.500.000' -> 16500000."""
    if raw is None:
        return None
    text = re.sub(r"\s+", "", str(raw).strip())
    if not text:
        return None
    match = re.search(r"-?\d[\d.,]*", text)
    if not match:
        return None
    token = match.group(0).lstrip("-")
    if "," in token and "." in token:
        token = token.replace(".", "").replace(",", ".")
    elif "," in token:
        token = token.replace(",", ".")
    else:
        parts = token.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) > 1):
            token = "".join(parts)  # thousands separator
    try:
        return float(token)
    except ValueError:
        return None


# Header keyword -> column role. Order matters: specific first.
_ROLE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("code", ("mã ngành", "mã xét tuyển", "mã số", "mã")),
    ("name", ("tên ngành", "tên chương trình", "ngành đào tạo", "ngành", "tên")),
    ("quota", ("chỉ tiêu", "số lượng tuyển", "số lượng", "sl")),
    ("benchmark", ("điểm chuẩn", "điểm trúng tuyển", "điểm xét tuyển", "điểm")),
    ("combos", ("tổ hợp môn", "tổ hợp xét tuyển", "tổ hợp", "môn xét tuyển")),
    ("method", ("phương thức tuyển sinh", "phương thức", "hình thức xét")),
    ("tuition", ("học phí", "mức thu", "học phí/năm")),
)

# NOTE: method/combos/name/code columns are always kept as raw text —
# lists like "1,4" must NEVER be parsed as decimals (see _cell_facts).
def detect_column_role(header: str) -> tuple[str | None, str | None]:
    """Map a header to (role, year). Returns (None, year) when unrecognized."""
    normalized = _normalize_header(header)
    year_match = _YEAR_RE.search(normalized)
    year = year_match.group(0) if year_match else None
    for role, keywords in _ROLE_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return role, year
    return None, year


class FactExtractor:
    """Turns extracted tables into structured fact dicts for KnowledgeFact rows."""

    def extract(
        self,
        tables: list,
        collection_id: str,
        document_id: str,
    ) -> list[dict]:
        """Extract facts from all tables; always keeps one summary fact per table."""
        facts: list[dict] = []
        for table_idx, table in enumerate(tables):
            headers = [str(h or "").strip() for h in (table.headers or [])]
            rows = table.rows or []
            if len(headers) < 2 or not rows:
                continue
            facts.append(
                {
                    "collection_id": collection_id,
                    "document_id": document_id,
                    "entity_name": f"Bảng {table_idx + 1} (trang {table.page_number})",
                    "entity_type": "table",
                    "attribute_name": "Tiêu đề cột",
                    "attribute_value": ", ".join(headers),
                    "confidence": 1.0,
                    "raw_data": {"rows_sample": rows[:3], "page_number": table.page_number},
                }
            )
            facts.extend(
                self._extract_row_facts(
                    headers, rows, table_idx, table.page_number, collection_id, document_id
                )
            )
        return facts

    def _extract_row_facts(
        self,
        headers: list[str],
        rows: list[list[str]],
        table_idx: int,
        page_number: int,
        collection_id: str,
        document_id: str,
    ) -> list[dict]:
        roles: list[tuple[str | None, str | None]] = [detect_column_role(h) for h in headers]
        if not any(role in ("name", "code") for role, _ in roles):
            return []  # no entity column -> only the summary fact survives

        facts: list[dict] = []
        for row_idx, row in enumerate(rows):
            cells = [(row[i] if i < len(row) else "") or "" for i in range(len(headers))]
            # Keep EVERY recognized column (same role may repeat per year).
            role_cells: list[tuple[str, str | None, str]] = [
                (role, year, cell.strip())
                for (role, year), cell in zip(roles, cells)
                if role and cell.strip()
            ]
            named = [(role, year, cell) for role, year, cell in role_cells if role in ("name", "code")]
            name = next((cell for role, _, cell in named if role == "name"), "")
            code = next((cell for role, _, cell in named if role == "code"), "")
            if not name and not code:
                continue
            entity = f"{name} ({code})" if name and code else (name or code)
            location = {
                "table_index": table_idx,
                "row_index": row_idx,
                "page_number": page_number,
            }
            facts.extend(
                self._cell_facts(
                    role_cells, entity, collection_id, document_id, location
                )
            )
        return facts

    def _cell_facts(
        self,
        role_cells: list[tuple[str, str | None, str]],
        entity: str,
        collection_id: str,
        document_id: str,
        location: dict,
    ) -> list[dict]:
        facts: list[dict] = []

        def add(attribute: str, value: str, confidence: float) -> None:
            facts.append(
                {
                    "collection_id": collection_id,
                    "document_id": document_id,
                    "entity_name": entity,
                    "entity_type": "major",
                    "attribute_name": attribute,
                    "attribute_value": value,
                    "confidence": confidence,
                    "raw_data": dict(location),
                }
            )

        for role, year, cell in role_cells:
            suffix = f" {year}" if year else ""
            if role == "code":
                add("Mã ngành", cell, _CONFIDENCE_EXACT)
            elif role == "quota":
                quota = parse_vietnamese_int(cell)
                if quota is not None:
                    add(f"Chỉ tiêu{suffix}".strip(), str(quota), _CONFIDENCE_EXACT)
            elif role == "benchmark":
                score = parse_vietnamese_float(cell)
                if score is not None:
                    label = f"Điểm chuẩn{suffix}".strip()
                    text = str(int(score)) if float(score).is_integer() else str(score)
                    add(label, text, _CONFIDENCE_EXACT)
            elif role == "combos":
                add("Tổ hợp xét tuyển", cell, _CONFIDENCE_HEURISTIC)
            elif role == "method":
                add("Phương thức tuyển sinh", cell, _CONFIDENCE_HEURISTIC)
            elif role == "tuition":
                fee = parse_vietnamese_int(cell)
                label = f"Học phí{suffix}".strip()
                if fee is not None:
                    add(label, str(fee), _CONFIDENCE_EXACT)
                else:
                    add(label, cell, _CONFIDENCE_HEURISTIC)
        return facts


fact_extractor = FactExtractor()
