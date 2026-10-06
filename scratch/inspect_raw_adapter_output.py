import asyncio
import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pymupdf as fitz

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.ocr.adapters.openai_vision_adapter import QwenOCRAdapter

async def main():
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    adapter = QwenOCRAdapter(model_name="qwen3-vl:8b")
    print("Testing QwenOCRAdapter extraction on QD2139.pdf...")
    res = await adapter.extract(content, "QD2139.pdf")
    
    print("\n=== TOTAL PAGES ===", len(res.get("pages", [])))
    for p in res.get("pages", []):
        pnum = p["page_number"]
        txt = p["extracted_text"]
        blks = p.get("blocks", [])
        print(f"\n--- PAGE {pnum} (blocks: {len(blks)}) ---")
        for b in blks[:5]:
            print("  block:", b.get("type"), b.get("coordinates"), "snippet:", b.get("content_snippet", "")[:60])
        print("Text preview:")
        print(txt[:400])

if __name__ == "__main__":
    asyncio.run(main())
