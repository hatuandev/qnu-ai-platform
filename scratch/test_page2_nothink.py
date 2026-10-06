import asyncio
import os
import sys
import base64
import pymupdf as fitz
import httpx

async def test_page2():
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    doc = fitz.open(stream=content, filetype="pdf")
    page2 = doc[1]
    pix = page2.get_pixmap(dpi=110)
    img_bytes = pix.tobytes("jpeg")
    doc.close()

    b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = (
        "Bạn là chuyên gia OCR văn bản hành chính tiếng Việt của Trường Đại học Quy Nhơn (QNU). "
        "Hãy bóc tách toàn bộ nội dung của Trang 2 sang Markdown GFM tiếng Việt hoàn chỉnh.\n\n"
        "Quy tắc bắt buộc:\n"
        "1. Bảo toàn 100% nội dung chữ, bảng biểu, họ tên, chữ ký, con dấu, nơi nhận.\n"
        "2. Bảng biểu chuyển thành bảng Markdown hoàn chỉnh với đầy đủ các cột và các hàng tương ứng.\n"
        "3. Không dùng thẻ HTML thô. Chuẩn UTF-8 Unicode NFC."
    )

    url = "http://tormemrtxproto.tail0924dd.ts.net:11434/api/chat"
    payload = {
        "model": "qwen3-vl:8b",
        "messages": [
            {"role": "user", "content": prompt, "images": [b64]},
            {"role": "assistant", "content": "</think>\n"},
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": 4096,
        },
        "stream": False,
    }

    import time
    t0 = time.time()
    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
        r = await client.post(url, json=payload)
    dur = time.time() - t0
    
    msg = r.json().get("message", {})
    txt = msg.get("content", "")
    with open("scratch/nothink_quality_page2.md", "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"Page 2 done in {dur:.2f}s, Len: {len(txt)}")

if __name__ == "__main__":
    asyncio.run(test_page2())
