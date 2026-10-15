from pathlib import Path
import difflib
import json
import sys
import unicodedata

import pypdfium2 as pdfium

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent
OLD = Path("C:/Users/AnhTuan/Downloads/TUYỂN SINH - HẰNG-20261012T083111Z-1-001/TUYỂN SINH - HẰNG/BÁO CÁO TUYỂN SINH/Cẩm Nang Tuyển Sinh Đại Học Năm 2025 (1).pdf")
NEW = Path("D:/DuAnPhanMem/qnu-ai-platform/docs/tai_lieu/tuyen_sinh/Cẩm Nang Tuyển Sinh Đại Học Năm 2025 (1)1.pdf")


def text_of(path):
    document = pdfium.PdfDocument(str(path))
    pages = []
    for page in document:
        textpage = page.get_textpage()
        pages.append(textpage.get_text_range())
        textpage.close()
        page.close()
    document.close()
    return pages


old = text_of(OLD)
new = text_of(NEW)
old_words = unicodedata.normalize("NFC", " ".join(old)).split()
new_words = unicodedata.normalize("NFC", " ".join(new)).split()
matcher = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False)
changes = [
    {"type": op, "old": " ".join(old_words[i:j])[:220], "new": " ".join(new_words[k:l])[:220]}
    for op, i, j, k, l in matcher.get_opcodes() if op != "equal"
]
print(json.dumps({"old_pages": len(old), "new_pages": len(new), "token_sequence_similarity": matcher.ratio(),
                  "change_groups": len(changes), "examples": changes[:18]}, ensure_ascii=False))
document = pdfium.PdfDocument(str(NEW))
for n in [1, 2, 3, 4, 10, 11, 12, 18, 27, 42, 58, 89, 115, 116, 117]:
    page = document[n - 1]
    image = page.render(scale=1.8).to_pil().convert("RGB")
    image.save(OUT / f"reduced-{n:03}.png")
    page.close()
document.close()
