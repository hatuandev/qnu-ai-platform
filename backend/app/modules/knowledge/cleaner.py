"""Markdown Document Cleaner & Vietnamese Text Normalization."""

from __future__ import annotations

import re
import unicodedata

# Regex patterns for cleaning document text
_RE_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
_RE_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")
_RE_PAGE_NUMBERS = re.compile(
    r"^\s*(?:Trang\s+\d+(?:\s*/\s*\d+)?|[-—~–]\s*\d+\s*[-—~–]|\d+\s*/\s*\d+|\d{1,3})\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_RE_HEADING_NORMALIZE = re.compile(
    r"^(điều|khoản|chương|mục|phần)\s+(\d+|[IVXLCDM]+)[\.:]?\s*", re.IGNORECASE | re.MULTILINE
)


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and (s.endswith("|") or "|" in s[1:])


def _is_table_sep(line: str) -> bool:
    s = line.strip()
    if not s.startswith("|"):
        return False
    inner = s[1:-1] if s.endswith("|") else s.lstrip("|")
    cells = [c.strip() for c in inner.split("|")]
    return len(cells) > 0 and all(re.match(r"^:?-+:?$", c.replace(" ", "")) for c in cells if c)


def _count_cols(line: str) -> int:
    clean_s = line.strip().replace(r"\|", "___ESCAPED_PIPE___")
    inner = clean_s[1:-1] if clean_s.endswith("|") else clean_s.lstrip("|")
    return len(inner.split("|"))


def _is_likely_header_row(cells: list[str]) -> bool:
    """Morphological check: determine whether table cells represent column headers rather than data rows."""
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


def _normalize_markdown_table_block(table_lines: list[str]) -> list[str]:
    """Chuẩn hóa một khối bảng Markdown: căn chỉnh số cột, định dạng header và separator."""
    if not table_lines:
        return []

    cleaned_rows = [ln.strip() for ln in table_lines if ln.strip()]
    if not cleaned_rows:
        return []

    first_data = next((ln for ln in cleaned_rows if not _is_table_sep(ln)), None)
    if not first_data:
        return []

    expected_cols = _count_cols(first_data)
    if expected_cols < 2:
        return cleaned_rows

    result: list[str] = []

    for idx, row in enumerate(cleaned_rows):
        if _is_table_sep(row):
            sep_cells = [":---:" if c_i == 0 and expected_cols > 3 else ":---" for c_i in range(expected_cols)]
            result.append("| " + " | ".join(sep_cells) + " |")
            continue

        clean_s = row.replace(r"\|", "___ESCAPED_PIPE___")
        inner = clean_s[1:-1] if clean_s.endswith("|") else clean_s.lstrip("|")
        raw_cells = [c.replace("___ESCAPED_PIPE___", r"\|").strip() for c in inner.split("|")]

        if len(raw_cells) < expected_cols:
            raw_cells += [""] * (expected_cols - len(raw_cells))
        elif len(raw_cells) > expected_cols:
            raw_cells = raw_cells[:expected_cols]

        result.append("| " + " | ".join(raw_cells) + " |")

        # Tự động chèn dòng phân cách header sau dòng đầu tiên nếu thiếu VÀ dòng đầu tiên là header thực sự
        if (
            idx == 0
            and (len(cleaned_rows) == 1 or not _is_table_sep(cleaned_rows[1]))
            and _is_likely_header_row(raw_cells)
        ):
            sep_cells = [":---:" if c_i == 0 and expected_cols > 3 else ":---" for c_i in range(expected_cols)]
            result.append("| " + " | ".join(sep_cells) + " |")

    return result


def _is_orphan_markdown_row(line: str) -> bool:
    """Check if a markdown table row lacks primary keys (empty STT/Code) but has trailing text."""
    if not _is_table_row(line) or _is_table_sep(line):
        return False
    clean_s = line.replace(r"\|", "___PIPE___")
    inner = clean_s[1:-1] if clean_s.endswith("|") else clean_s.lstrip("|")
    cells = [c.replace("___PIPE___", r"\|").strip() for c in inner.split("|")]
    if len(cells) < 3:
        return False
    first_empty = not any(cells[:min(3, len(cells) - 1)])
    has_trailing = any(len(c) > 0 for c in cells[min(3, len(cells) - 1):])
    return first_empty and has_trailing


