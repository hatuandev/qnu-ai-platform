import asyncio
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.ocr.adapters.openai_vision_adapter import QwenOCRAdapter
from app.modules.knowledge.chunker import get_chunker

async def main():
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    adapter = QwenOCRAdapter(model_name="qwen3-vl:8b")
    print("Testing QwenOCRAdapter with updated prompt and resolution...")

    t0 = time.time()
    result = await adapter.extract(content, "QD2139.pdf")
    t1 = time.time()

    print(f"\n=== OCR Extraction Finished in {t1 - t0:.2f}s ===")
    print(f"Total pages: {result.get('total_pages')}")
    print(f"Engine used: {result.get('engine_used')}")
    raw_text = result.get("raw_text") or ""
    print(f"Raw text length: {len(raw_text)}")
    print(f"Confidence: {result.get('overall_confidence')}")

    for p in result.get("pages", []):
        print(f"\n--- Trang {p.get('page_number')} ---")
        print(f"  Word count: {p.get('word_count')}")
        print(f"  Line count: {p.get('line_count')}")
        print(f"  Has tables: {p.get('has_tables')}")
        print(f"  Blocks count: {len(p.get('blocks', []))}")
        txt = p.get("extracted_text") or ""
        print(f"  Text preview:\n{txt[:250].replace(chr(10), ' ')}")

    chunker = get_chunker("clause_based")
    chunks = chunker.chunk(raw_text)
    print(f"\n=== CHUNKING RESULT ===")
    print(f"Total chunks created: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i+1} [page={c.page_number}, tokens={c.token_count}]: {c.content[:80].replace(chr(10), ' ')}")

if __name__ == "__main__":
    asyncio.run(main())
