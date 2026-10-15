from pathlib import Path
import json
import logging
import sys

import pdfplumber
import pypdfium2 as pdfium

sys.stdout.reconfigure(encoding="utf-8")
logging.getLogger("pdfminer").setLevel(logging.ERROR)
SOURCE = Path("C:/Users/AnhTuan/Downloads/TUYỂN SINH - HẰNG-20261012T083111Z-1-001/TUYỂN SINH - HẰNG/BÁO CÁO TUYỂN SINH/Cẩm Nang Tuyển Sinh Đại Học Năm 2025 (1).pdf")
OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)
pdf = pdfium.PdfDocument(str(SOURCE))
for n in [1, 2, 3, 4, 5, 38, 88, 106, 107, 108]:
    page = pdf[n - 1]
    image = page.render(scale=1.6).to_pil().convert("RGB")
    image.save(OUT / f"source-{n:03}.png")
    page.close()
pdf.close()
with pdfplumber.open(SOURCE) as document:
    items = []
    for n, page in enumerate(document.pages, 1):
        cleaned = page.dedupe_chars(tolerance=2, extra_attrs=("fontname", "size"))
        lines = cleaned.extract_text_lines(layout=False, x_tolerance=2, y_tolerance=3)
        items.append({"page": n, "chars": len(cleaned.chars), "lines": [
            {"text": line["text"], "x0": line["x0"], "top": line["top"],
             "bottom": line["bottom"], "size": max((ch["size"] for ch in line["chars"]), default=0)}
            for line in lines], "images": len(page.images)})
        page.close()
    (OUT / "source_analysis.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"pages": len(items), "sparse_pages": [p["page"] for p in items if p["chars"] < 80],
                  "analysis": str(OUT / "source_analysis.json")}, ensure_ascii=False))