def _merge_orphan_into_row(target_row: str, orphan_row: str) -> str:
    """Merge trailing text of an orphan continuation row into the target table row."""
    clean_t = target_row.replace(r"\|", "___PIPE___")
    inner_t = clean_t[1:-1] if clean_t.endswith("|") else clean_t.lstrip("|")
    t_cells = [c.replace("___PIPE___", r"\|").strip() for c in inner_t.split("|")]

    clean_o = orphan_row.replace(r"\|", "___PIPE___")
    inner_o = clean_o[1:-1] if clean_o.endswith("|") else clean_o.lstrip("|")
    o_cells = [c.replace("___PIPE___", r"\|").strip() for c in inner_o.split("|")]

    max_c = max(len(t_cells), len(o_cells))
    t_cells += [""] * (max_c - len(t_cells))
    o_cells += [""] * (max_c - len(o_cells))

    merged = []
    for tc, oc in zip(t_cells, o_cells):
        if tc and oc:
            merged.append(f"{tc} {oc}".strip())
        else:
            merged.append(tc or oc)
    return "| " + " | ".join(merged) + " |"


def _stitch_table_continuations(text: str) -> str:
    """Nối các bảng bị ngắt qua ranh giới trang (<!-- Trang N --> hoặc ---) mà không làm mất hàng."""
    lines = text.splitlines()
    result: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if _is_table_row(line) and not _is_table_sep(line):
            result.append(line)
            cols = _count_cols(line)

            j = i + 1
            interstitial = []
            while j < n and (
                not lines[j].strip()
                or lines[j].strip() == "---"
                or bool(re.match(r"^<!--\s*(?:Trang|Page)\s+\d+\s*-->$", lines[j].strip(), re.IGNORECASE))
            ):
                interstitial.append(lines[j])
                j += 1

            has_page_boundary = any(
                bool(re.match(r"^<!--\s*(?:Trang|Page)\s+\d+\s*-->$", x.strip(), re.IGNORECASE))
                or x.strip() == "---"
                for x in interstitial
            )

            if has_page_boundary and j < n and _is_table_row(lines[j]):
                next_cols = _count_cols(lines[j])
                if next_cols == cols:
                    k = j
                    # Check if lines[k] is an orphan continuation row
                    if _is_orphan_markdown_row(lines[k]) and result:
                        # Merge into previous table's last row!
                        result[-1] = _merge_orphan_into_row(result[-1], lines[k])
                        k += 1
                        # If a separator was inserted under the orphan row, skip it
                        if k < n and _is_table_sep(lines[k]):
                            k += 1
                    else:
                        # Repeated header followed by separator on continuation page
                        if k + 1 < n and _is_table_sep(lines[k + 1]):
                            k += 2
                        elif _is_table_sep(lines[k]):
                            k += 1

                    result.extend(interstitial)
                    i = k - 1
            i += 1
            continue

        result.append(line)
        i += 1

    return "\n".join(result)



