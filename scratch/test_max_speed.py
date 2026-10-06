import asyncio
import os
import sys
import time
import base64
import pymupdf as fitz
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

async def ocr_single_page(client: httpx.AsyncClient, p_num: int, b64_data: str, url: str) -> dict:
    prompt = (
        f"Hãy bóc tách toàn bộ văn bản và bảng biểu Trang {p_num} sang Markdown GFM tiếng Việt chuẩn xác 100%. "
        "Không dùng thẻ HTML thô."
    )
    payload = {
        "model": "qwen3-vl:8b",
        "messages": [
            {"role": "user", "content": prompt, "images": [b64_data]},
            {"role": "assistant", "content": "</think>\n"},
        ],
        "options": {
            "temperature": 0.0,      # Greedy decoding: nhanh nhất, không tính xác suất ngẫu nhiên
            "num_predict": 2048,     # Đủ cho 1 trang A4, tiết kiệm buffer
            "top_k": 1,
            "top_p": 1.0,
        },
        "keep_alive": -1,            # Giữ model thường trực 100% trong VRAM RTX 5090
        "stream": False,
    }
    t0 = time.time()
    resp = await client.post(url, json=payload)
    dur = time.time() - t0
    data = resp.json()
    msg = data.get("message", {})
    txt = msg.get("content", "").strip()
    print(f"Trang {p_num} hoàn thành trong {dur:.2f}s | chars: {len(txt)}")
    return {"page_number": p_num, "text": txt, "duration": dur}

async def main():
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    doc = fitz.open(stream=content, filetype="pdf")
    pages_count = len(doc)
    page_b64s = []
    for p_idx in range(pages_count):
        page = doc[p_idx]
        # DPI 100, JPEG quality 85: siêu nhẹ, chữ vẫn cực kỳ sắc nét
        pix = page.get_pixmap(dpi=100)
        img_bytes = pix.tobytes("jpeg", jpg_quality=85)
        page_b64s.append((p_idx + 1, base64.b64encode(img_bytes).decode("utf-8"), len(img_bytes)//1024))
    doc.close()

    print(f"Tài liệu {pages_count} trang, kích thước ảnh: {[kb for _, _, kb in page_b64s]} KB")

    url = "http://tormemrtxproto.tail0924dd.ts.net:11434/api/chat"
    t_start = time.time()

    # Chạy song song (Parallel Concurrent Pages) trên GPU RTX 5090
    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
        tasks = [ocr_single_page(client, p_num, b64, url) for p_num, b64, _ in page_b64s]
        results = await asyncio.gather(*tasks)

    t_total = time.time() - t_start
    print(f"\n=== TỔNG THỜI GIAN OCR SONG SONG CẢ 2 TRANG: {t_total:.2f}s ===")
    for r in sorted(results, key=lambda x: x["page_number"]):
        print(f"Trang {r['page_number']}: {len(r['text'])} ký tự, preview:\n{r['text'][:150].replace(chr(10), ' ')}")

if __name__ == "__main__":
    asyncio.run(main())
