import asyncio

from app.core.database import AsyncSessionFactory
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.service import build_generic_system_instruction


async def main():
    async with AsyncSessionFactory() as db:
        query = "Theo Quyết định số 2327/QĐ-ĐHQN, trường Đại học Quy Nhơn đã bổ nhiệm ông Nguyễn Đức Tôn giữ chức vụ gì và thời hạn bổ nhiệm là bao lâu?"
        candidates = await hybrid_retriever.retrieve(
            db=db,
            collection_id="col_admissions",
            query=query,
            top_k=3,
            rerank_top_k=3,
        )
        context_texts = [c.content for c in candidates]
        system_instruction = build_generic_system_instruction("admissions", None)
        user_content = f"Câu hỏi của người dùng: {query}\n\nTÀI LIỆU TRÍCH XUẤT TỪ KHO TRI THỨC:\n"
        for i, text in enumerate(context_texts, 1):
            user_content += f"--- Đoạn trích [{i}] ---\n{text}\n\n"
            
        messages = [
            ChatMessage(role="system", content=system_instruction),
            ChatMessage(role="user", content=user_content)
        ]
        
        req = LLMGenerateRequest(
            messages=messages,
            temperature=0.2,
            max_tokens=1000,
            preferred_model_name="gemini-3.5-flash-lite",
        )
        res = await modelops_service.generate(db, req)
        print("=== LLM RAW OUTPUT ===")
        print(res.content)

if __name__ == '__main__':
    asyncio.run(main())