def clean_markdown_text(raw_text: str) -> str:
    """Clean and normalize raw extracted markdown/text from documents."""
    if not raw_text:
        return ""

    # 1. Unicode NFC normalization (Zero Mojibake)
    text = unicodedata.normalize("NFC", raw_text)

    # 2. Strip null bytes, form feeds, and BOM
    text = text.replace("\x00", "").replace("\x0c", "\n\n").replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Strip dead/local image artifacts (e.g. ![img-0.jpeg](...))
    text = re.sub(
        r"!\[.*?\]\((?:img-\d+\.(?:jpeg|jpg|png|webp)|image\d*\.(?:png|jpg|jpeg)|local:.*?|data:image/[^)]+)\)",
        "",
        text,
    )

    # 4. Remove standalone page number lines
    text = _RE_PAGE_NUMBERS.sub("", text)

    # 5. Normalize multiple spaces (preserving newlines)
    text = _RE_MULTIPLE_SPACES.sub(" ", text)

    # 6. Normalize tables
    lines = text.split("\n")
    cleaned_lines: list[str] = []
    current_table: list[str] = []

    for line in lines:
        stripped = line.strip()
        if _is_table_row(stripped):
            current_table.append(stripped)
        else:
            if current_table:
                cleaned_lines.extend(_normalize_markdown_table_block(current_table))
                current_table = []
            cleaned_lines.append(stripped)

    if current_table:
        cleaned_lines.extend(_normalize_markdown_table_block(current_table))

    text = "\n".join(cleaned_lines)

    # 7. Stitch table continuations across page markers
    text = _stitch_table_continuations(text)

    # 8. Limit consecutive blank lines to at most 2
    text = _RE_MULTIPLE_NEWLINES.sub("\n\n", text)

    return text.strip()


def extract_sections_metadata(text: str) -> list[dict[str, str]]:
    """Identify key legal document sections (Điều, Khoản, Chương) for metadata indexing."""
    sections = []
    for match in _RE_HEADING_NORMALIZE.finditer(text):
        sections.append(
            {
                "type": match.group(1).capitalize(),
                "number": match.group(2),
                "match": match.group(0).strip(),
            }
        )
    return sections


# Regex patterns for administrative document metadata (Decree 30/2020/ND-CP)
_RE_ADMIN_DATE = re.compile(
    r"(?:ngày|ng\u00e0y)\s+0?([1-9]|[12][0-9]|3[01])\s+th\u00e1ng\s+0?([1-9]|1[0-2])\s+n\u0103m\s+(19\d{2}|20\d{2})",
    re.IGNORECASE,
)
_RE_ADMIN_DOC_NUMBER = re.compile(
    r"(?:Số|S\u1ed1)\s*:\s*([0-9]+/[A-Z\u0110\u0111a-z0-9\-_/]+)",
    re.IGNORECASE,
)
_RE_ADMIN_SUBJECT = re.compile(
    r"(?:V/v|V\u1ec1\s+vi\u1ec7c)\s*[:\-]?\s*([^\n\r]+)",
    re.IGNORECASE,
)
_RE_ADMIN_AUTHORITY = re.compile(
    r"(?:TRƯỜNG\s+ĐẠI\s+HỌC\s+QUY\s+NHƠN|BỘ\s+GIÁO\s+DỤC\s+VÀ\s+ĐÀO\s+TẠO|UBND\s+[^\n\r,]+)",
    re.IGNORECASE,
)
_RE_ADMIN_HEADING_TYPE = re.compile(
    r"^\s*(QUYẾT\s+ĐỊNH|THÔNG\s+BÁO|KẾ\s+HOẠCH|HƯỚNG\s+DẪN|CHỈ\s+THỊ|NGHỊ\s+QUYẾT|BÁO\s+CÁO|QUY\s+CHẾ|QUY\s+ĐỊNH|TỜ\s+TRÌNH|CÔNG\s+VĂN|BIÊN\s+BẢN|ĐỀ\s+ÁN|PHƯƠNG\s+ÁN)\b",
    re.IGNORECASE | re.MULTILINE,
)
_RE_ADMIN_SIGNER = re.compile(
    r"(?:HIỆU\s+TRƯỞNG|PHÓ\s+HIỆU\s+TRƯỞNG|GIÁM\s+ĐỐC|TRƯỞNG\s+PHÒNG|CHỦ\s+TỊCH)\s*\n+([A-ZÀ-Ỹ\s]{3,35})\b",
    re.MULTILINE,
)

