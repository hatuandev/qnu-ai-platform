import asyncio
import os
import sys
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
    pix = page1.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("jpeg")
    doc.close()

    b64 = base64.b64encode(img_bytes).decode("utf-8")

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        resp = await client.post(
            "http://tormemrtxproto.tail0924dd.ts.net:11434/api/chat",
            json={
                "model": "qwen3-vl:8b",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hãy OCR và bóc tách toàn bộ nội dung của trang tài liệu này sang định dạng Markdown chuẩn GFM tiếng Việt. Bảo toàn chính xác 100% các bảng biểu học phí, số hiệu văn bản và căn cứ pháp lý.",
                        "images": [b64],
                    }
                ],
                "stream": False,
            }
        )

    data = resp.json()
    with open("scratch/simple_prompt_resp.json", "w", encoding="utf-8") as f:
        json.dump({
            "message_keys": list(data.get("message", {}).keys()),
            "content_len": len(data.get("message", {}).get("content", "")),
            "content": data.get("message", {}).get("content", ""),
            "thinking_len": len(data.get("message", {}).get("thinking", "")),
            "thinking_sample": data.get("message", {}).get("thinking", "")[:300],
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
