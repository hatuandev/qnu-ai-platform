import asyncio
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.assistants.models import AssistantModel

async def sync():
    async with AsyncSessionFactory() as db:
        print("=== 1. SYNCING KNOWLEDGE COLLECTIONS DATA_PROCESSING CONFIG ===")
        res = await db.execute(select(KnowledgeCollection))
        collections = res.scalars().all()
        for col in collections:
            meta = dict(col.collection_metadata or {})
            dp = meta.get("data_processing") or {}
            
            # Default to RTX 5090 BGE-M3 and Qwen3-VL 8B
            needs_update = False
            if not dp.get("embedding_model"):
                dp["embedding_model"] = "bge-m3:latest"
                dp["embedding_provider_id"] = "prov_rtx5090_ollama"
                dp["embedding_dimension"] = 1024
                needs_update = True
            
            if not dp.get("primary_ocr_model"):
                dp["ocr_mode"] = "combo"
                dp["primary_ocr_model"] = "qwen3-vl:8b"
                dp["primary_ocr_provider_id"] = "prov_rtx5090_ollama"
                dp["fallback_ocr_model"] = "gemini-3.1-flash-lite"
                dp["fallback_ocr_provider_id"] = "prov_gemini"
                dp["enable_ocr_rescue"] = True
                needs_update = True
            
            if needs_update or "data_processing" not in meta:
                meta["data_processing"] = dp
                col.collection_metadata = meta
                print(f"  + Updated collection '{col.name}' ({col.id}): Embedding={dp['embedding_model']}, Primary OCR={dp['primary_ocr_model']}")
            else:
                print(f"  * Collection '{col.name}' ({col.id}) already configured: Embedding={dp.get('embedding_model')}")

        print("\n=== 2. SYNCING ASSISTANTS RERANKER_POLICY CONFIG ===")
        res = await db.execute(select(AssistantModel))
        assistants = res.scalars().all()
        for ast in assistants:
            cfg = dict(ast.config or {})
            kp = dict(cfg.get("knowledge_policy") or {})
            rp = kp.get("reranker_policy") or {}
            
            if not rp or "enabled" not in rp:
                kp["reranker_policy"] = {
                    "enabled": True,
                    "model_name": "bge-reranker-base",
                    "top_k": 5,
                    "score_threshold": 0.4,
                }
                cfg["knowledge_policy"] = kp
                ast.config = cfg
                print(f"  + Updated assistant '{ast.name}' ({ast.code}): Reranker enabled (bge-reranker-base, top_k=5, score_threshold=0.4)")
            else:
                print(f"  * Assistant '{ast.name}' ({ast.code}) already has reranker: enabled={rp.get('enabled')}, model={rp.get('model_name')}")

        await db.commit()
        print("\n=== SYNC COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(sync())
