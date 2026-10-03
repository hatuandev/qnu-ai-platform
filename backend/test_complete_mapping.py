import re
import sys
import numpy as np
from PIL import Image
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

def associate_snippets_clean(
    regions: list[dict],
    markdown_text: str,
    page_number: int = 1,
    is_closing_page: bool = False,
) -> list[dict]:
    if not markdown_text or not regions:
        return regions

    raw = markdown_text.strip()
    header_text = ""
    table_text = ""
    table_snippet = ""
    sig_left_text = ""
    sig_right_text = ""

    # 1. Page 1 header table / text extraction
    if page_number == 1:
        m_hdr = re.search(r"<table[^>]*>[\s\S]*?(?:BỘ GIÁO DỤC|TRƯỜNG ĐẠI HỌC|CỘNG HÒA)[\s\S]*?</table>", raw, re.IGNORECASE)
        if m_hdr:
            h_html = m_hdr.group(0)
            clean_hdr = re.sub(r"<[^>]+>", "\n", h_html)
            clean_hdr = re.sub(r"\n\s*\n", "\n", clean_hdr).strip()
            header_text = clean_hdr
            raw = raw[:m_hdr.start()] + "\n" + raw[m_hdr.end():]

    # 2. Closing page signing block table / text extraction
    if is_closing_page:
        m_sig = re.search(r"<table[^>]*>[\s\S]*?(?:Nơi nhận|HIỆU TRƯỞNG)[\s\S]*?</table>", raw, re.IGNORECASE)
        if m_sig:
            sig_html = m_sig.group(0)
            tds = re.findall(r"<td[^>]*>([\s\S]*?)</td>", sig_html, re.IGNORECASE)
            if len(tds) >= 2:
                sig_left_text = re.sub(r"<[^>]+>", "\n", tds[0]).strip()
                sig_left_text = re.sub(r"\n\s*\n", "\n", sig_left_text)
                sig_right_text = re.sub(r"<[^>]+>", "\n", tds[1]).strip()
                sig_right_text = re.sub(r"\n\s*\n", "\n", sig_right_text)
            else:
                sig_right_text = re.sub(r"<[^>]+>", "\n", sig_html).strip()
            raw = raw[:m_sig.start()] + "\n" + raw[m_sig.end():]

    # 3. GFM Table extraction
    lines = raw.splitlines()
    table_lines = []
    non_tbl_lines = []
    in_tbl = False
    for line in lines:
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            in_tbl = True
            table_lines.append(s)
        else:
            if in_tbl:
                in_tbl = False
            non_tbl_lines.append(line)

    if table_lines:
        table_text = "\n".join(table_lines)
        if len(table_lines) > 0:
            table_snippet = table_lines[0][:160]

    remaining_raw = "\n".join(non_tbl_lines)
    # Remove HTML tags (<center>, <br>, <p>...)
    remaining_raw = re.sub(r"</?(?:br|center|p|div|span|td|tr|table)[^>]*>", "\n", remaining_raw, flags=re.IGNORECASE)

    raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", remaining_raw) if p.strip()]
    body_paras: list[str] = []
    title_para = ""

    for p in raw_paragraphs:
        if p.startswith("<!--"):
            continue
        clean_p = re.sub(r"\n+", "\n", p).strip()
        p_up = clean_p.upper()
        if page_number == 1 and not title_para and any(
            kw in p_up for kw in ("THÔNG BÁO", "THONG BAO", "QUYẾT ĐỊNH", "QUYET DINH", "QUY ĐỊNH", "QUY DINH", "KẾ HOẠCH", "KE HOACH")
        ):
            title_para = clean_p
        elif not header_text and page_number == 1 and any(
            kw in p_up for kw in ("BỘ GIÁO DỤC", "CỘNG HÒA XÃ HỘI")
        ):
            header_text = clean_p
        elif not sig_right_text and is_closing_page and any(
            kw in p_up for kw in ("HIỆU TRƯỞNG", "HIEU TRUONG", "PHÓ HIỆU TRƯỞNG")
        ):
            sig_right_text = clean_p
        elif not sig_left_text and is_closing_page and "NƠI NHẬN:" in p_up:
            sig_left_text = clean_p
        else:
            body_paras.append(clean_p)

    body_idx = 0
    for r in regions:
        rtype = r.get("type", "text")
        top_val = float(r.get("top", 0.0))
        label_val = str(r.get("label", ""))

        if rtype == "table":
            r["text"] = table_text or "Bảng dữ liệu"
            r["content_snippet"] = table_snippet or "Bảng dữ liệu"
        elif rtype == "header" and header_text:
            r["text"] = header_text
            r["content_snippet"] = header_text.splitlines()[0][:160]
        elif rtype == "title" and title_para:
            r["text"] = title_para
            r["content_snippet"] = title_para.splitlines()[0][:160]
        elif rtype == "signature":
            r["text"] = sig_right_text or label_val
            r["content_snippet"] = (sig_right_text.splitlines()[0] if sig_right_text else label_val)[:160]
        elif rtype == "list" and is_closing_page and top_val >= 70.0 and sig_left_text:
            r["text"] = sig_left_text
            r["content_snippet"] = (sig_left_text.splitlines()[0] if sig_left_text else label_val)[:160]
        else:
            if body_idx < len(body_paras):
                bp = body_paras[body_idx]
                r["text"] = bp
                r["content_snippet"] = bp.splitlines()[0][:160]
                body_idx += 1
            else:
                r["text"] = label_val or "Khối văn bản"
                r["content_snippet"] = label_val or "Khối văn bản"

    return regions

# Let's test with test_perfect_morphology regions!
from test_perfect_morphology import detect_morphology_refined
import asyncio
from app.core.database import AsyncSessionFactory
from sqlalchemy import select
from app.modules.knowledge.models import KnowledgeDocument

async def main():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == 'doc_64869d87a6f9'))
        doc = res.scalar_one_or_none()
        p_mds = (doc.doc_metadata or {}).get("page_markdowns") or {}

    pdf_path = r"d:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf"
    doc_fitz = fitz.open(pdf_path)

    for p_idx, page in enumerate(doc_fitz):
        p_num = p_idx + 1
        is_last = (p_num == len(doc_fitz))
        pix = page.get_pixmap(dpi=150)
        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        regs = detect_morphology_refined(pil_img, page_number=p_num, is_last_page=is_last)
        md = p_mds.get(str(p_num), "")
        mapped_regs = associate_snippets_clean(regs, md, page_number=p_num, is_closing_page=is_last)

        print(f"\n================ PAGE {p_num} (Mapped) ================")
        for idx, r in enumerate(mapped_regs, 1):
            coords = f"top={r['top']:4.1f}%, left={r['left']:4.1f}%, w={r['width']:4.1f}%, h={r['height']:4.1f}%"
            txt_preview = repr(r['text'][:50].replace('\n', ' '))
            snip_preview = repr(r['content_snippet'][:40])
            print(f"[{idx:2d}] {r['type']:10s} | {coords} | {r['label']:18s} | snip={snip_preview}")

asyncio.run(main())
