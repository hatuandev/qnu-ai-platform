import asyncio
import os
import sys
import time
import base64
import json
import pymupdf as fitz
import httpx

async def main():
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    doc = fitz.open(stream=content, filetype="pdf")
    page1 = doc[0]
    pix = page1.get_pixmap(dpi=110)
    img_bytes = pix.tobytes("jpeg")
    doc.close()

    b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = (
        "Bạn là chuyên gia OCR văn bản hành chính tiếng Việt của Trường Đại học Quy Nhơn (QNU). "
        "Hãy bóc tách toàn bộ nội dung của trang tài liệu này sang Markdown GFM tiếng Việt hoàn chỉnh.\n"
        "Quy tắc bắt buộc:\n"
        "1. Bảo toàn 100% nội dung chữ, số hiệu văn bản, ngày tháng, họ tên, căn cứ pháp lý, con dấu, chữ ký.\n"
        "2. Không dùng thẻ HTML thô. Mọi bảng biểu chuyển thành bảng Markdown hoàn chỉnh '|:---|:---|'.\n"
        "3. Giữ nguyên vẹn toàn bộ các hàng và cột bảng học phí/chỉ tiêu.\n"
        "4. Đảm bảo toàn bộ ký tự tiếng Việt chuẩn Unicode NFC."
    )

    t0 = time.time()
    payload = {
        "model": "qwen3-vl:8b",
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [b64],
            }
        ],
        "think": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 4096,
        },
        "stream": False,
    }

    print("Sending request with think: False...")
    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        resp = await client.post("http://tormemrtxproto.tail0924dd.ts.net:11434/api/chat", json=payload)
    
    dur = time.time() - t0
    data = resp.json()
    msg = data.get("message", {})
    content = msg.get("content", "")
    thinking = msg.get("thinking", "")

    print(f"\n--- Result with think=False ---")
    print(f"Status: {resp.status_code}")
    print(f"Elapsed: {dur:.2f}s")
    print(f"Content length: {len(content)}")
    print(f"Thinking length: {len(thinking)}")
    print(f"Content preview:\n{content[:500]}")

    with open("scratch/think_false_result.txt", "w", encoding="utf-8") as f:
        f.write(f"Duration: {dur:.2f}s\nContent len: {len(content)}\nThinking len: {len(thinking)}\n\n")
        f.write(content)

if __name__ == "__main__":
    asyncio.run(main())