_ND30_ABBREV_MAP = {
    "QD": "quyet_dinh",
    "QĐ": "quyet_dinh",
    "QC": "quy_che",
    "NQ": "nghi_quyet",
    "CT": "chi_thi",
    "TB": "thong_bao",
    "HD": "huong_dan",
    "KH": "ke_hoach",
    "PA": "phuong_an",
    "DA": "de_an",
    "ĐA": "de_an",
    "BC": "bao_cao",
    "BB": "bien_ban",
    "TTR": "to_trinh",
    "HDG": "hop_dong",
    "CV": "cong_van",
    "TT": "quy_dinh",
    "CTR": "chuong_trinh",
}


def extract_administrative_metadata(text: str) -> dict[str, object]:
    """Tự động trích xuất metadata thể thức văn bản hành chính theo Nghị định 30/2020/NĐ-CP.

    Thuật toán dựa trên các bất biến cú pháp thể thức văn bản hành chính:
    - issued_date: Ngày ký ban hành (dd/mm/yyyy -> datetime.date)
    - document_number: Số hiệu văn bản
    - document_type_code: Mã loại văn bản chuẩn NĐ 30
    - title: Trích yếu / tiêu đề văn bản
    - issuing_authority: Cơ quan ban hành
    - signer: Người ký văn bản
    """
    if not text:
        return {}

    from datetime import date

    from app.modules.document_types.catalog import normalize_document_type_code

    result: dict[str, object] = {}
    header_chunk = text[:3500]  # Thể thức hành chính NĐ 30 luôn nằm ở trang đầu

    # 1. Trích xuất Ngày ban hành
    date_match = _RE_ADMIN_DATE.search(header_chunk)
    if date_match:
        try:
            day = int(date_match.group(1))
            month = int(date_match.group(2))
            year = int(date_match.group(3))
            result["issued_date"] = date(year, month, day)
        except ValueError:
            pass

    # 2. Trích xuất Số hiệu văn bản
    num_match = _RE_ADMIN_DOC_NUMBER.search(header_chunk)
    if num_match:
        doc_num = num_match.group(1).strip()
        result["document_number"] = doc_num

        # 3. Phân tích loại văn bản từ số hiệu (vd: 123/QĐ-ĐHQN -> QĐ)
        if "/" in doc_num:
            suffix_part = doc_num.split("/", 1)[1]
            abbrev = suffix_part.split("-")[0].strip().upper()
            if abbrev in _ND30_ABBREV_MAP:
                result["document_type_code"] = _ND30_ABBREV_MAP[abbrev]

    # 4. Nếu chưa có loại văn bản từ số hiệu, tìm từ tiêu đề loại văn bản ở phần đầu
    if "document_type_code" not in result:
        type_match = _RE_ADMIN_HEADING_TYPE.search(header_chunk)
        if type_match:
            detected_type = normalize_document_type_code(type_match.group(1))
            if detected_type:
                result["document_type_code"] = detected_type

    # 5. Trích xuất Trích yếu nội dung (Tiêu đề)
    subject_match = _RE_ADMIN_SUBJECT.search(header_chunk)
    if subject_match:
        subj = subject_match.group(1).strip()
        subj = re.sub(r"^[\s:\-\"]+", "", subj).strip("\"' ")
        if len(subj) > 5:
            result["title"] = subj

    # 6. Trích xuất Cơ quan ban hành
    if re.search(r"TRƯỜNG\s+ĐẠI\s+HỌC\s+QUY\s+NHƠN", header_chunk, re.IGNORECASE):
        result["issuing_authority"] = "Trường Đại học Quy Nhơn"
    else:
        auth_match = _RE_ADMIN_AUTHORITY.search(header_chunk)
        if auth_match:
            result["issuing_authority"] = auth_match.group(0).strip().title()

    # 7. Trích xuất Người ký ở 2500 ký tự cuối văn bản
    tail_chunk = text[-2500:]
    signer_match = _RE_ADMIN_SIGNER.search(tail_chunk)
    if signer_match:
        raw_signer = signer_match.group(1).strip()
        if len(raw_signer) >= 3 and not any(kw in raw_signer.upper() for kw in ["NƠI NHẬN", "LƯU:"]):
            result["signer"] = raw_signer.title()

    return result
