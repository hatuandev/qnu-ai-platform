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

async def test_bypass():
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    doc = fitz.open(stream=content, filetype="pdf")
    page1 = doc[0]
    pix = page1.get_pixmap(dpi=110)
    img_bytes = pix.tobytes("jpeg")
    doc.close()

    b64 = base64.b64encode(img_bytes).decode("utf-8")

    url = "http://tormemrtxproto.tail0924dd.ts.net:11434/api/chat"

    # Test 1: prefill assistant with empty think
    t0 = time.time()
    payload1 = {
        "model": "qwen3-vl:8b",
        "messages": [
            {"role": "user", "content": "OCR toàn bộ trang sang Markdown tiếng Việt đầy đủ bảng biểu.", "images": [b64]},
            {"role": "assistant", "content": "</think>"},
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        r1 = await client.post(url, json=payload1)
    
    d1 = r1.json()
    dur1 = time.time() - t0
    m1 = d1.get("message", {})
    print(f"Test 1 (Prefill </think>): {dur1:.2f}s | content: {len(m1.get('content', ''))} | think: {len(m1.get('thinking', ''))}")
    if m1.get('content'):
        print("Content 1 sample:\n", m1.get('content')[:200].replace("\n", " "))

    # Test 2: via /api/generate with prompt prefix
    t0 = time.time()
    payload2 = {
        "model": "qwen3-vl:8b",
        "prompt": "OCR toàn bộ trang này sang Markdown tiếng Việt đầy đủ bảng biểu.\n</think>\n",
        "images": [b64],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        r2 = await client.post("http://tormemrtxproto.tail0924dd.ts.net:11434/api/generate", json=payload2)
    
    d2 = r2.json()
    dur2 = time.time() - t0
    resp2 = d2.get("response", "")
    th2 = d2.get("thinking", "")
    print(f"\nTest 2 (/api/generate with </think>): {dur2:.2f}s | resp: {len(resp2)} | think: {len(th2)}")
    if resp2:
        print("Resp 2 sample:\n", resp2[:200].replace("\n", " "))

if __name__ == "__main__":
    asyncio.run(test_bypass())
