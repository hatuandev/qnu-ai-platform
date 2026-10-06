import asyncio
import os
import sys
import time
import base64
import json
import pymupdf as fitz
import httpx

async def test_variation(name: str, dpi: int, prompt: str, options: dict):
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    doc = fitz.open(stream=content, filetype="pdf")
    page1 = doc[0]
    pix = page1.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("jpeg")
    doc.close()

    b64 = base64.b64encode(img_bytes).decode("utf-8")

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
        "options": options,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        resp = await client.post("http://tormemrtxproto.tail0924dd.ts.net:11434/api/chat", json=payload)
    
    elapsed = time.time() - t0
    data = resp.json()
    msg = data.get("message", {})
    content_text = msg.get("content", "")
    thinking_text = msg.get("thinking", "")

    result = {
        "name": name,
        "dpi": dpi,
        "image_size_kb": len(img_bytes) // 1024,
        "elapsed_s": round(elapsed, 2),
        "content_len": len(content_text),
        "thinking_len": len(thinking_text),
        "has_content": bool(content_text),
        "first_100_content": content_text[:100].replace("\n", " "),
    }
    print(f"[{name}] {elapsed:.1f}s | img: {result['image_size_kb']}KB | content: {len(content_text)} chars | think: {len(thinking_text)} chars")
    return result

async def main():
    # Test 1: Baseline DPI 150, prompt chuẩn không có layout_json
    p1 = (
        "Bạn là chuyên gia OCR tiếng Việt của Trường Đại học Quy Nhơn (QNU). "
        "Hãy bóc tách toàn bộ văn bản và bảng biểu của trang này sang Markdown chuẩn GFM tiếng Việt. "
        "Yêu cầu:\n"
        "- Giữ nguyên 100% nội dung, số hiệu, căn cứ pháp lý, bảng học phí.\n"
        "- Không dùng thẻ HTML (dùng thuần Markdown).\n"
        "- Xuất trực tiếp nội dung Markdown kết quả."
    )
    
    # Test 2: DPI 110, prompt chuẩn
    # Test 3: DPI 110, prompt có chỉ thị tắt suy nghĩ dài
    p3 = (
        "Bóc tách trang tài liệu hành chính này sang Markdown chuẩn GFM tiếng Việt. "
        "Xuất trực tiếp nội dung Markdown, không suy nghĩ hay giải thích thêm. "
        "Giữ nguyên toàn bộ văn bản, số hiệu và bảng biểu học phí."
    )

    results = []
    print("Starting tests...")
    
    res1 = await test_variation("DPI-150-Basic", dpi=150, prompt=p1, options={"temperature": 0.1, "num_predict": 4096})
    results.append(res1)

    res2 = await test_variation("DPI-110-Basic", dpi=110, prompt=p1, options={"temperature": 0.1, "num_predict": 4096})
    results.append(res2)

    res3 = await test_variation("DPI-110-FastPrompt", dpi=110, prompt=p3, options={"temperature": 0.1, "num_predict": 4096})
    results.append(res3)

    with open("scratch/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
