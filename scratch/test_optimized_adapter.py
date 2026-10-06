import asyncio
import os
import sys
import time
import base64
import json
import pymupdf as fitz
import httpx

sys.path.insert(0, os.path.abspath("backend"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.modules.knowledge.chunker import get_chunker
from app.modules.ocr.cleaner import post_process_ocr_output

async def run_optimized_ocr(pdf_path: str):
    with open(pdf_path, "rb") as f:
        content = f.read()

    doc = fitz.open(stream=content, filetype="pdf")
    pages_count = len(doc)
    page_images = []
    for p_idx in range(pages_count):
        page = doc[p_idx]
        # DPI 110 is sweet spot for OCR: sharp text, ~50% fewer visual tokens than DPI 150
        pix = page.get_pixmap(dpi=110)
        img_bytes = pix.tobytes("jpeg")
        page_images.append((p_idx + 1, img_bytes))
    doc.close()

    print(f"Loaded {pages_count} pages from {os.path.basename(pdf_path)}")

    prompt = (
        "Bạn là chuyên gia OCR tài liệu hành chính tiếng Việt cao cấp của Trường Đại học Quy Nhơn (QNU). "
        "Hãy bóc tách toàn bộ nội dung của trang tài liệu này sang định dạng Markdown GFM tiếng Việt hoàn chỉnh.\n\n"
        "Quy tắc bắt buộc:\n"
        "1. BẢO TOÀN NỘI DUNG & CHÍNH TẢ: Giữ nguyên 100% nội dung chữ, tiêu đề cấp mục (#, ##, ###), "
        "số hiệu văn bản, ngày tháng, họ tên, các điều khoản, căn cứ pháp lý, ghi chú, con dấu và chữ ký.\n"
        "2. BẢNG BIỂU CHUẨN GFM: Mọi bảng biểu phải chuyển thành bảng Markdown hoàn chỉnh với hàng tiêu đề "
        "và hàng phân cách '|:---|:---|'. Giữ nguyên vẹn toàn bộ các hàng và cột. Mỗi phương án đào tạo, mức học phí "
        "tách thành 1 hàng độc lập đầy đủ thông tin.\n"
        "3. CẤM THẺ HTML THÔ: Tuyệt đối không dùng <table>, <tr>, <td>, <br>. Sử dụng thuần túy Markdown GFM.\n"
        "4. CHUẨN UTF-8: Đảm bảo toàn bộ ký tự tiếng Việt hiển thị chính xác theo chuẩn Unicode NFC."
    )

    t_total_start = time.time()
    extracted_pages = []

    for p_num, img_bytes in page_images:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        print(f"\n--- Đang xử lý Trang {p_num}/{pages_count} (img size: {len(img_bytes)//1024} KB) ---")
        t_page_start = time.time()

        payload = {
            "model": "qwen3-vl:8b",
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64],
                }
            ],
            "options": {
                "temperature": 0.1,
                "num_predict": 16384,  # Guarantee plenty of headroom for thinking + full markdown
            },
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
            resp = await client.post("http://tormemrtxproto.tail0924dd.ts.net:11434/api/chat", json=payload)

        dur_page = time.time() - t_page_start
        data = resp.json()
        msg = data.get("message", {})
        content_text = (msg.get("content") or "").strip()
        thinking_text = (msg.get("thinking") or "").strip()

        # Safety Fallback: If content is empty but thinking contains Markdown tables/headers
        if not content_text and thinking_text:
            print(f"[Warning] Trang {p_num} content rỗng! Đang cứu vãn từ thinking...")
            # Check if there is markdown inside thinking
            import re
            m = re.search(r"(#\s+BỘ GIÁO DỤC|#\s+CỘNG HÒA|##\s+QUY ĐỊNH|\|[\s\S]+\|)", thinking_text)
            if m:
                content_text = thinking_text[m.start():].strip()

        print(f"Trang {p_num} hoàn thành trong {dur_page:.2f}s | content: {len(content_text)} chars | thinking: {len(thinking_text)} chars")
        extracted_pages.append({
            "page_number": p_num,
            "text": content_text,
            "duration": dur_page,
        })

    t_total = time.time() - t_total_start
    print(f"\n=== Tổng thời gian OCR cả 2 trang: {t_total:.2f}s ===")

    all_text = []
    for p in extracted_pages:
        all_text.append(f"<!-- Trang {p['page_number']} -->\n\n{p['text']}")
    joined_raw = "\n\n---\n\n".join(all_text)

    # Chunking test
    chunker = get_chunker("clause_based")
    chunks = chunker.chunk(joined_raw)
    print(f"Số chunks tạo ra với ClauseBasedChunker: {len(chunks)}")
    for idx, c in enumerate(chunks):
        print(f"  Chunk {idx+1} [section={c.section}, page={c.page_number}, tokens={c.token_count}]: {c.content[:80].replace(chr(10), ' ')}...")

    with open("scratch/optimized_ocr_output.md", "w", encoding="utf-8") as f:
        f.write(joined_raw)

if __name__ == "__main__":
    asyncio.run(run_optimized_ocr(r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"))
