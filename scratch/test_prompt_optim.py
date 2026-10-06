import asyncio
import os
import sys
import time
import base64
import json
import pymupdf as fitz
import httpx

async def test_prompt(name: str, messages: list[dict], options: dict | None = None):
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    doc = fitz.open(stream=content, filetype="pdf")
    page1 = doc[0]
    pix = page1.get_pixmap(dpi=110)
    img_bytes = pix.tobytes("jpeg")
    doc.close()

    b64 = base64.b64encode(img_bytes).decode("utf-8")

    # inject image to user message
    for m in messages:
        if m["role"] == "user":
            m["images"] = [b64]

    t0 = time.time()
    payload = {
        "model": "qwen3-vl:8b",
        "messages": messages,
        "stream": False,
    }
    if options:
        payload["options"] = options

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        resp = await client.post("http://tormemrtxproto.tail0924dd.ts.net:11434/api/chat", json=payload)
    
    elapsed = time.time() - t0
    data = resp.json()
    msg = data.get("message", {})
    c = msg.get("content", "")
    th = msg.get("thinking", "")
    done_reason = data.get("done_reason")
    eval_count = data.get("eval_count")

    print(f"[{name}] {elapsed:.1f}s | content: {len(c)} | think: {len(th)} | done_reason: {done_reason} | eval_count: {eval_count}")
    return {"name": name, "elapsed": elapsed, "c_len": len(c), "th_len": len(th), "c": c[:200], "th": th[:200]}

async def main():
    # Test A: system prompt forbidding thoughts
    resA = await test_prompt(
        "SysPrompt-NoThink",
        [
            {"role": "system", "content": "You are a professional OCR engine. You must output ONLY the extracted Markdown text directly. Never explain, never analyze, never output reasoning or thinking."},
            {"role": "user", "content": "Chuyển toàn bộ hình ảnh văn bản hành chính này thành Markdown GFM tiếng Việt chính xác 100% các bảng biểu."},
        ]
    )

    # Test B: /no_think tag or English prompt
    resB = await test_prompt(
        "Direct-Transcription",
        [
            {"role": "user", "content": "Transcribe the document in the image into Vietnamese Markdown text exactly as shown. Do not output anything else."},
        ]
    )

    with open("scratch/prompt_comparison.json", "w", encoding="utf-8") as f:
        json.dump([resA, resB], f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
