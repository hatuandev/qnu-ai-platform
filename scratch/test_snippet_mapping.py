import re
import sys
import numpy as np
from PIL import Image
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

def associate_snippets_with_regions(regions: list[dict], markdown_text: str, page_number: int = 1) -> list[dict]:
    if not markdown_text:
        return regions

    lines = [l.strip() for l in markdown_text.splitlines() if l.strip()]
    
    # 1. Extract table text
    table_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]
    table_text = "\n".join(table_lines) if table_lines else ""

    # 2. Extract paragraphs excluding table
    non_table_text = re.sub(r"(?:\|[^\n]+\|\n?)+", "\n\n", markdown_text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", non_table_text) if p.strip()]

    # Separate header & title from remaining paragraphs if page 1
    header_para = ""
    title_para = ""
    body_paras = []
    sig_para = ""

    for p in paragraphs:
        p_up = p.upper()
        if page_number == 1 and not header_para and any(kw in p_up for kw in ("CỘNG HÒA", "BỘ GIÁO DỤC", "ĐẠI HỌC QUY NHƠN")):
            header_para = p
        elif page_number == 1 and not title_para and any(kw in p_up for kw in ("THÔNG BÁO", "QUYẾT ĐỊNH", "QUY ĐỊNH", "KẾ HOẠCH")):
            title_para = p
        elif any(kw in p_up for kw in ("HIỆU TRƯỞNG", "PHÓ HIỆU TRƯỞNG", "TRƯỞNG PHÒNG", "GIÁM ĐỐC")):
            sig_para = p
        else:
            body_paras.append(p)

    # Now assign snippets
    body_idx = 0
    for r in regions:
        rtype = r.get("type", "text")
        if rtype == "table":
            r["text"] = table_text or "Bảng dữ liệu"
            r["content_snippet"] = (table_lines[0] if table_lines else "Bảng dữ liệu")[:160]
        elif rtype == "header" and header_para:
            r["text"] = header_para
            r["content_snippet"] = header_para[:160]
        elif rtype == "title" and title_para:
            r["text"] = title_para
            r["content_snippet"] = title_para[:160]
        elif rtype == "signature" and sig_para:
            r["text"] = sig_para
            r["content_snippet"] = sig_para[:160]
        else:
            if body_idx < len(body_paras):
                bp = body_paras[body_idx]
                r["text"] = bp
                r["content_snippet"] = bp[:160]
                body_idx += 1
            else:
                r["text"] = r.get("label", "Khối văn bản")
                r["content_snippet"] = r.get("label", "Khối văn bản")

    return regions

from scratch_test_detector_class import TestDetector
from scratch.test_md_mapping import sample_page_1_md

detector = TestDetector()
pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)

regs = detector._detect_morphology_regions(fitz_page=doc[0], markdown_text=sample_page_1_md, page_number=1)
regs = associate_snippets_with_regions(regs, sample_page_1_md, page_number=1)

print(f"=== PAGE 1 WITH SNIPPETS ({len(regs)} regions) ===")
for i, r in enumerate(regs, 1):
    snip = r.get('content_snippet', '').replace('\n', ' ')
    print(f"[{i:2d}] {r['type']:10s} y={r['top']:5.1f}% h={r['height']:5.1f}% -> {snip[:65]}")
