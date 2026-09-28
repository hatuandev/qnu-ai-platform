import asyncio
import json
from app.core.database import AsyncSessionFactory
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.service import rag_service
from app.modules.rag.schemas import AskRequest

async def main():
    async with AsyncSessionFactory() as db:
        query = "Theo Quyết định số 2327/QĐ-ĐHQN, trường Đại học Quy Nhơn đã bổ nhiệm ông Nguyễn Đức Tôn giữ chức vụ gì và thời hạn bổ nhiệm là bao lâu?"
        print("=== 1. RETRIEVE TEST ===")
        candidates = await hybrid_retriever.retrieve(
            db=db,
            collection_id="col_admissions",
            query=query,
            top_k=5,
            rerank_top_k=5,
        )
        print(f"Total candidates: {len(candidates)}")
        for c in candidates:
            print(f"- Doc: {c.document_id}, Chunk: {c.chunk_id}, Score: {c.rrf_score}")
            print(f"  Snippet: {c.content[:150]}...\n")
            
        print("=== 2. RAG ASK TEST ===")
        ask_req = AskRequest(
            question=query,
            collection_id="col_admissions",
            module_code="admissions",
            preferred_model_name="gemini-3.5-flash-lite",
            tenant_id="tenant_qnu",
        )
        res = await rag_service.ask(db, ask_req)
        print("Status:", res.status)
        print("Citations:", len(res.citations))
        for cite in res.citations:
            print("  Cite:", cite.source_id, cite.title, cite.quote[:80] if cite.quote else "")
        print("Answer:\n", res.answer)

if __name__ == '__main__':
    asyncio.run(main())
