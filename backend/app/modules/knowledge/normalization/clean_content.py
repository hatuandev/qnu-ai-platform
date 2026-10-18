"""Conservative, deterministic Markdown normalization and review diagnostics.

No OCR correction, inferred year, row merging, column trimming or page deletion.
Locations refer to Markdown lines, not unverified binary bounding boxes.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from typing import Any

VERSION = "clean-content-v1"
PAGE = re.compile(r"^<!--\s*(?:Trang|Page)\s+(\d+)\s*-->$", re.IGNORECASE)
NUMBER = re.compile(r"(?<!\w)[+-]?\d+(?:[.,/:–-]\d+)*(?:%|[A-Za-z]+)?")
LIST = re.compile(r"^(?:[-+*]\s|\d+[.)]\s|[a-zđ][.)]\s|\[\^[^]]+\]:)", re.IGNORECASE)
NEGATION = re.compile(r"\b(?:không|chưa|ngoại trừ|trừ khi|not|never|unless|except)\b", re.IGNORECASE)
WORD = re.compile(r"[^\W\d_]+")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def protected_line(line: str) -> bool:
    if line.startswith(("    ", "\t")):
        return True
    text = line.strip()
    return bool(not text or text.startswith(("#", "|", ">", "<", "$$", "\\[", "\\(", "    ", "\t"))
                or LIST.match(text) or re.search(r"[=<>∑√≤≥]|\$|\\[A-Za-z]+", text)
                or re.fullmatch(r"[\d\s.,%+*/:()–—-]+", text))


def normalize_content(markdown: str) -> str:
    """Reflow only ordinary prose soft-wraps; preserve code, math and indentation."""
    text = unicodedata.normalize("NFC", markdown).replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    fence: str | None = None
    math = False
    for raw in text.split("\n"):
        stripped = raw.lstrip()
        marker = re.match(r"(`{3,}|~{3,})", stripped)
        if marker:
            token = marker.group()
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append(raw)
            continue
        if fence or raw.startswith(("    ", "\t")):
            lines.append(raw)
            continue
        if stripped.startswith(("$$", r"\[")) or math:
            lines.append(raw)
            if stripped.startswith("$$") and stripped.count("$$") == 1:
                math = not math
            elif stripped.startswith(r"\["):
                math = r"\]" not in stripped
            elif r"\]" in stripped:
                math = False
            continue
        prefix = raw[:len(raw) - len(stripped)]
        line = prefix + re.sub(r"[ \t]+", " ", stripped).rstrip()
        if raw.endswith("  "):
            line += "  "
        previous = lines[-1] if lines else ""
        join = (len(previous) >= 40 and not protected_line(previous) and not protected_line(line)
                and not previous.endswith(("  ", "\\")) and previous[-1:].isalpha()
                and line[:1].islower())
        if join:
            lines[-1] += " " + line
        else:
            lines.append(line)
    return "\n".join(lines).strip("\n")


def inspect_content(markdown: str, baseline: str | None = None, page_count: int = 0) -> dict[str, Any]:
    """Heuristics indicate review work, never certify semantic/source correctness."""
    from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row

    issues: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    page: int | None = 1 if page_count == 1 else None
    table_width: int | None = None
    fence: str | None = None

    def issue(code: str, message: str, line: int | None, severity: str = "warning") -> None:
        issues.append({"id": digest(f"{code}:{page}:{line}")[:16], "code": code,
                       "message": message, "severity": severity,
                       "page_number": page, "line_number": line})

    for index, line in enumerate(markdown.splitlines(), 1):
        text = line.strip()
        if match := PAGE.fullmatch(text):
            page = int(match.group(1))
            table_width = None
            continue
        if "\ufffd" in line or "\x00" in line:
            issue("CONTENT_ENCODING_REVIEW", "Có ký tự lỗi; đối chiếu nguồn, không tự xóa.", index)
        if text.startswith(("```", "~~~")):
            token = re.match(r"(`{3,}|~{3,})", text).group()
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        if fence:
            kind = "code"
        elif text.startswith("|"):
            kind = "table"
            cells = _split_gfm_row(text)
            if table_width is None:
                table_width = len(cells)
                if any(not cell.strip() for cell in cells):
                    issue("CONTENT_HEADER_REVIEW", "Header bảng có ô trống; cần kiểm tra ngữ cảnh cột.", index)
            elif len(cells) != table_width:
                issue("CONTENT_TABLE_WIDTH", "Số ô không khớp header; giữ nguyên, không cắt hoặc điền ô.", index)
        else:
            table_width = None
            kind = ("heading" if text.startswith("#") else "footnote" if text.startswith("[^")
                    else "list" if LIST.match(text) else "formula" if re.search(r"\$|\\\[|[=∑√]", text)
                    else "paragraph")
            if text and not protected_line(line) and len(text) < 25:
                issue("CONTENT_FRAGMENT_REVIEW", "Đoạn ngắn; kiểm tra ngắt câu/thứ tự đọc nếu cần.", index, "info")
        if text:
            blocks.append({"kind": kind, "line_number": index, "page_number": page})
    # Document-wide findings have no verified page/line, not the final page scanned.
    page = None
    if fence:
        issue("CONTENT_UNCLOSED_CODE", "Khối code chưa đóng; kiểm tra cấu trúc.", None)
    if markdown.count("$$") % 2 or markdown.count(r"\[") != markdown.count(r"\]"):
        issue("CONTENT_FORMULA_REVIEW", "Dấu phân cách công thức chưa cân bằng.", None)
    refs = set(re.findall(r"\[\^([^]]+)\](?!:)", markdown))
    defs = set(re.findall(r"^\[\^([^]]+)\]:", markdown, re.MULTILINE))
    if refs - defs:
        issue("CONTENT_FOOTNOTE_REVIEW", "Chú thích được dẫn nhưng chưa có nội dung tương ứng.", None)
    changes: dict[str, Any] = {}
    if baseline is not None and baseline != markdown:
        # Comparisons are multisets: duplicated or removed numbers remain visible.
        for name, pattern in (("numbers", NUMBER), ("negations", NEGATION), ("wording", WORD)):
            before = Counter(pattern.findall(unicodedata.normalize("NFC", baseline).casefold()))
            after = Counter(pattern.findall(unicodedata.normalize("NFC", markdown).casefold()))
            if before != after:
                changes[name] = {"removed": list((before - after).elements()), "added": list((after - before).elements())}
                message = ("Có thay đổi từ ngữ (có thể gồm đơn vị/điều kiện); đối chiếu bản gốc."
                           if name == "wording" else "Có thay đổi số/năm hoặc phủ định; phải đối chiếu và ghi lý do.")
                issue(f"CONTENT_{name.upper()}_CHANGED", message, None)
        for name, pattern in (("table_rows", r"^\s*\|"), ("formulas", r"\$\$|\\\[|[=∑√]"),
                              ("footnotes", r"^\[\^[^]]+\]:")):
            if len(re.findall(pattern, markdown, re.MULTILINE)) < len(re.findall(pattern, baseline, re.MULTILINE)):
                changes[name] = "reduced"
                issue(f"CONTENT_{name.upper()}_REDUCED", "Bảng/công thức/chú thích bị giảm so với bản trước; cần xác nhận.", None)
    return {"version": VERSION, "content_hash": digest(markdown), "baseline_hash": digest(baseline) if baseline is not None else None,
            "issues": issues, "blocks": blocks, "changes": changes,
            "requires_review": any(i["severity"] != "info" for i in issues),
            "semantic_correctness": "not_measured"}


def attach_content_integrity(artifact: dict[str, Any], markdown: str, page_count: int,
                             baseline: str | None = None) -> None:
    report = inspect_content(markdown, baseline, page_count)
    for index, finding in enumerate(artifact["issues"]):
        report["issues"].append({"id": digest(f"source:{index}:{finding['code']}")[:16],
                                 "code": finding["code"], "severity": "warning",
                                 "message": finding.get("message") or f"Cấu trúc cần kiểm tra: {finding['code']}",
                                 "page_number": finding.get("page_number"), "line_number": None})
    for table in artifact.get("tables", []):
        for col, header in enumerate(table["headers"]):
            if len(set(re.findall(r"\b(?:19|20)\d{2}\b", header))) > 1:
                report["issues"].append({"id": digest(f"years:{table['id']}:{col}")[:16],
                                         "code": "CONTENT_HEADER_YEARS_AMBIGUOUS", "severity": "warning",
                                         "message": f"Header '{header}' có nhiều năm; không tự gán một năm cho các ô.",
                                         "page_number": table.get("page_number"), "line_number": None})
            if table["rows"] and all(col >= len(row) or not row[col].strip() for row in table["rows"]):
                report["issues"].append({"id": digest(f"empty:{table['id']}:{col}")[:16],
                                         "code": "CONTENT_EMPTY_COLUMN", "severity": "warning",
                                         "message": f"Cột '{header}' chưa có dữ liệu; không tự điền hoặc đổi thành 0.",
                                         "page_number": table.get("page_number"), "line_number": None})
    report["requires_review"] = any(i["severity"] != "info" for i in report["issues"])
    artifact["content_integrity"] = report
    known = {i["code"] for i in artifact["issues"]}
    artifact["issues"].extend(i for i in report["issues"] if i["severity"] != "info" and i["code"] not in known)
    if artifact["issues"] or baseline is not None:
        artifact["review"] = {"status": "required"}


def mark_repeated_margins(manifest: list[dict[str, Any]]) -> None:
    """Flag repeated edge text without treating repetition as permission to delete."""
    edges: list[tuple[dict[str, Any], list[str]]] = []
    counts: Counter[str] = Counter()
    for page in manifest:
        lines = [s.strip() for s in page.get("extracted_markdown", "").splitlines() if s.strip()]
        candidates = list(dict.fromkeys([lines[0], lines[-1]])) if lines else []
        candidates = [s for s in candidates if not s.startswith(("|", "```", "~~~"))]
        edges.append((page, candidates))
        counts.update(candidates)
    for page, candidates in edges:
        page["margin_candidates"] = [s for s in candidates if counts[s] >= 2]
