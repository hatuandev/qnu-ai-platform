import asyncio
import os
import sys
import time
import base64
import json
import pymupdf as fitz
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.knowledge.chunker import get_chunker

async def main():
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    doc = fitz.open(stream=content, filetype="pdf")
    pages_count = len(doc)
    page_images = []
    for p_idx in range(pages_count):
        page = doc[p_idx]
        pix = page.get_pixmap(dpi=110)
        img_bytes = pix.tobytes("jpeg")
        page_images.append((p_idx + 1, img_bytes))
    doc.close()

    print(f"Loaded {pages_count} pages.")

    # Pure, clean, effective prompt that DOES NOT confuse the model
    clean_prompt = (
        "Bạn là chuyên gia OCR tài liệu tiếng Việt của Trường Đại học Quy Nhơn (QNU). "
        "Hãy bóc tách toàn bộ nội dung của trang tài liệu này sang định dạng Markdown chuẩn GFM tiếng Việt.\n\n"
        "Yêu cầu:\n"
        "- Giữ nguyên 100% nội dung chữ, số hiệu văn bản, ngày tháng, họ tên, căn cứ pháp lý, con dấu, chữ ký.\n"
        "- Mọi bảng biểu chuyển đổi thành bảng Markdown hoàn chỉnh với đầy đủ các cột và các hàng tương ứng.\n"
        "- Tuyệt đối không dùng thẻ HTML. Sử dụng thuần túy Markdown GFM.\n"
        "- Đảm bảo ký tự tiếng Việt chuẩn Unicode NFC."
    )

    extracted_pages = []
    t_start = time.time()

    for p_num, img_bytes in page_images:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        print(f"\n--- Đang xử lý Trang {p_num}/{pages_count} ---")
        t0 = time.time()

        payload = {
            "model": "qwen3-vl:8b",
            "messages": [
                {
                    "role": "user",
                    "content": clean_prompt,
                    "images": [b64],
                }
            ],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
            resp = await client.post("http://tormemrtxproto.tail0924dd.ts.net:11434/api/chat", json=payload)
        
        dur = time.time() - t0
        data = resp.json()
        msg = data.get("message", {})
        c = (msg.get("content") or "").strip()
        th = (msg.get("thinking") or "").strip()

        print(f"Trang {p_num} xong trong {dur:.2f}s | content: {len(c)} chars | thinking: {len(th)} chars")
        if c:
            print("Preview 200 chars:\n", c[:200].replace("\n", " "))
        else:
            print("[Warning] Content is empty!")
            print("Thinking preview:\n", th[:300].replace("\n", " "))

        extracted_pages.append({
            "page_number": p_num,
            "text": c,
            "duration": dur,
        })

    total_dur = time.time() - t_start
    print(f"\n=== TỔNG THỜI GIAN OCR: {total_dur:.2f}s ===")

    all_text = [f"<!-- Trang {p['page_number']} -->\n\n{p['text']}" for p in extracted_pages if p["text"]]
    joined = "\n\n---\n\n".join(all_text)

    chunker = get_chunker("clause_based")
    chunks = chunker.chunk(joined)
    print(f"Số chunks tạo ra: {len(chunks)}")
    for idx, ck in enumerate(chunks[:5]):
        print(f"Chunk {idx+1} (p={ck.page_number}): {ck.content[:100].replace(chr(10), ' ')}")

    with open("scratch/clean_prompt_full_output.md", "w", encoding="utf-8") as f:
        f.write(joined)

if __name__ == "__main__":
    asyncio.run(main())
