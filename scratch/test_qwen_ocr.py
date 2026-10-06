import asyncio
import os
import sys
import time
import pymupdf as fitz
import httpx

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.ocr.adapters.openai_vision_adapter import QwenOCRAdapter

async def main():
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    with open(pdf_path, "rb") as f:
        content = f.read()

    adapter = QwenOCRAdapter(model_name="qwen3-vl:8b")
    print(f"Adapter base_url: {adapter._base_url}")
    print(f"Adapter is_ollama: {adapter._is_ollama}")
    
    # Test checking Ollama tags
    async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
        try:
            resp = await client.get(f"{adapter._base_url}/api/tags")
            print("Ollama models available:", [m["name"] for m in resp.json().get("models", [])])
        except Exception as e:
            print("Failed to reach Ollama tags:", e)
            return

    # Let's extract just page 1 content to test raw output
    doc = fitz.open(stream=content, filetype="pdf")
    page1 = doc[0]
    pix = page1.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("jpeg")
    doc.close()
    
    print(f"Page 1 rendered image size: {len(img_bytes)} bytes, width={pix.width}, height={pix.height}")

    t0 = time.time()
    # Let's inspect raw message response directly for page 1
    import base64
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    async with httpx.AsyncClient(timeout=180.0) as client:
        ollama_resp = await client.post(
            f"{adapter._base_url}/api/chat",
            json={
                "model": "qwen3-vl:8b",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hãy OCR và bóc tách trang này sang Markdown tiếng Việt đầy đủ bảng biểu.",
                        "images": [b64],
                    }
                ],
                "stream": False,
            }
        )
        print("Simple prompt Ollama status:", ollama_resp.status_code)
        ollama_data = ollama_resp.json()
        simple_content = ollama_data.get("message", {}).get("content", "")
        print(f"Simple prompt time: {time.time() - t0:.2f}s, length: {len(simple_content)}")
        print("Simple content preview:\n", simple_content[:400])

    # Now run actual adapter extract
    t_start = time.time()
    res = await adapter.extract(content, "QD2139.pdf")
    t1 = time.time()
    
    print(f"\n--- Total OCR time: {t1 - t0:.2f}s ---")
    print("Total pages:", res.get("total_pages"))
    print("Raw text length:", len(res.get("raw_text", "")))
    print("Raw text sample (first 500 chars):")
    print(repr(res.get("raw_text", "")[:500]))
    for idx, p in enumerate(res.get("pages", [])):
        print(f"\nPage {p.get('page_number')}:")
        print(f"  extracted_text length: {len(p.get('extracted_text', ''))}")
        print(f"  word_count: {p.get('word_count')}")
        print(f"  line_count: {p.get('line_count')}")
        print(f"  blocks count: {len(p.get('blocks', []))}")
        print(f"  Sample text:\n{p.get('extracted_text', '')[:300]}")

if __name__ == "__main__":
    asyncio.run(main())
