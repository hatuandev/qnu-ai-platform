"""scripts/check_mojibake.py — Kiểm tra tự động lỗi mã hóa ký tự (Mojibake) và vỡ font tiếng Việt.

Sử dụng:
    uv run python scripts/check_mojibake.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Đảm bảo stdout/stderr trên Windows luôn xuất chuẩn UTF-8
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Các pattern Mojibake thường gặp khi UTF-8 bị decode nhầm sang Windows-1252 hoặc ISO-8859-1
MOJIBAKE_PATTERNS = [
    # Unicode replacement character
    (re.compile(r"\ufffd"), "Ký tự thay thế Unicode lỗi (\\ufffd - )"),
    # Chuỗi byte UTF-8 tiếng Việt bị decode nhầm bằng latin1/cp1252
    (re.compile(r"(?:Ã¡|Ã |Ã£|Ã³|Ã²|Ãµ|Ã¹|Ãº|Ãª|Ã´|Ã¢|Ä‘|Ä\x91|á»|áº)"), "Mojibake tiếng Việt (Double UTF-8 / CP1252 decoding)"),
    # OCR scan artifacts đặc thù
    (re.compile(r"(?:Quyt\s*`<nh|B~\s*GIA\?O|Chuong\s+[\?]+|\?oAn\s+\?cc)"), "Ký tự rác OCR scan bị vỡ font"),
    # Question mark anomalies inside Vietnamese words (e.g. "Quy?n", "Tr??ng", "ng??i")
    (re.compile(r"(?:[À-ỹ]\?+[A-Za-zÀ-ỹ]|[A-Za-zÀ-ỹ]\?+[À-ỹ]|[A-Za-zÀ-ỹ]\?{2,}[A-Za-zÀ-ỹ])"), "Ký tự tiếng Việt bị thay thế bằng dấu hỏi '?'"),
]

# Thư mục cần kiểm tra
SCAN_DIRS = [
    Path("frontend/src"),
    Path("backend/app"),
    Path(".agents/skills"),
]

# Đuôi tệp cần quét
TARGET_EXTS = {".ts", ".tsx", ".py", ".json", ".md", ".css"}

# Bỏ qua các tệp build, cache, test snapshot nhị phân
EXCLUDE_PARTS = {"node_modules", "dist", ".vite", "__pycache__", ".pytest_cache", ".git", ".tempmediaStorage"}


def scan_file(file_path: Path) -> list[tuple[int, str, str]]:
    """Kiểm tra một tệp tin xem có lỗi Mojibake hoặc lỗi encoding không."""
    issues: list[tuple[int, str, str]] = []

    # 1. Kiểm tra UTF-8 decoding
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        issues.append((1, "Lỗi Encoding", f"Tệp không phải là UTF-8 hợp lệ: {exc}"))
        return issues

    # 2. Quét từng dòng với patterns
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        # Bỏ qua dòng kiểm tra regex chính nó
        if "re.compile" in line or "MOJIBAKE_PATTERNS" in line:
            continue
        for pattern, desc in MOJIBAKE_PATTERNS:
            match = pattern.search(line)
            if match:
                snippet = line.strip()[:80]
                issues.append((idx, desc, snippet))
                break

    return issues


def main() -> int:
    print("==================================================")
    print("🔍 QNU AI Platform — Bộ Kiểm Toán Zero Mojibake")
    print("==================================================")

    root = Path(".")
    total_files = 0
    total_issues = 0

    for scan_dir in SCAN_DIRS:
        target_dir = root / scan_dir
        if not target_dir.exists():
            continue

        for file_path in target_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in TARGET_EXTS:
                continue
            if any(part in file_path.parts for part in EXCLUDE_PARTS):
                continue

            total_files += 1
            issues = scan_file(file_path)
            if issues:
                total_issues += len(issues)
                print(f"\n❌ [MOJIBAKE PHÁT HIỆN] {file_path}")
                for line_no, desc, snippet in issues:
                    print(f"   Dòng {line_no}: [{desc}] -> {snippet}")

    print("\n--------------------------------------------------")
    print(f"Tổng số tệp đã quét: {total_files}")
    if total_issues == 0:
        print("✅ TUYỆT VỜI: Không phát hiện bất kỳ lỗi Mojibake hay vỡ font tiếng Việt nào!")
        print("==================================================")
        return 0
    else:
        print(f"⚠️ CẢNH BÁO: Phát hiện {total_issues} vị trí có nguy cơ Mojibake!")
        print("==================================================")
        return 1


if __name__ == "__main__":
    sys.exit(main())
